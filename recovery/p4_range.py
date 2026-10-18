"""Index one inclusive nonce range by fully paged inclusion-block windows.

The module is not executed. SQLite and raw GraphQL bodies stay under data/raw/.
A range with a missing nonce or two assignment ids is not marked complete.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from recovery.assignments import (
    PROCESS_ID,
    SPAWN_BLOCK,
    TAIL_INCLUSION_BLOCK,
    TAIL_NONCE,
    fetch_block_window,
    fetch_exact_nonces,
    merge_assignments,
    sha256_bytes,
)
from recovery.coverage import coverage_report, window_passed_end
from recovery.gql import DEFAULT_ENDPOINT, post_graphql
from recovery.hashchain import check_links

ROOT = Path(__file__).resolve().parents[1]
P3_NONCE0 = "o6ia7Yi1ijVV0lXM75qK1DM2Alhk4JcdFOd6jnq2pTY"
P1_NONCE2 = "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    with partial.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignment (
            nonce INTEGER NOT NULL,
            epoch TEXT NOT NULL,
            assignment_id TEXT NOT NULL PRIMARY KEY,
            message_id TEXT NOT NULL,
            timestamp_ms TEXT NOT NULL,
            assignment_block_height TEXT,
            inclusion_height INTEGER,
            inclusion_timestamp INTEGER,
            hash_chain TEXT NOT NULL,
            source_file TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS assignment_nonce ON assignment(nonce)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cursor (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            next_height INTEGER NOT NULL,
            windows INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    return conn


def insert_rows(conn: sqlite3.Connection, rows, source_file: str) -> int:
    added = 0
    for row in rows:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO assignment (
                nonce, epoch, assignment_id, message_id, timestamp_ms,
                assignment_block_height, inclusion_height, inclusion_timestamp,
                hash_chain, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.nonce, row.epoch, row.assignment_id, row.message_id, row.timestamp_ms,
                row.assignment_block_height, row.inclusion_height, row.inclusion_timestamp,
                row.hash_chain, source_file,
            ),
        )
        added += cur.rowcount
    conn.commit()
    return added


def nonce_ids(conn: sqlite3.Connection) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}
    for nonce, assignment_id in conn.execute(
        "SELECT nonce, assignment_id FROM assignment ORDER BY nonce, assignment_id"
    ):
        grouped.setdefault(int(nonce), []).append(assignment_id)
    return grouped


def load_range_rows(conn: sqlite3.Connection, start: int, end: int):
    from recovery.assignments import Assignment
    rows = []
    for record in conn.execute(
        """
        SELECT assignment_id, nonce, epoch, message_id, timestamp_ms, hash_chain,
               assignment_block_height, inclusion_height, inclusion_timestamp
        FROM assignment
        WHERE nonce BETWEEN ? AND ?
        ORDER BY nonce, assignment_id
        """,
        (start, end),
    ):
        rows.append(Assignment(
            assignment_id=record[0],
            nonce=record[1],
            epoch=record[2],
            message_id=record[3],
            timestamp_ms=record[4],
            hash_chain=record[5],
            assignment_block_height=record[6],
            inclusion_height=record[7],
            inclusion_timestamp=record[8],
            tags={},
        ))
    return rows


def copy_nonce_range(source: sqlite3.Connection, dest: sqlite3.Connection, start: int, end: int) -> int:
    """Copy one assignment row per nonce. Two ids for one nonce are not collapsed."""
    rows = source.execute(
        """
        SELECT nonce, epoch, assignment_id, message_id, timestamp_ms,
               assignment_block_height, inclusion_height, inclusion_timestamp,
               hash_chain, source_file
        FROM assignment
        WHERE nonce BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchall()
    dest.executemany(
        """
        INSERT OR IGNORE INTO assignment (
            nonce, epoch, assignment_id, message_id, timestamp_ms,
            assignment_block_height, inclusion_height, inclusion_timestamp,
            hash_chain, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    dest.commit()
    return len(rows)


def scan(
    start: int = 0,
    end: int = 49999,
    *,
    max_windows: int = 4000,
    resume_run_id: str | None = None,
    start_height: int | None = None,
    seed_db: str | None = None,
) -> dict:
    if start < 0 or end > TAIL_NONCE or end < start:
        raise ValueError("range outside the frozen tail")
    run_id = resume_run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-p4-{start}-{end}"
    )
    raw_dir = ROOT / "data" / "raw" / "p4" / f"{start}-{end}" / run_id
    evidence_dir = ROOT / "evidence" / "p4" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    db_path = raw_dir / "assignments.sqlite"
    conn = open_db(db_path)
    row = conn.execute("SELECT next_height, windows FROM cursor WHERE id = 1").fetchone()
    if row is None and seed_db:
        source = sqlite3.connect(f"file:{seed_db}?mode=ro", uri=True)
        copied = copy_nonce_range(source, conn, start, end)
        source.close()
        print(f"seeded {copied} rows from {seed_db}", flush=True)
    height = int(row[0]) if row else (start_height if start_height is not None else SPAWN_BLOCK)
    windows_done = int(row[1]) if row else 0
    width = 40
    pages_path = raw_dir / "pages.json"
    files: list[dict] = []
    if pages_path.exists():
        files = json.loads(pages_path.read_text())
    else:
        for path in sorted(raw_dir.glob("*.body")):
            body = path.read_bytes()
            files.append({
                "path": str(path.relative_to(ROOT)),
                "bytes": len(body),
                "sha256": sha256_bytes(body),
                "http_status": None,
                "elapsed_ms": None,
                "attempt": None,
                "error": None,
                "request": None,
                "note": "hashed on resume; request metadata was not reloaded",
            })
    page_n = len(files)
    stopped = None
    print(f"scan {start}..{end} from height {height} run {run_id}", flush=True)

    def save_page(kind: str, request: dict, response) -> str:
        nonlocal page_n
        page_n += 1
        body_path = raw_dir / f"{page_n:05d}-{kind}.body"
        atomic_write(body_path, response.body or b"")
        record = {
            "path": str(body_path.relative_to(ROOT)),
            "bytes": len(response.body or b""),
            "sha256": sha256_bytes(response.body or b""),
            "http_status": response.http_status,
            "elapsed_ms": response.elapsed_ms,
            "attempt": response.attempt,
            "error": response.error,
            "request": request,
        }
        files.append(record)
        return record["path"]

    def post_factory(kind: str):
        def post(query, variables, endpoint=DEFAULT_ENDPOINT):
            response = post_graphql(query, variables, endpoint=endpoint)
            save_page(kind, {"variables": variables}, response)
            return response
        return post

    while height <= TAIL_INCLUSION_BLOCK and windows_done < max_windows:
        window_max = min(TAIL_INCLUSION_BLOCK, height + width - 1)
        window = fetch_block_window(
            height, window_max, page_size=100, max_pages=25,
            post=post_factory(f"h{height}"),
        )
        if not window.closed:
            if width > 10:
                width = max(10, width // 2)
                print(f"shrink width to {width} at {height}: {window.error}", flush=True)
                continue
            stopped = {
                "reason": "block_window_not_closed",
                "height": height,
                "width": width,
                "error": window.error,
            }
            break
        source = f"{run_id}:{height}-{window_max}"
        added = insert_rows(conn, merge_assignments(window.rows), source)
        windows_done += 1
        past_end = window_passed_end(window.rows, height, window_max, end)
        print(
            f"height {height}-{window_max} rows {len(window.rows)} added {added} "
            f"width {width} pages {len(window.pages)} past_end {past_end}",
            flush=True,
        )
        height = window_max + 1
        conn.execute(
            "INSERT INTO cursor (id, next_height, windows, updated_at) VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET next_height=excluded.next_height, windows=excluded.windows, updated_at=excluded.updated_at",
            (height, windows_done, utc_now()),
        )
        conn.commit()
        if past_end:
            stopped = {"reason": "window_min_nonce_past_range_end", "next_height": height}
            break
        if not window.rows and width < 640:
            width *= 2
        elif len(window.rows) < 50 and width < 160:
            width *= 2
        elif len(window.rows) > 500 and width > 10:
            width = max(10, width // 2)
        atomic_write(pages_path, json.dumps(files).encode("utf-8"))
    if stopped is None and windows_done >= max_windows:
        stopped = {"reason": "window_budget", "next_height": height, "windows": windows_done}
    if stopped is None and height > TAIL_INCLUSION_BLOCK:
        stopped = {"reason": "reached_frozen_tail_block", "next_height": height}

    ids = nonce_ids(conn)
    report = coverage_report(start, end, ids)
    gap_fill = []
    if report["missing_count"] and report["missing_count"] <= 100 and not report["conflict_count"]:
        missing = []
        for lo, hi in report["missing_ranges"]:
            missing.extend(range(lo, hi + 1))
        for offset in range(0, len(missing), 5):
            batch = missing[offset:offset + 5]
            fetched = fetch_exact_nonces(batch, post=post_factory("gap"))
            gap_fill.append({
                "nonces": batch,
                "closed": fetched.closed,
                "error": fetched.error,
                "rows": len(fetched.rows),
            })
            if fetched.closed:
                insert_rows(conn, merge_assignments(fetched.rows), f"{run_id}:gap")
        ids = nonce_ids(conn)
        report = coverage_report(start, end, ids)

    identity = {
        "nonce_0": ids.get(0),
        "nonce_0_matches_p3": ids.get(0) == [P3_NONCE0] if 0 in range(start, end + 1) else None,
        "nonce_2": ids.get(2),
        "nonce_2_matches_p1": ids.get(2) == [P1_NONCE2] if 2 in range(start, end + 1) else None,
    }
    if identity["nonce_0_matches_p3"] is False or identity["nonce_2_matches_p1"] is False:
        report["complete"] = False
        report["identity_conflict"] = True

    chain = {"verified": False, "links_checked": 0, "links_matched": 0, "links_mismatched": None}
    if report["unique_count"]:
        chain = check_links(load_range_rows(conn, start, end))
        # A hash-chain mismatch means this range is not a clean schedule, even
        # when every nonce has one id. Do not promote it to complete.
        if not chain["verified"]:
            report["complete"] = False

    conn.execute("PRAGMA wal_checkpoint(FULL)")
    conn.commit()
    db_bytes = db_path.stat().st_size
    db_hash = sha256_bytes(db_path.read_bytes())
    manifest = {
        "run_id": run_id,
        "phase": "P4",
        "process_id": PROCESS_ID,
        "executed_module": False,
        "range_inclusive": [start, end],
        "endpoint": DEFAULT_ENDPOINT,
        "started_height": SPAWN_BLOCK,
        "stopped": stopped,
        "windows": windows_done,
        "coverage": report,
        "identity": identity,
        "hash_chain": {
            "verified": chain["verified"],
            "links_checked": chain["links_checked"],
            "links_matched": chain["links_matched"],
            "links_mismatched": chain["links_mismatched"],
            "mismatch_sample": chain.get("mismatch_sample", [])[:5],
        },
        "gap_fill": gap_fill,
        "sqlite": {
            "path": str(db_path.relative_to(ROOT)),
            "bytes": db_bytes,
            "sha256": db_hash,
            "committed": False,
        },
        "raw_page_count": len(files),
        "raw_pages": [
            {key: item[key] for key in ("path", "bytes", "sha256", "http_status", "elapsed_ms", "error")}
            for item in files
        ],
        "finished_at": utc_now(),
        "complete": report["complete"],
        "rebuild": "Re-walk inclusion heights from block 1505290 with the P3 block-window query until the window's minimum nonce exceeds the range end, then set-difference the integer nonces. Do not treat row count as coverage.",
    }
    # Full page hash list is local; the committed manifest keeps the count and
    # the sqlite hash. A sibling file under data/raw lists every page.
    atomic_write(raw_dir / "pages.json", json.dumps(files).encode("utf-8"))
    atomic_write(evidence_dir / "range-manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    atomic_write(evidence_dir / "gaps.json", json.dumps({
        "run_id": run_id,
        "range_inclusive": [start, end],
        "missing_count": report["missing_count"],
        "missing_ranges": report["missing_ranges"],
        "status": "no_gap" if report["missing_count"] == 0 else "unresolved",
        "note": "A gateway miss is not proof the nonce was never published.",
    }, indent=2, sort_keys=True).encode() + b"\n")
    atomic_write(evidence_dir / "conflicts.json", json.dumps({
        "run_id": run_id,
        "range_inclusive": [start, end],
        "conflict_count": report["conflict_count"],
        "conflicts": report["conflicts"],
        "identity": identity,
    }, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({
        "run_id": run_id,
        "complete": report["complete"],
        "unique": report["unique_count"],
        "missing": report["missing_count"],
        "conflicts": report["conflict_count"],
        "hash_verified": chain["verified"],
        "links": chain["links_checked"],
        "stopped": stopped,
    }, indent=2), flush=True)
    conn.close()
    return manifest


def write_scanned_range_evidence(run_id: str, start: int, end: int, gap_attempts: dict) -> dict:
    """Write the manifest for a scan that already stopped. Does not query the gateway."""
    raw_dir = ROOT / "data" / "raw" / "p4" / f"{start}-{end}" / run_id
    evidence_dir = ROOT / "evidence" / "p4" / run_id
    db_path = raw_dir / "assignments.sqlite"
    conn = open_db(db_path)
    conn.execute("PRAGMA wal_checkpoint(FULL)")
    conn.commit()
    ids = nonce_ids(conn)
    report = coverage_report(start, end, ids)
    identity = {
        "nonce_0": ids.get(0),
        "nonce_0_matches_p3": ids.get(0) == [P3_NONCE0],
        "nonce_2": ids.get(2),
        "nonce_2_matches_p1": ids.get(2) == [P1_NONCE2],
    }
    chain = check_links(load_range_rows(conn, start, end))
    skipped = chain["skipped_because_previous_nonce_absent"]
    complete = bool(report["complete"] and chain["verified"] and not skipped and identity["nonce_0_matches_p3"] and identity["nonce_2_matches_p1"])
    db_hash = sha256_bytes(db_path.read_bytes())
    pages_path = raw_dir / "pages.json"
    pages_meta = None
    if pages_path.exists():
        page_bytes = pages_path.read_bytes()
        pages_meta = {
            "path": str(pages_path.relative_to(ROOT)),
            "bytes": len(page_bytes),
            "sha256": sha256_bytes(page_bytes),
            "committed": False,
        }
    cursor = conn.execute("SELECT next_height, windows, updated_at FROM cursor WHERE id = 1").fetchone()
    conn.close()
    manifest = {
        "run_id": run_id,
        "phase": "P4",
        "process_id": PROCESS_ID,
        "executed_module": False,
        "range_inclusive": [start, end],
        "endpoint": DEFAULT_ENDPOINT,
        "complete": complete,
        "coverage": report,
        "identity": identity,
        "hash_chain": {
            "verified_on_present_consecutive_pairs": chain["verified"],
            "links_checked": chain["links_checked"],
            "links_matched": chain["links_matched"],
            "links_mismatched": chain["links_mismatched"],
            "skipped_because_previous_nonce_absent": skipped,
            "mismatch_sample": chain.get("mismatch_sample", [])[:5],
            "note": "A matching pair does not cross the unresolved hole. The range is not fully chained.",
        },
        "gap_attempts": gap_attempts,
        "cursor": {
            "next_height": cursor[0] if cursor else None,
            "windows": cursor[1] if cursor else None,
            "updated_at": cursor[2] if cursor else None,
        },
        "sqlite": {
            "path": str(db_path.relative_to(ROOT)),
            "bytes": db_path.stat().st_size,
            "sha256": db_hash,
            "committed": False,
        },
        "pages_json": pages_meta,
        "finished_at": utc_now(),
        "rebuild": "Forward inclusion-block scan from 1505290, then exact Nonce queries for the set difference. Do not treat row count as coverage.",
    }
    atomic_write(evidence_dir / "range-manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    atomic_write(evidence_dir / "gaps.json", json.dumps({
        "run_id": run_id,
        "range_inclusive": [start, end],
        "missing_count": report["missing_count"],
        "missing_ranges": report["missing_ranges"],
        "status": "no_gap" if report["missing_count"] == 0 else "unresolved",
        "classification": "not_indexed_by_gateway_after_exact_and_block_window" if report["missing_count"] else "no_gap",
        "note": "A closed empty gateway response is not proof the nonce was never published.",
    }, indent=2, sort_keys=True).encode() + b"\n")
    atomic_write(evidence_dir / "conflicts.json", json.dumps({
        "run_id": run_id,
        "range_inclusive": [start, end],
        "conflict_count": report["conflict_count"],
        "conflicts": report["conflicts"],
        "identity": identity,
    }, indent=2, sort_keys=True).encode() + b"\n")
    failure = {
        "run_id": run_id,
        "phase": "P4",
        "complete": False,
        "last_good_point": {
            "contiguous_from_nonce_0_through": report["missing_ranges"][0][0] - 1 if report["missing_ranges"] else end,
            "range_end_seen": end in ids,
            "cursor_next_height": cursor[0] if cursor else None,
        },
        "missing_ranges": report["missing_ranges"],
        "gap_attempts": gap_attempts,
        "recovery_condition": "Obtain assignment bytes for epoch 0 nonces 5770..5793 for this process from a source other than the arweave.net GraphQL index, then rerun the set difference and the hash-chain link across 5769..5794. Do not start nonce 50000 replay while this hole is open.",
    }
    atomic_write(evidence_dir / "failure.json", json.dumps(failure, indent=2, sort_keys=True).encode() + b"\n")
    stop = "\n".join([
        "# STOP",
        "",
        "goal_complete=false",
        "",
        "P4 range 0..49999 is not complete.",
        "Unresolved nonces: 5770..5793 inclusive (24 nonces).",
        "Exact Nonce queries, with and without epoch 0, and epoch 1 for nonce 5770, returned no assignment.",
        "Closed block window 1543160..1543170 contains nonces 5698..5841 except that hole.",
        "Neighbors 5769 (block 1543163) and 5794 (block 1543166) are present.",
        "Nonce 0 matches the P3 assignment. Nonce 2 matches P1. Nonce 49999 was indexed.",
        "The module was not executed.",
        "",
        "Last cursor: inclusion height next is the scanned cursor in range-manifest.json.",
        "SQLite is local only: data/raw/p4/0-49999/20261016T175757Z-p4-0-49999/assignments.sqlite",
        "",
        "Recovery: bring in those 24 assignments from outside this GraphQL index, then recheck the hash chain from 5769 to 5794.",
        "Do not mark this range complete. Do not replay past the hole. Do not publish a claim list.",
        "",
    ])
    atomic_write(evidence_dir / "STOP.md", stop.encode())
    atomic_write(ROOT / "STOP.md", stop.encode())
    print(json.dumps({
        "complete": complete,
        "unique": report["unique_count"],
        "missing": report["missing_count"],
        "missing_ranges": report["missing_ranges"],
        "conflicts": report["conflict_count"],
        "hash_pairs_matched": chain["links_matched"],
        "hash_pairs_checked": chain["links_checked"],
        "hash_mismatched": chain["links_mismatched"],
        "skipped": skipped[:10],
        "identity": identity,
    }, indent=2))
    return manifest


if __name__ == "__main__":
    scan(0, 49999)

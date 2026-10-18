"""P3 sample: three nonce windows and a recoverable block-window index method.

Does not execute the module. Does not claim full nonce coverage.
Raw GraphQL bodies go under data/raw/p3/<run_id>/ and stay untracked.
"""

from __future__ import annotations

import collections
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from recovery.assignments import (
    PROCESS_ID,
    SPAWN_BLOCK,
    TAIL_INCLUSION_BLOCK,
    TAIL_NONCE,
    Assignment,
    diff_nonces,
    fetch_block_window,
    fetch_exact_nonces,
    fetch_transaction,
    merge_assignments,
    narrow_nonce_search,
    sha256_bytes,
)
from recovery.gql import DEFAULT_ENDPOINT, post_graphql
from recovery.hashchain import check_links, gen_hash_chain

ROOT = Path(__file__).resolve().parents[1]
P1_REUSED = {
    2: "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI",
    2075920: "RWqN5oiVdw2KPxKKw2NsvJwGdgUjDpWvwEg9Y73Egow",
    2075921: "mqb3_fdrWoCC6qO-r0qofRqJqKht-wWHC7wBCUhLKIA",
    2075922: "33OYeknNDTfNj0f7EyUTX0t-qOe_PW45TCJYHZSfkcM",
    2075923: "MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs",
}
WINDOWS = (
    (0, 19),
    (1037960, 1037979),
    (2075904, 2075923),
)


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


class RawStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.files: list[dict] = []
        self._n = 0

    def save(self, kind: str, request: dict, response) -> dict:
        self._n += 1
        stem = f"{self._n:04d}-{kind}"
        body_path = self.directory / f"{stem}.body"
        meta_path = self.directory / f"{stem}.meta.json"
        atomic_write(body_path, response.body or b"")
        meta = {
            "kind": kind,
            "endpoint": response.endpoint,
            "http_status": response.http_status,
            "elapsed_ms": response.elapsed_ms,
            "attempt": response.attempt,
            "error": response.error,
            "request": request,
            "saved_at": utc_now(),
        }
        meta_bytes = json.dumps(meta, sort_keys=True).encode("utf-8")
        atomic_write(meta_path, meta_bytes)
        record = {
            "body": str(body_path.relative_to(ROOT)),
            "meta": str(meta_path.relative_to(ROOT)),
            "body_bytes": len(response.body or b""),
            "body_sha256": sha256_bytes(response.body or b""),
            "meta_sha256": sha256_bytes(meta_bytes),
            "http_status": response.http_status,
            "elapsed_ms": response.elapsed_ms,
            "attempt": response.attempt,
            "error": response.error,
            "kind": kind,
        }
        self.files.append(record)
        return record


def capture_goldsky_redirect(store: RawStore) -> dict:
    url = "https://arweave-search.goldsky.com/graphql"
    payload = json.dumps({"query": "{ __typename }"}).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "qar-ledger-recovery"},
        method="POST",
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    started = time.monotonic()
    try:
        with opener.open(request, timeout=30) as response:
            body = response.read()
            status = response.status
            location = response.headers.get("location")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        location = exc.headers.get("location")
    except Exception as exc:  # noqa: BLE001
        body = str(exc).encode()
        status = 0
        location = None
    elapsed = int((time.monotonic() - started) * 1000)

    saved = type("Saved", (), {})()
    saved.endpoint = url
    saved.http_status = status
    saved.elapsed_ms = elapsed
    saved.attempt = 1
    saved.error = None if status in (200, 307) else f"http {status}"
    saved.body = body

    store.save("goldsky-redirect", {"query": "{ __typename }"}, saved)
    return {
        "requested": url,
        "http_status": status,
        "location": location,
        "elapsed_ms": elapsed,
        "followed_for_queries": DEFAULT_ENDPOINT,
        "note": "P0 named arweave-search.goldsky.com. This run recorded the live redirect and queried the redirect target directly.",
    }


def saving_post(store: RawStore, kind: str):
    def post(query, variables, endpoint=DEFAULT_ENDPOINT):
        response = post_graphql(query, variables, endpoint=endpoint)
        store.save(kind, {"endpoint": endpoint, "variables": variables, "query": query}, response)
        return response

    return post


def rows_json(rows: list[Assignment]) -> list[dict]:
    return [row.to_json() for row in sorted(rows, key=lambda item: (item.nonce, item.assignment_id))]


def window_report(name: str, start: int, end: int, rows: list[Assignment], source: str) -> dict:
    expected = list(range(start, end + 1))
    diff = diff_nonces(expected, rows)
    present = []
    for nonce in expected:
        row = diff.unique.get(nonce)
        if row is None:
            continue
        present.append({
            "nonce": nonce,
            "assignment_id": row.assignment_id,
            "message_id": row.message_id,
            "epoch": row.epoch,
            "hash_chain": row.hash_chain,
            "timestamp_ms": row.timestamp_ms,
            "assignment_block_height": row.assignment_block_height,
            "inclusion_height": row.inclusion_height,
            "reused_from_p1": P1_REUSED.get(nonce),
            "matches_p1_id": (P1_REUSED[nonce] == row.assignment_id) if nonce in P1_REUSED else None,
        })
    p1_conflicts = [
        item for item in present
        if item["matches_p1_id"] is False
    ]
    return {
        "window": name,
        "expected_nonce_start": start,
        "expected_nonce_end": end,
        "expected_count": len(expected),
        "source": source,
        "unique_match_count": sum(1 for nonce in expected if nonce in diff.unique),
        "missing_nonces": diff.missing,
        "duplicate_ids": {str(k): v for k, v in diff.duplicate_ids.items()},
        "conflicts": {str(k): v for k, v in diff.conflicts.items()},
        "p1_id_conflicts": p1_conflicts,
        "clean": diff.clean and not p1_conflicts,
        "rows": present,
    }


def chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


FRONTIER_QUERY = """
query($min:Int!, $max:Int!) {
  transactions(
    first: 1
    sort: HEIGHT_DESC
    block: { min: $min, max: $max }
    tags: [
      { name: "Data-Protocol", values: ["ao"] }
      { name: "Type", values: ["Assignment"] }
      { name: "Process", values: ["%s"] }
    ]
  ) {
    pageInfo { hasNextPage }
    edges { node { id block { height timestamp } tags { name value } } }
  }
}
""" % PROCESS_ID


def locate_nonce_block(store: RawStore, nonce: int) -> dict:
    """Find one nonce by inclusion height.

    HEIGHT_DESC first:1 only identifies the highest block at or below a probe.
    That block is then fully paged, because one block can hold many nonces.
    Absence is claimed only after the final narrowed window is closed and the
    surrounding nonces are present without the target.
    """
    lo = SPAWN_BLOCK
    hi = TAIL_INCLUSION_BLOCK
    probes = []
    post = saving_post(store, f"locate-{nonce}")
    found: Assignment | None = None
    for _ in range(28):
        if lo > hi:
            break
        if hi - lo <= 40:
            final = fetch_block_window(lo, hi, page_size=100, max_pages=20, post=post)
            probes.append({
                "final": True, "min": lo, "max": hi,
                "closed": final.closed, "rows": len(final.rows), "error": final.error,
            })
            if not final.closed:
                return {"nonce": nonce, "status": "not_located", "lo": lo, "hi": hi, "probes": probes}
            matches = [row for row in final.rows if row.nonce == nonce]
            distinct = {row.assignment_id for row in matches}
            if len(distinct) > 1:
                return {"nonce": nonce, "status": "conflict", "assignment_ids": sorted(distinct), "probes": probes}
            if len(distinct) == 1:
                found = matches[0]
                break
            nonces = [row.nonce for row in final.rows]
            return {
                "nonce": nonce,
                "status": "absent_inside_populated_slice" if nonces else "not_located",
                "lo": lo,
                "hi": hi,
                "min_nonce": min(nonces) if nonces else None,
                "max_nonce": max(nonces) if nonces else None,
                "probes": probes,
            }
        mid = (lo + hi) // 2
        response = post(FRONTIER_QUERY, {"min": SPAWN_BLOCK, "max": mid})
        if not response.ok or response.parsed is None:
            probes.append({"mid": mid, "error": response.error, "http": response.http_status})
            return {"nonce": nonce, "status": "not_located", "lo": lo, "hi": hi, "probes": probes}
        edges = (((response.parsed.get("data") or {}).get("transactions") or {}).get("edges") or [])
        if not edges:
            probes.append({"mid": mid, "empty": True})
            lo = mid + 1
            continue
        try:
            hint = parse_assignment_edge(edges[0])
        except ValueError as exc:
            return {"nonce": nonce, "status": "not_located", "error": str(exc), "probes": probes}
        height = hint.inclusion_height
        if height is None:
            return {"nonce": nonce, "status": "not_located", "error": "frontier block missing", "probes": probes}
        block_rows = fetch_block_window(height, height, page_size=100, max_pages=20, post=post)
        nonces = [row.nonce for row in block_rows.rows]
        probes.append({
            "mid": mid,
            "frontier_height": height,
            "closed": block_rows.closed,
            "rows": len(block_rows.rows),
            "min_nonce": min(nonces) if nonces else None,
            "max_nonce": max(nonces) if nonces else None,
            "error": block_rows.error,
        })
        if not block_rows.closed or not nonces:
            return {"nonce": nonce, "status": "not_located", "lo": lo, "hi": hi, "probes": probes}
        matches = [row for row in block_rows.rows if row.nonce == nonce]
        distinct = {row.assignment_id for row in matches}
        if len(distinct) > 1:
            return {"nonce": nonce, "status": "conflict", "assignment_ids": sorted(distinct), "probes": probes}
        if len(distinct) == 1:
            found = matches[0]
            break
        lo, hi = narrow_nonce_search(lo, hi, mid, height, min(nonces), max(nonces), nonce)
    if found is None:
        return {"nonce": nonce, "status": "not_located", "lo": lo, "hi": hi, "probes": probes}
    return {"nonce": nonce, "status": "found", "assignment": found.to_json(), "probes": probes}


def parse_assignment_edge(edge: dict):
    from recovery.assignments import parse_assignment
    return parse_assignment(edge)


def collect_exact(store: RawStore, nonces: list[int]) -> tuple[list[Assignment], list[dict]]:
    rows: list[Assignment] = []
    attempts = []
    post = saving_post(store, "exact-nonce")
    for batch in chunked(nonces, 5):
        window = fetch_exact_nonces(batch, page_size=100, max_pages=5, post=post)
        attempts.append({
            "nonces": batch,
            "closed": window.closed,
            "error": window.error,
            "row_count": len(window.rows),
            "http": [page.response.http_status for page in window.pages],
            "elapsed_ms": [page.response.elapsed_ms for page in window.pages],
        })
        if window.closed:
            rows.extend(window.rows)
    return merge_assignments(rows), attempts


def main() -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-p3a"
    raw_dir = ROOT / "data" / "raw" / "p3" / run_id
    evidence_dir = ROOT / "evidence" / "p3" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    store = RawStore(raw_dir)
    started = utc_now()

    redirect = capture_goldsky_redirect(store)
    print("redirect", redirect.get("http_status"), redirect.get("location"), flush=True)

    # Small early window: the spawn block holds more than one assignment.
    # Page size 2 must still return the same ids as page size 100.
    early_min, early_max = SPAWN_BLOCK, SPAWN_BLOCK + 120
    full = fetch_block_window(
        early_min, early_max, page_size=100, max_pages=20,
        post=saving_post(store, "early-page100"),
    )
    paged = fetch_block_window(
        early_min, early_max, page_size=2, max_pages=400,
        post=saving_post(store, "early-page2"),
    )
    full_ids = sorted(row.assignment_id for row in merge_assignments(full.rows))
    paged_ids = sorted(row.assignment_id for row in merge_assignments(paged.rows))
    pagination_check = {
        "block_min": early_min,
        "block_max": early_max,
        "page_size_100_closed": full.closed,
        "page_size_100_pages": len(full.pages),
        "page_size_100_rows": len(full.rows),
        "page_size_100_error": full.error,
        "page_size_2_closed": paged.closed,
        "page_size_2_pages": len(paged.pages),
        "page_size_2_rows": len(paged.rows),
        "page_size_2_error": paged.error,
        "assignment_id_sets_equal": full_ids == paged_ids,
        "heights_with_more_than_two_assignments": {
            str(height): count
            for height, count in collections.Counter(
                row.inclusion_height for row in full.rows
            ).items()
            if count > 2
        },
        "note": "Page size 2 walks the cursor through blocks that contain more than two assignments. Equality with page size 100 is the check that a short page does not drop the rest of that block.",
    }
    pagination_check["same_height_preserved"] = bool(
        pagination_check["assignment_id_sets_equal"]
        and pagination_check["heights_with_more_than_two_assignments"]
        and pagination_check["page_size_2_closed"]
        and pagination_check["page_size_100_closed"]
    )

    print("pagination", pagination_check["page_size_100_rows"], pagination_check["page_size_2_pages"], pagination_check["assignment_id_sets_equal"], flush=True)
    early_rows = merge_assignments(full.rows if full.closed else [])
    early_report = window_report("0..19", 0, 19, early_rows, "block_window")

    # If 0..19 is not fully inside the first 400 blocks, extend in closed slices.
    extend_notes = []
    height = early_max + 1
    while early_report["missing_nonces"] and height <= SPAWN_BLOCK + 5000:
        nxt = fetch_block_window(
            height, height + 399, page_size=100, max_pages=20,
            post=saving_post(store, "early-extend"),
        )
        extend_notes.append({
            "min": height,
            "max": height + 399,
            "closed": nxt.closed,
            "rows": len(nxt.rows),
            "error": nxt.error,
        })
        if not nxt.closed:
            break
        early_rows = merge_assignments(early_rows + nxt.rows)
        early_report = window_report("0..19", 0, 19, early_rows, "block_window")
        height += 400

    # Exact Nonce tags are the fallback and the cost probe, not the bulk method.
    # One batch of five known early nonces measures the gateway. Missing sample
    # nonces are queried the same way after the block windows, at most five per request.
    exact_rows, exact_attempts = collect_exact(store, [0, 1, 2, 3, 4])
    located = []
    block_fill_rows: list[Assignment] = []
    for start, end in WINDOWS[1:]:
        located_ends = []
        for endpoint in (start, end):
            print(f"locate {endpoint}", flush=True)
            found = locate_nonce_block(store, endpoint)
            located.append(found)
            print(f"located {endpoint} {found.get('status')}", flush=True)
            if found.get("status") == "found" and isinstance(found["assignment"].get("inclusion_height"), int):
                located_ends.append(found["assignment"]["inclusion_height"])
                block_fill_rows.append(Assignment(
                    assignment_id=found["assignment"]["assignment_id"],
                    nonce=found["assignment"]["nonce"],
                    epoch=found["assignment"]["epoch"],
                    message_id=found["assignment"]["message_id"],
                    timestamp_ms=found["assignment"]["timestamp_ms"],
                    hash_chain=found["assignment"]["hash_chain"],
                    assignment_block_height=found["assignment"]["assignment_block_height"],
                    inclusion_height=found["assignment"]["inclusion_height"],
                    inclusion_timestamp=found["assignment"]["inclusion_timestamp"],
                    tags=found["assignment"]["tags"],
                ))
        if len(located_ends) == 2:
            lo_h, hi_h = min(located_ends), max(located_ends)
            span = fetch_block_window(
                max(SPAWN_BLOCK, lo_h - 1),
                min(TAIL_INCLUSION_BLOCK, hi_h + 1),
                page_size=100,
                max_pages=40,
                post=saving_post(store, f"fill-{start}-{end}"),
            )
            located.append({
                "fill_window": [start, end],
                "block_min": lo_h,
                "block_max": hi_h,
                "closed": span.closed,
                "rows": len(span.rows),
                "error": span.error,
            })
            if span.closed:
                block_fill_rows.extend(span.rows)

    combined = merge_assignments(early_rows + exact_rows + block_fill_rows)
    still_missing = []
    for start, end in WINDOWS:
        have = {row.nonce for row in combined}
        still_missing.extend(nonce for nonce in range(start, end + 1) if nonce not in have)
    if still_missing:
        retry_rows, retry_attempts = collect_exact(store, still_missing)
        exact_rows = merge_assignments(exact_rows + retry_rows)
        exact_attempts.extend(retry_attempts)
        combined = merge_assignments(combined + retry_rows)
    reports = [
        window_report(f"{start}..{end}", start, end, combined, "block_window_plus_exact_nonce")
        for start, end in WINDOWS
    ]
    # Keep the pure block-window report for 0..19 as the method witness.
    reports[0]["block_window_only"] = {
        "clean": early_report["clean"],
        "missing_nonces": early_report["missing_nonces"],
        "unique_match_count": early_report["unique_match_count"],
    }

    process_tx = fetch_transaction(PROCESS_ID, post=saving_post(store, "process-tx"))
    process_tags = {}
    process_block = None
    if process_tx.ok and process_tx.parsed:
        node = (process_tx.parsed.get("data") or {}).get("transaction") or {}
        process_tags = {item["name"]: item["value"] for item in node.get("tags") or []}
        process_block = node.get("block")

    nonce0 = next((row for row in combined if row.nonce == 0), None)
    nonce1 = next((row for row in combined if row.nonce == 1), None)
    message_tags = {}
    for label, row in (("nonce0_message", nonce0), ("nonce1_message", nonce1)):
        if row is None or not row.message_id:
            continue
        msg = fetch_transaction(row.message_id, post=saving_post(store, label))
        if msg.ok and msg.parsed:
            node = (msg.parsed.get("data") or {}).get("transaction") or {}
            message_tags[label] = {
                "id": node.get("id"),
                "block": node.get("block"),
                "tags": {item["name"]: item["value"] for item in node.get("tags") or []},
                "id_equals_process": node.get("id") == PROCESS_ID,
            }

    seed_hash = None
    seed_matches_nonce0 = None
    if nonce0 is not None:
        try:
            seed_hash = gen_hash_chain(PROCESS_ID, None)
            seed_matches_nonce0 = seed_hash == nonce0.hash_chain
        except ValueError as exc:
            seed_hash = f"error: {exc}"

    sample_rows = [row for row in combined if any(start <= row.nonce <= end for start, end in WINDOWS)]
    hash_report = check_links(sample_rows)
    hash_report["nonce0_equals_sha256_process_id"] = seed_matches_nonce0
    hash_report["historical_scheduler_verified"] = bool(
        hash_report["verified"] and seed_matches_nonce0
    )

    start_rule = {
        "process_id": PROCESS_ID,
        "process_block": process_block,
        "process_type_tag": process_tags.get("Type"),
        "process_module": process_tags.get("Module"),
        "nonce_0_present": nonce0.to_json() if nonce0 else None,
        "nonce_1_present": nonce1.to_json() if nonce1 else None,
        "nonce_0_message_is_process_id": bool(nonce0 and nonce0.message_id == PROCESS_ID),
        "nonce_1_message_is_process_id": bool(nonce1 and nonce1.message_id == PROCESS_ID),
        "message_transactions": message_tags,
        "nonce0_hash_chain_equals_sha256_of_process_id": seed_matches_nonce0,
        "coverage_model": (
            "Nonce 0 and nonce 1 are scheduled assignments in this sample. "
            "The first logical P4 range is 0..49999 inclusive. Nonce 0 is not dropped."
            if nonce0 and nonce1 else
            "Nonce 0 or nonce 1 was not both proven in this run. Do not set the start at nonce 2."
        ),
        "reference_not_a_verdict": (
            "permaweb/ao scheduler.rs at 7ba5df7 says a process can be assigned nonce 0, "
            "or an older process can leave nonce 0 to the first message. This process is "
            "decided only by the rows above."
        ),
    }

    all_clean = all(report["clean"] for report in reports)
    sample = {
        "run_id": run_id,
        "phase": "P3",
        "started_at": started,
        "finished_at": utc_now(),
        "process_id": PROCESS_ID,
        "executed_module": False,
        "full_coverage": False,
        "sample_passed": all_clean,
        "verdict": "sample_passed" if all_clean else "sample_incomplete",
        "windows": reports,
        "reused_p1_ids": P1_REUSED,
        "start_rule": start_rule,
        "tail_boundary_unchanged": {
            "epoch": "0",
            "nonce": TAIL_NONCE,
            "assignment_id": P1_REUSED[TAIL_NONCE],
            "note": "Re-fetching the tail window cross-checks P1. It does not replace evidence/p1-tail.json.",
        },
    }
    gaps = {
        "run_id": run_id,
        "scope": "sample windows only",
        "full_history_gaps": "unknown",
        "windows": [
            {
                "window": report["window"],
                "missing_nonces": report["missing_nonces"],
                "conflicts": report["conflicts"],
                "p1_id_conflicts": report["p1_id_conflicts"],
                "status": "no_sample_gap" if report["clean"] else "unresolved",
            }
            for report in reports
        ],
    }
    for item in gaps["windows"]:
        if item["missing_nonces"] and not item["conflicts"]:
            item["status"] = "unresolved"
            item["classification"] = (
                "Exact nonce queries and the block-window fill did not produce a unique "
                "assignment. This is not recorded as never-published."
            )

    index_method = {
        "run_id": run_id,
        "selected_method": "inclusion_block_window_then_numeric_nonce",
        "sample_passed_name": "sample_passed",
        "not_full_coverage": True,
        "why": "GraphQL tag filters take exact values. A 50000-value Nonce filter is refused. Block windows are fully paginated with the gateway cursor, then merged by integer nonce.",
        "endpoint": DEFAULT_ENDPOINT,
        "goldsky_redirect": redirect,
        "page_size": 100,
        "max_nonce_values_per_exact_query": 5,
        "pagination": "Repeat the same block min/max with after=last edge cursor until pageInfo.hasNextPage is false. Do not open the next block window on a page that is still open. Do not advance by last_block+1 inside an open page.",
        "pagination_equivalence": pagination_check,
        "early_extend": extend_notes,
        "exact_nonce_attempts": exact_attempts,
        "locate_probes": located,
        "dedup": "Same assignment id on two pages is one row. Two ids for one nonce are a conflict and the range is not complete.",
        "recovery": "Re-request the same block window from the beginning, or resume after the last cursor whose raw body was flushed and hashed. A .part file is not a finished page.",
        "budget": {
            "max_attempts_per_request": 3,
            "backoff_seconds": "1,2,4 capped at 8",
            "max_pages_per_block_window_during_p3": 30,
        },
        "request_template": {
            "block_window": {
                "sort": "HEIGHT_ASC",
                "block": {"min": "<inclusive inclusion height>", "max": "<inclusive inclusion height>"},
                "first": 100,
                "after": "<previous cursor or null>",
                "tags": [
                    {"name": "Data-Protocol", "values": ["ao"]},
                    {"name": "Type", "values": ["Assignment"]},
                    {"name": "Process", "values": [PROCESS_ID]},
                ],
            },
            "exact_nonce_fallback_batch_max_5": {
                "tags_extra": [
                    {"name": "Epoch", "values": ["0"]},
                    {"name": "Nonce", "values": ["<up to 5 decimal strings>"]},
                ]
            },
        },
        "next_cursor": None if all_clean else "unresolved sample; do not start P4 coverage",
        "first_logical_range": "0..49999",
        "first_logical_range_inclusive": [0, 49999],
        "expected_assignment_count_if_nonce_starts_at_0_through_tail": TAIL_NONCE + 1,
        "hash_chain": hash_report,
        "raw_pages": store.files,
    }

    def dump(name: str, value: dict) -> None:
        atomic_write(evidence_dir / name, json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n")

    dump("sample.json", sample)
    dump("gaps.json", gaps)
    dump("index-method.json", index_method)
    manifest = {
        "run_id": run_id,
        "phase": "P3",
        "executed_module": False,
        "evidence": [
            f"evidence/p3/{run_id}/sample.json",
            f"evidence/p3/{run_id}/gaps.json",
            f"evidence/p3/{run_id}/index-method.json",
        ],
        "raw_directory": f"data/raw/p3/{run_id}",
        "raw_files": store.files,
        "sample_passed": all_clean,
        "full_coverage": False,
    }
    dump("query-manifest.json", manifest)
    print(json.dumps({
        "run_id": run_id,
        "sample_passed": all_clean,
        "windows": [
            {
                "window": report["window"],
                "clean": report["clean"],
                "unique": report["unique_match_count"],
                "missing": report["missing_nonces"],
                "conflicts": report["conflicts"],
            }
            for report in reports
        ],
        "pagination_equal": pagination_check["assignment_id_sets_equal"],
        "nonce0_is_process": start_rule["nonce_0_message_is_process_id"],
        "hash_chain_verified": hash_report["historical_scheduler_verified"],
        "hash_links": {
            "checked": hash_report["links_checked"],
            "matched": hash_report["links_matched"],
            "mismatched": hash_report["links_mismatched"],
        },
    }, indent=2))
    return sample


if __name__ == "__main__":
    main()

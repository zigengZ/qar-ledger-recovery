"""Bind assignments 2074400..2075923 to the checkpoint tags and the P1 tail.

Uses the existing exact-nonce index, then block windows, then the closed
bundle reader when a nonce is absent from GraphQL. Does not execute the
module and does not write STATE.md.

Bulk bytes go to data/raw/tail-2074400/ under the repository root.
Evidence goes to evidence/p4-tail/<run>-w-tail/.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from recovery.ans104_item import build_data_item, signature_id, signature_valid
from recovery.assignments import (
    PROCESS_ID,
    Assignment,
    diff_nonces,
    fetch_block_window,
    fetch_exact_nonces,
    sha256_bytes,
)
from recovery.bundle_recover import recover_closed_scan
from recovery.chunk_scan import read_tx_range, scan_tx_chunks
from recovery.coverage import missing_ranges
from recovery.gql import DEFAULT_ENDPOINT, post_graphql
from recovery.hashchain import b64url_decode, check_links, link_matches

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data/raw/tail-2074400"
START = 2074400
END = 2075923
TAIL_NONCE = 2075923
TAIL_ASSIGNMENT = "MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs"
TAIL_HASH = "mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE"
TAIL_MESSAGE = "wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ"
P1_SPOTS = {
    2075920: {
        "assignment_id": "RWqN5oiVdw2KPxKKw2NsvJwGdgUjDpWvwEg9Y73Egow",
        "hash_chain": "W6Gzci9Ct1HykKvSNghmxp-j8fjjXQ7znKaNaadozQU",
        "message_id": "MbhvdcksYvxYprkIEso9yhedcHc9daIleu6bEx_Jbv0",
    },
    2075921: {
        "assignment_id": "mqb3_fdrWoCC6qO-r0qofRqJqKht-wWHC7wBCUhLKIA",
        "hash_chain": "zl6XaylhEMjXoP8njYkEZrL1f2QYl7_ClHBHVOgkpzU",
        "message_id": "BcdiVkSk8EEcIhcjGYWwsJqIBeOW7DBNvqVYJ2DLS_w",
    },
    2075922: {
        "assignment_id": "33OYeknNDTfNj0f7EyUTX0t-qOe_PW45TCJYHZSfkcM",
        "hash_chain": "FeI_sXq8qYZa7Zb750QFO88PK6LOWc52jAYPixPfMe0",
        "message_id": "CmbnA1NGvC_XhTCVezl5ScSK6vlmcsN16vtcv9peHTI",
    },
    2075923: {
        "assignment_id": TAIL_ASSIGNMENT,
        "hash_chain": TAIL_HASH,
        "message_id": TAIL_MESSAGE,
    },
}
ENDPOINTS = [
    DEFAULT_ENDPOINT,
    "https://arweave-search.goldsky.com/graphql",
]
DATA_GATEWAYS = [
    "https://arweave.net",
    "https://ar-io.dev",
    "https://vilenarios.com",
    "https://turbo-gateway.com",
]
USER_AGENT = "qar-ledger-recovery"
WORKERS = 4

CHECKPOINT_QUERY = """
query($nonces:[String!]!, $after:String) {
  transactions(
    first: 10
    after: $after
    sort: HEIGHT_DESC
    tags: [
      { name: "Type", values: ["Checkpoint"] }
      { name: "Process", values: ["%s"] }
      { name: "Nonce", values: $nonces }
    ]
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        owner { address }
        data { size }
        block { height timestamp }
        tags { name value }
      }
    }
  }
}
""" % PROCESS_ID

MESSAGE_QUERY = """
query($ids:[ID!]!, $first:Int!, $after:String) {
  transactions(
    ids: $ids
    first: $first
    after: $after
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        anchor
        signature
        recipient
        owner { address key }
        data { size }
        bundledIn { id }
        block { height timestamp }
        tags { name value }
      }
    }
  }
}
"""

BUNDLE_LIST_QUERY = """
query($min:Int!, $max:Int!, $first:Int!, $after:String) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    block: { min: $min, max: $max }
    tags: [{ name: "Bundle-Format", values: ["binary"] }]
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node { id data { size } block { height } tags { name value } }
    }
  }
}
"""


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


def write_json(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n")


class Store:
    """Thread-safe raw GraphQL body log."""

    def __init__(self, raw: Path):
        self.raw = raw
        self.gql = raw / "gql"
        self.gql.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.n = len(list(self.gql.glob("*.body")))
        self.files: list[dict] = []

    def save(self, kind: str, variables: dict, response, endpoint: str) -> dict:
        with self.lock:
            self.n += 1
            seq = self.n
        body = response.body or b""
        body_path = self.gql / f"{seq:05d}-{kind}.body"
        req_path = self.gql / f"{seq:05d}-{kind}.request.json"
        atomic_write(body_path, body)
        atomic_write(req_path, json.dumps(
            {"endpoint": endpoint, "kind": kind, "variables": variables},
            sort_keys=True,
        ).encode("utf-8"))
        record = {
            "body_path": str(body_path),
            "request_path": str(req_path),
            "bytes": len(body),
            "sha256": sha256_bytes(body),
            "http_status": response.http_status,
            "elapsed_ms": response.elapsed_ms,
            "attempt": response.attempt,
            "error": response.error,
            "endpoint": endpoint,
            "kind": kind,
        }
        with self.lock:
            self.files.append(record)
        return record


def make_post(store: Store, kind: str):
    def post(query, variables, endpoint=DEFAULT_ENDPOINT):
        response = post_graphql(query, variables, endpoint=endpoint, timeout_s=90, max_attempts=4)
        store.save(kind, variables, response, endpoint)
        return response
    return post


def fetch_nonces(nonces: list[int], store: Store):
    """Exact nonce query. A second gateway is used only when the first is incomplete."""
    post = make_post(store, "exact")
    primary = fetch_exact_nonces(nonces, page_size=100, max_pages=10, endpoint=ENDPOINTS[0], post=post)
    rows = list(primary.rows)
    closed = primary.closed
    if primary.closed and all(any(row.nonce == nonce for row in rows) for nonce in nonces):
        return rows, True, None
    missing = [nonce for nonce in nonces if not any(row.nonce == nonce for row in rows)]
    secondary = fetch_exact_nonces(
        missing or nonces, page_size=100, max_pages=10, endpoint=ENDPOINTS[1], post=post,
    )
    rows.extend(secondary.rows)
    if secondary.closed and primary.closed:
        return rows, True, None
    if secondary.closed or primary.closed:
        # One gateway closed. Nonces it did not return are index misses, not transport failures.
        return rows, True, None
    error = secondary.error or primary.error or "exact nonce query did not close"
    return rows, False, error


def index_assignments(store: Store) -> tuple[list[Assignment], list[dict]]:
    batches = [list(range(start, min(END, start + 19) + 1)) for start in range(START, END + 1, 20)]
    rows: list[Assignment] = []
    failures: list[dict] = []
    lock = threading.Lock()
    done = 0

    def one(batch: list[int]):
        got, closed, error = fetch_nonces(batch, store)
        if closed:
            return got, []
        singles = []
        failed = []
        for nonce in batch:
            one_rows, one_closed, one_error = fetch_nonces([nonce], store)
            if one_closed:
                singles.extend(one_rows)
            else:
                failed.append({
                    "nonces": [nonce],
                    "error": one_error or error or "exact nonce query did not close",
                })
        return singles, failed

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, batch) for batch in batches]
        for future in as_completed(futures):
            got, failed = future.result()
            with lock:
                rows.extend(got)
                failures.extend(failed)
                done += 1
                if done % 10 == 0 or done == len(batches):
                    print(f"exact batches {done}/{len(batches)} rows {len(rows)}", flush=True)
    return rows, failures


def assignment_from_record(record: dict, source: str) -> Assignment:
    return Assignment(
        assignment_id=record["assignment_id"],
        nonce=int(record["nonce"]),
        epoch=str(record.get("epoch", "")),
        message_id=record.get("message_id", ""),
        timestamp_ms=str(record.get("timestamp_ms", "")),
        hash_chain=record.get("hash_chain", ""),
        assignment_block_height=record.get("assignment_block_height"),
        inclusion_height=record.get("inclusion_height"),
        inclusion_timestamp=record.get("inclusion_timestamp"),
        tags={"source": source},
    )


def fill_blocks(store: Store, unique: dict[int, Assignment], holes: list[list[int]]) -> list[int]:
    """Page inclusion heights between the nonces on either side of a hole."""
    post = make_post(store, "block")
    recovered: list[int] = []
    for start, end in holes:
        left = unique.get(start - 1)
        right = unique.get(end + 1)
        if left is None or right is None or left.inclusion_height is None or right.inclusion_height is None:
            print(f"hole {start}..{end} has no neighbor height", flush=True)
            continue
        lo = min(left.inclusion_height, right.inclusion_height)
        hi = max(left.inclusion_height, right.inclusion_height)
        if hi - lo > 8000:
            print(f"hole {start}..{end} spans heights {lo}..{hi}, too wide for a block walk", flush=True)
            continue
        height = lo
        width = 40
        print(f"block fill {start}..{end} heights {lo}..{hi}", flush=True)
        while height <= hi:
            window_max = min(hi, height + width - 1)
            window = fetch_block_window(height, window_max, page_size=100, max_pages=25, post=post)
            if not window.closed:
                if width > 10:
                    width = max(10, width // 2)
                    print(f"shrink width to {width} at {height}: {window.error}", flush=True)
                    continue
                print(f"block window {height}..{window_max} not closed: {window.error}", flush=True)
                break
            for row in window.rows:
                if start <= row.nonce <= end and row.nonce not in unique:
                    unique[row.nonce] = row
                    recovered.append(row.nonce)
            height = window_max + 1
    return recovered


def list_binary_bundles(store: Store, lo: int, hi: int) -> list[dict]:
    post = make_post(store, "bundle-list")
    found: list[dict] = []
    cursor = None
    while True:
        variables = {"min": lo, "max": hi, "first": 100, "after": cursor}
        response = post(BUNDLE_LIST_QUERY, variables, endpoint=ENDPOINTS[0])
        if not response.ok or response.parsed is None:
            raise RuntimeError(response.error or f"bundle list http {response.http_status}")
        page = ((response.parsed.get("data") or {}).get("transactions") or {})
        edges = page.get("edges") or []
        for edge in edges:
            node = edge["node"]
            tags = {item["name"]: item["value"] for item in node.get("tags") or []}
            if tags.get("Bundle-Format") != "binary":
                continue
            found.append({
                "id": node["id"],
                "size": int((node.get("data") or {}).get("size") or 0),
                "height": (node.get("block") or {}).get("height"),
            })
        if not (page.get("pageInfo") or {}).get("hasNextPage"):
            return found
        if not edges or edges[-1].get("cursor") == cursor:
            raise RuntimeError("bundle list page stalled")
        cursor = edges[-1]["cursor"]


def fill_bundles(store: Store, unique: dict[int, Assignment], missing: list[int]) -> list[int]:
    """Scan binary bundles in the neighbor height span. A scan that is not closed inserts nothing."""
    if not missing:
        return []
    heights = []
    for nonce in missing:
        for neighbor in (nonce - 1, nonce + 1):
            row = unique.get(neighbor)
            if row is not None and row.inclusion_height is not None:
                heights.append(row.inclusion_height)
    if not heights:
        print("bundle fill has no neighbor height", flush=True)
        return []
    lo, hi = min(heights), max(heights)
    if hi - lo > 400:
        print(f"bundle fill span {lo}..{hi} is wider than 400 blocks; not scanning blindly", flush=True)
        return []
    wanted = set(missing)
    bundles = list_binary_bundles(store, lo, hi)
    print(f"bundle fill {len(bundles)} binary txs in {lo}..{hi} for {len(wanted)} nonces", flush=True)
    recovered: list[int] = []
    raw_notes = store.raw / "bundle-scans"
    raw_notes.mkdir(parents=True, exist_ok=True)
    for bundle in bundles:
        if not wanted:
            break
        scan = scan_tx_chunks(bundle["id"], set(wanted))
        atomic_write(
            raw_notes / f"{bundle['id']}.json",
            json.dumps({**bundle, **{k: v for k, v in scan.items() if k != "process_offsets"}}, indent=2).encode(),
        )
        if not scan.get("closed") or not scan.get("nonce_hits"):
            continue

        def read(start: int, end: int, tx_id=bundle["id"]) -> bytes:
            return read_tx_range(tx_id, start, end)

        try:
            records = recover_closed_scan(scan, read)
        except Exception as exc:  # noqa: BLE001 — one bundle must not drop the others
            print(f"recover {bundle['id']} failed: {type(exc).__name__}: {exc}", flush=True)
            continue
        for record in records:
            nonce = int(record["nonce"])
            if nonce not in wanted:
                continue
            record["inclusion_height"] = bundle.get("height")
            row = assignment_from_record(record, f"bundle:{bundle['id']}")
            previous = unique.get(nonce)
            if previous is not None and previous.assignment_id != row.assignment_id:
                print(f"conflict nonce {nonce} {previous.assignment_id} vs {row.assignment_id}", flush=True)
                continue
            unique[nonce] = row
            wanted.discard(nonce)
            recovered.append(nonce)
            print(f"recovered nonce {nonce} from {bundle['id']}", flush=True)
    return recovered


def row_public(row: Assignment) -> dict:
    return {
        "nonce": row.nonce,
        "epoch": row.epoch,
        "assignment_id": row.assignment_id,
        "message_id": row.message_id,
        "timestamp_ms": row.timestamp_ms,
        "hash_chain": row.hash_chain,
        "assignment_block_height": row.assignment_block_height,
        "inclusion_height": row.inclusion_height,
        "inclusion_timestamp": row.inclusion_timestamp,
        "tags": row.tags,
    }


def load_rows(path: Path) -> list[Assignment]:
    payload = json.loads(path.read_text())
    rows = []
    for item in payload:
        rows.append(Assignment(
            assignment_id=item["assignment_id"],
            nonce=int(item["nonce"]),
            epoch=str(item.get("epoch", "")),
            message_id=item.get("message_id", ""),
            timestamp_ms=str(item.get("timestamp_ms", "")),
            hash_chain=item.get("hash_chain", ""),
            assignment_block_height=item.get("assignment_block_height"),
            inclusion_height=item.get("inclusion_height"),
            inclusion_timestamp=item.get("inclusion_timestamp"),
            tags=item.get("tags") or {},
        ))
    return rows


def fetch_checkpoints(store: Store) -> dict:
    post = make_post(store, "checkpoint")
    nonces = ["2074508", "2074510", "2074518"]
    cursor = None
    edges = []
    closed = False
    error = None
    while True:
        response = post(CHECKPOINT_QUERY, {"nonces": nonces, "after": cursor}, endpoint=ENDPOINTS[0])
        if not response.ok or response.parsed is None:
            error = response.error or f"http {response.http_status}"
            break
        page = ((response.parsed.get("data") or {}).get("transactions") or {})
        page_edges = page.get("edges") or []
        edges.extend(page_edges)
        if not (page.get("pageInfo") or {}).get("hasNextPage"):
            closed = True
            break
        if not page_edges or page_edges[-1].get("cursor") == cursor:
            error = "checkpoint page stalled"
            break
        cursor = page_edges[-1]["cursor"]
    by_nonce = {}
    for edge in edges:
        node = edge["node"]
        tags = {item["name"]: item["value"] for item in node.get("tags") or []}
        nonce = tags.get("Nonce")
        if nonce:
            by_nonce[nonce] = {
                "id": node.get("id"),
                "owner": (node.get("owner") or {}).get("address"),
                "data_size": (node.get("data") or {}).get("size"),
                "block": node.get("block"),
                "tags": tags,
            }
    return {"closed": closed, "error": error, "by_nonce": by_nonce, "edge_count": len(edges)}


def checkpoint_bind(unique: dict[int, Assignment], checkpoints: dict) -> dict:
    report = {}
    for nonce in (2074508, 2074510, 2074518):
        row = unique.get(nonce)
        checkpoint = checkpoints.get(str(nonce))
        item = {
            "nonce": nonce,
            "assignment_present": row is not None,
            "checkpoint_present": checkpoint is not None,
        }
        if row is not None:
            item["assignment_id"] = row.assignment_id
            item["hash_chain"] = row.hash_chain
            item["message_id"] = row.message_id
        if checkpoint is not None:
            tags = checkpoint["tags"]
            item["checkpoint_id"] = checkpoint["id"]
            item["checkpoint_owner"] = checkpoint["owner"]
            item["checkpoint_assignment_tag"] = tags.get("Assignment")
            item["checkpoint_hash_chain_tag"] = tags.get("Hash-Chain")
            item["checkpoint_ordinate"] = tags.get("Ordinate")
            item["assignment_tag_matches"] = bool(row and tags.get("Assignment") == row.assignment_id)
            item["hash_chain_tag_matches"] = bool(row and tags.get("Hash-Chain") == row.hash_chain)
        report[str(nonce)] = item
    return report


def spot_checks(unique: dict[int, Assignment]) -> dict:
    report = {}
    for nonce, expected in P1_SPOTS.items():
        row = unique.get(nonce)
        report[str(nonce)] = {
            "present": row is not None,
            "assignment_id_matches": bool(row and row.assignment_id == expected["assignment_id"]),
            "hash_chain_matches": bool(row and row.hash_chain == expected["hash_chain"]),
            "message_id_matches": bool(row and row.message_id == expected["message_id"]),
            "expected": expected,
            "actual_assignment_id": None if row is None else row.assignment_id,
            "actual_hash_chain": None if row is None else row.hash_chain,
            "actual_message_id": None if row is None else row.message_id,
        }
    return report


def decode_optional(value: str | None) -> bytes:
    if not value:
        return b""
    raw = b64url_decode(value)
    if len(raw) != 32:
        raise ValueError(f"optional field is {len(raw)} bytes, expected 32")
    return raw


def graphql_messages(store: Store, ids: list[str]) -> tuple[dict[str, dict], list[str]]:
    post = make_post(store, "message")
    found: dict[str, dict] = {}
    failed: list[str] = []

    def one_batch(batch: list[str]) -> tuple[list[dict], bool, str | None]:
        cursor = None
        edges = []
        for _ in range(8):
            response = post(
                MESSAGE_QUERY,
                {"ids": batch, "first": max(len(batch), 1), "after": cursor},
                endpoint=ENDPOINTS[0],
            )
            if not response.ok or response.parsed is None:
                return edges, False, response.error or f"http {response.http_status}"
            page = ((response.parsed.get("data") or {}).get("transactions") or {})
            page_edges = page.get("edges") or []
            edges.extend(page_edges)
            if not (page.get("pageInfo") or {}).get("hasNextPage"):
                return edges, True, None
            if not page_edges or page_edges[-1].get("cursor") == cursor:
                return edges, False, "message page stalled"
            cursor = page_edges[-1]["cursor"]
        return edges, False, "message page budget exhausted"

    batches = [ids[index:index + 10] for index in range(0, len(ids), 10)]
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(one_batch, batch): batch for batch in batches}
        for future in as_completed(futures):
            batch = futures[future]
            edges, closed, error = future.result()
            with lock:
                done += 1
                if not closed:
                    print(f"message batch failed {error}; splitting {len(batch)}", flush=True)
                if done % 20 == 0 or done == len(batches):
                    print(f"message meta {done}/{len(batches)}", flush=True)
            if not closed:
                for message_id in batch:
                    one_edges, one_closed, _one_error = one_batch([message_id])
                    if not one_closed:
                        failed.append(message_id)
                        continue
                    for edge in one_edges:
                        node = edge.get("node") or {}
                        if node.get("id"):
                            found[node["id"]] = node
                continue
            for edge in edges:
                node = edge.get("node") or {}
                if node.get("id"):
                    found[node["id"]] = node
            for message_id in batch:
                if message_id not in found:
                    failed.append(message_id)
    return found, failed


class Gate:
    def __init__(self):
        self.lock = threading.Lock()
        self.next_ok = 0.0

    def wait(self) -> None:
        with self.lock:
            delay = self.next_ok - time.time()
        if delay > 0:
            time.sleep(delay)

    def backoff(self, seconds: float) -> None:
        with self.lock:
            self.next_ok = max(self.next_ok, time.time() + seconds)


def fetch_bytes(message_id: str, expected: int | None, dest: Path, errors: Path, gate: Gate) -> dict:
    """Download the data payload. A size mismatch is not accepted as the payload."""
    if expected == 0:
        atomic_write(dest, b"")
        return {
            "ok": True,
            "bytes": 0,
            "sha256": sha256_bytes(b""),
            "url": None,
            "http_status": None,
            "note": "graphql data.size is 0; no gateway request",
        }
    attempts = []
    for base in DATA_GATEWAYS:
        url = f"{base}/{message_id}"
        host = base.split("/")[2]
        for attempt in range(1, 5):
            gate.wait()
            started = time.monotonic()
            status = 0
            body = b""
            error = None
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=90) as response:
                    status = int(response.status)
                    body = response.read()
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                body = exc.read()
                error = f"HTTPError {status}"
            except Exception as exc:  # noqa: BLE001 — recorded, then the next gateway
                error = f"{type(exc).__name__}: {exc}"
            elapsed = int((time.monotonic() - started) * 1000)
            record = {
                "url": url,
                "http_status": status,
                "bytes": len(body),
                "sha256": sha256_bytes(body),
                "elapsed_ms": elapsed,
                "attempt": attempt,
                "error": error,
            }
            attempts.append(record)
            size_ok = expected is None or len(body) == expected
            if status == 200 and size_ok and error is None:
                atomic_write(dest, body)
                record["ok"] = True
                record["path"] = str(dest)
                return record
            if status in (429, 500, 502, 503, 504) or status == 0:
                gate.backoff(min(8, 2 ** (attempt - 1)))
                continue
            if body:
                atomic_write(errors / f"{message_id}.{host}.a{attempt}.body", body)
            break
    return {"ok": False, "attempts": attempts, "error": "no gateway returned the expected data bytes"}


def store_message(raw: Path, row: Assignment, node: dict | None, gate: Gate) -> dict:
    message_id = row.message_id
    dest_dir = raw / "messages"
    dest_dir.mkdir(parents=True, exist_ok=True)
    meta_path = dest_dir / f"{message_id}.meta.json"
    if meta_path.exists():
        existing = json.loads(meta_path.read_text())
        if existing.get("stored") and existing.get("signature_valid"):
            existing["nonce"] = row.nonce
            existing["assignment_id"] = row.assignment_id
            return existing
    result = {
        "nonce": row.nonce,
        "assignment_id": row.assignment_id,
        "message_id": message_id,
        "stored": False,
        "signature_valid": False,
        "signature_id_matches": False,
    }
    if node is None:
        result["error"] = "graphql returned no transaction"
        atomic_write(meta_path, json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
        return result
    tags = [{"name": item["name"], "value": item["value"]} for item in node.get("tags") or []]
    size_text = (node.get("data") or {}).get("size")
    expected = int(size_text) if size_text not in (None, "") else None
    data_path = dest_dir / f"{message_id}.data"
    fetched = fetch_bytes(message_id, expected, data_path, raw / "http-errors", gate)
    result["data_http"] = {key: fetched.get(key) for key in (
        "ok", "url", "http_status", "bytes", "sha256", "elapsed_ms", "attempt", "error", "note", "path",
    )}
    if not fetched.get("ok"):
        result["error"] = fetched.get("error")
        atomic_write(meta_path, json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
        return result
    data = data_path.read_bytes()
    try:
        signature = b64url_decode(node.get("signature") or "")
        owner = b64url_decode(((node.get("owner") or {}).get("key")) or "")
        target = decode_optional(node.get("recipient"))
        anchor = decode_optional(node.get("anchor"))
        item = build_data_item(signature, owner, target, anchor, tags, data)
    except Exception as exc:  # noqa: BLE001 — the fields are still recorded
        result["error"] = f"build failed: {type(exc).__name__}: {exc}"
        result["owner_address"] = (node.get("owner") or {}).get("address")
        result["target"] = node.get("recipient") or ""
        result["anchor"] = node.get("anchor") or ""
        result["tags"] = tags
        result["data_bytes"] = len(data)
        result["data_sha256"] = sha256_bytes(data)
        atomic_write(meta_path, json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
        return result
    item_path = dest_dir / f"{message_id}.ans104"
    atomic_write(item_path, item)
    valid = signature_valid(item)
    result.update({
        "stored": True,
        "ans104_path": str(item_path),
        "data_path": str(data_path),
        "bytes": len(item),
        "sha256": sha256_bytes(item),
        "data_bytes": len(data),
        "data_sha256": sha256_bytes(data),
        "signature_id_matches": signature_id(signature) == message_id,
        "signature_valid": valid,
        "owner_address": (node.get("owner") or {}).get("address"),
        "target": node.get("recipient") or "",
        "anchor": node.get("anchor") or "",
        "tags": tags,
        "block": node.get("block"),
        "bundled_in": (node.get("bundledIn") or {}).get("id") or "",
    })
    if not valid:
        result["error"] = "reconstructed ANS-104 signature did not verify"
    atomic_write(meta_path, json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    return result


def fetch_all_messages(raw: Path, store: Store, rows: list[Assignment]) -> list[dict]:
    unique_ids = list(dict.fromkeys(row.message_id for row in rows if row.message_id))
    print(f"message ids {len(unique_ids)}", flush=True)
    nodes, failed_lookup = graphql_messages(store, unique_ids)
    print(f"message graphql found {len(nodes)} failed_lookup {len(failed_lookup)}", flush=True)
    by_id = {row.message_id: row for row in rows}
    gate = Gate()
    results: dict[str, dict] = {}
    pending = unique_ids
    print(f"message bodies to fetch {len(pending)}", flush=True)
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [
            pool.submit(store_message, raw, by_id[message_id], nodes.get(message_id), gate)
            for message_id in pending
        ]
        for future in as_completed(futures):
            result = future.result()
            with lock:
                results[result["message_id"]] = result
                done += 1
                if done % 100 == 0 or done == len(futures):
                    valid = sum(1 for item in results.values() if item.get("signature_valid"))
                    print(f"messages {done}/{len(futures)} signature_valid {valid}", flush=True)
    ordered = []
    for row in sorted(rows, key=lambda item: item.nonce):
        meta_path = raw / "messages" / f"{row.message_id}.meta.json"
        if row.message_id in results:
            item = dict(results[row.message_id])
        elif meta_path.exists():
            item = json.loads(meta_path.read_text())
        else:
            item = {
                "nonce": row.nonce,
                "assignment_id": row.assignment_id,
                "message_id": row.message_id,
                "stored": False,
                "error": "no meta written",
            }
        item["nonce"] = row.nonce
        item["assignment_id"] = row.assignment_id
        ordered.append(item)
    return ordered


def chain_report(rows: list[Assignment]) -> dict:
    report = check_links(rows)
    ordered = sorted(rows, key=lambda row: row.nonce)
    tail_link = None
    if len(ordered) >= 2 and ordered[-1].nonce == TAIL_NONCE and ordered[-2].nonce == TAIL_NONCE - 1:
        tail_link = link_matches(ordered[-2], ordered[-1])
    report["tail_link_matches"] = tail_link
    report["links_failed"] = report["links_mismatched"]
    return report


def main() -> None:
    run_id = os.environ.get("TAIL_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = RAW_ROOT / run_id
    evidence = ROOT / "evidence" / "p4-tail" / f"{run_id}-w-tail"
    raw.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    store = Store(raw)
    print(f"run {run_id}", flush=True)
    assignments_path = raw / "assignments.json"
    if assignments_path.exists() and os.environ.get("TAIL_RUN_ID"):
        rows = load_rows(assignments_path)
        print(f"loaded {len(rows)} assignments", flush=True)
        query_failures = []
    else:
        fetched, query_failures = index_assignments(store)
        diff = diff_nonces(list(range(START, END + 1)), fetched)
        unique = dict(diff.unique)
        extras = [row for row in fetched if row.nonce in diff.conflicts]
        holes = missing_ranges([nonce for nonce in diff.missing if nonce not in diff.conflicts])
        if holes:
            print(f"exact miss {len(diff.missing)} holes {len(holes)}", flush=True)
            fill_blocks(store, unique, holes)
            still = [
                nonce for nonce in range(START, END + 1)
                if nonce not in unique and nonce not in diff.conflicts
            ]
            if still:
                fill_bundles(store, unique, still)
        if diff.conflicts:
            print(f"conflicts {sorted(diff.conflicts)}", flush=True)
        rows = list(unique.values()) + extras
        write_json(assignments_path, [row_public(row) for row in rows])
        write_json(raw / "query-failures.json", query_failures)
    diff = diff_nonces(list(range(START, END + 1)), rows)
    chain = chain_report(list(diff.unique.values()))
    checkpoints = fetch_checkpoints(store)
    binds = checkpoint_bind(diff.unique, checkpoints["by_nonce"])
    spots = spot_checks(diff.unique)
    continuous = (
        not diff.missing
        and not diff.conflicts
        and chain["links_checked"] == END - START
        and chain["links_matched"] == END - START
        and chain["links_mismatched"] == 0
    )
    bind_ok = all(
        item.get("assignment_tag_matches") and item.get("hash_chain_tag_matches")
        for item in binds.values()
    )
    tail_ok = all(
        item["assignment_id_matches"] and item["hash_chain_matches"] and item["message_id_matches"]
        for item in spots.values()
    )
    print(
        f"assignments unique {len(diff.unique)} missing {len(diff.missing)} "
        f"chain {chain['links_matched']}/{chain['links_checked']} "
        f"bind {bind_ok} tail {tail_ok}",
        flush=True,
    )
    messages = fetch_all_messages(raw, store, list(diff.unique.values()))
    stored = [item for item in messages if item.get("stored")]
    valid = [item for item in messages if item.get("signature_valid")]
    missing_messages = [item for item in messages if not item.get("stored")]
    print(
        f"messages stored {len(stored)} signature_valid {len(valid)} missing {len(missing_messages)}",
        flush=True,
    )
    page_files = []
    for record in store.files:
        page_files.append(record)
    range_manifest = {
        "run_id": run_id,
        "worker": "w-tail",
        "process_id": PROCESS_ID,
        "module_executed": False,
        "goal_complete": False,
        "nonce_set": {
            "inclusive_start": START,
            "inclusive_end": END,
            "expected_count": END - START + 1,
            "unique_count": len(diff.unique),
            "missing_count": len(diff.missing),
            "missing": diff.missing,
            "missing_ranges": missing_ranges(diff.missing),
            "conflict_count": len(diff.conflicts),
            "conflicts": {str(nonce): ids for nonce, ids in sorted(diff.conflicts.items())},
            "contiguous": not diff.missing and not diff.conflicts,
        },
        "hash_chain": {
            "links_checked": chain["links_checked"],
            "links_matched": chain["links_matched"],
            "links_failed": chain["links_mismatched"],
            "mismatch_sample": chain["mismatch_sample"],
            "skipped_because_previous_nonce_absent": chain["skipped_because_previous_nonce_absent"],
            "verified_present_links": chain["verified"],
            "continuous_from_start_through_tail": continuous,
            "tail_link_matches": chain["tail_link_matches"],
            "algorithm": chain["algorithm"],
            "source": chain["source"],
        },
        "checkpoints": {
            "query_closed": checkpoints["closed"],
            "query_error": checkpoints["error"],
            "edge_count": checkpoints["edge_count"],
            "bind": binds,
            "all_three_match": bind_ok,
        },
        "p1_tail": {
            "nonce": TAIL_NONCE,
            "assignment_id": TAIL_ASSIGNMENT,
            "hash_chain": TAIL_HASH,
            "message_id": TAIL_MESSAGE,
            "spots": spots,
            "all_match": tail_ok,
        },
        "assignments_path": str(assignments_path),
        "assignments_bytes": assignments_path.stat().st_size,
        "assignments_sha256": sha256_bytes(assignments_path.read_bytes()),
        "graphql_pages": page_files,
        "bound": continuous and bind_ok and tail_ok,
    }
    message_files = []
    for item in messages:
        message_files.append({
            "nonce": item.get("nonce"),
            "assignment_id": item.get("assignment_id"),
            "message_id": item.get("message_id"),
            "stored": bool(item.get("stored")),
            "path": item.get("ans104_path"),
            "bytes": item.get("bytes"),
            "sha256": item.get("sha256"),
            "data_path": item.get("data_path"),
            "data_bytes": item.get("data_bytes"),
            "data_sha256": item.get("data_sha256"),
            "signature_id_matches": item.get("signature_id_matches"),
            "signature_valid": item.get("signature_valid"),
            "owner_address": item.get("owner_address"),
            "target": item.get("target"),
            "anchor": item.get("anchor"),
            "tags": item.get("tags"),
            "error": item.get("error"),
            "data_http_status": (item.get("data_http") or {}).get("http_status"),
            "data_url": (item.get("data_http") or {}).get("url"),
        })
    messages_manifest = {
        "run_id": run_id,
        "process_id": PROCESS_ID,
        "module_executed": False,
        "expected_messages": len(messages),
        "stored": len(stored),
        "signature_valid": len(valid),
        "missing_count": len(missing_messages),
        "missing": [
            {
                "nonce": item.get("nonce"),
                "assignment_id": item.get("assignment_id"),
                "message_id": item.get("message_id"),
                "error": item.get("error"),
            }
            for item in missing_messages
        ],
        "files": message_files,
    }
    write_json(evidence / "range-manifest.json", range_manifest)
    write_json(evidence / "messages-manifest.json", messages_manifest)
    write_json(evidence / "assignments.json", [row_public(row) for row in sorted(diff.unique.values(), key=lambda row: row.nonce)])
    bound_text = "yes" if range_manifest["bound"] else "no"
    summary = f"""# Checkpoint to tail

Run `{run_id}-w-tail`. Process `{PROCESS_ID}`. The module was not executed.

Nonce set {START}..{END} inclusive is {END - START + 1} nonces. Indexed {len(diff.unique)}. Missing {len(diff.missing)}. Conflicts {len(diff.conflicts)}. Contiguous: {not diff.missing and not diff.conflicts}.

Hash chain: {chain['links_matched']} matched, {chain['links_mismatched']} failed, {chain['links_checked']} checked. Continuous through the tail: {continuous}.

Checkpoint Assignment and Hash-Chain tags match the indexed assignment at 2074508, 2074510, and 2074518: {bind_ok}.

P1 tail nonce {TAIL_NONCE} assignment `{TAIL_ASSIGNMENT}` hash `{TAIL_HASH}` message `{TAIL_MESSAGE}` matches this index, including 2075920..2075922: {tail_ok}.

Messages stored {len(stored)} of {len(messages)}. Signature verified {len(valid)}. Missing {len(missing_messages)}.

Bound checkpoint to tail: {bound_text}.

## Evidence

- `evidence/p4-tail/{run_id}-w-tail/range-manifest.json`
- `evidence/p4-tail/{run_id}-w-tail/messages-manifest.json`
- `evidence/p4-tail/{run_id}-w-tail/assignments.json`
- Raw GraphQL bodies and ANS-104 items: `{raw}`

## Unfinished

- This run does not replay the process and does not produce a balance ledger. `goal_complete` stays false.
- Checkpoint bytes were not downloaded. The bind uses the Checkpoint tags and the assignment index.
- A GraphQL miss is not proof a nonce was never published. Missing nonces, if any, are listed in the range manifest.
"""
    atomic_write(evidence / "SUMMARY.md", summary.encode("utf-8"))
    print(f"DONE bound={bound_text} evidence={evidence}", flush=True)


if __name__ == "__main__":
    main()

"""Pull nonces 5770..5793 out of the bundle GraphQL did not fully index."""

from __future__ import annotations

import json
from pathlib import Path

from recovery.ans104 import data_field, item_for_offset, nested_assignments, parse_bundle_header
from recovery.assignments import Assignment
from recovery.chunk_scan import fetch_json, iter_unpacked_chunks
from recovery.hashchain import link_matches

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "jMUfJeklmGk0IUTpsVbqasjfu6F8qoYyFOXBWECQ4P4"
HITS = ROOT / "data" / "raw" / "p4" / "gap-1543163-1543166" / f"1543166-{BUNDLE}.json"
DB = ROOT / "data" / "raw" / "p4" / "0-49999" / "20261016T175757Z-p4-0-49999" / "assignments.sqlite"


def bundle_bytes(tx_id: str, start_at: int, end_at: int) -> tuple[int, bytes]:
    """Return (file_start_offset, bytes covering [start_at, end_at))."""
    parts: list[bytes] = []
    file_at = 0
    blob_start = None
    for _cursor, piece, _start, _end in iter_unpacked_chunks(tx_id):
        next_at = file_at + len(piece)
        if next_at <= start_at:
            file_at = next_at
            continue
        if blob_start is None:
            blob_start = file_at
        parts.append(piece)
        file_at = next_at
        if file_at >= end_at:
            break
    if blob_start is None:
        raise RuntimeError("range not found in bundle")
    return blob_start, b"".join(parts)


def load_hits() -> list[dict]:
    payload = json.loads(HITS.read_text())
    if not payload.get("closed"):
        raise RuntimeError("bundle scan was not closed")
    return payload["nonce_hits"]


def recover() -> list[dict]:
    hits = load_hits()
    meta = fetch_json(f"https://arweave.net/tx/{BUNDLE}/offset")
    size = int(meta["size"])
    # Header is small relative to the payload. Read the count from the first bytes.
    header_start, header_prefix = bundle_bytes(BUNDLE, 0, 32)
    if header_start != 0:
        raise RuntimeError("bundle did not start at offset 0")
    count = int.from_bytes(header_prefix[:32], "little")
    header_len = 32 + 64 * count
    _, header = bundle_bytes(BUNDLE, 0, header_len)
    items = parse_bundle_header(header)
    covered = items[-1][0] + items[-1][1] if items else header_len
    if covered != size:
        raise RuntimeError(f"bundle items cover {covered} bytes, tx size is {size}")
    chosen = []
    for hit in hits:
        item = item_for_offset(items, hit["offset"])
        if item is None:
            raise RuntimeError(f"no item contains offset {hit['offset']}")
        chosen.append((hit, item))
    low = min(item[0] for _hit, item in chosen)
    high = max(item[0] + item[1] for _hit, item in chosen)
    base, blob = bundle_bytes(BUNDLE, low, high)
    records = []
    for hit, (data_offset, item_size, item_id) in chosen:
        start = data_offset - base
        item_bytes = blob[start:start + item_size]
        if len(item_bytes) != item_size:
            raise RuntimeError(f"short item at {data_offset}")
        # The top-level entry is a two-item bundle. Its own id is not the assignment id.
        inner = [row for row in nested_assignments(data_field(item_bytes)) if row["nonce"] == hit["nonce"]]
        if len(inner) != 1:
            raise RuntimeError(f"offset {hit['offset']} produced {len(inner)} nonce {hit['nonce']} assignments")
        row = inner[0]
        if row["process"] != "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8":
            raise RuntimeError("inner assignment is for a different process")
        records.append({
            "assignment_id": row["assignment_id"],
            "wrapper_id": item_id,
            "nonce": row["nonce"],
            "epoch": row["epoch"],
            "message_id": row["message_id"],
            "timestamp_ms": row["timestamp_ms"],
            "hash_chain": row["hash_chain"],
            "assignment_block_height": row["assignment_block_height"],
            "inclusion_height": 1543166,
        })
    records.sort(key=lambda row: row["nonce"])
    return records


def check_links(records: list[dict]) -> dict:
    import sqlite3
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    def one(nonce: int) -> Assignment:
        row = conn.execute(
            "SELECT assignment_id, nonce, epoch, message_id, timestamp_ms, hash_chain FROM assignment WHERE nonce=?",
            (nonce,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"sqlite missing nonce {nonce}")
        return Assignment(row[0], row[1], row[2], row[3], row[4], row[5], None, None, None, {})
    chain = [one(5769)]
    for record in records:
        chain.append(Assignment(
            record["assignment_id"], record["nonce"], record["epoch"], record["message_id"],
            record["timestamp_ms"], record["hash_chain"], None, None, None, {},
        ))
    chain.append(one(5794))
    conn.close()
    bad = []
    for previous, current in zip(chain, chain[1:]):
        if not link_matches(previous, current):
            bad.append(current.nonce)
    return {"checked": len(chain) - 1, "mismatched_nonces": bad}


if __name__ == "__main__":
    found = recover()
    print(json.dumps({
        "count": len(found),
        "nonces": [row["nonce"] for row in found],
        "links": check_links(found),
        "first": {key: found[0][key] for key in ("nonce", "assignment_id", "message_id", "hash_chain")},
    }, indent=2))
    out = ROOT / "data" / "raw" / "p4" / "gap-1543163-1543166" / "recovered-5770.json"
    out.write_text(json.dumps(found, indent=2))
    print("wrote", out)

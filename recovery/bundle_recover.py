"""Turn bundle nonce hits into inner assignment records.

GraphQL indexes the assignment inside the top-level bundle item, not the
top-level item itself. The id stored here is sha256(signature) of that inner
item. A scan that is not closed is not a source of records.
"""

from __future__ import annotations

from recovery.ans104 import data_field, item_for_offset, nested_assignments, parse_bundle_header
from recovery.bundle_scan import PROCESS_ID


def assignments_for_hits(read, hits: list[dict], *, size: int, process_id: str = PROCESS_ID) -> list[dict]:
    """Read only the bundle header and the items that contain `hits`.

    `read(start, end)` returns file bytes `[start, end)`. `hits` are
    `{nonce, offset}` into that file, as produced by `scan_stream`.
    """
    if size < 32:
        raise ValueError(f"bundle size {size} is shorter than a header count")
    count = int.from_bytes(read(0, 32), "little")
    header_len = 32 + 64 * count
    if count < 1 or header_len > size:
        raise ValueError(f"bundle count {count} does not fit in {size} bytes")
    items = parse_bundle_header(read(0, header_len))
    covered = items[-1][0] + items[-1][1]
    if covered != size:
        raise ValueError(f"bundle items cover {covered} bytes, size is {size}")
    found: dict[int, dict] = {}
    item_cache: dict[int, bytes] = {}
    for hit in hits:
        item = item_for_offset(items, int(hit["offset"]))
        if item is None:
            raise RuntimeError(f"no item contains offset {hit['offset']}")
        data_offset, item_size, wrapper_id = item
        if data_offset not in item_cache:
            item_bytes = read(data_offset, data_offset + item_size)
            if len(item_bytes) != item_size:
                raise RuntimeError(f"short item at {data_offset}")
            item_cache[data_offset] = item_bytes
        inner = [
            row for row in nested_assignments(data_field(item_cache[data_offset]))
            if row["nonce"] == int(hit["nonce"])
        ]
        if len(inner) != 1:
            raise RuntimeError(
                f"offset {hit['offset']} produced {len(inner)} nonce {hit['nonce']} assignments"
            )
        row = inner[0]
        if row["process"] != process_id:
            raise RuntimeError(f"nonce {row['nonce']} is for a different process")
        if row["assignment_id"] == wrapper_id:
            raise RuntimeError(f"nonce {row['nonce']} id is the wrapper id")
        record = {
            "assignment_id": row["assignment_id"],
            "wrapper_id": wrapper_id,
            "nonce": row["nonce"],
            "epoch": row["epoch"],
            "message_id": row["message_id"],
            "timestamp_ms": row["timestamp_ms"],
            "hash_chain": row["hash_chain"],
            "assignment_block_height": row["assignment_block_height"],
            "process": row["process"],
        }
        previous = found.get(record["nonce"])
        if previous is not None and previous["assignment_id"] != record["assignment_id"]:
            raise RuntimeError(f"two assignment ids for nonce {record['nonce']}")
        found[record["nonce"]] = record
    return [found[nonce] for nonce in sorted(found)]


def recover_closed_scan(scan: dict, read, *, process_id: str = PROCESS_ID) -> list[dict]:
    """Recover inner assignments from one closed bundle scan."""
    if not scan.get("closed"):
        raise RuntimeError(f"bundle scan is not closed: {scan.get('error')}")
    hits = list(scan.get("nonce_hits") or [])
    size = int(scan["bytes"])
    return assignments_for_hits(read, hits, size=size, process_id=process_id)


def recover_scan_payload(scan: dict, *, fetch=None) -> list[dict]:
    """Download the header and hit items of one closed scan and parse them.

    The assignment id is the inner id. The top-level bundle entry id is kept
    separately as `wrapper_id`.
    """
    from recovery.chunk_scan import TxBytes

    if not scan.get("closed"):
        raise RuntimeError(f"bundle scan is not closed: {scan.get('error')}")
    tx_id = scan.get("id") or scan.get("tx_id")
    if not tx_id:
        raise ValueError("scan has no bundle id")
    reader = TxBytes(tx_id, fetch=fetch) if fetch is not None else TxBytes(tx_id)
    if reader.size != int(scan["bytes"]):
        raise RuntimeError(f"gateway size {reader.size} != scanned bytes {scan['bytes']}")
    records = recover_closed_scan(scan, reader.read)
    for row in records:
        row["bundle_id"] = tx_id
        if scan.get("block") is not None:
            row["inclusion_height"] = int(scan["block"])
    return records


def anchored_link_report(existing, recovered) -> dict:
    """Every recovered nonce must match the neighbor on each side that is present.

    A nonce with no present neighbor is not anchored. A mismatch is not a gap.
    """
    from recovery.hashchain import link_matches

    known = {}
    conflicts = []
    for row in list(existing) + list(recovered):
        previous = known.get(row.nonce)
        if previous is not None and previous.assignment_id != row.assignment_id:
            conflicts.append(row.nonce)
            continue
        known.setdefault(row.nonce, row)
    mismatches = []
    unanchored = []
    for row in recovered:
        checks = []
        left = known.get(row.nonce - 1)
        right = known.get(row.nonce + 1)
        if left is not None:
            ok = link_matches(left, row)
            checks.append(ok)
            if not ok:
                mismatches.append({"nonce": row.nonce, "side": "previous"})
        if right is not None:
            ok = link_matches(row, right)
            checks.append(ok)
            if not ok:
                mismatches.append({"nonce": row.nonce, "side": "next"})
        if not checks:
            unanchored.append(row.nonce)
    return {
        "anchored": not mismatches and not unanchored and not conflicts and len(recovered) > 0,
        "mismatches": mismatches,
        "unanchored": unanchored,
        "conflicts": conflicts,
    }


def commit_if_links_match(conn, records: list[dict], source_file: str) -> dict:
    """Insert recovered rows only when each one links to a present neighbor.

    A failed check writes nothing. Missing neighbors stay missing; they are not
    filled with a zero or with the wrapper id.
    """
    from recovery.assignments import Assignment
    from recovery.p4_range import insert_rows, load_range_rows

    if not records:
        return {"inserted": 0, "anchored": False, "reason": "no records"}
    nonces = [int(row["nonce"]) for row in records]
    existing = load_range_rows(conn, min(nonces) - 1, max(nonces) + 1)
    recovered = [
        Assignment(
            assignment_id=row["assignment_id"],
            nonce=int(row["nonce"]),
            epoch=str(row["epoch"]),
            message_id=row["message_id"],
            timestamp_ms=str(row["timestamp_ms"]),
            hash_chain=row["hash_chain"],
            assignment_block_height=row.get("assignment_block_height"),
            inclusion_height=row.get("inclusion_height"),
            inclusion_timestamp=None,
            tags={},
        )
        for row in records
    ]
    report = anchored_link_report(existing, recovered)
    if not report["anchored"]:
        return {"inserted": 0, "anchored": False, "links": report}
    inserted = insert_rows(conn, recovered, source_file)
    return {"inserted": inserted, "anchored": True, "links": report}

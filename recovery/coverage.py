"""Nonce-set coverage for one inclusive range. Missing values stay missing."""

from __future__ import annotations


def window_passed_end(rows, requested_min: int, requested_max: int, end: int) -> bool:
    """True when every assignment actually included in the requested heights is past `end`.

    Rows the gateway returned from outside the requested heights do not keep
    the scan open. An empty in-window result does not mean the range ended.
    """
    inside = [
        row for row in rows
        if row.inclusion_height is not None and requested_min <= row.inclusion_height <= requested_max
    ]
    if not inside:
        return False
    return min(row.nonce for row in inside) > end


def missing_ranges(missing: list[int]) -> list[list[int]]:
    """Compress sorted missing nonces into inclusive [start, end] pairs."""
    if not missing:
        return []
    ordered = sorted(missing)
    ranges: list[list[int]] = []
    start = previous = ordered[0]
    for nonce in ordered[1:]:
        if nonce == previous + 1:
            previous = nonce
            continue
        ranges.append([start, previous])
        start = previous = nonce
    ranges.append([start, previous])
    return ranges


def coverage_report(
    start: int,
    end: int,
    nonce_ids: dict[int, list[str]],
) -> dict:
    """Compare an expected inclusive nonce range with the ids actually stored.

    `nonce_ids` maps a nonce to every distinct assignment id seen. One id is a
    match. Several ids are a conflict. Nonces outside the range are ignored
    for the missing-set, and listed separately so a scan that ran past the
    end is visible. Count equality is not treated as coverage.
    """
    if end < start:
        raise ValueError("end < start")
    expected_count = end - start + 1
    conflicts = {
        nonce: ids
        for nonce, ids in nonce_ids.items()
        if start <= nonce <= end and len(ids) > 1
    }
    present = {
        nonce
        for nonce, ids in nonce_ids.items()
        if start <= nonce <= end and len(ids) == 1
    }
    missing = [nonce for nonce in range(start, end + 1) if nonce not in present and nonce not in conflicts]
    outside = sorted(nonce for nonce in nonce_ids if nonce < start or nonce > end)
    return {
        "start": start,
        "end": end,
        "expected_count": expected_count,
        "unique_count": len(present),
        "missing_count": len(missing),
        "missing_ranges": missing_ranges(missing),
        "conflict_count": len(conflicts),
        "conflicts": {str(nonce): ids for nonce, ids in sorted(conflicts.items())},
        "outside_range_nonce_count": len(outside),
        "complete": not missing and not conflicts,
    }

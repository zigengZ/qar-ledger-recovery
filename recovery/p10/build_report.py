"""Build the P10 ledger, reconciliation, and Done-means report.

The builder does not execute the process module, does not move collateral,
and does not publish a claim list. A missing balance is left out. It is not
written as zero. Total supply is an input, never the sum of the same rows.

Class merge priority, highest first: bridge, lock, pool, user, process_unknown.
A bridge, lock, or pool label is kept when another source says user.
process_unknown is the class used when no source assigns a label.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0"
CHECKPOINT_ID = "ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk"
CHECKPOINT_NONCE = 2074518
CHECKPOINT_SIGNER = "WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk"
AMENDED_FLAGS = (
    "tail_fixed",
    "checkpoint_verified",
    "tail_inputs_complete",
    "runtime_reproducible",
    "available_checks_match",
    "independent_agreement",
    "ledger_complete",
    "ledger_delta_zero",
    "classification_disclosed",
)
LEGACY_FLAGS = (
    "tail_fixed",
    "schedule_covered",
    "inputs_complete",
    "runtime_reproducible",
    "available_checks_match",
    "ledger_complete",
    "ledger_delta_zero",
    "classification_sourced",
    "collateral_sourced",
    "collateral_reconciled",
)
DENOMINATION = 10**12
DRY_RUN_LABEL = "试运行，不是最终结果"
CLASS_PRIORITY = ("bridge", "lock", "pool", "user", "process_unknown")
CLASS_RANK = {name: index for index, name in enumerate(CLASS_PRIORITY)}
LEDGER_COLUMNS = ("address", "raw_balance", "human_balance", "class", "source")
DONE_MEANS = (
    "Tail assignment: process, epoch, nonce, message id, timestamp, and the query that shows no higher pushed nonce.",
    "Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.",
    f"Module id `{MODULE_ID}` bytes hashed, and the evaluator named.",
    "Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.",
    "Ledger rows: address, raw balance, human balance at 12 decimals.",
    "Sum of raw balances equals the process total supply at that nonce.",
    "Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.",
    "Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.",
)

_ROLE_EXACT = {
    "pool": "pool",
    "amm": "pool",
    "amm_pool": "pool",
    "pool_candidate": "pool",
    "dex_pool": "pool",
    "lock": "lock",
    "lockup": "lock",
    "locked": "lock",
    "stake": "lock",
    "staking": "lock",
    "vesting": "lock",
    "bridge": "bridge",
    "bridge_process": "bridge",
    "cross_chain": "bridge",
    "user": "user",
    "wallet": "user",
    "end_user": "user",
    "eoa": "user",
    "unknown": "process_unknown",
    "unknown_process": "process_unknown",
    "process": "process_unknown",
    "other": "process_unknown",
    "other_contract": "process_unknown",
    "token": "process_unknown",
    "token_process": "process_unknown",
}


def canonical_balance_sha256(balances: dict[str, int]) -> str:
    """Hash nonzero balances as sorted compact JSON with one trailing newline.

    Raw amounts are decimal strings. Zero rows are omitted. Key order is the
    address sort, not the input order.
    """
    body = {
        address: str(raw)
        for address, raw in sorted(balances.items())
        if raw != 0
    }
    payload = json.dumps(body, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def raw_to_human(raw: int) -> str:
    """Format a raw integer at exactly 12 decimal places.

    Division is integer divmod. Float is not used.
    """
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ValueError(f"raw balance is not a non-negative integer: {raw!r}")
    whole, frac = divmod(raw, DENOMINATION)
    return f"{whole}.{frac:012d}"


def human_to_raw(text: str) -> int:
    whole, sep, frac = text.partition(".")
    if sep != "." or not whole.isdigit() or len(frac) != 12 or not frac.isdigit():
        raise ValueError(f"human balance is not 12 decimal places: {text!r}")
    return int(whole) * DENOMINATION + int(frac)


def parse_raw(value) -> int:
    """Accept a canonical non-negative integer or digit string.

    Floats, scientific notation, blanks, and the word unknown are rejected.
    They are not coerced to zero.
    """
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise ValueError(f"raw balance is not an integer string: {value!r}")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"raw balance is negative: {value}")
        return value
    if not isinstance(value, str):
        raise ValueError(f"raw balance is not an integer string: {value!r}")
    text = value.strip()
    if text.lower() == "unknown" or text == "":
        raise ValueError("raw balance is unknown")
    if text.startswith("+"):
        text = text[1:]
    if not text.isdigit() or (len(text) > 1 and text.startswith("0")):
        raise ValueError(f"raw balance is not a canonical integer string: {value!r}")
    return int(text)


def parse_optional_raw(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "unknown", "null", "none"}:
        return None
    return parse_raw(value)


def merge_class(classes: list[str]) -> str:
    if not classes:
        raise ValueError("no class to merge")
    unknown = [item for item in classes if item not in CLASS_RANK]
    if unknown:
        raise ValueError(f"unknown class: {unknown}")
    return min(classes, key=lambda item: CLASS_RANK[item])


def map_role(role: str | None) -> str | None:
    if not isinstance(role, str):
        return None
    key = role.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in key:
        key = key.replace("__", "_")
    if not key:
        return None
    if key in _ROLE_EXACT:
        return _ROLE_EXACT[key]
    if key.endswith("_pool") or key.endswith("_amm"):
        return "pool"
    if key.endswith(("_lock", "_lockup", "_stake", "_staking", "_vesting")):
        return "lock"
    if key == "bridge" or key.endswith("_bridge"):
        return "bridge"
    return None


def _source_bits(record: dict) -> str:
    source = record.get("source") or record.get("class_source") or ""
    if not isinstance(source, str):
        source = json.dumps(source, ensure_ascii=False, sort_keys=True)
    bits = [source] if source else []
    if record.get("name"):
        bits.append(f"name:{record['name']}")
    if record.get("confidence"):
        bits.append(f"confidence:{record['confidence']}")
    return " ".join(str(bit) for bit in bits) or "source not stated"


def hits_from_record(record: dict) -> list[tuple[str, str]]:
    source = _source_bits(record)
    hits: list[tuple[str, str]] = []
    explicit = record.get("class")
    if isinstance(explicit, str) and explicit in CLASS_RANK:
        hits.append((explicit, source))
    elif isinstance(explicit, str) and explicit != "":
        hits.append(("process_unknown", f"unrecognized class {explicit}; {source}"))
    mapped = map_role(record.get("role")) if isinstance(record.get("role"), str) else None
    if mapped:
        hits.append((mapped, source))
    for extra in record.get("also") or []:
        if isinstance(extra, str):
            extra_class = map_role(extra)
            if extra_class:
                hits.append((extra_class, source))
    is_process = record.get("is_process", None)
    if not hits:
        if is_process is False:
            hits.append(("user", source if source != "source not stated" else "is_process false"))
        else:
            hits.append(("process_unknown", source))
    if is_process is True:
        kept = [hit for hit in hits if hit[0] != "user"]
        hits = kept or [("process_unknown", source)]
    return hits


def holder_disclosure(records: list[dict]) -> dict:
    """Count wallet and unknown_process labels without relabeling them."""
    unknown_process = 0
    unknown_process_as_user = 0
    wallet = 0
    for record in records:
        role = record.get("role")
        if not isinstance(role, str):
            continue
        key = role.strip().lower().replace("-", "_").replace(" ", "_")
        while "__" in key:
            key = key.replace("__", "_")
        if key == "unknown_process":
            unknown_process += 1
            if map_role(key) == "user":
                unknown_process_as_user += 1
        elif key == "wallet":
            wallet += 1
    return {
        "unknown_process": unknown_process,
        "unknown_process_as_user": unknown_process_as_user,
        "wallet": wallet,
    }


def read_agreement(path: Path) -> dict:
    data = read_json(path)
    sha = data.get("canonical_balances_sha256")
    if isinstance(sha, str) and len(sha) == 64 and all(ch in "0123456789abcdef" for ch in sha):
        return {"path": str(path), "kind": "sha256", "sha256": sha}
    comparison = data.get("comparison") if isinstance(data.get("comparison"), dict) else {}
    equal = comparison.get("equal")
    if equal is None:
        equal = data.get("equal")
    rows = data.get("rows")
    return {
        "path": str(path),
        "kind": "map",
        "equal": equal is True,
        "rows": rows if isinstance(rows, int) and not isinstance(rows, bool) else None,
        "sum_raw": data.get("sum_raw") if isinstance(data.get("sum_raw"), str) else None,
    }


def classify_holders(records: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        address = record.get("address")
        if not isinstance(address, str) or address == "":
            continue
        grouped.setdefault(address, []).append(record)
    classified = {}
    for address, group in grouped.items():
        hits: list[tuple[str, str]] = []
        for record in group:
            hits.extend(hits_from_record(record))
        classified[address] = {
            "class": merge_class([hit[0] for hit in hits]),
            "source": " | ".join(f"{kind}:{text}" for kind, text in hits),
        }
    return classified


def iter_holder_records(data) -> list[dict]:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = None
        for key in ("holders", "addresses", "rows"):
            if isinstance(data.get(key), list):
                records = data[key]
                break
        if records is None:
            records = []
            for key, value in data.items():
                if isinstance(value, str):
                    records.append({"address": key, "class": value})
                elif isinstance(value, dict):
                    record = dict(value)
                    record.setdefault("address", key)
                    records.append(record)
    else:
        raise ValueError("holders file is not a list or object")
    return [record for record in records if isinstance(record, dict)]


def iter_balance_items(data) -> list[dict]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("balances"), dict):
        return [{"address": key, "raw": value} for key, value in data["balances"].items()]
    elif isinstance(data, dict) and isinstance(data.get("balances"), list):
        items = data["balances"]
    elif isinstance(data, dict) and isinstance(data.get("rows"), list):
        items = data["rows"]
    elif isinstance(data, dict):
        return [{"address": key, "raw": value} for key, value in data.items()]
    else:
        raise ValueError("balances file is not a map or list")
    rows = []
    for item in items:
        if not isinstance(item, dict):
            rows.append({"address": None, "raw": item})
            continue
        raw = item.get("raw_balance", item.get("raw", item.get("balance")))
        rows.append({"address": item.get("address"), "raw": raw})
    return rows


def load_balance_rows(data) -> tuple[dict[str, int], list[dict]]:
    good: dict[str, int] = {}
    bad: list[dict] = []
    conflicts: set[str] = set()
    for item in iter_balance_items(data):
        address = item.get("address")
        raw_value = item.get("raw")
        if not isinstance(address, str) or address == "":
            bad.append({"address": address, "raw": _jsonish(raw_value), "reason": "missing address"})
            continue
        try:
            raw = parse_raw(raw_value)
        except ValueError as exc:
            bad.append({"address": address, "raw": _jsonish(raw_value), "reason": str(exc)})
            continue
        if address in conflicts:
            bad.append({"address": address, "raw": str(raw), "reason": "conflicting raw balances"})
            continue
        if address in good and good[address] != raw:
            conflicts.add(address)
            del good[address]
            bad.append({
                "address": address,
                "raw": str(raw),
                "reason": "conflicting raw balances; row omitted and not set to 0",
            })
            continue
        good[address] = raw
    return good, bad


def reconcile_sum(raws: list[int], supply: int | None) -> dict:
    total = 0
    for raw in raws:
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(f"raw balance is not a non-negative integer: {raw!r}")
        total += raw
    if supply is None:
        return {
            "sum_raw": str(total),
            "total_supply_raw": None,
            "sum_equals_total_supply": None,
            "ledger_delta_raw": None,
        }
    if isinstance(supply, bool) or not isinstance(supply, int) or supply < 0:
        raise ValueError("total supply is not a non-negative integer")
    delta = total - supply
    return {
        "sum_raw": str(total),
        "total_supply_raw": str(supply),
        "sum_equals_total_supply": delta == 0,
        "ledger_delta_raw": str(delta),
    }


def class_totals(rows: list[dict], classification_present: bool) -> dict:
    counts = {name: 0 for name in CLASS_PRIORITY}
    raws = {name: 0 for name in CLASS_PRIORITY}
    for row in rows:
        counts[row["class"]] += 1
        raws[row["class"]] += int(row["raw_balance"])
    totals = {}
    for name in CLASS_PRIORITY:
        if name != "process_unknown" and not classification_present:
            totals[name] = {"count": None, "raw": None, "status": "unclassified"}
        else:
            totals[name] = {
                "count": counts[name],
                "raw": str(raws[name]),
                "status": "present",
            }
    return totals


def _ratio_is_one(value) -> bool:
    return value in (1, "1", "1:1", "1/1")


def interpret_collateral(data, supply: int | None) -> dict:
    """Return one collateral-versus-supply delta, or unknown.

    raw_amount_now is not subtracted from supply. Different assets are not
    added together. Unknown stays null and is not reported as zero.
    """
    if data is None:
        return {
            "present": False,
            "asset": None,
            "holder": None,
            "raw_amount": None,
            "source": None,
            "delta_raw": None,
            "status": "unknown",
            "reason": "collateral.json was not provided. The gap is unknown.",
            "per_asset": [],
        }
    records = data if isinstance(data, list) else [data]
    if not records or not all(isinstance(record, dict) for record in records):
        return {
            "present": True,
            "asset": None,
            "holder": None,
            "raw_amount": None,
            "source": None,
            "delta_raw": None,
            "status": "unknown",
            "reason": "collateral.json has no asset object. The gap is unknown.",
            "per_asset": [],
        }
    per_asset = [_one_asset(record, supply) for record in records]
    if len(per_asset) != 1:
        return {
            "present": True,
            "asset": None,
            "holder": None,
            "raw_amount": None,
            "source": None,
            "delta_raw": None,
            "status": "unknown",
            "reason": "more than one collateral asset; raw units are not added together. The single gap is unknown.",
            "per_asset": per_asset,
        }
    one = per_asset[0]
    return {
        "present": True,
        "asset": one["asset"],
        "holder": one["holder"],
        "raw_amount": one["raw_amount"],
        "source": one["source"],
        "delta_raw": one["delta_raw"],
        "status": one["status"],
        "reason": one["reason"],
        "per_asset": per_asset,
    }


def _one_asset(record: dict, supply: int | None) -> dict:
    asset = record.get("asset")
    holder = record.get("holder")
    source = record.get("source")
    held_fields = {
        "eligible_held_raw": parse_optional_raw(record.get("eligible_held_raw")),
        "raw_amount_at_tail": parse_optional_raw(record.get("raw_amount_at_tail")),
        "raw_amount": parse_optional_raw(record.get("raw_amount")),
    }
    present_held = {key: value for key, value in held_fields.items() if value is not None}
    raw_now = parse_optional_raw(record.get("raw_amount_now"))
    if len(set(present_held.values())) > 1:
        held = None
        held_reason = "held raw fields disagree. The gap is unknown."
    elif len(present_held) == 1:
        held = next(iter(present_held.values()))
        held_reason = None
    else:
        held = None
        held_reason = "held raw amount at the tail is unknown."
        if raw_now is not None:
            held_reason = "only raw_amount_now is present. It is not subtracted from supply. The tail gap is unknown."
    required = parse_optional_raw(record.get("required_backing_raw"))
    if required is None and _ratio_is_one(record.get("ratio")) and supply is not None:
        required = supply
    if held is None or required is None:
        return {
            "asset": asset if isinstance(asset, str) and asset.lower() != "unknown" else None,
            "holder": holder if isinstance(holder, str) and holder.lower() != "unknown" else None,
            "raw_amount": None if held is None else str(held),
            "source": source if isinstance(source, str) and source.lower() != "unknown" else None,
            "required_backing_raw": None if required is None else str(required),
            "delta_raw": None,
            "status": "unknown",
            "reason": held_reason or "required backing is unknown, and the file does not state a 1:1 ratio. The gap is unknown.",
        }
    return {
        "asset": asset if isinstance(asset, str) and asset.lower() != "unknown" else None,
        "holder": holder if isinstance(holder, str) and holder.lower() != "unknown" else None,
        "raw_amount": str(held),
        "source": source if isinstance(source, str) else None,
        "required_backing_raw": str(required),
        "delta_raw": str(held - required),
        "status": "number",
        "reason": "delta_raw = eligible held raw - required backing raw.",
    }


def expand_ranges(ranges) -> tuple[list[int], bool]:
    seen: set[int] = set()
    overlap = False
    ordered: list[int] = []
    for pair in ranges or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"missing range is not a pair: {pair!r}")
        start, end = int(pair[0]), int(pair[1])
        if end < start:
            raise ValueError(f"missing range ends before it starts: {pair!r}")
        for nonce in range(start, end + 1):
            if nonce in seen:
                overlap = True
            else:
                seen.add(nonce)
                ordered.append(nonce)
    return ordered, overlap


def _add_gap(unindexed: list, start: int, end: int, first_nonce: int, tail_nonce: int) -> None:
    lo = max(start, first_nonce)
    hi = min(end, tail_nonce)
    if lo <= hi:
        unindexed.append([lo, hi])


def judge_continuity(ranges: list[dict], first_nonce: int, tail_nonce: int) -> dict:
    """A nonce is covered only by a counted index span or an explicit hole.

    An unindexed span is not filled by the checkpoint and is not a zero-length hole.
    """
    ordered = sorted(ranges, key=lambda item: (item["start"], item["end"]))
    overlaps = []
    for left, right in zip(ordered, ordered[1:]):
        if right["start"] <= left["end"]:
            overlaps.append({
                "left": [left["start"], left["end"]],
                "right": [right["start"], right["end"]],
            })
    unindexed = []
    cursor = first_nonce
    for item in ordered:
        if item["start"] > cursor:
            _add_gap(unindexed, cursor, item["start"] - 1, first_nonce, tail_nonce)
        cursor = max(cursor, item["end"] + 1)
    if cursor <= tail_nonce:
        _add_gap(unindexed, cursor, tail_nonce, first_nonce, tail_nonce)
    missing: list[int] = []
    inconsistent = []
    for item in ordered:
        missing.extend(item["missing_nonces"])
        if not item["consistent"]:
            inconsistent.append({"start": item["start"], "end": item["end"], "reason": item.get("reason")})
    met = (
        not overlaps
        and not unindexed
        and not inconsistent
        and bool(ordered)
        and ordered[0]["start"] <= first_nonce
        and cursor > tail_nonce
    )
    return {
        "met": met,
        "first_nonce": first_nonce,
        "tail_nonce": tail_nonce,
        "unindexed": unindexed,
        "overlaps": overlaps,
        "inconsistent_ranges": inconsistent,
        "missing_nonces": missing,
        "missing_count": len(missing),
        "ranges": [
            {
                "start": item["start"],
                "end": item["end"],
                "present_count": item.get("present_count"),
                "missing_count": len(item["missing_nonces"]),
                "consistent": item["consistent"],
                "source": item.get("source"),
            }
            for item in ordered
        ],
    }


def load_range_account(path: Path) -> dict:
    data = read_json(path)
    sibling = None
    if "nonce_set" in data and isinstance(data["nonce_set"], dict):
        nonce_set = data["nonce_set"]
        start = int(nonce_set["inclusive_start"])
        end = int(nonce_set["inclusive_end"])
        missing_ranges = nonce_set.get("missing_ranges") or []
        declared = nonce_set.get("missing_count")
        present = nonce_set.get("unique_count")
        expected = nonce_set.get("expected_count", end - start + 1)
    else:
        missing_ranges = _missing_ranges(data)
        declared = _declared_count(data)
        present = data.get("unique_nonces_in_range")
        coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
        if present is None:
            present = coverage.get("unique_count")
        span = data.get("range_inclusive")
        if span is None and coverage.get("start") is not None:
            span = [coverage["start"], coverage["end"]]
        sibling_path = path.parent / "range-manifest.json"
        if sibling_path != path and sibling_path.is_file() and (span is None or present is None):
            sibling = read_json(sibling_path)
            sib_coverage = sibling.get("coverage") if isinstance(sibling.get("coverage"), dict) else {}
            if span is None:
                span = sibling.get("range_inclusive")
            if present is None:
                present = sib_coverage.get("unique_count")
            if declared is None:
                declared = sib_coverage.get("missing_count")
        if span is None:
            raise ValueError(f"{path} has no range_inclusive")
        start, end = int(span[0]), int(span[1])
        expected = end - start + 1
        if isinstance(data.get("coverage"), dict) and data["coverage"].get("expected_count") is not None:
            expected = int(data["coverage"]["expected_count"])
        elif sibling and isinstance(sibling.get("coverage"), dict) and sibling["coverage"].get("expected_count") is not None:
            expected = int(sibling["coverage"]["expected_count"])
    nonces, overlap = expand_ranges(missing_ranges)
    reasons = []
    if overlap:
        reasons.append("missing ranges overlap")
    if declared is not None and int(declared) != len(nonces):
        reasons.append(f"declared missing count {declared} != expanded {len(nonces)}")
    if any(nonce < start or nonce > end for nonce in nonces):
        reasons.append("a missing nonce is outside the range")
    if present is not None and int(present) + len(nonces) != int(expected):
        reasons.append(f"present {present} + missing {len(nonces)} != expected {expected}")
    if present is None and len(nonces) != int(expected):
        reasons.append("present count is absent, so the range is not fully counted")
    return {
        "start": start,
        "end": end,
        "missing_ranges": missing_ranges,
        "missing_nonces": nonces,
        "present_count": None if present is None else int(present),
        "expected_count": int(expected),
        "consistent": not reasons,
        "reason": "; ".join(reasons),
        "source": str(path),
    }


def _missing_ranges(data: dict):
    if "missing_ranges" in data:
        return data["missing_ranges"]
    coverage = data.get("coverage")
    if isinstance(coverage, dict) and "missing_ranges" in coverage:
        return coverage["missing_ranges"]
    raise ValueError("no missing_ranges")


def _declared_count(data: dict):
    for key in ("missing_count", "still_missing"):
        if data.get(key) is not None:
            return data[key]
    coverage = data.get("coverage")
    if isinstance(coverage, dict):
        return coverage.get("missing_count")
    return None


def build_ledger_rows(
    balances: dict[str, int],
    holders: dict[str, dict] | None,
    balance_label: str,
    dry_run: bool,
) -> tuple[list[dict], list[dict], list[str]]:
    rows = []
    missing_from_holders = []
    prefix = "dry-run; " if dry_run else ""
    for address in sorted(balances):
        raw = balances[address]
        if holders is None:
            klass = "process_unknown"
            class_source = "holders-classified.json not provided"
        elif address not in holders:
            klass = "process_unknown"
            class_source = "address absent from holders-classified.json"
            missing_from_holders.append(address)
        else:
            klass = holders[address]["class"]
            class_source = holders[address]["source"]
        rows.append({
            "address": address,
            "raw_balance": str(raw),
            "human_balance": raw_to_human(raw),
            "class": klass,
            "source": f"{prefix}balance:{balance_label}; class:{klass}; class_source:{class_source}",
        })
    unresolved = []
    if holders is not None:
        for address in sorted(holders):
            if address not in balances:
                unresolved.append({
                    "address": address,
                    "class": holders[address]["class"],
                    "source": holders[address]["source"],
                    "raw_balance": None,
                    "reason": "classified address has no balance row; not entered as 0",
                })
    return rows, unresolved, missing_from_holders


def build_report(spec: dict) -> dict:
    spec = dict(spec)
    if not spec.get("canonical_balance_sha256"):
        spec["canonical_balance_sha256"] = canonical_balance_sha256(spec.get("balances") or {})
    balances = spec["balances"]
    holders = spec.get("holders")
    dry_run = bool(spec.get("dry_run"))
    rows, unresolved, missing_from_holders = build_ledger_rows(
        balances,
        holders,
        spec.get("balance_label") or "balances",
        dry_run,
    )
    for row in rows:
        if human_to_raw(row["human_balance"]) != int(row["raw_balance"]):
            raise ValueError(f"human balance does not round-trip: {row['address']}")
    classification_present = holders is not None
    totals = class_totals(rows, classification_present)
    supply = spec.get("supply_raw")
    summed = reconcile_sum([int(row["raw_balance"]) for row in rows], supply)
    collateral = interpret_collateral(spec.get("collateral"), supply)
    continuity = judge_continuity(
        spec.get("ranges") or [],
        int(spec.get("first_nonce", 0)),
        int(spec["tail_nonce"]),
    )
    proof = _continuity_proof(spec, continuity)
    items = evaluate_done_means(spec, rows, summed, collateral, continuity, missing_from_holders, unresolved)
    flags = evaluate_flags(spec, rows, items, summed, collateral, continuity)
    goal_complete = _goal_complete(spec, flags)
    return {
        "label": DRY_RUN_LABEL if dry_run else "P10 reconciliation",
        "dry_run": dry_run,
        "final_result": False if dry_run else goal_complete,
        "goal_complete": goal_complete,
        "publish_claims": False,
        "move_collateral": False,
        "not_a_claim_list": True,
        "process_id": spec.get("process_id", PROCESS_ID),
        "ledger_nonce": spec.get("ledger_nonce"),
        "tail_nonce": spec.get("tail_nonce"),
        "ledger_is_tail": spec.get("ledger_nonce") == spec.get("tail_nonce") and not dry_run,
        "rows": rows,
        "bad_balances": spec.get("bad_balances") or [],
        "unresolved_missing_balances": unresolved,
        "balance_addresses_missing_from_holders": missing_from_holders,
        "holder_balance_mismatches": spec.get("holder_balance_mismatches") or [],
        "sum": summed,
        "class_totals": totals,
        "classification_present": classification_present,
        "collateral": collateral,
        "continuity": continuity,
        "continuity_proof": proof,
        "done_means": items,
        "flags": flags,
        "inputs": spec.get("inputs") or [],
        "tail": spec.get("tail"),
        "module": spec.get("module"),
        "replay": spec.get("replay"),
        "checkpoint": spec.get("checkpoint"),
    }


def _goal_complete(spec: dict, flags: dict) -> bool:
    if spec.get("dry_run"):
        return False
    if spec.get("ledger_nonce") != spec.get("tail_nonce"):
        return False
    amended = flags.get("amended") or {}
    return all(amended.get(name) is True for name in AMENDED_FLAGS)


def evaluate_flags(
    spec: dict,
    rows: list[dict],
    items: list[dict],
    summed: dict,
    collateral: dict,
    continuity: dict,
) -> dict:
    """Amended 2026-10-18 flags, plus the old ten flags marked legacy.

    A legacy flag is not copied from an earlier JSON file. Each boolean is
    read from the loaded evidence. Collateral stays in the report and is not
    an amended gate.
    """
    dry_run = bool(spec.get("dry_run"))
    at_tail = spec.get("ledger_nonce") == spec.get("tail_nonce") and not dry_run
    tail = spec.get("tail") or {}
    module = spec.get("module") or {}
    replay = spec.get("replay") or {}
    checkpoint = spec.get("checkpoint") or {}
    proof = _continuity_proof(spec, continuity)
    chain = proof["checkpoint_to_tail"]
    disclosure = spec.get("holder_disclosure") or {}
    poolish = [row for row in rows if row["class"] in {"pool", "lock", "bridge"}]
    missing_source = [row["address"] for row in poolish if "class_source:" not in row["source"]]
    module_ok = bool(items[2]["met"]) if len(items) > 2 else False
    replay_met = bool(items[3]["met"]) if len(items) > 3 else False
    rows_met = bool(items[4]["met"]) if len(items) > 4 else False
    sum_met = bool(items[5]["met"]) if len(items) > 5 else False
    class_met = bool(items[6]["met"]) if len(items) > 6 else False
    tail_met = bool(items[0]["met"]) if items else False

    checkpoint_ok = (
        at_tail
        and checkpoint.get("id") == CHECKPOINT_ID
        and checkpoint.get("nonce") == CHECKPOINT_NONCE
        and checkpoint.get("signer") == CHECKPOINT_SIGNER
        and checkpoint.get("signer_matches_cu") is True
        and checkpoint.get("ans104_signature_valid") is True
        and checkpoint.get("sha256_tag_matches_uncompressed") is True
        and isinstance(checkpoint.get("uncompressed_sha256"), str)
        and checkpoint.get("uncompressed_sha256") != ""
    )
    window = chain.get("window") or [None, None]
    window_covers = (
        isinstance(window, list)
        and len(window) == 2
        and window[0] is not None
        and window[1] is not None
        and int(window[0]) <= CHECKPOINT_NONCE
        and int(window[1]) == spec.get("tail_nonce")
    )
    links_ok = (
        isinstance(chain.get("links_matched"), int)
        and chain.get("links_matched") == chain.get("links_checked")
        and chain.get("links_failed") == 0
        and chain.get("links_matched", 0) > 0
    )
    tail_inputs_ok = bool(
        at_tail
        and chain.get("continuous") is True
        and chain.get("checkpoint_inside_window") is True
        and window_covers
        and links_ok
    )
    computed = spec.get("canonical_balance_sha256")
    methods = []
    if isinstance(computed, str) and computed:
        methods.append("ledger")
    if (
        replay.get("balance_value_diff_vs_fast") == 0
        and replay.get("balance_addresses") == len(rows)
        and replay.get("balance_sum") == summed.get("sum_raw")
        and rows
    ):
        methods.append(replay.get("source") or "replay-comparison")
    for source in spec.get("agreement_sources") or []:
        if source.get("kind") == "sha256" and source.get("sha256") == computed:
            methods.append(source.get("path"))
        elif (
            source.get("kind") == "map"
            and source.get("equal") is True
            and source.get("rows") == len(rows)
            and source.get("sum_raw") == summed.get("sum_raw")
        ):
            methods.append(source.get("path"))
    distinct_methods = []
    for method in methods:
        if method and method not in distinct_methods:
            distinct_methods.append(method)
    independent_ok = at_tail and len(distinct_methods) >= 2
    disclosed_ok = (
        at_tail
        and spec.get("holders") is not None
        and not missing_source
        and disclosure.get("unknown_process_as_user", 0) == 0
    )
    unknown_processes = disclosure.get("unknown_process", 0)
    wallets = disclosure.get("wallet", 0)
    legacy_class = bool(class_met and unknown_processes == 0 and wallets == 0)
    legacy_collateral_sourced = bool(
        collateral.get("asset")
        and collateral.get("holder")
        and collateral.get("raw_amount") not in (None, "")
        and collateral.get("source")
    )
    amended = {
        "tail_fixed": tail_met,
        "checkpoint_verified": checkpoint_ok,
        "tail_inputs_complete": tail_inputs_ok,
        "runtime_reproducible": bool(at_tail and module_ok and replay_met),
        "available_checks_match": bool(at_tail and replay_met),
        "independent_agreement": independent_ok,
        "ledger_complete": rows_met,
        "ledger_delta_zero": sum_met and summed.get("ledger_delta_raw") == "0",
        "classification_disclosed": disclosed_ok,
    }
    legacy = {
        "tail_fixed": tail_met,
        "schedule_covered": continuity.get("met") is True,
        "inputs_complete": bool(module_ok and continuity.get("met") is True),
        "runtime_reproducible": bool(
            at_tail
            and replay.get("balances_written") is True
            and replay.get("compared_with_pushed_result") is True
            and _replay_reached_tail(replay, spec.get("tail_nonce"), checkpoint.get("nonce"))
        ),
        "available_checks_match": bool(at_tail and replay_met),
        "ledger_complete": rows_met,
        "ledger_delta_zero": sum_met and summed.get("ledger_delta_raw") == "0",
        "classification_sourced": legacy_class,
        "collateral_sourced": legacy_collateral_sourced,
        "collateral_reconciled": collateral.get("delta_raw") == "0",
    }
    return {
        "basis": "amendment-2026-10-18",
        "amended": amended,
        "legacy": legacy,
        "independent_methods": distinct_methods,
        "canonical_balance_sha256": computed,
        "collateral_in_conjunction": False,
    }


def _continuity_proof(spec: dict, continuity: dict) -> dict:
    tail = spec.get("tail") or {}
    checkpoint = spec.get("checkpoint") or {}
    window = tail.get("window")
    checkpoint_nonce = checkpoint.get("nonce")
    tail_nonce = spec.get("tail_nonce")
    inside = False
    if window and checkpoint_nonce is not None and tail_nonce is not None:
        inside = int(window[0]) <= int(checkpoint_nonce) <= int(tail_nonce) <= int(window[1])
    chain_ok = bool(tail.get("hash_chain_continuous")) and int(tail.get("links_failed") or 0) == 0
    bound = bool(tail.get("checkpoint_bound"))
    batches = []
    for item in spec.get("ranges") or []:
        if item.get("missing_nonces"):
            batches.append({
                "start": item["start"],
                "end": item["end"],
                "missing_count": len(item["missing_nonces"]),
                "missing_ranges": item.get("missing_ranges"),
                "missing_nonces": item["missing_nonces"],
                "source": item.get("source"),
            })
    return {
        "checkpoint_to_tail": {
            "method": "hash chain",
            "from_nonce": checkpoint_nonce,
            "to_nonce": tail_nonce,
            "window": window,
            "checkpoint_inside_window": inside,
            "links_matched": tail.get("links_matched"),
            "links_checked": tail.get("links_checked"),
            "links_failed": tail.get("links_failed"),
            "continuous": chain_ok and inside and bound,
            "checkpoint_bound": bound,
            "source": tail.get("hash_chain_source"),
        },
        "before_checkpoint": {
            "method": "CU-signed checkpoint",
            "nonce": checkpoint_nonce,
            "signer": checkpoint.get("signer"),
            "signer_matches_cu": checkpoint.get("signer_matches_cu"),
            "ans104_signature_valid": checkpoint.get("ans104_signature_valid"),
            "sha256_tag_matches_uncompressed": checkpoint.get("sha256_tag_matches_uncompressed"),
            "uncompressed_sha256": checkpoint.get("uncompressed_sha256"),
            "replay_start_accepted": checkpoint.get("replay_start_accepted"),
            "source": checkpoint.get("source"),
            "covers_state_not_a_nonce_index": True,
        },
        "explicit_missing_batches": batches,
        "unindexed": continuity["unindexed"],
        "first_through_tail_met": continuity["met"],
    }


def evaluate_done_means(
    spec: dict,
    rows: list[dict],
    summed: dict,
    collateral: dict,
    continuity: dict,
    missing_from_holders: list[str],
    unresolved: list[dict],
) -> list[dict]:
    dry_run = bool(spec.get("dry_run"))
    ledger_nonce = spec.get("ledger_nonce")
    tail_nonce = spec.get("tail_nonce")
    at_tail = ledger_nonce == tail_nonce and not dry_run
    tail = spec.get("tail") or {}
    module = spec.get("module") or {}
    replay = spec.get("replay") or {}
    paths = spec.get("paths") or {}

    tail_ok, tail_detail = _tail_detail(tail, paths)
    module_ok, module_detail = _module_detail(module, paths)
    continuity_detail = _continuity_detail(spec, continuity, paths)
    replay_ok, replay_detail = _replay_detail(
        replay, at_tail, tail_nonce, paths, spec.get("checkpoint") or {}
    )
    rows_ok, rows_detail = _rows_detail(spec, rows, at_tail, paths)
    sum_ok, sum_detail = _sum_detail(spec, summed, at_tail, paths)
    class_ok, class_detail = _class_detail(spec, rows, missing_from_holders, unresolved, at_tail, paths)
    collateral_ok, collateral_detail = _collateral_detail(collateral, at_tail, paths)
    flags = (
        tail_ok,
        continuity["met"],
        module_ok,
        replay_ok,
        rows_ok,
        sum_ok,
        class_ok,
        collateral_ok,
    )
    details = (
        tail_detail,
        continuity_detail,
        module_detail,
        replay_detail,
        rows_detail,
        sum_detail,
        class_detail,
        collateral_detail,
    )
    path_lists = (
        _present(paths.get("p1")),
        _present(paths.get("p4_tail"), paths.get("ranges")),
        _present(paths.get("p2"), paths.get("p6")),
        _present(paths.get("replay"), paths.get("p6")),
        _present(paths.get("balances")),
        _present(paths.get("balances"), paths.get("supply")),
        _present(paths.get("holders")),
        _present(paths.get("collateral")),
    )
    items = []
    for item, met, detail, item_paths in zip(DONE_MEANS, flags, details, path_lists):
        items.append({
            "item": item,
            "met": bool(met),
            "status": "满足" if met else "不满足",
            "paths": item_paths,
            "detail": detail,
        })
    return items


def _present(*values) -> list[str]:
    found = []
    for value in values:
        if isinstance(value, list):
            found.extend(str(item) for item in value if item)
        elif value:
            found.append(str(value))
    return found


def _tail_detail(tail: dict, paths: dict) -> tuple[bool, str]:
    if not tail:
        return False, "P1 tail evidence was not provided."
    required = {
        "process_id": tail.get("process_id"),
        "epoch": tail.get("epoch"),
        "nonce": tail.get("nonce"),
        "assignment_id": tail.get("assignment_id"),
        "message_id": tail.get("message_id"),
        "timestamp_utc": tail.get("timestamp_utc"),
        "no_higher_query": tail.get("no_higher_query"),
    }
    missing = [key for key, value in required.items() if value in (None, "")]
    if missing or tail.get("process_id") != PROCESS_ID:
        return False, f"Tail evidence is incomplete: {missing or 'process id mismatch'}."
    limit = tail.get("limit") or ""
    text = (
        f"process {tail['process_id']}, epoch {tail['epoch']}, nonce {tail['nonce']}, "
        f"assignment {tail['assignment_id']}, message {tail['message_id']}, "
        f"timestamp {tail['timestamp_utc']}, block {tail.get('block_height')}. "
        f"Query: {tail['no_higher_query']}."
    )
    if limit:
        text += f" Limit recorded by P1: {limit}"
    return True, text


def _module_detail(module: dict, paths: dict) -> tuple[bool, str]:
    if not module:
        return False, "Module hash and evaluator evidence were not both provided."
    same = module.get("sha256_p2") and module.get("sha256_p2") == module.get("sha256_eval")
    named = bool(module.get("evaluator_name") and module.get("evaluator_version"))
    right_id = module.get("module_id") == MODULE_ID
    if same and named and right_id:
        return True, (
            f"Module {MODULE_ID} sha256 {module['sha256_p2']}. "
            f"Evaluator {module['evaluator_name']} {module['evaluator_version']}."
        )
    return False, (
        f"module_id={module.get('module_id')}, p2 sha256={module.get('sha256_p2')}, "
        f"evaluator sha256={module.get('sha256_eval')}, "
        f"evaluator={module.get('evaluator_name')} {module.get('evaluator_version')}."
    )


def _continuity_detail(spec: dict, continuity: dict, paths: dict) -> str:
    proof = _continuity_proof(spec, continuity)
    chain = proof["checkpoint_to_tail"]
    before = proof["before_checkpoint"]
    batches = ", ".join(
        f"{item['start']}..{item['end']} missing {item['missing_count']}"
        for item in proof["explicit_missing_batches"]
    ) or "none loaded"
    unindexed = ", ".join(f"{start}..{end}" for start, end in continuity["unindexed"]) or "none"
    return (
        "检查点到尾部由哈希链证明："
        f"continuous={chain['continuous']}, window={chain['window']}, "
        f"links {chain['links_matched']}/{chain['links_checked']}, failed {chain['links_failed']}. "
        "检查点之前由 CU 签名的检查点覆盖，不是逐 nonce 索引："
        f"signature_valid={before['ans104_signature_valid']}, "
        f"signer_matches_cu={before['signer_matches_cu']}, "
        f"sha256_matches={before['sha256_tag_matches_uncompressed']}, "
        f"replay_start_accepted={before['replay_start_accepted']}. "
        f"显式缺失列表：{batches}. "
        f"未建索引、因此既不是存在也不是缺失列表的区间：{unindexed}. "
        + (
            "从第一条已推送 assignment 到尾部的 nonce 都落在已点数的区间或显式缺失列表里。"
            if continuity["met"]
            else "从第一条已推送 assignment 到尾部还没有被完整点数。"
        )
    )


def _replay_reached_tail(replay: dict, tail_nonce, checkpoint_nonce) -> bool:
    """True when the saved replay finished at the tail.

    A last-nonce object is used when it is present. A finished crosscheck can
    omit that object. Completion is then the exited process, zero handler
    errors, and an assignment count equal to tail nonce minus checkpoint nonce.
    This does not invent a last nonce.
    """
    last = replay.get("last_nonce")
    if last is not None:
        return last == tail_nonce
    if replay.get("exited") is not True or replay.get("handler_errors") != 0:
        return False
    assignments = replay.get("assignments")
    if isinstance(assignments, bool) or not isinstance(assignments, int):
        return False
    if isinstance(tail_nonce, bool) or not isinstance(tail_nonce, int):
        return False
    if isinstance(checkpoint_nonce, bool) or not isinstance(checkpoint_nonce, int):
        return False
    if assignments != tail_nonce - checkpoint_nonce:
        return False
    applied = replay.get("applied")
    next_index = replay.get("next_index")
    if isinstance(applied, int) and isinstance(next_index, int) and applied != next_index:
        return False
    return True


def _replay_detail(replay: dict, at_tail: bool, tail_nonce, paths: dict, checkpoint: dict | None = None) -> tuple[bool, str]:
    last = replay.get("last_nonce")
    written = replay.get("balances_written")
    semantic = replay.get("semantic_through_nonce")
    checkpoint_nonce = (checkpoint or {}).get("nonce")
    reached = _replay_reached_tail(replay, tail_nonce, checkpoint_nonce)
    text = (
        f"balances_written={written}, last saved assignment nonce={last}, "
        f"tail={tail_nonce}, semantic comparison through nonce {semantic}, "
        f"byte_gate={replay.get('byte_gate')}."
    )
    if last is None and reached:
        text += (
            " The crosscheck has no last-nonce object. "
            f"exited={replay.get('exited')}, assignments={replay.get('assignments')}, "
            f"checkpoint nonce={checkpoint_nonce}."
        )
    if replay.get("full_safe_mode_ran") is False:
        text += " Full safe mode was not run."
    if not replay:
        text = "No tail replay evidence was provided. " + text
    compared = replay.get("compared_with_pushed_result") is True
    if at_tail and written is True and reached and compared:
        return True, text
    return False, text + " Replay has not reached the tail and been checked."


def _rows_detail(spec: dict, rows: list[dict], at_tail: bool, paths: dict) -> tuple[bool, str]:
    bad = spec.get("bad_balances") or []
    format_ok = not bad and all(
        human_to_raw(row["human_balance"]) == int(row["raw_balance"]) for row in rows
    )
    text = (
        f"This table has {len(rows)} rows at nonce {spec.get('ledger_nonce')} "
        f"with address, raw_balance, and a 12-decimal human_balance. "
        f"format_ok={format_ok}. Bad rows omitted rather than set to 0: {len(bad)}. "
        f"Tail nonce is {spec.get('tail_nonce')}."
    )
    if spec.get("dry_run"):
        text = DRY_RUN_LABEL + ". " + text
    return bool(at_tail and format_ok and rows), text


def _sum_detail(spec: dict, summed: dict, at_tail: bool, paths: dict) -> tuple[bool, str]:
    text = (
        f"At ledger nonce {spec.get('ledger_nonce')}: sum_raw={summed['sum_raw']}, "
        f"total_supply_raw={summed['total_supply_raw']}, "
        f"sum_equals_total_supply={summed['sum_equals_total_supply']}, "
        f"ledger_delta_raw={summed['ledger_delta_raw']}. "
        f"Supply source: {spec.get('supply_source')}. "
        "The sum is not used as the supply."
    )
    if spec.get("dry_run"):
        text += f" {DRY_RUN_LABEL}. The tail supply is not this number."
    met = bool(at_tail and summed.get("sum_equals_total_supply") is True)
    return met, text


def _class_detail(spec, rows, missing_from_holders, unresolved, at_tail, paths) -> tuple[bool, str]:
    if spec.get("holders") is None:
        return False, (
            "holders-classified.json was not provided. No address is class user, pool, lock, or bridge. "
            "Those class totals are unknown, not zero."
        )
    poolish = [row for row in rows if row["class"] in {"pool", "lock", "bridge"}]
    missing_source = [row["address"] for row in poolish if "class_source:" not in row["source"]]
    text = (
        f"Classified ledger rows: pool/lock/bridge {len(poolish)}. "
        f"Balance addresses absent from the holders file: {len(missing_from_holders)}. "
        f"Classified addresses with no balance row, not filled as 0: {len(unresolved)}."
    )
    met = at_tail and not missing_from_holders and not missing_source
    if spec.get("dry_run"):
        met = False
        text = DRY_RUN_LABEL + ". " + text
    return met, text


def _collateral_detail(collateral: dict, at_tail: bool, paths: dict) -> tuple[bool, str]:
    text = (
        f"asset={collateral.get('asset')}, holder={collateral.get('holder')}, "
        f"raw_amount={collateral.get('raw_amount')}, source={collateral.get('source')}, "
        f"delta_raw={collateral.get('delta_raw')}, status={collateral.get('status')}. "
        f"{collateral.get('reason')}"
    )
    known = (
        collateral.get("status") == "number"
        and collateral.get("asset")
        and collateral.get("holder")
        and collateral.get("raw_amount") is not None
        and collateral.get("source")
        and collateral.get("delta_raw") is not None
    )
    met = bool(at_tail and known)
    if collateral.get("delta_raw") not in (None, "0") and met:
        text += " goal_complete stays false while this gap is not 0."
    return met, text


def render_report_md(result: dict) -> str:
    lines = []
    if result["dry_run"]:
        lines.append(f"# {DRY_RUN_LABEL}")
        lines.append("")
        lines.append("BLOCKED — NOT A CLAIM LIST")
        lines.append("")
        lines.append(
            f"This is a dry run of the P10 builder at nonce {result['ledger_nonce']}. "
            f"The tail nonce is {result['tail_nonce']}. This is not the final ledger."
        )
    else:
        title = "P10 reconciliation" if result["goal_complete"] else "BLOCKED — NOT A CLAIM LIST"
        lines.append(f"# {title}")
        lines.append("")
    lines.append(f"goal_complete: {str(result['goal_complete']).lower()}")
    lines.append("publish_claims: false")
    lines.append("move_collateral: false")
    lines.append("")
    lines.append("## Done means")
    lines.append("")
    for index, item in enumerate(result["done_means"], start=1):
        lines.append(f"### {index}. {item['item']}")
        lines.append("")
        lines.append(f"状态：{item['status']}")
        lines.append("")
        if item["paths"]:
            lines.append("证据：")
            for path in item["paths"]:
                lines.append(f"- `{path}`")
            lines.append("")
        else:
            lines.append("证据：没有提供对应文件。")
            lines.append("")
        lines.append(item["detail"])
        lines.append("")
    lines.append("## Amended flags")
    lines.append("")
    lines.append("Basis: amendment 2026-10-18. Legacy flags are not the completion rule.")
    lines.append("")
    for name in AMENDED_FLAGS:
        lines.append(f"- {name}: {str(result['flags']['amended'][name]).lower()}")
    lines.append("")
    lines.append("## Legacy flags")
    lines.append("")
    for name in LEGACY_FLAGS:
        lines.append(f"- {name}: {str(result['flags']['legacy'][name]).lower()}")
    lines.append("")
    lines.append("Collateral is a report field. It is not an amended gate.")
    lines.append("")
    lines.append("## Numbers")
    lines.append("")
    summed = result["sum"]
    lines.append(f"- ledger nonce: {result['ledger_nonce']}")
    lines.append(f"- rows: {len(result['rows'])}")
    lines.append(f"- sum_raw: {summed['sum_raw']}")
    lines.append(f"- total_supply_raw: {summed['total_supply_raw']}")
    lines.append(f"- sum_equals_total_supply: {summed['sum_equals_total_supply']}")
    lines.append(f"- ledger_delta_raw: {summed['ledger_delta_raw']}")
    lines.append(f"- collateral delta_raw: {result['collateral']['delta_raw']}")
    lines.append(f"- collateral status: {result['collateral']['status']}")
    lines.append("")
    lines.append("Class totals are sums of ledger rows only. A missing row is not a zero in these totals.")
    lines.append("")
    for name in CLASS_PRIORITY:
        item = result["class_totals"][name]
        lines.append(f"- {name}: count {item['count']}, raw {item['raw']}, {item['status']}")
    lines.append("")
    lines.append(f"Unresolved classified addresses with no balance row: {len(result['unresolved_missing_balances'])}.")
    lines.append(f"Bad balance values omitted: {len(result['bad_balances'])}.")
    lines.append("")
    return "\n".join(lines)


def render_summary(result: dict, out_dir: Path) -> str:
    summed = result["sum"]
    collateral = result["collateral"]
    chain = result["continuity_proof"]["checkpoint_to_tail"]
    lines = [
        f"# {result['label']}",
        "",
        "## Conclusion",
        "",
        f"goal_complete is {str(result['goal_complete']).lower()}. publish_claims is false. move_collateral is false.",
        f"Ledger nonce {result['ledger_nonce']} has {len(result['rows'])} rows. "
        f"sum_raw {summed['sum_raw']}. total_supply_raw {summed['total_supply_raw']}. "
        f"sum_equals_total_supply {summed['sum_equals_total_supply']}. "
        f"ledger_delta_raw {summed['ledger_delta_raw']}.",
        f"Collateral delta_raw is {collateral['delta_raw']} ({collateral['status']}). {collateral['reason']}",
        f"Checkpoint-to-tail hash chain continuous={chain['continuous']}, "
        f"links {chain['links_matched']}/{chain['links_checked']}.",
        "The tail ledger is not in this directory." if result["dry_run"] else "See REPORT.md for each Done means line.",
        "",
        "## Numbers",
        "",
        f"- rows: {len(result['rows'])}",
        f"- bad balance values omitted: {len(result['bad_balances'])}",
        f"- classified addresses without a balance row: {len(result['unresolved_missing_balances'])}",
        f"- explicit missing nonces: {result['continuity']['missing_count']}",
        f"- unindexed spans: {result['continuity']['unindexed']}",
    ]
    for name in CLASS_PRIORITY:
        item = result["class_totals"][name]
        lines.append(f"- class {name}: count {item['count']}, raw {item['raw']}")
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- `{out_dir / 'ledger.csv'}`",
        f"- `{out_dir / 'reconciliation.json'}`",
        f"- `{out_dir / 'REPORT.md'}`",
        f"- `{out_dir / 'manifest.json'}`",
    ])
    for item in result["inputs"]:
        lines.append(f"- `{item['path']}` sha256 `{item['sha256']}` bytes {item['bytes']}")
    test_path = out_dir / "test-result.json"
    if test_path.is_file():
        lines.extend([
            "",
            "## Tests",
            "",
            "`python3 -m unittest tests.test_build_report -v` result is in `test-result.json` and `test-result.txt`.",
            "",
        ])
    lines.extend([
        "",
        "## Unfinished",
        "",
    ])
    for item in result["done_means"]:
        if not item["met"]:
            lines.append(f"- 不满足. {item['item']}")
    if not any(not item["met"] for item in result["done_means"]):
        lines.append("- No Done means line is unmet.")
    lines.append("")
    return "\n".join(lines)


def reconciliation_document(result: dict) -> dict:
    document = dict(result)
    document.pop("rows", None)
    document["ledger_csv"] = "ledger.csv"
    document["row_count"] = len(result["rows"])
    return document


def write_outputs(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    occupied = [
        path.name for path in out_dir.iterdir()
        if path.name not in {"test-result.txt", "test-result.json"}
    ]
    if occupied:
        raise SystemExit(f"output directory is not empty: {out_dir} contains {occupied}")
    ledger_path = out_dir / "ledger.csv"
    with ledger_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["rows"])
    report_path = out_dir / "REPORT.md"
    report_path.write_text(render_report_md(result), encoding="utf-8")
    summary_path = out_dir / "SUMMARY.md"
    summary_path.write_text(render_summary(result, out_dir), encoding="utf-8")
    recon = reconciliation_document(result)
    recon_path = out_dir / "reconciliation.json"
    _dump_json(recon_path, recon)
    output_paths = [ledger_path, recon_path, report_path, summary_path]
    for name in ("test-result.txt", "test-result.json"):
        candidate = out_dir / name
        if candidate.is_file():
            output_paths.append(candidate)
    manifest = {
        "dry_run": result["dry_run"],
        "label": result["label"],
        "goal_complete": result["goal_complete"],
        "files": [file_info(path) for path in output_paths],
        "inputs": result["inputs"],
    }
    _dump_json(out_dir / "manifest.json", manifest)


def _hashable_path(value: str) -> Path | None:
    path = Path(value.split("#", 1)[0])
    if path.is_file():
        return path
    return None


def file_info(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def read_json(path: Path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc


def _dump_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _jsonish(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _load_tail(p1_path: Path, p4_path: Path) -> dict:
    p1 = read_json(p1_path)
    tail = p1.get("tail") or {}
    manifest = read_json(p4_path if p4_path.is_file() else p4_path / "range-manifest.json")
    nonce_set = manifest.get("nonce_set") or {}
    chain = manifest.get("hash_chain") or {}
    bind = ((manifest.get("checkpoints") or {}).get("bind") or {})
    checkpoint_bind = bind.get("2074518") or bind.get(2074518) or {}
    absent = p1.get("absent_nonces") or []
    query = (
        f"gateway {p1.get('no_assignment_query_gateway')} found no assignment at block height "
        f">= {p1.get('no_assignment_at_block_height_gte')}; "
        f"gateway {p1.get('nonce_query_gateway')} absent nonces {absent}; "
        f"network height {p1.get('network_height_arweave_net_info')}"
    )
    return {
        "process_id": p1.get("process_id"),
        "epoch": tail.get("epoch"),
        "nonce": int(tail["nonce"]),
        "assignment_id": tail.get("id"),
        "message_id": tail.get("message"),
        "timestamp_utc": tail.get("timestamp_utc"),
        "block_height": tail.get("block_height"),
        "hash_chain": tail.get("hash_chain"),
        "no_higher_query": query,
        "limit": p1.get("limit"),
        "window": [nonce_set.get("inclusive_start"), nonce_set.get("inclusive_end")],
        "hash_chain_continuous": bool(chain.get("continuous_from_start_through_tail")) and nonce_set.get("contiguous") is True,
        "links_matched": chain.get("links_matched"),
        "links_checked": chain.get("links_checked"),
        "links_failed": chain.get("links_failed"),
        "checkpoint_bound": bool(checkpoint_bind.get("assignment_tag_matches") and checkpoint_bind.get("hash_chain_tag_matches")),
        "hash_chain_source": str(p4_path if p4_path.is_file() else p4_path / "range-manifest.json"),
    }


def _load_module(p2_path: Path | None, p6_path: Path | None) -> dict | None:
    if p2_path is None and p6_path is None:
        return None
    p2 = {}
    evaluator = {}
    if p2_path is not None:
        module_path = p2_path if p2_path.is_file() else p2_path / "module.json"
        p2 = read_json(module_path)
    if p6_path is not None:
        eval_path = p6_path if p6_path.is_file() else p6_path / "evaluator.json"
        evaluator = read_json(eval_path)
    return {
        "module_id": p2.get("module_id") or evaluator.get("moduleId"),
        "sha256_p2": p2.get("sha256"),
        "sha256_eval": evaluator.get("moduleSha256"),
        "evaluator_name": evaluator.get("name"),
        "evaluator_version": evaluator.get("version"),
        "executed": p2.get("executed"),
    }


def _load_checkpoint(p5_path: Path | None, acceptance_path: Path | None) -> dict | None:
    if p5_path is None:
        return None
    replay_path = p5_path if p5_path.is_file() else p5_path / "replay-start.json"
    data = read_json(replay_path)
    accepted = None
    source = str(replay_path)
    if acceptance_path is not None:
        acceptance = read_json(acceptance_path)
        accepted = acceptance.get("replay_start_accepted")
        source = f"{replay_path} ; {acceptance_path}"
    return {
        "nonce": data.get("nonce"),
        "signer": data.get("signer"),
        "signer_matches_cu": data.get("signer_matches_cu"),
        "ans104_signature_valid": data.get("ans104_signature_valid"),
        "sha256_tag_matches_uncompressed": data.get("sha256_tag_matches_uncompressed"),
        "uncompressed_sha256": data.get("uncompressed_sha256"),
        "id": data.get("id"),
        "assignment_id": data.get("assignment"),
        "hash_chain": data.get("hash_chain"),
        "replay_start_accepted": accepted,
        "source": source,
    }


def _compared_from_measurements(data: dict):
    """Use a recorded sha match and a zero balance diff. Do not invent either."""
    sha_match = data.get("memory_sha_matches_fast_and_clean_clone")
    diff = data.get("balance_value_diff_vs_fast")
    if sha_match is None and diff is None:
        return None
    diff_ok = type(diff) is int and diff == 0
    if sha_match is True and diff_ok:
        return True
    if sha_match is False or (type(diff) is int and diff != 0):
        return False
    return None


def _last_nonce(data: dict):
    for key in ("last_assignment_inside_save", "last"):
        last = data.get(key)
        if isinstance(last, dict) and last.get("nonce") is not None:
            return last.get("nonce")
    return None


def _load_replay(path: Path | None, p6_path: Path | None) -> dict:
    replay = {
        "balances_written": None,
        "last_nonce": None,
        "source": None,
        "semantic_through_nonce": None,
        "byte_gate": None,
        "compared_with_pushed_result": None,
        "full_safe_mode_ran": None,
    }
    if path is not None:
        data = read_json(path)
        compared = data.get("checked_against_pushed_result")
        if compared is None:
            compared = _compared_from_measurements(data)
        replay.update({
            "balances_written": data.get("balances_written"),
            "last_nonce": _last_nonce(data),
            "next_index": data.get("next_index"),
            "stream_total": data.get("stream_total"),
            "exited": data.get("exited"),
            "applied": data.get("applied"),
            "assignments": data.get("assignments"),
            "handler_errors": data.get("handler_errors"),
            "balance_value_diff_vs_fast": data.get("balance_value_diff_vs_fast"),
            "balance_addresses": data.get("balance_addresses"),
            "balance_sum": data.get("balance_sum"),
            "source": str(path),
            "compared_with_pushed_result": compared,
            "full_safe_mode_ran": data.get("full_safe_mode_ran"),
        })
    if p6_path is not None:
        semantic_path = p6_path / "semantic.json"
        if semantic_path.is_file():
            semantic = read_json(semantic_path)
            replay["semantic_gate"] = semantic.get("semanticGate")
            replay["byte_gate"] = semantic.get("byteGate")
            gates = semantic.get("gates") or []
            if gates:
                replay["semantic_through_nonce"] = gates[-1].get("toNonce")
            if replay["source"]:
                replay["source"] = f"{replay['source']} ; {semantic_path}"
            else:
                replay["source"] = str(semantic_path)
    return replay


def _holder_mismatches(balances: dict[str, int], records: list[dict]) -> list[dict]:
    mismatches = []
    for record in records:
        address = record.get("address")
        if address not in balances or "raw_balance" not in record:
            continue
        try:
            raw = parse_raw(record.get("raw_balance"))
        except ValueError:
            continue
        if raw != balances[address]:
            mismatches.append({
                "address": address,
                "balance_raw": str(balances[address]),
                "holder_raw": str(raw),
                "reason": "holder raw_balance differs from the balance table; the ledger keeps the balance table",
            })
    return mismatches


def assemble(args) -> dict:
    balance_path = Path(args.balances)
    balance_data = read_json(balance_path)
    balances, bad = load_balance_rows(balance_data)
    holders = None
    mismatches = []
    holder_records: list[dict] = []
    if args.holders:
        holder_path = Path(args.holders)
        holder_records = iter_holder_records(read_json(holder_path))
        holders = classify_holders(holder_records)
        mismatches = _holder_mismatches(balances, holder_records)
    agreement_sources = [read_agreement(Path(path)) for path in args.agreement]
    collateral = read_json(Path(args.collateral)) if args.collateral else None
    tail = _load_tail(Path(args.p1), Path(args.p4_tail)) if args.p1 and args.p4_tail else None
    module = _load_module(Path(args.p2) if args.p2 else None, Path(args.p6) if args.p6 else None)
    checkpoint = _load_checkpoint(
        Path(args.p5) if args.p5 else None,
        Path(args.acceptance) if args.acceptance else None,
    )
    ranges = [load_range_account(Path(path)) for path in args.closed_range]
    ranges.extend(load_range_account(Path(path)) for path in args.missing)
    if args.p4_tail:
        p4_path = Path(args.p4_tail)
        manifest = p4_path if p4_path.is_file() else p4_path / "range-manifest.json"
        ranges.append(load_range_account(manifest))
    replay = _load_replay(Path(args.replay) if args.replay else None, Path(args.p6) if args.p6 else None)
    supply = parse_optional_raw(args.total_supply) if args.total_supply is not None else None
    inputs = []
    for label, value in (
        ("balances", args.balances),
        ("holders", args.holders),
        ("collateral", args.collateral),
        ("p1", args.p1),
        ("p4_tail", args.p4_tail),
        ("p5", args.p5),
        ("p6", args.p6),
        ("p2", args.p2),
        ("acceptance", args.acceptance),
        ("replay", args.replay),
        ("supply_source", args.total_supply_source),
    ):
        hashed = _hashable_path(value) if value else None
        if hashed is not None:
            info = file_info(hashed)
            info["label"] = label
            inputs.append(info)
    for path in args.agreement:
        info = file_info(Path(path))
        info["label"] = "agreement"
        inputs.append(info)
    for path in list(args.missing) + list(args.closed_range):
        info = file_info(Path(path))
        info["label"] = "range"
        inputs.append(info)
    if args.p4_tail and Path(args.p4_tail).is_dir():
        manifest = Path(args.p4_tail) / "range-manifest.json"
        info = file_info(manifest)
        info["label"] = "p4_tail"
        inputs.append(info)
    if args.p6 and Path(args.p6).is_dir():
        for name in ("evaluator.json", "semantic.json"):
            candidate = Path(args.p6) / name
            if candidate.is_file():
                info = file_info(candidate)
                info["label"] = name
                inputs.append(info)
    tail_nonce = tail["nonce"] if tail else (int(args.tail_nonce) if args.tail_nonce else None)
    if tail_nonce is None:
        raise SystemExit("tail nonce is unknown; pass --p1 and --p4-tail, or --tail-nonce")
    return build_report({
        "dry_run": args.dry_run,
        "balances": balances,
        "bad_balances": bad,
        "holders": holders,
        "holder_disclosure": holder_disclosure(holder_records),
        "agreement_sources": agreement_sources,
        "holder_balance_mismatches": mismatches,
        "collateral": collateral,
        "supply_raw": supply,
        "supply_source": args.total_supply_source,
        "balance_label": args.balance_label or balance_path.name,
        "ledger_nonce": int(args.ledger_nonce) if args.ledger_nonce else None,
        "tail_nonce": tail_nonce,
        "first_nonce": 0,
        "tail": tail,
        "module": module,
        "checkpoint": checkpoint,
        "replay": replay,
        "ranges": ranges,
        "inputs": inputs,
        "paths": {
            "balances": args.balances,
            "holders": args.holders,
            "collateral": args.collateral,
            "p1": args.p1,
            "p4_tail": str(Path(args.p4_tail) / "range-manifest.json") if args.p4_tail and Path(args.p4_tail).is_dir() else args.p4_tail,
            "p2": args.p2,
            "p6": args.p6,
            "supply": args.total_supply_source,
            "replay": args.replay,
            "ranges": list(args.missing) + list(args.closed_range),
        },
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the P10 reconciliation report. Does not execute the module.")
    parser.add_argument("--balances", required=True)
    parser.add_argument("--holders")
    parser.add_argument("--collateral")
    parser.add_argument("--p1")
    parser.add_argument("--p4-tail")
    parser.add_argument("--p5")
    parser.add_argument("--p6")
    parser.add_argument("--p2")
    parser.add_argument("--acceptance")
    parser.add_argument("--replay")
    parser.add_argument("--agreement", action="append", default=[])
    parser.add_argument("--missing", action="append", default=[])
    parser.add_argument("--closed-range", action="append", default=[])
    parser.add_argument("--total-supply")
    parser.add_argument("--total-supply-source")
    parser.add_argument("--ledger-nonce")
    parser.add_argument("--tail-nonce")
    parser.add_argument("--balance-label")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = assemble(args)
    write_outputs(result, Path(args.out))
    print(json.dumps({
        "out": args.out,
        "dry_run": result["dry_run"],
        "goal_complete": result["goal_complete"],
        "rows": len(result["rows"]),
        "sum_raw": result["sum"]["sum_raw"],
        "sum_equals_total_supply": result["sum"]["sum_equals_total_supply"],
        "collateral_delta_raw": result["collateral"]["delta_raw"],
        "continuity_met": result["continuity"]["met"],
        "amended": result["flags"]["amended"],
        "legacy": result["flags"]["legacy"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

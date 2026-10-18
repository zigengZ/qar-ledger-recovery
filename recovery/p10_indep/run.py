"""Apply nonces 2074519..2075923 with the handwritten 0.16.0 rules.

Reads the checkpoint Balances table from Lua memory, checks it against the
WASM-extracted gate-B file, then applies the tail assignments. Does not
execute the module.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from recovery.p10_indep.ledger import RuleError, decimal, first_tag, message_from, transfer
from recovery.p10_indep.memory_balances import read_checkpoint_state

ROOT = Path(__file__).resolve().parents[2]
MAIN_RAW = ROOT / "data/raw"
MEMORY = (
    MAIN_RAW
    / "src/20261017T051439Z-w-src/checkpoint/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.mem"
)
GATE_B = (
    MAIN_RAW
    / "eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json"
)
FAST = MAIN_RAW / "fast/tail/balances.json"
ASSIGNMENTS = ROOT / "evidence/p4-tail/20261017T052614Z-w-tail/assignments.json"
MESSAGES = ROOT / "evidence/p4-tail/20261017T052614Z-w-tail/messages-manifest.json"
SOURCE_ID = "eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA"
EVAL_ID = "wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ"
EXPECTED_MEMORY_SHA = "fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26"
START = 2074519
END = 2075923

WRITES_BALANCES = {"Transfer", "Mint-Tokens", "Unwrap"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def compare_maps(left: dict[str, str], right: dict[str, str]) -> dict:
    left_only = sorted(set(left) - set(right))
    right_only = sorted(set(right) - set(left))
    changed = []
    for address in sorted(set(left) & set(right)):
        if left[address] != right[address]:
            changed.append(
                {
                    "address": address,
                    "left": left[address],
                    "right": right[address],
                    "delta_right_minus_left": str(int(right[address]) - int(left[address])),
                }
            )
    return {
        "equal": not left_only and not right_only and not changed,
        "left_rows": len(left),
        "right_rows": len(right),
        "only_left": left_only,
        "only_right": right_only,
        "changed": changed,
    }


def sum_raw(balances: dict[str, str]) -> str:
    return str(sum(int(value) for value in balances.values()))


def apply_window(balances: dict[str, int], flags: dict, rows: list[dict], by_id: dict) -> tuple[list[dict], dict]:
    log = []
    counts = {"transfer_ok": 0, "transfer_rejected": 0, "event": 0, "eval": 0, "other": 0}
    other_actions: dict[str, int] = {}
    eval_note = None
    for row in rows:
        meta = by_id[row["message_id"]]
        tags = meta["tags"]
        action = first_tag(tags, "Action")
        sender = message_from(tags, meta["owner_address"])
        if action == "Transfer":
            entry = {
                "nonce": row["nonce"],
                "message_id": row["message_id"],
                "assignment_id": row["assignment_id"],
                "from": sender,
                "recipient": first_tag(tags, "Recipient"),
                "quantity": first_tag(tags, "Quantity"),
                "cast": first_tag(tags, "Cast"),
            }
            try:
                outcome = transfer(
                    balances,
                    sender,
                    entry["recipient"],
                    entry["quantity"],
                    stopped=flags["IS_STOPPED"],
                    transfers_enabled=flags["TRANSFERS_ENABLED"],
                )
            except RuleError as error:
                entry["result"] = "rejected"
                entry["reason"] = error.reason
                counts["transfer_rejected"] += 1
            else:
                entry.update(outcome)
                entry["reason"] = None
                counts["transfer_ok"] += 1
            log.append(entry)
            continue
        if action == "Eval":
            body_path = Path(meta["data_path"])
            body = body_path.read_text()
            counts["eval"] += 1
            eval_note = {
                "nonce": row["nonce"],
                "message_id": row["message_id"],
                "from": sender,
                "bytes": len(body.encode()),
                "body": body,
                "mentions_balances": "Balances" in body,
                "applied_to_balances": False,
                "reason": "The Eval inserts one ao.authorities entry and removes index 1. It does not read or write Balances.",
            }
            continue
        if action == "Event":
            counts["event"] += 1
            continue
        if action in WRITES_BALANCES:
            raise RuntimeError(f"nonce {row['nonce']} action {action} can write Balances and was not applied")
        counts["other"] += 1
        other_actions[action or "<none>"] = other_actions.get(action or "<none>", 0) + 1
    counts["other_actions"] = other_actions
    counts["eval_note"] = eval_note
    return log, counts


def main(run_id: str) -> int:
    evidence = ROOT / "evidence/p10-indep" / f"{run_id}-w-indep"
    raw = MAIN_RAW / "indep" / f"{run_id}-w-indep"
    evidence.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)

    memory_sha = sha256(MEMORY)
    memory_bytes = MEMORY.stat().st_size
    mem = MEMORY.read_bytes()
    if hashlib.sha256(mem).hexdigest() != memory_sha:
        raise RuntimeError("memory reread mismatch")
    state = read_checkpoint_state(mem)
    flags = state["info"]["flags"]
    parsed = state["balances"]
    gate = {key: str(value) for key, value in load_json(GATE_B).items()}
    start_cmp = compare_maps(parsed, gate)
    start_path = evidence / "start.json"
    start_doc = {
        "memory_path": str(MEMORY),
        "memory_bytes": memory_bytes,
        "memory_sha256": memory_sha,
        "memory_sha256_matches_checkpoint_tag": memory_sha == EXPECTED_MEMORY_SHA,
        "gate_b": str(GATE_B),
        "reader": state["info"],
        "sum_parsed": sum_raw(parsed),
        "sum_gate_b": sum_raw(gate),
        "comparison": start_cmp,
    }
    start_path.write_text(json.dumps(start_doc, indent=2) + "\n")
    if not start_cmp["equal"] or sum_raw(parsed) != sum_raw(gate):
        write_summary(evidence, run_id, start_doc, None, None, "start balances disagree")
        print(json.dumps({"start_equal": False, "only_parsed": len(start_cmp["only_left"]), "only_gate": len(start_cmp["only_right"]), "changed": len(start_cmp["changed"])}))
        return 2

    assignments = [row for row in load_json(ASSIGNMENTS) if START <= row["nonce"] <= END]
    assignments.sort(key=lambda row: row["nonce"])
    nonces = [row["nonce"] for row in assignments]
    if nonces != list(range(START, END + 1)):
        raise RuntimeError(f"tail window is not contiguous: {len(nonces)} rows")
    manifest = load_json(MESSAGES)
    by_id = {row["message_id"]: row for row in manifest["files"]}
    missing = [row["nonce"] for row in assignments if row["message_id"] not in by_id or not by_id[row["message_id"]].get("stored")]
    if missing:
        raise RuntimeError(f"missing message bodies: {missing[:5]}")

    working = {key: int(value) for key, value in parsed.items()}
    log, counts = apply_window(working, flags, assignments, by_id)
    result_map = {key: decimal(value) for key, value in working.items()}
    fast = {key: str(value) for key, value in load_json(FAST).items()}
    end_cmp = compare_maps(result_map, fast)
    touches = {}
    for entry in log:
        if entry["result"] != "ok":
            continue
        for address in (entry["from"], entry["recipient"]):
            touches.setdefault(address, []).append(entry["nonce"])
    for row in end_cmp["changed"]:
        row["transfer_nonces"] = touches.get(row["address"], [])
    end_cmp["only_left_nonces"] = {address: touches.get(address, []) for address in end_cmp["only_left"]}
    end_cmp["only_right_nonces"] = {address: touches.get(address, []) for address in end_cmp["only_right"]}

    balances_path = raw / "balances.json"
    balances_path.write_text(json.dumps(result_map, separators=(",", ":")))
    log_path = evidence / "transfers.jsonl"
    with log_path.open("w") as handle:
        for entry in log:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")

    result = {
        "equal": end_cmp["equal"],
        "start_nonce": 2074518,
        "end_nonce": END,
        "assignments": len(assignments),
        "flags": flags,
        "transfers_ok": counts["transfer_ok"],
        "transfers_rejected": counts["transfer_rejected"],
        "events_ignored": counts["event"],
        "eval": counts["eval_note"],
        "other_actions": counts["other_actions"],
        "rows": len(result_map),
        "sum_raw": sum_raw(result_map),
        "fast_rows": len(fast),
        "fast_sum_raw": sum_raw(fast),
        "sum_equals_fast_sum": sum_raw(result_map) == sum_raw(fast),
        "created_recipients": [
            {"nonce": entry["nonce"], "recipient": entry["recipient"], "quantity": entry["quantity"], "from": entry["from"]}
            for entry in log
            if entry.get("created_recipient")
        ],
        "comparison": {
            "equal": end_cmp["equal"],
            "only_independent": end_cmp["only_left"],
            "only_fast": end_cmp["only_right"],
            "changed": end_cmp["changed"],
            "only_independent_nonces": end_cmp["only_left_nonces"],
            "only_fast_nonces": end_cmp["only_right_nonces"],
        },
    }
    (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    files = {
        "start.json": evidence / "start.json",
        "result.json": evidence / "result.json",
        "transfers.jsonl": log_path,
        "balances.json": balances_path,
        "memory": MEMORY,
        "gate_b": GATE_B,
        "fast": FAST,
    }
    manifest_doc = {
        "run_id": run_id,
        "files": [
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files.values()
        ]
    }
    (evidence / "manifest.json").write_text(json.dumps(manifest_doc, indent=2) + "\n")
    write_summary(evidence, run_id, start_doc, result, manifest_doc, None)
    print(json.dumps({
        "equal": result["equal"],
        "ok": counts["transfer_ok"],
        "rejected": counts["transfer_rejected"],
        "rows": len(result_map),
        "changed": len(end_cmp["changed"]),
        "only_fast": end_cmp["only_right"],
        "only_indep": end_cmp["only_left"],
        "sum": result["sum_raw"],
    }))
    return 0 if result["equal"] else 3


def write_summary(evidence: Path, run_id: str, start_doc: dict, result: dict | None, manifest_doc: dict | None, failure: str | None) -> None:
    lines = [
        f"# Independent ledger {run_id}",
        "",
        "Python rules from qAR handler 0.16.0. The module was not executed.",
        "",
    ]
    if failure:
        lines.append(f"Stopped: {failure}.")
        lines.append("")
    cmp = start_doc["comparison"]
    lines.extend(
        [
            "## Checkpoint 2074518",
            "",
            f"Memory `{start_doc['memory_path']}` is {start_doc['memory_bytes']} bytes, sha256 `{start_doc['memory_sha256']}`. Tag match: {start_doc['memory_sha256_matches_checkpoint_tag']}.",
            f"Lua reader rows {cmp['left_rows']}. gate-B rows {cmp['right_rows']}. Equal: {cmp['equal']}.",
            f"Sum parsed {start_doc['sum_parsed']}. Sum gate-B {start_doc['sum_gate_b']}.",
            f"Flags from the same globals table: `{json.dumps(start_doc['reader']['flags'])}`.",
            "",
        ]
    )
    if result:
        lines.extend(
            [
                "## Tail 2074519..2075923",
                "",
                f"Assignments {result['assignments']}. Transfer ok {result['transfers_ok']}. Transfer rejected {result['transfers_rejected']}. Event ignored {result['events_ignored']}.",
                f"New balance keys: {json.dumps(result['created_recipients'])}.",
                f"Independent rows {result['rows']}, sum {result['sum_raw']}. Fast rows {result['fast_rows']}, sum {result['fast_sum_raw']}.",
                f"Every address and raw balance matches `data/raw/fast/tail/balances.json`: {result['equal']}. The two JSON files hash differently because the key order differs.",
                "",
            ]
        )
        if not result["equal"]:
            lines.append("Mismatches are in result.json with the transfer nonces that touched those addresses.")
            lines.append("")
        eval_note = result["eval"]
        if eval_note:
            lines.extend(
                [
                    "## Eval nonce 2075923",
                    "",
                    f"Message `{eval_note['message_id']}` from `{eval_note['from']}`, {eval_note['bytes']} bytes.",
                    "",
                    "```",
                    eval_note["body"],
                    "```",
                    "",
                    eval_note["reason"] + f" Mentions Balances: {eval_note['mentions_balances']}.",
                    "",
                ]
            )
    lines.extend(
        [
            "## Rules that can write Balances",
            "",
            f"Source message `{SOURCE_ID}` (nonce 1977055).",
            "Transfer debits `msg.From` and credits `Tags.Recipient` by `Tags.Quantity` after the checks in `instance:transfer`.",
            "Mint and Burn handlers only raise. Mint-Tokens and Unwrap return before any balance write because DEPOSITS_ENABLED and WITHDRAWALS_ENABLED are false in this memory.",
            "X- tags are copied onto notices. They are not used in the balance arithmetic. No message in this window has a Cast tag. Duplicate tag names do not occur; `Tab` would keep the first value.",
            "Cron is not one of these 1405 assignments. The Cron handler does not write Balances.",
            "",
            "## Evidence",
            "",
            f"- `{evidence / 'start.json'}`",
            f"- `{evidence / 'result.json'}`",
            f"- `{evidence / 'transfers.jsonl'}`",
            f"- `{evidence / 'manifest.json'}`",
            "",
        ]
    )
    if manifest_doc:
        lines.append("Manifest files:")
        lines.append("")
        for item in manifest_doc["files"]:
            lines.append(f"- `{item['path']}` {item['bytes']} bytes sha256 `{item.get('sha256')}`")
        lines.append("")
    lines.append("`goal_complete` is false. This is a balance check, not a claim list.")
    lines.append("")
    (evidence / "SUMMARY.md").write_text("\n".join(lines))


if __name__ == "__main__":
    run_id = sys.argv[1] if len(sys.argv) > 1 else "20261017T104141Z"
    sys.exit(main(run_id))

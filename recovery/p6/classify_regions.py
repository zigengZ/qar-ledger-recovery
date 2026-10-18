#!/usr/bin/env python3
"""Classify byte differences between a gateway-height replay and its checkpoint.

Reads the two heaps, counts exact differing bytes (no gap merging), buckets
them, and compares retained cron / inbox / event strings. Does not modify
either memory.
"""
import gzip
import json
import re
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
RAW = _REPO / "data/raw/eval/20261017T052333Z-w-eval"
CK = _REPO / "data/raw/checkpoints"
OUT = RAW / "semantic"

GATES = [
    {
        "name": "A",
        "replay": RAW / "replay" / "gate-A-gateway.memory",
        "checkpoint": CK / "lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg.bin",
        "balances": OUT / "gate-A-balances-checkpoint.json",
    },
    {
        "name": "B",
        "replay": RAW / "replay" / "gate-B-gateway.memory",
        "checkpoint": CK / "ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.bin",
        "balances": OUT / "gate-B-balances-checkpoint.json",
    },
]

CRON_ID = re.compile(rb"X-Cron-Request-Id:(\d+)-(\d+)")
ANCHOR = re.compile(rb'"Anchor":"(\d+)"')
EVENT_AMOUNT = re.compile(
    rb'"(sender_balance_old|sender_balance_new|recipient_balance_old|recipient_balance_new)":"(\d+)"'
)
TRANSFERRED = re.compile(rb"Transferred (\d+) qAR")
QUANTITY = re.compile(rb'"Quantity","value":"(\d+)"')
HEIGHT_LOG = re.compile(rb"Updating latest block height: (\d+) -> (\d+)")
PAIR = re.compile(rb'"([A-Za-z0-9_-]{43})":"(\d+)"')


def load_checkpoint(path):
    return gzip.decompress(path.read_bytes())


def differing_spans(replay, checkpoint):
    """Yield [start, end) of exact differing runs. Equal megabyte chunks use memcmp."""
    left = memoryview(replay)
    right = memoryview(checkpoint)
    size = len(replay)
    chunk = 1 << 20
    offset = 0
    while offset < size:
        end = min(size, offset + chunk)
        if left[offset:end] == right[offset:end]:
            offset = end
            continue
        index = offset
        while index < end:
            if left[index] == right[index]:
                index += 1
                continue
            start = index
            while index < size and left[index] != right[index]:
                index += 1
            yield start, index
        offset = index if index > end else end


def exact_diff(replay, checkpoint):
    if len(replay) != len(checkpoint):
        raise SystemExit(f"length {len(replay)} != {len(checkpoint)}")
    runs = 0
    diff_bytes = 0
    first = None
    last = None
    buckets = [0] * ((len(replay) >> 20) + 1)
    classes = Counter()
    class_bytes = Counter()
    samples = {name: [] for name in ("cron-log", "inbox-or-event", "block-height", "binary", "other-text")}
    for start, index in differing_spans(replay, checkpoint):
        runs += 1
        length = index - start
        diff_bytes += length
        if first is None:
            first = start
        last = index
        cursor = start
        while cursor < index:
            bucket = cursor >> 20
            end = min(index, (bucket + 1) << 20)
            buckets[bucket] += end - cursor
            cursor = end
        kind = classify(replay, checkpoint, start, index)
        classes[kind] += 1
        class_bytes[kind] += length
        if len(samples[kind]) < 6:
            samples[kind].append(sample(replay, checkpoint, start, index))
    occupied = [{"mb": i, "diffBytes": n} for i, n in enumerate(buckets) if n]
    return {
        "bytes": len(replay),
        "exactDiffBytes": diff_bytes,
        "runs": runs,
        "firstDiff": first,
        "lastDiff": last,
        "occupiedMb": occupied,
        "classes": dict(classes),
        "classBytes": dict(class_bytes),
        "samples": samples,
    }


def classify(replay, checkpoint, start, end):
    ctx = replay[max(0, start - 96): min(len(replay), end + 96)] + checkpoint[max(0, start - 96): min(len(checkpoint), end + 96)]
    if b"X-Cron-Request-Id" in ctx or b"[Cron]" in ctx:
        return "cron-log"
    if (
        b"Anchor" in ctx
        or b"recipient_balance" in ctx
        or b"sender_balance" in ctx
        or b"Transferred " in ctx
        or b"Quantity" in ctx
    ):
        return "inbox-or-event"
    if b"Block-Height" in ctx:
        return "block-height"
    blob = replay[start:end] + checkpoint[start:end]
    printable = sum(1 for byte in blob if 32 <= byte < 127)
    if printable * 2 < len(blob):
        return "binary"
    return "other-text"


def sample(replay, checkpoint, start, end):
    def text(buf):
        window = buf[max(0, start - 40): min(len(buf), end + 40)]
        return "".join(chr(byte) if 32 <= byte < 127 else "." for byte in window)[:220]

    return {"start": start, "length": end - start, "replay": text(replay), "checkpoint": text(checkpoint)}


def bag(pattern, buf, group):
    return Counter(match.group(group).decode() for match in pattern.finditer(buf))


def bag_pairs(pattern, buf):
    return Counter(match.group(0).decode() for match in pattern.finditer(buf))


def counter_delta(left, right, limit=12):
    only_left = []
    only_right = []
    for key, count in left.items():
        delta = count - right.get(key, 0)
        if delta > 0:
            only_left.append({"value": key, "replayMinusCheckpoint": delta})
    for key, count in right.items():
        delta = count - left.get(key, 0)
        if delta > 0:
            only_right.append({"value": key, "checkpointMinusReplay": delta})
    only_left.sort(key=lambda item: item["value"])
    only_right.sort(key=lambda item: item["value"])
    return {
        "replayOnly": len(only_left),
        "checkpointOnly": len(only_right),
        "replayOnlySample": only_left[:limit],
        "checkpointOnlySample": only_right[:limit],
    }


def balance_pairs_inside_diffs(replay, checkpoint, balances):
    """Flag an address whose ASCII amount pair differs inside a diff window.

    The live Balances table is what the handler encodes. This only checks
    whether a stored JSON pair in the heap was rewritten.
    """
    amounts = {address: str(amount) for address, amount in balances.items()}
    flagged = []
    for match in PAIR.finditer(replay):
        address = match.group(1).decode()
        amount = match.group(2).decode()
        expected = amounts.get(address)
        if expected is None or amount == expected:
            continue
        start, end = match.span()
        if replay[start:end] != checkpoint[start:end]:
            flagged.append({"address": address, "replay": amount, "table": expected, "start": start})
            if len(flagged) >= 20:
                break
    return flagged


def main():
    reports = []
    for gate in GATES:
        replay = gate["replay"].read_bytes()
        checkpoint = load_checkpoint(gate["checkpoint"])
        balances = json.loads(gate["balances"].read_text())
        regions = exact_diff(replay, checkpoint)
        cron_replay = bag_pairs(CRON_ID, replay)
        cron_checkpoint = bag_pairs(CRON_ID, checkpoint)
        report = {
            "gate": gate["name"],
            "regions": {
                key: regions[key]
                for key in ("bytes", "exactDiffBytes", "runs", "firstDiff", "lastDiff", "classes", "classBytes")
            },
            "occupiedMb": regions["occupiedMb"],
            "samples": regions["samples"],
            "cronRequestIds": counter_delta(cron_replay, cron_checkpoint),
            "anchors": counter_delta(bag(ANCHOR, replay, 1), bag(ANCHOR, checkpoint, 1)),
            "eventAmounts": counter_delta(bag_pairs(EVENT_AMOUNT, replay), bag_pairs(EVENT_AMOUNT, checkpoint)),
            "transferred": counter_delta(bag(TRANSFERRED, replay, 1), bag(TRANSFERRED, checkpoint, 1)),
            "quantities": counter_delta(bag(QUANTITY, replay, 1), bag(QUANTITY, checkpoint, 1)),
            "heightLogs": counter_delta(bag_pairs(HEIGHT_LOG, replay), bag_pairs(HEIGHT_LOG, checkpoint)),
            "storedJsonPairsDifferingFromTable": balance_pairs_inside_diffs(replay, checkpoint, balances),
            "supplyStringOffsets": {
                "replay": [match.start() for match in re.finditer(b"189487568412204611", replay)],
                "checkpoint": [match.start() for match in re.finditer(b"189487568412204611", checkpoint)],
            },
        }
        reports.append(report)
        print(json.dumps({
            "gate": gate["name"],
            "exactDiffBytes": regions["exactDiffBytes"],
            "runs": regions["runs"],
            "firstDiff": regions["firstDiff"],
            "lastDiff": regions["lastDiff"],
            "classes": regions["classes"],
            "classBytes": regions["classBytes"],
            "cronOnly": report["cronRequestIds"]["replayOnly"],
            "cronCkpt": report["cronRequestIds"]["checkpointOnly"],
            "anchorOnly": [report["anchors"]["replayOnly"], report["anchors"]["checkpointOnly"]],
            "eventOnly": [report["eventAmounts"]["replayOnly"], report["eventAmounts"]["checkpointOnly"]],
            "transferredOnly": [report["transferred"]["replayOnly"], report["transferred"]["checkpointOnly"]],
            "pairFlags": len(report["storedJsonPairsDifferingFromTable"]),
            "occupiedMb": len(regions["occupiedMb"]),
        }, ensure_ascii=False))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "regions.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()

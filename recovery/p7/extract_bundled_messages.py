"""Find message data items inside the binary bundles of one block.

The scan uses the chunk API. A chunk 404 stays a gap and is not filled.
Message ids that are not found stay missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recovery.bundle_list import list_ao_bundles  # noqa: E402
from recovery.chunk_scan import TxBytes  # noqa: E402
from recovery.p7.message_item import raw_id, scan_reader  # noqa: E402


class Reporting:
    def __init__(self, inner: TxBytes):
        self.inner = inner
        self.size = inner.size
        self.gaps: list[list[int]] = []

    def read(self, start: int, end: int) -> bytes:
        return self.inner.read(start, end)

    def iter_pieces(self):
        count = 0
        for item in self.inner.iter_pieces():
            count += 1
            if count % 25 == 0:
                print(f"  chunks {count}", flush=True)
            yield item
        self.gaps = list(getattr(self.inner, "gaps", []) or [])
        print(f"  chunks {count} gaps {len(self.gaps)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--messages", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ao-only", action="store_true")
    args = parser.parse_args()
    wanted_rows = json.loads(args.messages.read_text())
    wanted = {raw_id(row["message_id"]): row["message_id"] for row in wanted_rows}
    listed = list_ao_bundles(args.height, args.height, max_pages=40)
    if not listed["closed"]:
        raise RuntimeError(f"bundle list is not closed: {listed.get('error')}")
    bundles = listed["bundles"]
    if args.ao_only:
        bundles = [bundle for bundle in bundles if bundle["ao_bundler"]]
    bundles.sort(key=lambda bundle: bundle["size"])
    found: dict[str, dict] = {}
    reports = []
    for bundle in bundles:
        if len(found) == len(wanted):
            break
        print(f"scan {bundle['id']} bytes {bundle['size']} ao {bundle['ao_bundler']}", flush=True)
        reader = Reporting(TxBytes(bundle["id"]))
        remaining = {raw: message_id for raw, message_id in wanted.items() if message_id not in found}
        result = scan_reader(reader, remaining)
        for message_id, item in result["found"].items():
            row = next(row for row in wanted_rows if row["message_id"] == message_id)
            try:
                text = item["data"].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"{message_id} data is not utf-8") from exc
            action = next((tag["value"] for tag in item["tags"] if tag["name"] == "Action"), None)
            found[message_id] = {
                **row,
                "owner": item["owner"],
                "signature": item["signature"],
                "anchor": item["anchor"],
                "tags": item["tags"],
                "data": text,
                "action": action,
                "data_size": len(item["data"]),
                "source_bundle": bundle["id"],
            }
            print(f"  found nonce {row['nonce']} {action} {len(item['data'])}", flush=True)
        reports.append({
            "bundle": bundle["id"],
            "size": bundle["size"],
            "ao_bundler": bundle["ao_bundler"],
            "found": sorted(result["found"]),
            "gaps": result["gaps"],
        })
    missing = [row for row in wanted_rows if row["message_id"] not in found]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "recovered.json").write_text(json.dumps(list(found.values())))
    (args.out / "scan.json").write_text(json.dumps({
        "height": args.height,
        "bundles_listed": len(listed["bundles"]),
        "bundles_scanned": len(reports),
        "found": len(found),
        "missing": missing,
        "reports": reports,
    }, indent=2) + "\n")
    print(json.dumps({"found": len(found), "missing": [row["nonce"] for row in missing]}))
    if missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

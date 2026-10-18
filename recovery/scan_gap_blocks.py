"""Stream every binary bundle in blocks 1543163..1543166 and search for the hole."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import urllib.request

from recovery.chunk_scan import scan_tx_chunks

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = (1543163, 1543164, 1543165, 1543166)
WANTED = set(range(5770, 5794)) | {5769, 5794}
RAW = ROOT / "data" / "raw" / "p4" / "gap-1543163-1543166"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bundle_list() -> list[dict]:
    query = """
    query($h:Int!){
      transactions(first:100, block:{min:$h, max:$h}){
        pageInfo { hasNextPage }
        edges { node { id data { size } tags { name value } } }
      }
    }
    """
    rows = []
    for height in BLOCKS:
        body = json.dumps({"query": query, "variables": {"h": height}}).encode()
        request = urllib.request.Request(
            "https://arweave.net/graphql",
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "qar-ledger-recovery"},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read())
        page = payload["data"]["transactions"]
        if page["pageInfo"]["hasNextPage"]:
            raise RuntimeError(f"block {height} tx page did not close")
        for edge in page["edges"]:
            node = edge["node"]
            tags = {item["name"]: item["value"] for item in node.get("tags") or []}
            if tags.get("Bundle-Format") != "binary":
                continue
            size = int((node.get("data") or {}).get("size") or 0)
            rows.append({
                "block": height,
                "id": node["id"],
                "size": int((node.get("data") or {}).get("size") or 0),
            })
    return rows


def write_result(row: dict, result: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{row['block']}-{row['id']}.json"
    partial = path.with_suffix(".json.part")
    body = json.dumps({**row, **result, "saved_at": utc_now()}, sort_keys=True).encode()
    with partial.open("wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def main() -> None:
    rows = bundle_list()
    rows.sort(key=lambda item: item["size"])
    print(f"bundles {len(rows)} bytes {sum(item['size'] for item in rows)}", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(scan_tx_chunks, row["id"], WANTED): row
            for row in rows
        }
        for future in as_completed(futures):
            row = futures[future]
            result = future.result()
            write_result(row, result)
            done += 1
            print(
                f"{done}/{len(rows)} block {row['block']} closed {result['closed']} "
                f"bytes {result['bytes']}/{row['size']} process {result['process_hit_count']} "
                f"nonces {result['nonce_hits'][:6]} err {result['error']}",
                flush=True,
            )


if __name__ == "__main__":
    main()

"""Fetch one P7 nonce segment's message bodies and the Arweave blocks between them.

Bodies and block pages stay under data/raw/. A failed fetch is recorded and the
script exits non-zero. An unread body is not stored as an empty string.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recovery.gql import post_graphql  # noqa: E402

DB = ROOT / "data/raw/p4/0-49999/20261016T175757Z-p4-0-49999/assignments.sqlite"
IDS_QUERY = """
query($ids:[ID!]!) {
  transactions(ids: $ids, first: 20) {
    edges {
      node {
        id
        signature
        anchor
        owner { address }
        tags { name value }
        data { size }
      }
    }
  }
}
"""
BLOCK_QUERY = """
query($min:Int!, $max:Int!, $after:String) {
  blocks(first: 100, after: $after, sort: HEIGHT_ASC, height: { min: $min, max: $max }) {
    pageInfo { hasNextPage }
    edges { cursor node { height timestamp } }
  }
}
"""


def gql(query: str, variables: dict) -> dict:
    response = post_graphql(query, variables)
    if not response.ok or response.parsed is None:
        raise RuntimeError(f"graphql http {response.http_status} {response.error}")
    return response.parsed["data"]


def fetch_bytes(tx_id: str) -> bytes:
    request = urllib.request.Request(
        f"https://arweave.net/{tx_id}",
        headers={"User-Agent": "qar-ledger-recovery"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        if int(response.status) != 200:
            raise RuntimeError(f"{tx_id} http {response.status}")
        return response.read()


def load_rows(start: int, end: int) -> list[dict]:
    conn = sqlite3.connect(DB)
    rows = []
    for record in conn.execute(
        """
        SELECT nonce, epoch, assignment_id, message_id, timestamp_ms,
               assignment_block_height, hash_chain
        FROM assignment
        WHERE nonce BETWEEN ? AND ?
        ORDER BY nonce
        """,
        (start, end),
    ):
        rows.append({
            "nonce": int(record[0]),
            "epoch": record[1],
            "assignment_id": record[2],
            "message_id": record[3],
            "timestamp_ms": record[4],
            "assignment_block_height": record[5],
            "hash_chain": record[6],
        })
    conn.close()
    expected = list(range(start, end + 1))
    got = [row["nonce"] for row in rows]
    if got != expected:
        missing = sorted(set(expected) - set(got))
        raise RuntimeError(f"index is not contiguous for {start}..{end}; first missing {missing[:8]}")
    return rows


def fetch_blocks(min_height: int, max_height: int) -> list[dict]:
    blocks = []
    after = None
    seen = set()
    while True:
        data = gql(BLOCK_QUERY, {"min": min_height, "max": max_height, "after": after})
        page = data["blocks"]
        edges = page["edges"]
        if not edges and page["pageInfo"]["hasNextPage"]:
            raise RuntimeError("block page returned no edges while hasNextPage is true")
        for edge in edges:
            node = edge["node"]
            height = int(node["height"])
            if height in seen:
                continue
            seen.add(height)
            blocks.append({"height": height, "timestamp": int(node["timestamp"])})
            after = edge["cursor"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        if after is None:
            raise RuntimeError("block page has a next page and no cursor")
    blocks.sort(key=lambda block: block["height"])
    if not blocks or blocks[0]["height"] != min_height or blocks[-1]["height"] != max_height:
        raise RuntimeError(f"block span {blocks[0]['height'] if blocks else None}..{blocks[-1]['height'] if blocks else None} != {min_height}..{max_height}")
    if [block["height"] for block in blocks] != list(range(min_height, max_height + 1)):
        raise RuntimeError("block heights are not contiguous")
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = load_rows(args.start, args.end)
    by_id = {}
    for offset in range(0, len(rows), 20):
        chunk = [row["message_id"] for row in rows[offset:offset + 20]]
        data = gql(IDS_QUERY, {"ids": chunk})
        for edge in data["transactions"]["edges"]:
            by_id[edge["node"]["id"]] = edge["node"]
    missing = [row for row in rows if row["message_id"] not in by_id]
    if missing:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "unresolved.json").write_text(json.dumps({
            "start": args.start,
            "end": args.end,
            "resolved": len(rows) - len(missing),
            "missing": [
                {"nonce": row["nonce"], "message_id": row["message_id"], "assignment_id": row["assignment_id"]}
                for row in missing
            ],
        }, indent=2) + "\n")
        raise RuntimeError(
            f"{len(missing)} message ids are absent from transactions(ids); "
            f"first nonce {missing[0]['nonce']}. See {args.out / 'unresolved.json'}"
        )
    messages = []
    for row in rows:
        tx = by_id[row["message_id"]]
        size = int(tx["data"]["size"])
        body = fetch_bytes(row["message_id"])
        if len(body) != size:
            raise RuntimeError(f"nonce {row['nonce']} body {len(body)} != graphql {size}")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"nonce {row['nonce']} body is not utf-8") from exc
        tags = [{"name": tag["name"], "value": tag["value"]} for tag in tx["tags"]]
        action = next((tag["value"] for tag in tags if tag["name"] == "Action"), None)
        messages.append({
            **row,
            "owner": tx["owner"]["address"],
            "signature": tx["signature"],
            "anchor": tx["anchor"] or "",
            "tags": tags,
            "data": text,
            "action": action,
            "data_size": size,
        })
        print(f"message {row['nonce']} {action} {size}", flush=True)
    heights = [int(row["assignment_block_height"]) for row in rows]
    blocks = fetch_blocks(min(heights), max(heights))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "messages.json").write_text(json.dumps(messages))
    (args.out / "blocks.json").write_text(json.dumps(blocks))
    print(json.dumps({
        "messages": len(messages),
        "blocks": len(blocks),
        "height": [blocks[0]["height"], blocks[-1]["height"]],
    }))


if __name__ == "__main__":
    main()

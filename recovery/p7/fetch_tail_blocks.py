"""Fetch the Arweave blocks the tail replay uses for cron Block-Height.

Pages are written as they arrive. A failed page is recorded and the script
exits non-zero. Missing heights are not invented.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recovery.gql import post_graphql  # noqa: E402

QUERY = """
query($min:Int!, $max:Int!, $after:String) {
  blocks(first: 100, after: $after, sort: HEIGHT_ASC, height: { min: $min, max: $max }) {
    pageInfo { hasNextPage }
    edges { cursor node { height timestamp } }
  }
}
"""


def page(min_height: int, max_height: int, after: str | None) -> dict:
    response = post_graphql(QUERY, {"min": min_height, "max": max_height, "after": after})
    if not response.ok or response.parsed is None:
        raise RuntimeError(f"graphql http {response.http_status} {response.error} after {after}")
    return response.parsed["data"]["blocks"]


def main() -> None:
    out = ROOT / "data/raw/p7/tail-blocks"
    out.mkdir(parents=True, exist_ok=True)
    min_height = 1863436
    max_height = 1951866
    # Walk cursors first so each page request is independent. The cursor is
    # the last height of the previous page, which is known from the span.
    spans = []
    height = min_height
    while height <= max_height:
        end = min(height + 99, max_height)
        spans.append((height, end))
        height = end + 1
    print(f"pages {len(spans)}", flush=True)
    blocks = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(page, start, end, None): (start, end) for start, end in spans}
        done = 0
        for future in as_completed(futures):
            start, end = futures[future]
            body = future.result()
            edges = body["edges"]
            got = [edge["node"] for edge in edges]
            if [node["height"] for node in got] != list(range(start, end + 1)):
                raise RuntimeError(f"page {start}..{end} returned count {len(got)}")
            if body["pageInfo"]["hasNextPage"]:
                raise RuntimeError(f"page {start}..{end} is not closed")
            for node in got:
                blocks.append({"height": int(node["height"]), "timestamp": int(node["timestamp"])})
            done += 1
            if done % 20 == 0 or done == len(spans):
                print(f"pages_done {done}", flush=True)
    blocks.sort(key=lambda item: item["height"])
    if [item["height"] for item in blocks] != list(range(min_height, max_height + 1)):
        raise RuntimeError("merged block heights are not contiguous")
    (out / "blocks.json").write_text(json.dumps(blocks))
    print(json.dumps({"blocks": len(blocks), "first": blocks[0], "last": blocks[-1]}))


if __name__ == "__main__":
    main()

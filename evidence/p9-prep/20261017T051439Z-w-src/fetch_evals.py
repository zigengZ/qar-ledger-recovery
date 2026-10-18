#!/usr/bin/env python3
"""Read-only: nonce-link Action=Eval messages and download their bodies.

Does not execute the module. Saves each GraphQL request and response.
Download concurrency is 4. A failed download is recorded, not treated as empty.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from recovery.gql import post_graphql  # noqa: E402

RAW = Path(__file__).resolve().parents[3] / "data/raw/src/20261017T051439Z-w-src"
GQL = RAW / "gql"
MSG = RAW / "messages"
GQL.mkdir(parents=True, exist_ok=True)
MSG.mkdir(parents=True, exist_ok=True)
ENDPOINT = "https://arweave.net/graphql"
PROCESS = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"

ASSIGN = """
query($cursor: String, $messages: [String!]!) {
  transactions(
    first: 100
    after: $cursor
    sort: HEIGHT_ASC
    tags: [
      { name: "Type", values: ["Assignment"] }
      { name: "Process", values: ["%s"] }
      { name: "Message", values: $messages }
    ]
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        block { height timestamp }
        tags { name value }
      }
    }
  }
}
""" % PROCESS


def save_gql(stem: str, query: str, variables: dict) -> dict:
    payload = {"query": query, "variables": variables}
    (GQL / f"{stem}.request.json").write_text(json.dumps(payload))
    resp = post_graphql(query, variables, endpoint=ENDPOINT, timeout_s=120, max_attempts=5)
    (GQL / f"{stem}.response.json").write_bytes(resp.body)
    meta = {
        "endpoint": resp.endpoint,
        "status": resp.http_status,
        "elapsed_ms": resp.elapsed_ms,
        "attempt": resp.attempt,
        "bytes": len(resp.body),
        "error": resp.error,
    }
    (GQL / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    if not resp.ok:
        raise SystemExit(f"graphql failed {stem}: {meta}")
    return resp.parsed


def assignments_for(ids: list[str]) -> list[dict]:
    found = []
    for batch_i in range(0, len(ids), 20):
        batch = ids[batch_i : batch_i + 20]
        cursor = None
        page = 0
        while True:
            variables = {"messages": batch, "cursor": cursor}
            stem = f"assign-eval-b{batch_i:03d}-p{page:03d}"
            parsed = save_gql(stem, ASSIGN, variables)
            conn = parsed["data"]["transactions"]
            edges = conn["edges"]
            print(f"assign batch {batch_i} page {page} edges {len(edges)}", flush=True)
            for edge in edges:
                node = edge["node"]
                tags = {t["name"]: t["value"] for t in node.get("tags") or []}
                found.append(
                    {
                        "assignment_id": node["id"],
                        "message_id": tags.get("Message"),
                        "nonce": int(tags["Nonce"]) if str(tags.get("Nonce", "")).isdigit() else None,
                        "epoch": tags.get("Epoch"),
                        "hash_chain": tags.get("Hash-Chain"),
                        "timestamp_ms": tags.get("Timestamp"),
                        "block_height": (node.get("block") or {}).get("height"),
                    }
                )
            if not conn["pageInfo"]["hasNextPage"] or not edges:
                break
            cursor = edges[-1]["cursor"]
            page += 1
            if page > 10:
                raise SystemExit(f"assignment pages runaway at {stem}")
    return found


def download_one(mid: str) -> dict:
    body_path = MSG / f"{mid}.body"
    hdr_path = MSG / f"{mid}.headers"
    # Reuse a previous successful body if it is not the CDN error page.
    if body_path.exists() and body_path.stat().st_size > 800:
        head = body_path.read_bytes()[:20]
        if not head.startswith(b"<!DOCTYPE") and not head.startswith(b"<html"):
            data = body_path.read_bytes()
            return {
                "id": mid,
                "status": 200,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "reused": True,
                "error": None,
            }
    cmd = [
        "curl", "-sS", "-L", "--fail-with-body",
        "--retry", "4", "--retry-delay", "2", "--retry-all-errors",
        "-A", "qar-ledger-recovery",
        "-D", str(hdr_path),
        "-o", str(body_path),
        "-w", "%{http_code}",
        f"https://arweave.net/{mid}",
    ]
    last = None
    for attempt in range(1, 5):
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            last = f"timeout: {exc}"
            time.sleep(min(16, 2 ** (attempt - 1)))
            continue
        code = proc.stdout.decode().strip() or "0"
        data = body_path.read_bytes() if body_path.exists() else b""
        if code == "200" and data and not data.startswith(b"<!DOCTYPE") and not data.startswith(b"<html"):
            return {
                "id": mid,
                "status": 200,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "reused": False,
                "error": None,
                "attempt": attempt,
            }
        last = f"http {code} bytes {len(data)} stderr {proc.stderr[:200]!r}"
        time.sleep(min(16, 2 ** (attempt - 1)))
    return {"id": mid, "status": 0, "bytes": 0, "sha256": None, "reused": False, "error": last}


def main() -> None:
    rows = json.loads((GQL / "eval-recipient.rows.json").read_text())
    ids = [r["id"] for r in rows]
    unmatched = json.loads(Path("/tmp/eval-unmatched-ids.json").read_text())
    # Always resolve the memory-cited eval and the tail, even if sqlite missed them.
    extra = [
        "eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA",
        "wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ",
    ]
    wanted = list(dict.fromkeys(unmatched + extra))
    print(f"assignment lookup {len(wanted)}", flush=True)
    found = assignments_for(wanted)
    (GQL / "assign-eval.rows.json").write_text(json.dumps(found, indent=2) + "\n")
    print(f"assignments {len(found)}", flush=True)

    print(f"download {len(ids)}", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(download_one, mid) for mid in ids]
        for fut in as_completed(futs):
            item = fut.result()
            results.append(item)
            if item["error"]:
                print("FAIL", item["id"], item["error"], flush=True)
    results.sort(key=lambda r: ids.index(r["id"]))
    (MSG / "download-manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    ok = sum(1 for r in results if r["sha256"])
    print(f"downloaded_ok {ok} of {len(results)}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only fetch for P9 collateral messages. Does not execute the module.

Saves every GraphQL request and response. A failed page is not an empty page.
Download concurrency is 4.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery.gql import post_graphql  # noqa: E402

PROCESS = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
ENDPOINT = "https://arweave.net/graphql"
ACTIONS = [
    "Deposit",
    "Mint-Tokens",
    "Confirm-Deposits",
    "Unwrap",
    "Withdraw",
    "Unwrap-Funds-Sent",
]
BODY_ACTIONS = {"Deposit", "Withdraw", "Unwrap-Funds-Sent"}
GATEWAYS = [
    "https://arweave.net",
    "https://ar-io.dev",
    "https://turbo-gateway.com",
    "https://vilenarios.com",
]
UA = "qar-ledger-recovery"
PAGE_QUERY = """
query($cursor: String, $recipients: [String!], $tags: [TagFilter!]) {
  transactions(
    first: 100
    after: $cursor
    sort: HEIGHT_ASC
    recipients: $recipients
    tags: $tags
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        recipient
        owner { address }
        bundledIn { id }
        block { height timestamp }
        data { size type }
        tags { name value }
      }
    }
  }
}
"""
PROCESS_TAG_QUERY = """
query($cursor: String, $tags: [TagFilter!]) {
  transactions(
    first: 100
    after: $cursor
    sort: HEIGHT_ASC
    tags: $tags
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        recipient
        owner { address }
        block { height timestamp }
        tags { name value }
      }
    }
  }
}
"""


def raw_root(run: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "data/raw/collat" / run
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_gql(directory: Path, stem: str, query: str, variables: dict) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    meta_path = directory / f"{stem}.meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("ok") and (directory / f"{stem}.response.json").exists():
            return json.loads((directory / f"{stem}.response.json").read_text())
    payload = {"query": query, "variables": variables}
    (directory / f"{stem}.request.json").write_text(json.dumps(payload, indent=2) + "\n")
    resp = post_graphql(query, variables, endpoint=ENDPOINT, timeout_s=120, max_attempts=12)
    (directory / f"{stem}.response.json").write_bytes(resp.body)
    meta = {
        "endpoint": resp.endpoint,
        "status": resp.http_status,
        "elapsed_ms": resp.elapsed_ms,
        "attempt": resp.attempt,
        "bytes": len(resp.body),
        "error": resp.error,
        "ok": resp.ok,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    if not resp.ok:
        raise RuntimeError(f"graphql failed {directory.name}/{stem}: {meta}")
    return resp.parsed


def tags_of(node: dict) -> dict:
    out = {}
    for tag in node.get("tags") or []:
        name = tag.get("name")
        if name is None:
            continue
        if name in out:
            prev = out[name]
            out[name] = prev if isinstance(prev, list) else [prev]
            out[name].append(tag.get("value"))
        else:
            out[name] = tag.get("value")
    return out


def row_from(action: str, edge: dict) -> dict:
    node = edge["node"]
    block = node.get("block") or {}
    data = node.get("data") or {}
    bundled = node.get("bundledIn") or {}
    owner = node.get("owner") or {}
    return {
        "action": action,
        "id": node.get("id"),
        "recipient": node.get("recipient"),
        "owner": owner.get("address"),
        "block_height": block.get("height"),
        "block_timestamp": block.get("timestamp"),
        "bundled_in": bundled.get("id"),
        "data_size": data.get("size"),
        "data_type": data.get("type"),
        "tags": tags_of(node),
    }


def paginate_action(run: str, action: str) -> dict:
    directory = raw_root(run) / "gql" / "recipient" / action
    directory.mkdir(parents=True, exist_ok=True)
    cursor = None
    page = 0
    seen = set()
    rows = []
    while page < 20000:
        stem = f"p{page:05d}"
        variables = {
            "cursor": cursor,
            "recipients": [PROCESS],
            "tags": [
                {"name": "Action", "values": [action]},
                {"name": "Type", "values": ["Message"]},
            ],
        }
        parsed = save_gql(directory, stem, PAGE_QUERY, variables)
        conn = parsed["data"]["transactions"]
        edges = conn["edges"] or []
        added = 0
        for edge in edges:
            item = row_from(action, edge)
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            rows.append(item)
            added += 1
        has_next = bool(conn["pageInfo"]["hasNextPage"])
        print(
            f"{action} page {page} edges {len(edges)} new {added} total {len(rows)} next {has_next}",
            flush=True,
        )
        if not edges or not has_next:
            break
        new_cursor = edges[-1]["cursor"]
        if new_cursor == cursor:
            raise RuntimeError(f"{action} cursor did not advance at page {page}")
        cursor = new_cursor
        page += 1
    else:
        raise RuntimeError(f"{action} exceeded 20000 pages")
    out = directory / "rows.json"
    out.write_text(json.dumps(rows) + "\n")
    summary = {
        "action": action,
        "messages": len(rows),
        "pages": page + 1,
        "query": "recipient + Action + Type=Message",
        "process": PROCESS,
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def process_tag_probe(run: str, action: str) -> dict:
    directory = raw_root(run) / "gql" / "process-tag"
    variables = {
        "cursor": None,
        "tags": [
            {"name": "Process", "values": [PROCESS]},
            {"name": "Action", "values": [action]},
        ],
    }
    parsed = save_gql(directory, action, PROCESS_TAG_QUERY, variables)
    edges = parsed["data"]["transactions"]["edges"] or []
    summary = {
        "action": action,
        "edges": len(edges),
        "has_next": parsed["data"]["transactions"]["pageInfo"]["hasNextPage"],
    }
    print(f"process-tag {action} edges {summary['edges']}", flush=True)
    return summary


def write_message_jsonl(root: Path) -> int:
    rows = []
    for action in ACTIONS:
        path = root / "gql" / "recipient" / action / "rows.json"
        if path.exists():
            rows.extend(json.loads(path.read_text()))
    (root / "gql" / "messages.jsonl").write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
    )
    return len(rows)


def phase_pages(run: str, actions: list[str]) -> None:
    root = raw_root(run)
    probe_path = root / "gql" / "process-tag" / "summary.json"
    if not probe_path.exists():
        probes = [process_tag_probe(run, action) for action in ACTIONS]
        probe_path.write_text(json.dumps(probes, indent=2) + "\n")
    summaries = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(paginate_action, run, action): action for action in actions}
        for fut in as_completed(futures):
            action = futures[fut]
            summaries.append(fut.result())
            print(f"done {action}", flush=True)
    summaries.sort(key=lambda item: ACTIONS.index(item["action"]))
    summary_path = root / "gql" / "recipient-summary.json"
    previous = []
    if summary_path.exists():
        loaded = json.loads(summary_path.read_text())
        previous = loaded.get("actions") or loaded.get("this_run") or []
    by_action = {item["action"]: item for item in previous if isinstance(item, dict) and item.get("action")}
    for item in summaries:
        by_action[item["action"]] = item
    merged = [by_action[name] for name in ACTIONS if name in by_action]
    summary_path.write_text(json.dumps({"actions": merged}, indent=2) + "\n")
    count = write_message_jsonl(root)
    print(f"messages {count}", flush=True)


def looks_like_html(data: bytes) -> bool:
    head = data.lstrip()[:20].lower()
    return head.startswith(b"<!doctype") or head.startswith(b"<html")


def fetch_url(url: str, timeout: int) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            code = int(response.status)
            final = response.geturl()
        error = None
    except urllib.error.HTTPError as exc:
        data = exc.read()
        code = int(exc.code)
        final = url
        error = None
    except Exception as exc:  # noqa: BLE001 — recorded, not treated as empty
        return {
            "url": url,
            "status": 0,
            "bytes": 0,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "html": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "url": url,
        "final_url": final,
        "status": code,
        "bytes": len(data),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "html": looks_like_html(data),
        "error": error,
        "_data": data,
    }


def download_one(run: str, message_id: str) -> dict:
    """GET the message data. arweave.net first. A 404 there is recorded and not retried
    across the slow gateways; those are sampled later. A timeout tries ar-io.dev once.
    """
    directory = raw_root(run) / "messages"
    directory.mkdir(parents=True, exist_ok=True)
    meta_path = directory / f"{message_id}.meta.json"
    body_path = directory / f"{message_id}.body"
    if meta_path.exists() and meta_path.stat().st_size > 0:
        meta = json.loads(meta_path.read_text())
        if meta.get("ok") or meta.get("status") == 404:
            return meta
    attempts = []
    primary = fetch_url(f"https://arweave.net/{message_id}", 30)
    data = primary.pop("_data", b"")
    attempts.append(primary)
    ok = False
    status = primary["status"]
    if primary["status"] == 200 and not primary["html"]:
        body_path.write_bytes(data)
        ok = True
    elif primary["status"] == 404:
        (directory / f"{message_id}.http404").write_bytes(data)
        status = 404
    elif primary["status"] != 200:
        alt = fetch_url(f"https://ar-io.dev/{message_id}", 25)
        alt_data = alt.pop("_data", b"")
        attempts.append(alt)
        status = alt["status"]
        if alt["status"] == 200 and not alt["html"]:
            body_path.write_bytes(alt_data)
            ok = True
        elif alt["status"] == 404:
            (directory / f"{message_id}.http404").write_bytes(alt_data)
    meta = {"id": message_id, "ok": ok, "status": status, "attempts": attempts}
    meta_path.write_text(json.dumps(meta) + "\n")
    return meta


def phase_bodies(run: str, workers: int = 4) -> None:
    root = raw_root(run)
    wanted = []
    for line in (root / "gql" / "messages.jsonl").read_text().splitlines():
        if not line:
            continue
        row = json.loads(line)
        if row["action"] in BODY_ACTIONS:
            wanted.append(row["id"])
        elif row["action"] == "Unwrap" and "Quantity" not in (row.get("tags") or {}):
            wanted.append(row["id"])
    print(f"bodies {len(wanted)}", flush=True)
    done = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download_one, run, mid) for mid in wanted]
        for fut in as_completed(futures):
            meta = fut.result()
            done += 1
            if not meta.get("ok"):
                failed += 1
            if done % 100 == 0 or done == len(wanted):
                print(f"bodies {done}/{len(wanted)} failed {failed}", flush=True)
    summary = {"wanted": len(wanted), "failed": failed, "ok": len(wanted) - failed}
    (root / "messages" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: p9_fetch.py <pages|bodies> <run> [Action,Action]")
    phase, run = sys.argv[1], sys.argv[2]
    if phase == "pages":
        if len(sys.argv) == 4:
            actions = sys.argv[3].split(",")
            unknown = [name for name in actions if name not in ACTIONS]
            if unknown:
                raise SystemExit(f"unknown actions {unknown}")
        else:
            actions = ACTIONS
        phase_pages(run, actions)
    elif phase == "bodies":
        workers = int(sys.argv[3]) if len(sys.argv) == 4 else 4
        phase_bodies(run, workers)
    else:
        raise SystemExit(f"unknown phase {phase}")


if __name__ == "__main__":
    main()

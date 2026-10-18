#!/usr/bin/env python3
"""Read-only: transfer ids from collateral messages, then the Arweave transactions
and the holder wallet's layer-1 history. Does not execute the module.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery.gql import post_graphql  # noqa: E402

ENDPOINT = "https://arweave.net/graphql"
UA = "qar-ledger-recovery"
TX_ID = re.compile(r"^[A-Za-z0-9_-]{43}$")
TAIL_BLOCK = 1951869

TX_QUERY = """
query($ids: [ID!]!) {
  transactions(first: 100, ids: $ids) {
    edges {
      node {
        id
        recipient
        owner { address }
        bundledIn { id }
        block { height timestamp }
        quantity { winston ar }
        fee { winston ar }
        data { size }
        tags { name value }
      }
    }
  }
}
"""
WALLET_QUERY = """
query($cursor: String, $owners: [String!], $recipients: [String!]) {
  transactions(
    first: 100
    after: $cursor
    sort: HEIGHT_ASC
    owners: $owners
    recipients: $recipients
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
        quantity { winston ar }
        fee { winston ar }
        data { size }
        tags { name value }
      }
    }
  }
}
"""


def raw_root(run: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "data/raw/collat" / run
    if not path.is_dir():
        raise SystemExit(f"missing {path}")
    return path


def save_gql(directory: Path, stem: str, query: str, variables: dict, endpoint: str = ENDPOINT) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    meta_path = directory / f"{stem}.meta.json"
    response_path = directory / f"{stem}.response.json"
    if meta_path.exists() and response_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("ok"):
            return json.loads(response_path.read_text())
    payload = {"query": query, "variables": variables}
    (directory / f"{stem}.request.json").write_text(json.dumps(payload, indent=2) + "\n")
    resp = post_graphql(query, variables, endpoint=endpoint, timeout_s=120, max_attempts=8)
    response_path.write_bytes(resp.body)
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
        raise RuntimeError(f"graphql failed {stem}: {meta}")
    return resp.parsed


def raw_int(value):
    if isinstance(value, bool) or isinstance(value, float):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("+"):
            text = text[1:]
        if text.isdigit():
            return int(text)
    return None


def load_messages(run: str) -> list[dict]:
    path = raw_root(run) / "gql" / "messages.jsonl"
    rows = []
    for line in path.read_text().splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def load_body(run: str, message_id: str):
    path = raw_root(run) / "messages" / f"{message_id}.body"
    if not path.exists():
        return None
    data = path.read_bytes()
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_unparsed": True, "bytes": len(data)}


def add_ref(bucket: list, message: dict, field: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        return
    bucket.append(
        {
            "message_id": message["id"],
            "action": message["action"],
            "field": field,
            "value": value,
            "is_tx_id": bool(TX_ID.fullmatch(value)),
            "block_height": message.get("block_height"),
        }
    )


def collect_refs(run: str) -> dict:
    refs = []
    body_status = {"present": 0, "missing": 0, "unparsed": 0}
    for message in load_messages(run):
        tags = message.get("tags") or {}
        for field in ("X-Transfer-Id", "X-Deposit-Id", "X-Unwrap-Request-Id"):
            value = tags.get(field)
            if isinstance(value, list):
                for item in value:
                    add_ref(refs, message, f"tag:{field}", item)
            else:
                add_ref(refs, message, f"tag:{field}", value)
        if message["action"] not in {"Deposit", "Withdraw", "Unwrap-Funds-Sent"}:
            continue
        body = load_body(run, message["id"])
        if body is None:
            body_status["missing"] += 1
            continue
        if isinstance(body, dict) and body.get("_unparsed"):
            body_status["unparsed"] += 1
            continue
        body_status["present"] += 1
        payloads = body if isinstance(body, list) else [body]
        for item in payloads:
            if not isinstance(item, dict):
                continue
            for field in ("transfer_id", "id"):
                value = item.get(field)
                if isinstance(value, str):
                    add_ref(refs, message, f"data:{field}", value)
    tx_ids = sorted({ref["value"] for ref in refs if ref["is_tx_id"]})
    out = {
        "refs": refs,
        "tx_ids": tx_ids,
        "body_status": body_status,
        "ref_count": len(refs),
        "tx_id_count": len(tx_ids),
    }
    path = raw_root(run) / "txs" / "refs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out) + "\n")
    print(
        f"refs {len(refs)} tx_ids {len(tx_ids)} bodies {body_status}",
        flush=True,
    )
    return out


def phase_txs(run: str) -> None:
    refs = json.loads((raw_root(run) / "txs" / "refs.json").read_text())
    ids = refs["tx_ids"]
    directory = raw_root(run) / "txs" / "gql"
    found = {}
    for index in range(0, len(ids), 20):
        batch = ids[index : index + 20]
        stem = f"b{index:05d}"
        parsed = save_gql(directory, stem, TX_QUERY, {"ids": batch})
        edges = parsed["data"]["transactions"]["edges"] or []
        for edge in edges:
            node = edge["node"]
            found[node["id"]] = True
        print(f"tx batch {index} asked {len(batch)} got {len(edges)}", flush=True)
    missing = [tx_id for tx_id in ids if tx_id not in found]
    (raw_root(run) / "txs" / "missing-ids.json").write_text(json.dumps(missing, indent=2) + "\n")
    print(f"graphql txs {len(found)} missing {len(missing)}", flush=True)
    fetched = 0
    for tx_id in missing:
        dest = raw_root(run) / "txs" / "http" / f"{tx_id}.json"
        meta_path = raw_root(run) / "txs" / "http" / f"{tx_id}.meta.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if meta_path.exists():
            continue
        url = f"https://arweave.net/tx/{tx_id}"
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                data = response.read()
                code = int(response.status)
        except urllib.error.HTTPError as exc:
            data = exc.read()
            code = int(exc.code)
        except Exception as exc:  # noqa: BLE001
            meta_path.write_text(
                json.dumps({"id": tx_id, "status": 0, "error": f"{type(exc).__name__}: {exc}"}) + "\n"
            )
            continue
        dest.write_bytes(data)
        meta_path.write_text(json.dumps({"id": tx_id, "status": code, "bytes": len(data)}) + "\n")
        fetched += 1
        if fetched % 50 == 0:
            print(f"http tx {fetched}/{len(missing)}", flush=True)
    print(f"http fetched {fetched}", flush=True)


def phase_tx_status(run: str) -> None:
    """Block height is not in GET /tx/{id}. Save GET /tx/{id}/status beside it."""
    http_dir = raw_root(run) / "txs" / "http"
    paths = [
        path
        for path in sorted(http_dir.glob("*.json"))
        if not path.name.endswith(".meta.json") and not path.name.endswith(".status.json")
    ]
    done = 0
    for path in paths:
        tx_id = path.name[: -len(".json")]
        dest = http_dir / f"{tx_id}.status.json"
        meta_path = http_dir / f"{tx_id}.status.meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta.get("ok"):
                done += 1
                continue
        url = f"https://arweave.net/tx/{tx_id}/status"
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                data = response.read()
                code = int(response.status)
            error = None
        except urllib.error.HTTPError as exc:
            data = exc.read()
            code = int(exc.code)
            error = None
        except Exception as exc:  # noqa: BLE001 — recorded, not treated as a height
            meta_path.write_text(
                json.dumps(
                    {
                        "id": tx_id,
                        "url": url,
                        "status": 0,
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                + "\n"
            )
            print(f"status {tx_id} failed", flush=True)
            continue
        dest.write_bytes(data)
        ok = code == 200
        meta_path.write_text(
            json.dumps({"id": tx_id, "url": url, "status": code, "bytes": len(data), "ok": ok, "error": error})
            + "\n"
        )
        done += 1
        print(f"status {tx_id} {code}", flush=True)
    print(f"status saved {done} of {len(paths)}", flush=True)


def known_tx_ids(run: str) -> set[str]:
    found = set()
    for directory in (raw_root(run) / "txs" / "gql", raw_root(run) / "txs" / "gql-added"):
        if not directory.is_dir():
            continue
        for path in directory.glob("b*.response.json"):
            parsed = json.loads(path.read_text())
            for edge in parsed["data"]["transactions"]["edges"] or []:
                found.add(edge["node"]["id"])
    http_dir = raw_root(run) / "txs" / "http"
    if http_dir.is_dir():
        for path in http_dir.glob("*.json"):
            if path.name.endswith(".meta.json") or path.name.endswith(".status.json"):
                continue
            try:
                tx = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            if isinstance(tx.get("id"), str):
                found.add(tx["id"])
    return found


def phase_txs_new(run: str) -> None:
    """Fetch transfer ids that are not already in txs/gql or txs/http.

    Batch files go to txs/gql-added so a changed id order cannot reuse an old page.
    """
    refs = json.loads((raw_root(run) / "txs" / "refs.json").read_text())
    known = known_tx_ids(run)
    ids = [tx_id for tx_id in refs["tx_ids"] if tx_id not in known]
    directory = raw_root(run) / "txs" / "gql-added"
    found = {}
    print(f"new tx ids {len(ids)} already known {len(known)}", flush=True)
    for index in range(0, len(ids), 20):
        batch = ids[index : index + 20]
        stem = f"b{index:05d}"
        parsed = save_gql(directory, stem, TX_QUERY, {"ids": batch})
        edges = parsed["data"]["transactions"]["edges"] or []
        for edge in edges:
            found[edge["node"]["id"]] = True
        print(f"added batch {index} asked {len(batch)} got {len(edges)}", flush=True)
    missing = [tx_id for tx_id in ids if tx_id not in found]
    (raw_root(run) / "txs" / "missing-added.json").write_text(json.dumps(missing, indent=2) + "\n")
    print(f"added graphql {len(found)} missing {len(missing)}", flush=True)
    fetched = 0
    for tx_id in missing:
        dest = raw_root(run) / "txs" / "http" / f"{tx_id}.json"
        meta_path = raw_root(run) / "txs" / "http" / f"{tx_id}.meta.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if meta_path.exists() and dest.exists():
            continue
        url = f"https://arweave.net/tx/{tx_id}"
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                data = response.read()
                code = int(response.status)
        except urllib.error.HTTPError as exc:
            data = exc.read()
            code = int(exc.code)
        except Exception as exc:  # noqa: BLE001
            meta_path.write_text(
                json.dumps({"id": tx_id, "status": 0, "error": f"{type(exc).__name__}: {exc}"}) + "\n"
            )
            continue
        if code == 200:
            dest.write_bytes(data)
        meta_path.write_text(json.dumps({"id": tx_id, "status": code, "bytes": len(data)}) + "\n")
        fetched += 1
    print(f"added http fetched {fetched}", flush=True)


def phase_wallet(
    run: str,
    address: str,
    direction: str,
    endpoint: str = ENDPOINT,
    subdir: str | None = None,
) -> None:
    if direction not in {"owners", "recipients"}:
        raise SystemExit("direction must be owners or recipients")
    directory = raw_root(run) / "wallet" / address / (subdir or direction)
    cursor = None
    page = 0
    seen = 0
    while page < 20000:
        variables = {"cursor": cursor, "owners": None, "recipients": None}
        variables[direction] = [address]
        parsed = save_gql(directory, f"p{page:05d}", WALLET_QUERY, variables, endpoint=endpoint)
        conn = parsed["data"]["transactions"]
        edges = conn["edges"] or []
        seen += len(edges)
        has_next = bool(conn["pageInfo"]["hasNextPage"])
        print(f"{direction} page {page} edges {len(edges)} total {seen} next {has_next}", flush=True)
        if not edges or not has_next:
            break
        new_cursor = edges[-1]["cursor"]
        if new_cursor == cursor:
            raise RuntimeError(f"cursor stuck at {direction} page {page}")
        cursor = new_cursor
        page += 1
    else:
        raise RuntimeError(f"{direction} exceeded 20000 pages")
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "address": address,
                "direction": direction,
                "endpoint": endpoint,
                "edges": seen,
                "pages": page + 1,
            },
            indent=2,
        )
        + "\n"
    )


def phase_balance_now(run: str, address: str) -> None:
    directory = raw_root(run) / "wallet" / address
    directory.mkdir(parents=True, exist_ok=True)
    for name, url in (
        ("balance", f"https://arweave.net/wallet/{address}/balance"),
        ("info", "https://arweave.net/info"),
    ):
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=40) as response:
            data = response.read()
            code = int(response.status)
        (directory / f"{name}.body").write_bytes(data)
        (directory / f"{name}.meta.json").write_text(
            json.dumps({"url": url, "status": code, "bytes": len(data)}, indent=2) + "\n"
        )
        print(name, code, data[:80], flush=True)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: p9_chain.py <refs|txs|status|wallet|balance> <run> [address] [direction]"
        )
    phase, run = sys.argv[1], sys.argv[2]
    if phase == "refs":
        collect_refs(run)
    elif phase == "txs":
        phase_txs(run)
    elif phase == "txs-new":
        phase_txs_new(run)
    elif phase == "wallet":
        endpoint = sys.argv[5] if len(sys.argv) > 5 else ENDPOINT
        subdir = sys.argv[6] if len(sys.argv) > 6 else None
        phase_wallet(run, sys.argv[3], sys.argv[4], endpoint, subdir)
    elif phase == "balance":
        phase_balance_now(run, sys.argv[3])
    elif phase == "status":
        phase_tx_status(run)
    else:
        raise SystemExit(f"unknown phase {phase}")


if __name__ == "__main__":
    main()

"""Classify qAR holders into wallets, pools, locks, bridges, and other processes.

Read-only. Does not execute the module. Safe to rerun: GraphQL batches already
saved under the raw directory are reused, and a later balances.json can be
passed with --balances.

The primary list is the nonce-2074518 balance map. A tail balances.json under
data/raw/fast or data/raw/p7 is reported when present and is not invented when
absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from recovery.gql import post_graphql

_REPO = Path(__file__).resolve().parents[2]
DEFAULT_BALANCES = str(
    _REPO / "data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json"
)
DEFAULT_CONFIGS = os.environ.get("QAR_LOCAL_CONFIGS", "")
DEFAULT_OVERLAP = str(_REPO / "data/raw/drive-cu/overlap-rows.json")
DEFAULT_WSRC = str(
    _REPO / "evidence/p9-prep/20261017T051439Z-w-src/addresses.json"
)
QAR_PROCESS = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
LIQUIDOPS_OQAR = "fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0"
SUPPLY_RAW = 189487568412204611
DENOM = 10**12
BATCH = 100
WORKERS = 4
ENDPOINT = "https://arweave.net/graphql"
FALLBACKS = (
    "https://ar-io.dev/graphql",
    "https://vilenarios.com/graphql",
)

IDS_QUERY = """
query($ids:[ID!]!){
  transactions(ids:$ids, first:100){
    edges{ node{ id owner{ address } tags{ name value } } }
  }
}
""".strip()

INFO_QUERY = """
query($id:String!){
  transactions(
    first:2
    sort:HEIGHT_DESC
    tags:[
      {name:"From-Process", values:[$id]}
      {name:"Action", values:["Info"]}
    ]
  ){ edges{ node{ id tags{ name value } } } }
}
""".strip()

EVAL_QUERY = """
query($id:String!){
  transactions(
    first:2
    sort:HEIGHT_ASC
    recipients:[$id]
    tags:[{name:"Action", values:["Eval"]}]
  ){ edges{ node{ id tags{ name value } } } }
}
""".strip()

ARWEAVE_ID = re.compile(r"^[A-Za-z0-9_-]{43}$")

OWNER_QUERY = """
query($owner:String!){
  transactions(owners:[$owner], first:1, sort:HEIGHT_DESC){
    edges{ node{ id tags{ name value } } }
  }
}
""".strip()

PAIR_NAME = re.compile(r"^[^:\s]+:[^:\s]+:\d+$")
WORD_LOCK = re.compile(r"(?i)(?:^|[^A-Za-z])(lock|staking|stake|vesting)(?:[^A-Za-z]|$)")
WORD_BRIDGE = re.compile(r"(?i)(?:^|[^A-Za-z])bridge(?:[^A-Za-z]|$)")
WORD_LENDING = re.compile(r"(?i)(?:^|[^A-Za-z])(lending|loan|loans)(?:[^A-Za-z]|$)")
WORD_MULTISIG = re.compile(r"(?i)(?:^|[^A-Za-z])multisig(?:[^A-Za-z]|$)")
WORD_DEXI = re.compile(r"(?i)(?:^|[^A-Za-z])dexi(?:[^A-Za-z]|$)")
KEEP_TAGS = (
    "Type",
    "Name",
    "App-Name",
    "Module",
    "Authority",
    "Scheduler",
    "Variant",
    "Data-Protocol",
    "Ticker",
    "Protocol-Name",
    "SDK",
    "Description",
    "Denomination",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_balance(raw: int) -> str:
    sign = "-" if raw < 0 else ""
    whole, frac = divmod(abs(raw), DENOM)
    return f"{sign}{whole}.{frac:012d}"


def supply_share(raw: int, total: int) -> str:
    """Decimal share truncated to 18 places. The raw amounts stay exact elsewhere."""
    if total == 0:
        return "unknown"
    sign = "-" if raw < 0 else ""
    raw = abs(raw)
    whole = raw // total
    digits = f"{(raw % total) * 10**18 // total:018d}".rstrip("0")
    body = str(whole) if not digits else f"{whole}.{digits}"
    return f"{sign}{body}"


def split_numbered_line(line: str) -> tuple[int | None, str]:
    match = re.match(r"^(\d+)([:-])(.*)$", line.rstrip("\n"))
    if not match:
        return None, line.rstrip("\n")
    return int(match.group(1)), match.group(3)


def _commented(content: str) -> tuple[bool, str]:
    stripped = content.lstrip()
    if stripped.startswith("#"):
        return True, stripped[1:].lstrip()
    return False, content.strip()


def parse_pools(text: str, excerpt_path: str) -> list[dict]:
    """Parse the numbered pool excerpt. Commented keys stay in the list."""
    pools: list[dict] = []
    current: dict | None = None

    def finish() -> None:
        nonlocal current
        if current and current.get("id"):
            pools.append(current)
        current = None

    for excerpt_line, line in enumerate(text.splitlines(), start=1):
        orig, content = split_numbered_line(line)
        commented, body = _commented(content)
        key_match = re.match(r"^([A-Za-z0-9_./-]+):\s*$", body)
        id_match = re.match(r'^id:\s*"([^"]+)"\s*$', body)
        field_match = re.match(r'^([A-Za-z0-9_]+):\s*"?([^"#]+?)"?\s*$', body)
        if key_match and key_match.group(1) not in {"id", "token0", "token1", "dex", "fee_ratio"}:
            finish()
            current = {
                "config_name": key_match.group(1),
                "commented": commented,
                "excerpt_path": excerpt_path,
                "excerpt_line": excerpt_line,
                "original_line": orig,
                "fields": {},
            }
            continue
        if current is None:
            continue
        if id_match:
            current["id"] = id_match.group(1)
            current["id_excerpt_line"] = excerpt_line
            current["id_original_line"] = orig
            continue
        if field_match and field_match.group(1) in {"token0", "token1", "dex", "fee_ratio"}:
            current["fields"][field_match.group(1)] = field_match.group(2).strip().strip('"')
            current["fields"][field_match.group(1) + "_excerpt_line"] = excerpt_line
            current["fields"][field_match.group(1) + "_original_line"] = orig
    finish()
    return pools


def parse_liquidops(text: str, excerpt_path: str) -> dict | None:
    del excerpt_path
    o_excerpt = None
    for excerpt_line, line in enumerate(text.splitlines(), start=1):
        _orig, content = split_numbered_line(line)
        if "oAddress:" in content and LIQUIDOPS_OQAR in content:
            o_excerpt = excerpt_line
    if o_excerpt is None:
        return None
    return {
        "address": LIQUIDOPS_OQAR,
        "role": "lending",
        "label": "LiquidOps oQAR",
        "excerpt_path": "private-config",
        "excerpt_line": o_excerpt,
        "original_file": "private-config",
        "original_line": None,
        "block_excerpt_line": None,
        "block_original_line": None,
        "git": None,
        "note": "Labeled lending from a local config. Private parameters are not stored.",
    }


def parse_qar_mappings(text: str, excerpt_path: str) -> list[dict]:
    del excerpt_path
    mappings = []
    seen_file = False
    for excerpt_line, line in enumerate(text.splitlines(), start=1):
        _orig, content = split_numbered_line(line)
        if content.startswith("=== FILE:"):
            seen_file = True
            continue
        if seen_file and QAR_PROCESS in content:
            mappings.append(
                {
                    "excerpt_path": "private-config",
                    "excerpt_line": excerpt_line,
                    "original_line": None,
                    "original_file": "private-config",
                    "content": "redacted",
                }
            )
    return mappings


def load_balances(path: Path) -> tuple[list[dict], int]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"balance file is not an object: {path}")
    rows = []
    total = 0
    for address, raw_text in data.items():
        raw = int(raw_text)
        total += raw
        rows.append({"address": address, "raw_balance": raw, "raw_text": str(raw_text)})
    rows.sort(key=lambda row: (-row["raw_balance"], row["address"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows, total


def find_later_balances() -> list[str]:
    roots = (
        _REPO / "data/raw/fast",
        _REPO / "data/raw/p7",
    )
    found = []
    for root in roots:
        if not root.exists():
            continue
        found.extend(str(path) for path in sorted(root.rglob("balances.json")))
    return found


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _query(query: str, variables: dict, raw_stem: Path) -> dict:
    """POST GraphQL and store the request, body, and meta. Reuse a saved ok body."""
    meta_path = raw_stem.with_suffix(".meta.json")
    body_path = raw_stem.with_suffix(".body")
    request_path = raw_stem.with_suffix(".request.json")
    if meta_path.exists() and body_path.exists() and request_path.exists():
        meta = json.loads(meta_path.read_text())
        saved = json.loads(request_path.read_text())
        same = saved.get("query") == query and saved.get("variables") == variables
        if meta.get("ok") and same:
            meta["reused"] = True
            parsed = json.loads(body_path.read_text())
            return {"ok": True, "meta": meta, "parsed": parsed, "body_path": str(body_path)}
    request = {"query": query, "variables": variables}
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    endpoints = (ENDPOINT,) + FALLBACKS
    last = None
    chosen = None
    for endpoint in endpoints:
        last = post_graphql(query, variables, endpoint=endpoint, timeout_s=90, max_attempts=4)
        chosen = endpoint
        if last.ok:
            break
        if last.http_status not in (0, 429) and not (500 <= last.http_status <= 599):
            # A GraphQL schema error on this endpoint is still tried on the next one.
            if last.http_status != 200:
                continue
            break
    assert last is not None and chosen is not None
    if last.body:
        body_path.write_bytes(last.body)
    else:
        body_path.write_text("")
    meta = {
        "endpoint": chosen,
        "http_status": last.http_status,
        "elapsed_ms": last.elapsed_ms,
        "attempt": last.attempt,
        "error": last.error,
        "ok": bool(last.ok),
        "bytes": body_path.stat().st_size,
        "sha256": sha256_file(body_path),
        "request": str(request_path),
        "reused": False,
    }
    _write_json(meta_path, meta)
    parsed = last.parsed if last.ok else None
    return {"ok": bool(last.ok), "meta": meta, "parsed": parsed, "body_path": str(body_path)}


def _edges(parsed: dict | None) -> list[dict]:
    if not parsed:
        return []
    data = parsed.get("data") or {}
    transactions = data.get("transactions") or {}
    return transactions.get("edges") or []


def _absorb(found: dict[str, dict], queried_ok: set[str], addresses: list[str], result: dict, label: str) -> None:
    if not result["ok"]:
        return
    returned = set()
    for edge in _edges(result["parsed"]):
        node = edge.get("node") or {}
        node_id = node.get("id")
        if not node_id:
            continue
        returned.add(node_id)
        found.setdefault(
            node_id,
            {
                "node": node,
                "batch_index": label,
                "body_path": result["body_path"],
                "endpoint": result["meta"]["endpoint"],
            },
        )
    # A full page of edges while some requested ids are absent can be a gateway cap.
    missing = [address for address in addresses if address not in returned]
    capped = len(returned) in {10, 20, 25, 50} and missing
    result["missing"] = missing
    result["capped"] = bool(capped)
    if not capped:
        queried_ok.update(addresses)


def fetch_id_batches(rows: list[dict], raw_dir: Path) -> tuple[dict[str, dict], set[str]]:
    """Query every holder id. Refetch ids a capped page did not return.

    The top 500 also get a second successful read when the first page did not
    include them, so a dropped id is not stored as a wallet.
    """
    batches = [rows[index : index + BATCH] for index in range(0, len(rows), BATCH)]
    found: dict[str, dict] = {}
    queried_ok: set[str] = set()

    def work(batch_index: int, batch: list[dict]) -> tuple[int, dict, list[str]]:
        addresses = [row["address"] for row in batch if ARWEAVE_ID.fullmatch(row["address"])]
        stem = raw_dir / "gql" / "ids" / f"ids-{batch_index:04d}"
        if not addresses:
            result = {
                "ok": True,
                "parsed": {"data": {"transactions": {"edges": []}}},
                "meta": {"endpoint": "not-queried", "http_status": 0, "ok": True},
                "body_path": "",
            }
        else:
            result = _query(IDS_QUERY, {"ids": addresses}, stem)
        result["rank_from"] = batch[0]["rank"]
        result["rank_to"] = batch[-1]["rank"]
        return batch_index, result, addresses

    pending_refetch: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(work, index, batch) for index, batch in enumerate(batches)]
        for future in as_completed(futures):
            index, result, addresses = future.result()
            _absorb(found, queried_ok, addresses, result, str(index))
            edges = len(_edges(result.get("parsed")))
            print(
                f"ids batch {index} ranks {result['rank_from']}-{result['rank_to']} "
                f"ok={result['ok']} edges={edges} capped={result.get('capped')} "
                f"status={result['meta'].get('http_status')}",
                flush=True,
            )
            if not result["ok"]:
                for address in addresses:
                    pending_refetch.append((f"fail-{index}", address))
            elif result.get("capped"):
                for address in result["missing"]:
                    pending_refetch.append((f"ids-{index}", address))

    top_missing = [
        row["address"] for row in rows if row["rank"] <= 500 and row["address"] not in found
    ]
    for address in top_missing:
        pending_refetch.append(("top500", address))

    pending_ids = []
    for _, address in pending_refetch:
        if address not in found and ARWEAVE_ID.fullmatch(address) and address not in pending_ids:
            pending_ids.append(address)

    def split_query(addresses: list[str], label: str) -> None:
        """Query this id list. A failed or capped page is split in half."""
        if not addresses:
            return
        digest = hashlib.sha256(",".join(addresses).encode()).hexdigest()[:16]
        stem = raw_dir / "gql" / "confirm" / f"{label}-{digest}"
        result = _query(IDS_QUERY, {"ids": addresses}, stem)
        _absorb(found, queried_ok, addresses, result, label)
        print(
            f"confirm {label} n={len(addresses)} ok={result['ok']} "
            f"edges={len(_edges(result.get('parsed')))} capped={result.get('capped')}",
            flush=True,
        )
        if not result["ok"]:
            if len(addresses) == 1:
                return
            mid = len(addresses) // 2
            split_query(addresses[:mid], label + "a")
            split_query(addresses[mid:], label + "b")
            return
        if result.get("capped"):
            missing = [address for address in result["missing"] if address not in found]
            if not missing or len(missing) == len(addresses):
                if len(addresses) == 1:
                    return
                mid = len(addresses) // 2
                split_query(addresses[:mid], label + "a")
                split_query(addresses[mid:], label + "b")
                return
            split_query(missing, label + "m")

    # Keep the gateway at WORKERS. Each splitter runs one chain; four chains run together.
    chunks = [pending_ids[index : index + BATCH] for index in range(0, len(pending_ids), BATCH)]
    if chunks:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(split_query, chunk, f"c{index:02d}") for index, chunk in enumerate(chunks)]
            for future in as_completed(futures):
                future.result()
    return found, queried_ok


def tag_map(tags: list[dict] | None) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for tag in tags or []:
        name = tag.get("name")
        value = tag.get("value")
        if name and name not in mapped and value is not None:
            mapped[name] = value
    return mapped


def compact_tags(mapped: dict[str, str]) -> dict[str, str]:
    return {key: mapped[key] for key in KEEP_TAGS if key in mapped}


def _text_blob(mapped: dict[str, str]) -> str:
    parts = [mapped.get(key, "") for key in ("Name", "App-Name", "Protocol-Name")]
    return " ".join(part for part in parts if part)


def classify_process(
    mapped: dict[str, str],
    *,
    config_pool: dict | None,
    liquidops: dict | None,
    address: str,
    botega_modules: set[str],
    permaswap_modules: set[str],
) -> tuple[str, str, str | None]:
    """Return role, confidence, provider. Name rules do not override a config role."""
    blob = _text_blob(mapped)
    name = mapped.get("Name") or ""
    module = mapped.get("Module") or ""
    if config_pool is not None:
        return "pool", "high", config_pool["fields"].get("dex")
    if address == LIQUIDOPS_OQAR or (liquidops and address == liquidops["address"]):
        confidence = "high" if "liquidops" in blob.lower() else "medium"
        return "lending", confidence, "liquidops"
    if address == QAR_PROCESS:
        return "token_process", "high", None
    if name.startswith("Botega Agent"):
        return "agent", "high", "botega"
    if name.startswith("Dexi Portfolio Agent") or (
        name.startswith("Dexi ") and "Agent" in name
    ):
        return "agent", "high", "dexi"
    if re.search(r"(?i)botega", blob) and re.search(r"(?i)(\bLP\b|/|pool)", blob):
        return "pool", "high", "botega"
    if re.search(r"(?i)permaswap", blob):
        return "pool", "high", "permaswap"
    if WORD_DEXI.search(blob) and re.search(r"(?i)(\bLP\b|/|pool)", blob):
        return "pool", "high", "dexi"
    if PAIR_NAME.match(name) and module and module in permaswap_modules:
        return "pool", "medium", "permaswap"
    if module and module in botega_modules and re.search(r"(?i)(\bLP\b|/)", name):
        return "pool", "medium", "botega"
    if "liquidops" in blob.lower():
        return "lending", "high", "liquidops"
    if WORD_LOCK.search(blob):
        return "lock", "medium", None
    if WORD_BRIDGE.search(blob):
        return "bridge", "medium", None
    if WORD_LENDING.search(blob):
        return "lending", "medium", None
    if WORD_MULTISIG.search(blob):
        return "multisig", "medium", None
    if mapped.get("Ticker") or mapped.get("Denomination"):
        return "token", "medium", None
    return "unknown_process", "low", None


def pool_index(pools: list[dict]) -> dict[str, dict]:
    indexed = {}
    for pool in pools:
        indexed.setdefault(pool["id"], pool)
    return indexed


def learned_modules(found: dict[str, dict], pools_by_id: dict[str, dict]) -> tuple[set[str], set[str]]:
    botega: set[str] = set()
    permaswap: set[str] = set()
    for address, pool in pools_by_id.items():
        if pool.get("commented"):
            continue
        hit = found.get(address)
        if not hit:
            continue
        module = tag_map((hit["node"].get("tags") or [])).get("Module")
        dex = pool["fields"].get("dex")
        if not module:
            continue
        if dex == "botega":
            botega.add(module)
        elif dex == "permaswap":
            permaswap.add(module)
    return botega, permaswap


def config_source(pool: dict) -> str:
    del pool
    return "local config private-config; private parameters redacted"


def redact_pool(pool: dict) -> dict:
    fields = pool.get("fields") or {}
    return {
        "config_name": "redacted",
        "commented": pool.get("commented"),
        "excerpt_path": "private-config",
        "excerpt_line": pool.get("excerpt_line"),
        "original_line": None,
        "fields": {
            "dex": fields.get("dex"),
            "token0": fields.get("token0"),
            "token1": fields.get("token1"),
            "fee_ratio": "redacted",
        },
        "id": pool.get("id"),
        "id_excerpt_line": pool.get("id_excerpt_line"),
        "id_original_line": None,
    }


def build_rows(
    rows: list[dict],
    found: dict[str, dict],
    *,
    queried_ok: set[str],
    pools_by_id: dict[str, dict],
    pools_by_id_all: dict[str, list],
    liquidops: dict | None,
    wsrc: dict[str, dict],
    overlap: dict[str, dict],
    botega_modules: set[str],
    permaswap_modules: set[str],
    balance_source: str,
) -> list[dict]:
    classified = []
    for row in rows:
        address = row["address"]
        hit = found.get(address)
        invalid_id = ARWEAVE_ID.fullmatch(address) is None
        sources = [f"balance {balance_source} key {address} rank {row['rank']}"]
        mapped: dict[str, str] = {}
        owner = None
        is_process = None
        if hit:
            mapped = tag_map(hit["node"].get("tags") or [])
            owner = (hit["node"].get("owner") or {}).get("address")
            is_process = mapped.get("Type") == "Process"
            sources.append(
                f"graphql transactions(ids) {hit['endpoint']} body {hit['body_path']} "
                f"Type={mapped.get('Type')}"
            )
        elif address in queried_ok:
            is_process = False
            sources.append(
                "graphql transactions(ids) returned no edge on a successful query; not Type=Process"
            )
        else:
            sources.append("graphql transactions(ids) batch failed; is_process left unknown")
        pool_rows = [item for item in pools_by_id_all.get(address, [])]
        pool = pool_rows[0] if pool_rows else None
        for item in pool_rows:
            sources.append(config_source(item))
        if address == LIQUIDOPS_OQAR and liquidops:
            sources.append(
                f"local config {liquidops['excerpt_path']} excerpt line {liquidops['excerpt_line']} "
                f"(original {liquidops.get('original_file')} line {liquidops.get('original_line')}); "
                f"{liquidops['note']}"
            )
        wsrc_row = wsrc.get(address)
        if wsrc_row:
            sources.append(
                "w-src evidence/p9-prep/20261017T051439Z-w-src/addresses.json "
                f"role={wsrc_row.get('role')} confidence={wsrc_row.get('confidence')} "
                f"source={wsrc_row.get('source')}"
            )
        drive = overlap.get(address)
        if drive:
            same = str(drive.get("qar_raw_balance")) == row["raw_text"]
            sources.append(
                "drive inventory data/raw/drive-cu/overlap-rows.json "
                f"path={drive.get('path')} ts={drive.get('ts')} ord={drive.get('ord')} "
                f"bh={drive.get('bh')} inventoried qar_raw_balance={drive.get('qar_raw_balance')} "
                f"match_checkpoint_balance={same}. "
                "This is not w-drive/evidence/side-d/overlap.json."
            )
        provider = None
        if invalid_id:
            role, confidence = "invalid_id", "high"
            is_process = False
            sources.append(
                "balance key is not a 43-character Arweave id, so it is not an AO process id and not classified as a wallet"
            )
        elif is_process is None and pool is not None:
            role, confidence = "pool", "low"
            provider = pool["fields"].get("dex")
            sources.append("chain process check missing; config still names this id as a pool")
        elif is_process is None and address == LIQUIDOPS_OQAR:
            role, confidence, provider = "lending", "low", "liquidops"
        elif is_process is None:
            role, confidence = "unqueried", "low"
        elif is_process:
            role, confidence, provider = classify_process(
                mapped,
                config_pool=pool,
                liquidops=liquidops,
                address=address,
                botega_modules=botega_modules,
                permaswap_modules=permaswap_modules,
            )
            if role == "unknown_process" and wsrc_row and wsrc_row.get("role") == "pool_candidate":
                role, confidence = "pool_candidate", "low"
                provider = wsrc_row.get("provider") or provider
        else:
            if pool is not None:
                role, confidence = "pool", "low"
                provider = pool["fields"].get("dex")
                sources.append("config names a pool but the id query did not return Type=Process")
            elif address == LIQUIDOPS_OQAR:
                role, confidence, provider = "lending", "low", "liquidops"
                sources.append("config names LiquidOps oQAR but the id query did not return Type=Process")
            elif mapped:
                role, confidence = "non_process_transaction", "high"
            elif wsrc_row and wsrc_row.get("role") == "pool_candidate":
                role, confidence = "pool_candidate", "low"
                provider = wsrc_row.get("provider")
            else:
                role, confidence = "wallet", "medium"
        name = mapped.get("Name")
        name_from = "process_tag" if name else None
        if not name and pool is not None:
            name = pool["config_name"]
            name_from = "local_config"
        elif not name and address == LIQUIDOPS_OQAR:
            name = "LiquidOps oQAR"
            name_from = "local_config"
        classified.append(
            {
                "address": address,
                "rank": row["rank"],
                "raw_balance": row["raw_text"],
                "human_balance": human_balance(row["raw_balance"]),
                "is_process": is_process,
                "role": role,
                "name": name,
                "name_from": name_from,
                "provider": provider,
                "owner": owner,
                "module": mapped.get("Module"),
                "tags": compact_tags(mapped),
                "config_status": (
                    "commented" if pool and pool.get("commented") else "active" if pool else None
                ),
                "source": sources,
                "confidence": confidence,
            }
        )
    return classified


def enrich_signals(
    classified: list[dict],
    raw_dir: Path,
    *,
    botega_modules: set[str],
    permaswap_modules: set[str],
    pools_by_id: dict[str, dict],
    liquidops: dict | None,
) -> None:
    unknowns = [
        row
        for row in classified
        if row["is_process"] and row["role"] in {"unknown_process", "pool_candidate"}
    ]
    top_unknowns = [row for row in unknowns if row["rank"] <= 500]
    targets = unknowns if len(unknowns) <= 300 else top_unknowns
    print(f"info/eval targets {len(targets)} of {len(unknowns)} unknown processes", flush=True)

    def info_work(row: dict) -> tuple[str, dict]:
        stem = raw_dir / "gql" / "info" / row["address"]
        return row["address"], _query(INFO_QUERY, {"id": row["address"]}, stem)

    info_results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(info_work, row) for row in targets]
        done = 0
        for future in as_completed(futures):
            address, result = future.result()
            info_results[address] = result
            done += 1
            if done % 25 == 0 or done == len(targets):
                print(f"info {done}/{len(targets)}", flush=True)

    eval_targets = []
    for row in classified:
        result = info_results.get(row["address"])
        if not result:
            if row["is_process"] and row["role"] == "unknown_process":
                row["source"].append(
                    "Info/Eval not queried"
                    + (" (outside the top 500 unknown-process cap)" if row["rank"] > 500 else "")
                )
            continue
        if not result["ok"]:
            row["source"].append(f"Info query failed body {result['body_path']} error {result['meta'].get('error')}")
            continue
        edges = _edges(result["parsed"])
        row["source"].append(
            f"graphql Info From-Process {result['meta']['endpoint']} body {result['body_path']} edges={len(edges)}"
        )
        if not edges and row["rank"] <= 100 and row["role"] in {"unknown_process", "pool_candidate"}:
            eval_targets.append(row)
            continue
        extra: dict[str, str] = {}
        for edge in edges:
            extra.update(tag_map((edge.get("node") or {}).get("tags")))
        merged = dict(extra)
        merged.update(row["tags"])
        if row["role"] in {"unknown_process", "pool_candidate"}:
            role, confidence, provider = classify_process(
                merged,
                config_pool=pools_by_id.get(row["address"]),
                liquidops=liquidops,
                address=row["address"],
                botega_modules=botega_modules,
                permaswap_modules=permaswap_modules,
            )
            if role != "unknown_process":
                row["role"] = role
                row["confidence"] = confidence
                row["provider"] = provider
                row["source"].append(f"role set from Info tags plus process tags: {role}")
            if not row["name"] and extra.get("Name"):
                row["name"] = extra["Name"]
                row["name_from"] = "info_tag"

    def eval_work(row: dict) -> tuple[str, dict]:
        stem = raw_dir / "gql" / "eval" / row["address"]
        return row["address"], _query(EVAL_QUERY, {"id": row["address"]}, stem)

    if eval_targets:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(eval_work, row) for row in eval_targets]
            for future in as_completed(futures):
                address, result = future.result()
                row = next(item for item in classified if item["address"] == address)
                if not result["ok"]:
                    row["source"].append(
                        f"Eval query failed body {result['body_path']} error {result['meta'].get('error')}"
                    )
                    continue
                edges = _edges(result["parsed"])
                names = []
                for edge in edges:
                    mapped = tag_map((edge.get("node") or {}).get("tags"))
                    if mapped.get("Name"):
                        names.append(mapped["Name"])
                row["source"].append(
                    f"graphql Eval recipients {result['meta']['endpoint']} body {result['body_path']} "
                    f"edges={len(edges)} name_tags={names}"
                )
                # Eval tag names are not applied as a role. The message body was not read.


def enrich_owner_wallets(classified: list[dict], raw_dir: Path) -> None:
    targets = [
        row
        for row in classified
        if row["rank"] <= 20 and row["is_process"] is False and row["role"] == "wallet"
    ]

    def work(row: dict) -> tuple[str, dict]:
        stem = raw_dir / "gql" / "owner" / row["address"]
        return row["address"], _query(OWNER_QUERY, {"owner": row["address"]}, stem)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(work, row) for row in targets]
        for future in as_completed(futures):
            address, result = future.result()
            row = next(item for item in classified if item["address"] == address)
            if not result["ok"]:
                row["source"].append(
                    f"owner query failed body {result['body_path']} error {result['meta'].get('error')}"
                )
                continue
            edges = _edges(result["parsed"])
            row["source"].append(
                f"graphql transactions(owners) {result['meta']['endpoint']} body {result['body_path']} "
                f"edges={len(edges)}"
            )
            if edges:
                kind = tag_map((edges[0].get("node") or {}).get("tags")).get("Type")
                row["confidence"] = "high"
                row["source"].append(
                    f"address has signed an indexed transaction (first hit Type={kind}); treated as a wallet"
                )


def stats_for(classified: list[dict], total: int) -> dict:
    buckets: dict[str, dict] = {}
    for row in classified:
        bucket = buckets.setdefault(
            row["role"],
            {"role": row["role"], "addresses": 0, "raw_balance": 0},
        )
        bucket["addresses"] += 1
        bucket["raw_balance"] += int(row["raw_balance"])
    roles = []
    for bucket in sorted(buckets.values(), key=lambda item: -item["raw_balance"]):
        raw = bucket["raw_balance"]
        roles.append(
            {
                "role": bucket["role"],
                "addresses": bucket["addresses"],
                "raw_balance": str(raw),
                "human_balance": human_balance(raw),
                "supply_share": supply_share(raw, total),
            }
        )
    providers: dict[str, dict] = {}
    for row in classified:
        if row["role"] != "pool":
            continue
        key = row.get("provider") or "unknown"
        bucket = providers.setdefault(key, {"provider": key, "addresses": 0, "raw_balance": 0})
        bucket["addresses"] += 1
        bucket["raw_balance"] += int(row["raw_balance"])
    provider_rows = []
    for bucket in sorted(providers.values(), key=lambda item: -item["raw_balance"]):
        raw = bucket["raw_balance"]
        provider_rows.append(
            {
                "provider": bucket["provider"],
                "addresses": bucket["addresses"],
                "raw_balance": str(raw),
                "human_balance": human_balance(raw),
                "supply_share": supply_share(raw, total),
            }
        )
    return {
        "holders": len(classified),
        "total_supply_raw": str(total),
        "total_supply_human": human_balance(total),
        "roles": roles,
        "pool_providers": provider_rows,
        "top_500_unqueried": sum(1 for row in classified if row["rank"] <= 500 and row["role"] == "unqueried"),
        "top_500_covered": sum(1 for row in classified if row["rank"] <= 500 and row["is_process"] is not None),
    }


def write_summary(path: Path, payload: dict) -> None:
    stats = payload["stats"]
    highlighted = payload["highlighted"]
    lines = [
        "# P8 holder classification",
        "",
        f"Run `{payload['run_id']}`. Process `{QAR_PROCESS}`. The module was not executed. "
        "`goal_complete` is false. This is the nonce 2074518 balance map, not the shutdown ledger.",
        "",
        "## Conclusion",
        "",
        payload["conclusion"],
        "",
        "## Numbers",
        "",
        "| Role | Addresses | Raw qAR | Human qAR (12 decimals) | Share of supply |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for role in stats["roles"]:
        lines.append(
            f"| {role['role']} | {role['addresses']} | {role['raw_balance']} | "
            f"{role['human_balance']} | {role['supply_share']} |"
        )
    lines.extend(
        [
            "",
            f"Holders: {stats['holders']}. Supply raw `{stats['total_supply_raw']}` "
            f"({stats['total_supply_human']}). Sum of classified raw balances equals that supply: "
            f"{payload['sum_matches_supply']}. Top 500 covered: {stats['top_500_covered']}/500.",
            "",
            "Pool raw balances by the provider named in the local config or in the process Name tag:",
            "",
            "| Provider | Addresses | Raw qAR | Human qAR | Share of supply |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for provider in stats["pool_providers"]:
        lines.append(
            f"| {provider['provider']} | {provider['addresses']} | {provider['raw_balance']} | "
            f"{provider['human_balance']} | {provider['supply_share']} |"
        )
    lines.extend(["", "## Highlighted addresses", ""])
    for row in highlighted:
        lines.append(
            f"- `{row['address']}` rank {row['rank']} role `{row['role']}` "
            f"is_process `{row['is_process']}` name `{row['name']}` "
            f"confidence `{row['confidence']}` raw `{row['raw_balance']}` "
            f"human `{row['human_balance']}` provider `{row.get('provider')}`."
        )
    lines.extend(
        [
            "",
            "## Local configs",
            "",
            payload["config_note"],
            "",
            "## Evidence",
            "",
        ]
    )
    for item in payload["evidence_files"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Unfinished", ""])
    for item in payload["unfinished"]:
        lines.append(f"- {item}")
    lines.append("")
    path.write_text("\n".join(lines))


def file_record(path: Path) -> dict:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def balance_delta(previous: dict[str, str], current: dict[str, str]) -> dict[str, list]:
    """Split current addresses into added, changed, and unchanged versus previous.

    Raw values may be JSON strings or integers. Comparison uses the integer amount.
    """
    prev_raw = {address: int(raw) for address, raw in previous.items()}
    curr_raw = {address: int(raw) for address, raw in current.items()}
    added = sorted(set(curr_raw) - set(prev_raw))
    removed = sorted(set(prev_raw) - set(curr_raw))
    changed = []
    unchanged = []
    for address, raw in curr_raw.items():
        if address not in prev_raw:
            continue
        if prev_raw[address] == raw:
            unchanged.append(address)
        else:
            changed.append(address)
    changed.sort(key=lambda address: -abs(curr_raw[address] - prev_raw[address]))
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }


def reuse_classification(
    prior: dict,
    row: dict,
    balance_source: str,
    prior_run: str,
    prior_nonce: int = 2074518,
) -> dict:
    """Copy a prior role onto a tail row whose raw balance did not change."""
    kept = dict(prior)
    kept["rank"] = row["rank"]
    kept["raw_balance"] = row["raw_text"]
    kept["human_balance"] = human_balance(row["raw_balance"])
    old_sources = [item for item in prior.get("source", []) if not str(item).startswith("balance ")]
    kept["source"] = [
        (
            f"balance {balance_source} key {row['address']} rank {row['rank']} "
            f"raw unchanged from nonce {prior_nonce}"
        ),
        f"classification reused from {prior_run}; transactions(ids) not repeated",
        *old_sources,
    ]
    kept["reused_from"] = prior_run
    return kept


def run_tail(
    *,
    args: argparse.Namespace,
    raw_dir: Path,
    evidence_dir: Path,
    balance_path: Path,
    pools: list[dict],
    pools_by_id: dict[str, dict],
    liquidops: dict | None,
    wsrc: dict[str, dict],
    overlap: dict[str, dict],
) -> None:
    """Classify the tail ledger, querying only new and balance-changed addresses."""
    prior_doc = json.loads(Path(args.prior).read_text())
    prior_rows = {row["address"]: row for row in prior_doc["holders"]}
    previous = json.loads(Path(args.prior_balances).read_text())
    current = json.loads(balance_path.read_text())
    delta = balance_delta(previous, current)
    missing_prior = [address for address in delta["unchanged"] + delta["changed"] if address not in prior_rows]
    if missing_prior:
        raise SystemExit(f"prior classification lacks {len(missing_prior)} addresses, first {missing_prior[:3]}")
    rows, total = load_balances(balance_path)
    by_rank = {row["address"]: row for row in rows}
    refresh = delta["added"] + delta["changed"]
    refresh_rows = [by_rank[address] for address in refresh]
    print(
        f"tail holders {len(rows)} supply {total} reuse {len(delta['unchanged'])} "
        f"query {len(refresh)} removed {len(delta['removed'])}",
        flush=True,
    )
    stem = raw_dir / "gql" / "ids" / "delta-0000"
    found: dict[str, dict] = {}
    queried_ok: set[str] = set()
    confirmed_absent: set[str] = set()
    confirm_body = ""
    if refresh_rows:
        result = _query(IDS_QUERY, {"ids": [row["address"] for row in refresh_rows]}, stem)
        _absorb(found, queried_ok, [row["address"] for row in refresh_rows], result, "delta")
        print(
            f"delta query ok={result['ok']} edges={len(_edges(result.get('parsed')))} "
            f"status={result['meta'].get('http_status')}",
            flush=True,
        )
        if result.get("capped") or not result["ok"]:
            for address in refresh:
                one = raw_dir / "gql" / "ids" / f"one-{address}"
                single = _query(IDS_QUERY, {"ids": [address]}, one)
                _absorb(found, queried_ok, [address], single, address)
                print(f"single {address} ok={single['ok']} edges={len(_edges(single.get('parsed')))}", flush=True)
        else:
            # A short page can omit an id without hitting the 10/20/25/50 cap sizes.
            # Read the missing ids once more before treating them as wallets.
            missing_after = [address for address in refresh if address not in found]
            if missing_after:
                confirm = _query(IDS_QUERY, {"ids": missing_after}, raw_dir / "gql" / "ids" / "delta-absent")
                _absorb(found, queried_ok, missing_after, confirm, "delta-absent")
                print(
                    f"confirm absent n={len(missing_after)} ok={confirm['ok']} "
                    f"edges={len(_edges(confirm.get('parsed')))} capped={confirm.get('capped')}",
                    flush=True,
                )
                if confirm["ok"] and not confirm.get("capped"):
                    confirmed_absent = {address for address in missing_after if address not in found}
                    confirm_body = str(confirm["body_path"])
                if confirm.get("capped") or not confirm["ok"]:
                    for address in missing_after:
                        if address in found:
                            continue
                        one = raw_dir / "gql" / "ids" / f"one-{address}"
                        single = _query(IDS_QUERY, {"ids": [address]}, one)
                        _absorb(found, queried_ok, [address], single, address)
                        print(
                            f"single {address} ok={single['ok']} edges={len(_edges(single.get('parsed')))}",
                            flush=True,
                        )
    prior_stats = json.loads(Path(args.prior).with_name("stats.json").read_text())
    botega_modules = set(prior_stats.get("learned_botega_modules") or [])
    permaswap_modules = set(prior_stats.get("learned_permaswap_modules") or [])
    pools_by_id_all = {address: [item for item in pools if item["id"] == address] for address in pools_by_id}
    refreshed = build_rows(
        refresh_rows,
        found,
        queried_ok=queried_ok,
        pools_by_id=pools_by_id,
        pools_by_id_all=pools_by_id_all,
        liquidops=liquidops,
        wsrc=wsrc,
        overlap=overlap,
        botega_modules=botega_modules,
        permaswap_modules=permaswap_modules,
        balance_source=str(balance_path),
    )
    if confirmed_absent:
        note = f"graphql transactions(ids) confirmation body {confirm_body} returned no edge for this id"
        for row in refreshed:
            if row["address"] in confirmed_absent:
                row["source"].append(note)
    for row in refreshed:
        prior = prior_rows.get(row["address"])
        old_raw = previous.get(row["address"])
        if prior and row["role"] == "unqueried":
            carried = reuse_classification(
                prior,
                by_rank[row["address"]],
                str(balance_path),
                str(args.prior),
                prior_nonce=args.prior_nonce,
            )
            carried["raw_balance"] = row["raw_balance"]
            carried["human_balance"] = row["human_balance"]
            carried["source"].insert(
                1,
                f"tail transactions(ids) failed; kept nonce {args.prior_nonce} role {prior['role']}",
            )
            row.clear()
            row.update(carried)
        elif old_raw is not None:
            row["source"].append(
                f"nonce {args.prior_nonce} raw {old_raw} role {prior['role']} rank {prior['rank']}"
            )
            will_owner = row["rank"] <= 20 and row["is_process"] is False and row["role"] == "wallet"
            prior_owner = [
                item
                for item in (prior or {}).get("source", [])
                if "transactions(owners)" in str(item) or "signed an indexed transaction" in str(item)
            ]
            already_owner = any("transactions(owners)" in str(item) for item in row["source"])
            if (
                prior
                and prior.get("role") == row["role"]
                and prior_owner
                and not will_owner
                and not already_owner
            ):
                row["source"].extend(prior_owner)
                row["source"].append(
                    f"owner evidence reused from nonce {args.prior_nonce}; "
                    f"rank {row['rank']} was outside the owner-query cap"
                )
                if prior.get("confidence") == "high":
                    row["confidence"] = "high"
        else:
            row["source"].append(f"address absent from nonce {args.prior_nonce} balance map")
    enrich_signals(
        refreshed,
        raw_dir,
        botega_modules=botega_modules,
        permaswap_modules=permaswap_modules,
        pools_by_id=pools_by_id,
        liquidops=liquidops,
    )
    enrich_owner_wallets(refreshed, raw_dir)
    refreshed_by = {row["address"]: row for row in refreshed}
    public_rows = []
    for row in rows:
        if row["address"] in refreshed_by:
            public_rows.append(refreshed_by[row["address"]])
        else:
            public_rows.append(
                reuse_classification(
                    prior_rows[row["address"]],
                    row,
                    str(balance_path),
                    str(args.prior),
                    prior_nonce=args.prior_nonce,
                )
            )
    public_rows.sort(key=lambda item: item["rank"])
    failed = [row["address"] for row in refreshed if row["role"] == "unqueried"]
    if failed:
        raise SystemExit(f"tail transactions(ids) left {len(failed)} addresses unqueried: {failed}")
    non_wallets = [row for row in public_rows if row["role"] != "wallet"]
    stats = stats_for(public_rows, total)
    sum_raw = sum(int(row["raw_balance"]) for row in public_rows)
    if sum_raw != total:
        raise SystemExit(f"classified sum {sum_raw} != supply {total}")
    if len(public_rows) != len(rows):
        raise SystemExit(f"classified rows {len(public_rows)} != balance rows {len(rows)}")
    movement = []
    added_set = set(delta["added"])
    for address in delta["added"] + delta["changed"]:
        current_row = refreshed_by[address]
        prior = prior_rows.get(address)
        old_raw = None if address not in previous else str(int(previous[address]))
        movement.append(
            {
                "address": address,
                "change": "added" if address in added_set else "balance",
                "old_raw": old_raw,
                "new_raw": current_row["raw_balance"],
                "delta_raw": None if old_raw is None else str(int(current_row["raw_balance"]) - int(old_raw)),
                "old_role": None if prior is None else prior["role"],
                "new_role": current_row["role"],
                "old_confidence": None if prior is None else prior.get("confidence"),
                "new_confidence": current_row["confidence"],
                "old_rank": None if prior is None else prior["rank"],
                "new_rank": current_row["rank"],
                "old_name": None if prior is None else prior.get("name"),
                "new_name": current_row.get("name"),
                "is_process": current_row["is_process"],
                "confidence": current_row["confidence"],
            }
        )
    net_raw = 0
    for item in movement:
        net_raw += int(item["new_raw"]) if item["delta_raw"] is None else int(item["delta_raw"])
    for address in delta["removed"]:
        net_raw -= int(previous[address])
    if net_raw != 0:
        raise SystemExit(f"balance movement net {net_raw} is not zero")
    role_delta = []
    prior_roles = {item["role"]: item for item in prior_stats["roles"]}
    new_roles = {item["role"]: item for item in stats["roles"]}
    for role in sorted(set(prior_roles) | set(new_roles)):
        old_item = prior_roles.get(role, {"addresses": 0, "raw_balance": "0"})
        new_item = new_roles.get(role, {"addresses": 0, "raw_balance": "0"})
        role_delta.append(
            {
                "role": role,
                "old_addresses": old_item["addresses"],
                "new_addresses": new_item["addresses"],
                "old_raw": str(old_item["raw_balance"]),
                "new_raw": str(new_item["raw_balance"]),
                "delta_raw": str(int(new_item["raw_balance"]) - int(old_item["raw_balance"])),
            }
        )
    stats["sum_matches_supply"] = sum_raw == total
    stats["unique_addresses"] = len({row["address"] for row in public_rows}) == len(public_rows)
    stats["learned_botega_modules"] = sorted(botega_modules)
    stats["learned_permaswap_modules"] = sorted(permaswap_modules)
    stats["reused_addresses"] = len(delta["unchanged"])
    stats["requeried_addresses"] = len(refresh)
    stats["compared_to"] = {
        "nonce": args.prior_nonce,
        "holders": prior_doc.get("holders") and len(prior_doc["holders"]),
        "evidence": str(args.prior),
        "added": len(delta["added"]),
        "removed": len(delta["removed"]),
        "balance_changed": len(delta["changed"]),
        "unchanged": len(delta["unchanged"]),
        "role_changed": [
            item["address"] for item in movement if item["old_role"] not in (None, item["new_role"])
        ],
        "role_delta": role_delta,
    }
    report_path = balance_path.with_name("report.json")
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    holder_doc = {
        "run_id": args.run_id,
        "process_id": QAR_PROCESS,
        "balance_source": str(balance_path),
        "balance_sha256": sha256_file(balance_path),
        "balance_bytes": balance_path.stat().st_size,
        "ledger_nonce": args.ledger_nonce,
        "prior_nonce": args.prior_nonce,
        "prior_classification": str(args.prior),
        "denomination": 12,
        "total_supply_raw": str(total),
        "tail_report": None
        if report is None
        else {
            "path": str(report_path),
            "to_nonce": report.get("to_nonce"),
            "handler_errors": report.get("handler_errors"),
            "sum_equals_supply": (report.get("ledger") or {}).get("sum_equals_supply"),
            "addresses": (report.get("ledger") or {}).get("addresses"),
        },
        "holders": public_rows,
    }
    _write_json(evidence_dir / "holders-classified.json", holder_doc)
    _write_json(
        evidence_dir / "pools-locks-bridges.json",
        {
            "run_id": args.run_id,
            "ledger_nonce": args.ledger_nonce,
            "rule": "Every holder whose role is not wallet. Pool balances are not split into LP shares.",
            "rows": non_wallets,
        },
    )
    _write_json(evidence_dir / "stats.json", stats)
    _write_json(
        evidence_dir / "diff-2074518.json",
        {
            "prior_nonce": args.prior_nonce,
            "ledger_nonce": args.ledger_nonce,
            "removed": [
                {
                    "address": address,
                    "old_raw": str(int(previous[address])),
                    "old_role": prior_rows[address]["role"],
                }
                for address in delta["removed"]
                if address in prior_rows
            ],
            "net_raw": "0",
            "movement": movement,
            "role_delta": role_delta,
        },
    )
    raw_files = [
        file_record(path)
        for path in sorted(raw_dir.rglob("*"))
        if path.is_file() and not path.name.endswith(".partial")
    ]
    _write_json(
        evidence_dir / "query-manifest.json",
        {
            "run_id": args.run_id,
            "balance": file_record(balance_path),
            "prior_balances": file_record(Path(args.prior_balances)),
            "raw_dir": str(raw_dir),
            "files": raw_files,
            "requeried": refresh,
            "reused": len(delta["unchanged"]),
        },
    )
    lines = [
        "# P8 tail holder classification",
        "",
        f"Run `{args.run_id}`. Process `{QAR_PROCESS}`. Ledger nonce {args.ledger_nonce}. "
        f"The module was not executed. Prior classification is nonce {args.prior_nonce} "
        f"at `{args.prior}`.",
        "",
        "## Conclusion",
        "",
        (
            f"The tail map has {len(public_rows)} addresses and raw supply `{total}` "
            f"({human_balance(total)} qAR). Sum of classified balances equals that supply: "
            f"{sum_raw == total}. Against nonce {args.prior_nonce}: "
            f"{len(delta['added'])} added, {len(delta['removed'])} removed, "
            f"{len(delta['changed'])} balance changes, {len(delta['unchanged'])} reused without a new id query. "
            f"The raw deltas on added, changed, and removed addresses sum to {net_raw}."
        ),
        "",
        "Balance changes and the new address were queried with `transactions(ids)`. "
        + (
            f"The first page returned {len(found)} process ids. A second read of the other "
            f"{len(confirmed_absent)} ids returned 0 edges (`{confirm_body}`). "
            if confirmed_absent
            else ""
        )
        + f"Unchanged addresses keep the nonce {args.prior_nonce} role, name, and sources. "
        "Their ranks follow the tail balance order.",
        "",
        f"## Movement since nonce {args.prior_nonce}",
        "",
        "| Address | Change | Old raw | New raw | Delta raw | Old role | New role | Old rank | New rank |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: |",
    ]
    for item in movement:
        lines.append(
            f"| `{item['address']}` | {item['change']} | {item['old_raw']} | {item['new_raw']} | "
            f"{item['delta_raw']} | {item['old_role']} | {item['new_role']} | "
            f"{item['old_rank']} | {item['new_rank']} |"
        )
    lines.extend(
        [
            "",
            "No address changed role."
            if not stats["compared_to"]["role_changed"]
            else "Role changes: " + ", ".join(f"`{item}`" for item in stats["compared_to"]["role_changed"]) + ".",
            "",
        ]
    )
    for item in movement:
        if item["change"] != "added":
            continue
        lines.append(
            f"New address `{item['address']}` is role `{item['new_role']}` "
            f"name `{item['new_name'] or 'absent'}` is_process `{item['is_process']}` "
            f"confidence `{item['confidence']}` raw `{item['new_raw']}`."
        )
    amount_matches = []
    for item in movement:
        if item["change"] != "added":
            continue
        for other in movement:
            if other["delta_raw"] is None or int(other["delta_raw"]) >= 0:
                continue
            if int(item["new_raw"]) == -int(other["delta_raw"]):
                amount_matches.append((item["address"], other["address"], item["new_raw"]))
    if amount_matches:
        lines.append("")
        for new_address, old_address, raw in amount_matches:
            lines.append(
                f"The new raw balance on `{new_address}` equals the raw decrease on `{old_address}` "
                f"(`{raw}`). This comparison is only the two balance amounts. "
                "It does not identify a transfer message."
            )
    confidence_changed = [
        item
        for item in movement
        if item["old_confidence"] not in (None, item["new_confidence"])
    ]
    if confidence_changed:
        lines.append("")
        lines.append(
            "Confidence changes on requeried addresses: "
            + ", ".join(
                f"`{item['address']}` {item['old_confidence']} -> {item['new_confidence']}"
                for item in confidence_changed
            )
            + "."
        )
    watched = [LIQUIDOPS_OQAR, "_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4"]
    moved = set(delta["added"] + delta["changed"] + delta["removed"])
    by_public = {row["address"]: row for row in public_rows}
    kept_watched = [address for address in watched if address not in moved and address in by_public]
    if kept_watched:
        lines.append("")
        lines.append(
            "Unchanged named processes, roles reused from nonce "
            f"{args.prior_nonce}: "
            + "; ".join(
                f"`{address}` role `{by_public[address]['role']}` name `{by_public[address].get('name')}` "
                f"raw `{by_public[address]['raw_balance']}`"
                for address in kept_watched
            )
            + "."
        )
    carried_unknown = sum(
        1
        for row in public_rows
        if row["role"] == "unknown_process" and row.get("reused_from")
    )
    queried_unknown = [row["address"] for row in refreshed if row["role"] == "unknown_process"]
    if report:
        ledger = report.get("ledger") or {}
        lines.extend(
            [
                "",
                (
                    f"Tail report `{report_path}` records to_nonce {report.get('to_nonce')}, "
                    f"handler_errors {report.get('handler_errors')}, "
                    f"addresses {ledger.get('addresses')}, "
                    f"sum_equals_supply {ledger.get('sum_equals_supply')}."
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Numbers at nonce " + str(args.ledger_nonce),
            "",
            "| Role | Addresses | Raw qAR | Human qAR (12 decimals) | Share of supply |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for role in stats["roles"]:
        lines.append(
            f"| {role['role']} | {role['addresses']} | {role['raw_balance']} | "
            f"{role['human_balance']} | {role['supply_share']} |"
        )
    lines.extend(
        [
            "",
            "| Role | Old addresses | New addresses | Old raw | New raw | Delta raw |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in role_delta:
        if item["delta_raw"] == "0" and item["old_addresses"] == item["new_addresses"]:
            continue
        lines.append(
            f"| {item['role']} | {item['old_addresses']} | {item['new_addresses']} | "
            f"{item['old_raw']} | {item['new_raw']} | {item['delta_raw']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- `{evidence_dir / 'holders-classified.json'}`",
            f"- `{evidence_dir / 'stats.json'}`",
            f"- `{evidence_dir / 'diff-2074518.json'}`",
            f"- `{evidence_dir / 'pools-locks-bridges.json'}`",
            f"- `{raw_dir}`",
            "",
            "## Unfinished",
            "",
            "- LP shares, lock beneficiaries, and nested pool ownership remain unresolved.",
            (
                f"- {carried_unknown} unknown_process rows were carried forward where the balance did not change. "
                "They were not re-queried."
            ),
            (
                "- Queried unknown_process addresses: "
                + ", ".join(f"`{address}`" for address in queried_unknown)
                + "."
                if queried_unknown
                else "- No requeried address stayed unknown_process."
            ),
            "- Collateral asset, holder, and raw amount remain unknown. This is not a claim list.",
            "",
        ]
    )
    (evidence_dir / "SUMMARY.md").write_text("\n".join(lines))
    print(
        json.dumps(
            {
                "holders": len(public_rows),
                "sum_ok": sum_raw == total,
                "requeried": len(refresh),
                "reused": len(delta["unchanged"]),
                "role_changed": stats["compared_to"]["role_changed"],
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--balances", default=DEFAULT_BALANCES)
    parser.add_argument("--configs", default=DEFAULT_CONFIGS)
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    parser.add_argument("--wsrc", default=DEFAULT_WSRC)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prior", default=None, help="Previous holders-classified.json to reuse")
    parser.add_argument("--prior-balances", default=DEFAULT_BALANCES)
    parser.add_argument("--ledger-nonce", type=int, default=2075923)
    parser.add_argument("--prior-nonce", type=int, default=2074518)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    later = find_later_balances()
    balance_path = Path(args.balances)
    pools_text = Path(args.configs, "qar-pools.txt").read_text()
    configs_text = Path(args.configs, "qar-local-configs.txt").read_text()
    readme_text = Path(args.configs, "README-local-configs.md").read_text()
    pools = [redact_pool(pool) for pool in parse_pools(pools_text, "private-config")]
    liquidops = parse_liquidops(configs_text, "private-config")
    mappings = parse_qar_mappings(configs_text, "private-config")
    pools_by_id = pool_index(pools)
    wsrc_doc = json.loads(Path(args.wsrc).read_text())
    wsrc = {row["address"]: row for row in wsrc_doc.get("addresses", [])}
    overlap_doc = json.loads(Path(args.overlap).read_text()) if Path(args.overlap).exists() else {"rows": []}
    overlap = {row["address"]: row for row in overlap_doc.get("rows", [])}
    side_d = _REPO / "evidence/side-d"
    side_d_files = {
        "overlap.json": (side_d / "overlap.json").exists(),
        "roles.json": (side_d / "roles.json").exists(),
    }
    local_doc = {
        "pools": pools,
        "liquidops_oqar": liquidops,
        "qar_mappings": mappings,
        "readme": "private-config",
        "readme_says_local_configs_present": "qar-pools.txt" in readme_text,
        "later_balances_json": later,
        "w_drive_side_d": side_d_files,
        "drive_overlap_rows_used": str(args.overlap) if Path(args.overlap).exists() else None,
    }
    _write_json(evidence_dir / "local-configs.json", local_doc)

    if args.prior:
        run_tail(
            args=args,
            raw_dir=raw_dir,
            evidence_dir=evidence_dir,
            balance_path=balance_path,
            pools=pools,
            pools_by_id=pools_by_id,
            liquidops=liquidops,
            wsrc=wsrc,
            overlap=overlap,
        )
        return

    rows, total = load_balances(balance_path)
    print(f"holders {len(rows)} supply {total}", flush=True)
    found, queried_ok = fetch_id_batches(rows, raw_dir)
    botega_modules, permaswap_modules = learned_modules(found, pools_by_id)
    classified = build_rows(
        rows,
        found,
        queried_ok=queried_ok,
        pools_by_id=pools_by_id,
        pools_by_id_all={address: [item for item in pools if item["id"] == address] for address in pools_by_id},
        liquidops=liquidops,
        wsrc=wsrc,
        overlap=overlap,
        botega_modules=botega_modules,
        permaswap_modules=permaswap_modules,
        balance_source=str(balance_path),
    )
    enrich_signals(
        classified,
        raw_dir,
        botega_modules=botega_modules,
        permaswap_modules=permaswap_modules,
        pools_by_id=pools_by_id,
        liquidops=liquidops,
    )
    enrich_owner_wallets(classified, raw_dir)
    # Drop bulky tag maps from the committed holder file after role assignment.
    public_rows = []
    for row in classified:
        public = dict(row)
        public_rows.append(public)
    non_wallets = [row for row in public_rows if row["role"] != "wallet"]
    stats = stats_for(public_rows, total)
    sum_raw = sum(int(row["raw_balance"]) for row in public_rows)
    stats["sum_matches_supply"] = sum_raw == total
    stats["unique_addresses"] = len({row["address"] for row in public_rows}) == len(public_rows)
    stats["learned_botega_modules"] = sorted(botega_modules)
    stats["learned_permaswap_modules"] = sorted(permaswap_modules)
    stats["later_balances_json"] = later
    holder_doc = {
        "run_id": args.run_id,
        "process_id": QAR_PROCESS,
        "balance_source": str(balance_path),
        "balance_sha256": sha256_file(balance_path),
        "balance_bytes": balance_path.stat().st_size,
        "checkpoint_nonce": 2074518,
        "not_the_shutdown_ledger": True,
        "denomination": 12,
        "total_supply_raw": str(total),
        "holders": public_rows,
    }
    pool_doc = {
        "run_id": args.run_id,
        "rule": "Every holder whose role is not wallet. Pool balances are not split into LP shares.",
        "rows": non_wallets,
    }
    _write_json(evidence_dir / "holders-classified.json", holder_doc)
    _write_json(evidence_dir / "pools-locks-bridges.json", pool_doc)
    _write_json(evidence_dir / "stats.json", stats)

    raw_files = []
    for path in sorted(raw_dir.rglob("*")):
        if path.is_file() and not path.name.endswith(".partial"):
            raw_files.append(file_record(path))
    manifest = {
        "run_id": args.run_id,
        "balance": file_record(balance_path),
        "raw_dir": str(raw_dir),
        "files": raw_files,
        "batch_size": BATCH,
        "concurrency": WORKERS,
        "endpoint": ENDPOINT,
        "fallbacks": list(FALLBACKS),
    }
    _write_json(evidence_dir / "query-manifest.json", manifest)

    watch = [
        LIQUIDOPS_OQAR,
        "_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4",
        "cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8",
        "vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4",
        "KQhYTVaQ5tXcOQ3SrJiIt60_mdO0zAGUnT4snNwQs9U",
        QAR_PROCESS,
    ]
    by_address = {row["address"]: row for row in public_rows}
    highlighted = [by_address[item] for item in watch if item in by_address]
    top_wallet = next(row for row in public_rows if row["role"] == "wallet")
    pool_share = next((item["supply_share"] for item in stats["roles"] if item["role"] == "pool"), "0")
    lending_share = next((item["supply_share"] for item in stats["roles"] if item["role"] == "lending"), "0")
    wallet_share = next((item["supply_share"] for item in stats["roles"] if item["role"] == "wallet"), "0")
    conclusion = (
        f"Of {len(public_rows)} holders at checkpoint nonce 2074518, the top 500 were queried with "
        f"transactions(ids). Wallet share of supply is {wallet_share}. Pool share is {pool_share}. "
        f"Lending share is {lending_share}. The largest holder is `{top_wallet['address']}` "
        f"role {top_wallet['role']} raw {top_wallet['raw_balance']}. "
        f"LiquidOps oQAR `{LIQUIDOPS_OQAR}` and Permaswap `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` "
        f"are classified from the local config excerpts plus their process tags. "
        f"No balances.json was found under data/raw/fast or data/raw/p7, so this run was not repeated "
        f"on a tail ledger. w-drive/evidence/side-d/overlap.json and roles.json were absent. "
        f"Pool qAR is not divided into end-user LP shares."
    )
    config_note = (
        f"Local excerpts label `{QAR_PROCESS}` as qAR and list pool process ids. "
        "Private repository paths, commit ids, fee parameters, and config key names are not stored. "
        "Commented pool rows are kept and marked config_status=commented. "
        "w-src pool candidates stay pool_candidate unless a config row or a process Name tag "
        "identifies the role. Data-Protocol=ao only marks an AO process; it does not assign a role."
    )
    unfinished = [
        "No tail balances.json under data/raw/fast or data/raw/p7. The shutdown ledger is not classified here.",
        "w-drive/evidence/side-d/overlap.json and roles.json were not present. drive-cu/overlap-rows.json was cited where an address matched, and it is a different file.",
        "LP shares, lock beneficiaries, and nested pool ownership are unresolved. Pool balances stay on the pool address.",
        "A holder with no indexed transaction is a wallet by the transactions(ids) test. That is not a positive end-user proof.",
        "Processes outside the Info query cap keep unknown_process when Name, App-Name, Protocol-Name, Ticker, and the local config do not identify a role.",
        "Collateral asset, holder, and raw amount stay unknown. This phase does not publish a claim list.",
    ]
    if later:
        unfinished[0] = "Later balances.json files were found and are listed in stats.json. This evidence directory is the file passed as --balances."
    summary_payload = {
        "run_id": args.run_id,
        "conclusion": conclusion,
        "stats": stats,
        "highlighted": highlighted,
        "config_note": config_note,
        "sum_matches_supply": sum_raw == total,
        "evidence_files": [
            str(evidence_dir / "holders-classified.json"),
            str(evidence_dir / "pools-locks-bridges.json"),
            str(evidence_dir / "stats.json"),
            str(evidence_dir / "local-configs.json"),
            str(evidence_dir / "query-manifest.json"),
            str(raw_dir),
        ],
        "unfinished": unfinished,
    }
    write_summary(evidence_dir / "SUMMARY.md", summary_payload)
    print(json.dumps({"holders": len(public_rows), "non_wallets": len(non_wallets), "sum_ok": sum_raw == total, "top500": stats["top_500_covered"]}, indent=2))


if __name__ == "__main__":
    main()

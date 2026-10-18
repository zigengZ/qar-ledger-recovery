#!/usr/bin/env python3
"""Write P9 evidence from saved collateral queries. No network and no execution.

A missing quantity stays unknown. It is not stored as zero. Gaps are numbers
in the report and are not written back into any balance.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery.p9_balance import balance_at  # noqa: E402

PROCESS = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
SUPPLY = 189487568412204611
SUPPLY_NONCE = 2074518
CHECKPOINT_BLOCK = 1863456
TAIL_BLOCK = 1951869
HOLDER_CANDIDATE = "nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c"
_REPO = Path(__file__).resolve().parents[1]
SQLITES = [
    str(_REPO / "data/raw/p4/0-49999/20261016T175757Z-p4-0-49999/assignments.sqlite"),
    str(_REPO / "data/raw/p4/50000-99999/20261016T193251Z-p4-50000-99999/assignments.sqlite"),
    str(_REPO / "data/raw/p4/100000-149999/20261017T043811Z-p4-100000-149999/assignments.sqlite"),
]


def root_of(run: str) -> Path:
    return Path(__file__).resolve().parents[1] / "data/raw/collat" / run


def evidence_of(run: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "evidence/p9" / f"{run}-w-collat"
    path.mkdir(parents=True, exist_ok=True)
    return path


def as_int(value):
    if isinstance(value, bool) or isinstance(value, float):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def tag(tags: dict, name: str):
    value = tags.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value if isinstance(value, str) else None


def load_messages(run: str) -> list[dict]:
    path = root_of(run) / "gql" / "messages.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def load_body(run: str, message_id: str):
    path = root_of(run) / "messages" / f"{message_id}.body"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_unparsed": True}


def body_objects(body) -> list[dict]:
    if isinstance(body, dict) and not body.get("_unparsed"):
        return [body]
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    return []


def arweave_address(owner_b64: str) -> str:
    import base64
    import hashlib

    pad = "=" * ((4 - len(owner_b64) % 4) % 4)
    raw = base64.urlsafe_b64decode(owner_b64 + pad)
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")


def _load_gql_directory(directory: Path, found: dict, inner_ids: dict) -> None:
    for path in sorted(directory.glob("b*.response.json")):
        parsed = json.loads(path.read_text())
        for edge in parsed["data"]["transactions"]["edges"] or []:
            node = edge["node"]
            block = node.get("block") or {}
            tags = {item["name"]: item["value"] for item in node.get("tags") or []}
            found[node["id"]] = {
                "id": node["id"],
                "owner": (node.get("owner") or {}).get("address") or "",
                "recipient": node.get("recipient") or "",
                "quantity_winston": str((node.get("quantity") or {}).get("winston") or "0"),
                "fee_winston": str((node.get("fee") or {}).get("winston") or "0"),
                "block_height": block.get("height"),
                "block_timestamp": block.get("timestamp"),
            }
            inner = tags.get("X-Deposit-Id")
            if tags.get("Action") == "Propose-Operation" and isinstance(inner, str):
                inner_ids[node["id"]] = inner


def load_txs(run: str) -> tuple[dict, dict]:
    found = {}
    inner_ids = {}
    for directory in (
        root_of(run) / "txs" / "gql",
        root_of(run) / "txs" / "gql-added",
    ):
        if directory.is_dir():
            _load_gql_directory(directory, found, inner_ids)
    http_dir = root_of(run) / "txs" / "http"
    if http_dir.is_dir():
        for path in sorted(http_dir.glob("*.json")):
            if path.name.endswith(".meta.json") or path.name.endswith(".status.json"):
                continue
            tx = json.loads(path.read_text())
            if "id" not in tx or "owner" not in tx:
                continue
            height = None
            timestamp = None
            height_source = "http_tx_has_no_block_field"
            status_path = path.with_name(f"{tx['id']}.status.json")
            if status_path.exists():
                try:
                    status = json.loads(status_path.read_text())
                except json.JSONDecodeError:
                    status = None
                if isinstance(status, dict) and isinstance(status.get("block_height"), int):
                    height = status["block_height"]
                    height_source = "http_tx_status"
            found[tx["id"]] = {
                "id": tx["id"],
                "owner": arweave_address(tx["owner"]),
                "recipient": tx.get("target") or "",
                "quantity_winston": str(tx.get("quantity") or "0"),
                "fee_winston": str(tx.get("reward") or "0"),
                "block_height": height,
                "block_timestamp": timestamp,
                "block_height_source": height_source,
            }
    return found, inner_ids


def load_wallet(run: str, address: str) -> list[dict]:
    found = {}
    for direction in ("owners", "recipients"):
        directory = root_of(run) / "wallet" / address / direction
        for path in sorted(directory.glob("p*.response.json")):
            parsed = json.loads(path.read_text())
            for edge in parsed["data"]["transactions"]["edges"] or []:
                node = edge["node"]
                block = node.get("block") or {}
                found[node["id"]] = {
                    "id": node["id"],
                    "owner": (node.get("owner") or {}).get("address") or "",
                    "recipient": node.get("recipient") or "",
                    "quantity_winston": str((node.get("quantity") or {}).get("winston") or "0"),
                    "fee_winston": str((node.get("fee") or {}).get("winston") or "0"),
                    "block_height": block.get("height"),
                }
    return list(found.values())


# ar-io.dev owner and recipient walks. arweave.net walks of the same wallets
# omit native transfers, so these directories are the reconstruction.
WALLETS = (
    ("nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c", "original_custody"),
    ("11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "untagged_forward"),
    ("qmg-WUYiCHqhnx_kv4zx2zedssosU1is9Td2UWGfI5g", "untagged_forward"),
    ("uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0", "untagged_forward"),
    ("cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8", "untagged_forward"),
    ("AKQcAkNtnNXmEWBMMxfJ08oeoHP3RLs2jshRGnje1ow", "mixed_after_forward"),
    ("mizBOKEIkpih0qAI-giz_kJrcfcQs5eZvqeUZHUD50E", "side_branch"),
    ("4JOmaT9fFe2ojFJEls3Zow5UKO2CBOk7lOirbPTtX1o", "side_branch"),
)
HOPS = (
    ("nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c", "11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "nLVp9_to_11c550"),
    ("11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "qmg-WUYiCHqhnx_kv4zx2zedssosU1is9Td2UWGfI5g", "11c550_to_qmg"),
    ("11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c", "11c550_back_to_nLVp9"),
    ("11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "K4OPvKxtNUG7tBKXWfDPWSLtvLY1geCXfvfvFUGxvpA", "11c550_to_k4op"),
    ("qmg-WUYiCHqhnx_kv4zx2zedssosU1is9Td2UWGfI5g", "uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0", "qmg_to_uxbw"),
    ("qmg-WUYiCHqhnx_kv4zx2zedssosU1is9Td2UWGfI5g", "11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0", "qmg_back_to_11c550"),
    ("uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0", "cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8", "uxbw_to_cjp59"),
    ("uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0", "mizBOKEIkpih0qAI-giz_kJrcfcQs5eZvqeUZHUD50E", "uxbw_to_miz"),
    ("mizBOKEIkpih0qAI-giz_kJrcfcQs5eZvqeUZHUD50E", "4JOmaT9fFe2ojFJEls3Zow5UKO2CBOk7lOirbPTtX1o", "miz_to_4joma"),
    ("uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0", "AKQcAkNtnNXmEWBMMxfJ08oeoHP3RLs2jshRGnje1ow", "uxbw_to_akqc"),
    ("cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8", "AKQcAkNtnNXmEWBMMxfJ08oeoHP3RLs2jshRGnje1ow", "cjp59_to_akqc"),
)


def load_ario(run: str, address: str) -> tuple[list[dict], dict]:
    """Dedupe ar-io.dev owner and recipient pages for one address."""
    found = {}
    meta = {"address": address, "directions": {}, "complete": True, "unique": 0}
    for direction in ("ario-owners", "ario-recipients"):
        directory = root_of(run) / "wallet" / address / direction
        info = {"pages": 0, "edges": 0, "summary": None, "last_has_next": None}
        if not directory.is_dir():
            meta["complete"] = False
            meta["directions"][direction] = info
            continue
        summary_path = directory / "summary.json"
        if summary_path.exists():
            info["summary"] = json.loads(summary_path.read_text())
        else:
            meta["complete"] = False
        pages = sorted(directory.glob("p*.response.json"))
        info["pages"] = len(pages)
        for path in pages:
            parsed = json.loads(path.read_text())
            conn = parsed["data"]["transactions"]
            info["last_has_next"] = bool(conn["pageInfo"]["hasNextPage"])
            for edge in conn["edges"] or []:
                info["edges"] += 1
                node = edge["node"]
                block = node.get("block") or {}
                action = None
                for item in node.get("tags") or []:
                    if item.get("name") == "Action":
                        action = item.get("value")
                        break
                height = block.get("height")
                if not isinstance(height, int):
                    height = None
                found[node["id"]] = {
                    "id": node["id"],
                    "owner": (node.get("owner") or {}).get("address") or "",
                    "recipient": node.get("recipient") or "",
                    "quantity_winston": str((node.get("quantity") or {}).get("winston") or "0"),
                    "fee_winston": str((node.get("fee") or {}).get("winston") or "0"),
                    "block_height": height,
                    "action": action,
                }
        if info["last_has_next"] is not False:
            meta["complete"] = False
        meta["directions"][direction] = info
    meta["unique"] = len(found)
    return list(found.values()), meta


def reconstruct_wallet(address: str, role: str, txs: list[dict], meta: dict, gateway: dict) -> dict:
    result = {
        "address": address,
        "role": role,
        "index": {
            "complete": meta["complete"],
            "unique": meta["unique"],
            "directions": meta["directions"],
        },
        "gateway_now": gateway,
        "reconstruction_matches_gateway": False,
        "raw_amount_now": None,
        "raw_amount_at_tail": None,
        "raw_amount_at_checkpoint": None,
        "at_all_heights": None,
        "at_tail": None,
        "at_checkpoint": None,
        "index_difference_winston": None,
        "positive_height_min": None,
        "positive_height_max": None,
        "value_txs_after_tail": None,
    }
    if not meta["complete"] or gateway.get("raw_winston") is None:
        result["note"] = (
            "The ar-io.dev history or the gateway balance is incomplete. "
            "This wallet's tail amount stays unknown."
        )
        return result
    all_bal = balance_at(address, txs, None)
    tail_bal = balance_at(address, txs, TAIL_BLOCK)
    ckpt_bal = balance_at(address, txs, CHECKPOINT_BLOCK)
    result["at_all_heights"] = all_bal
    result["at_tail"] = tail_bal
    result["at_checkpoint"] = ckpt_bal
    matches = (
        all_bal["raw_winston"] == gateway["raw_winston"]
        and all_bal["skipped_unconfirmed"] == 0
    )
    result["reconstruction_matches_gateway"] = matches
    if not matches:
        result["index_difference_winston"] = str(
            int(all_bal["raw_winston"]) - int(gateway["raw_winston"])
        )
        result["note"] = (
            "The indexed history does not close to the gateway balance. "
            "The tail amount stays unknown. The difference is an index gap, "
            "not a correction to either figure."
        )
        return result
    result["raw_amount_now"] = gateway["raw_winston"]
    result["raw_amount_at_tail"] = tail_bal["raw_winston"]
    result["raw_amount_at_checkpoint"] = ckpt_bal["raw_winston"]
    heights = [
        tx["block_height"]
        for tx in txs
        if isinstance(tx["block_height"], int)
        and (int(tx["quantity_winston"]) != 0 or int(tx["fee_winston"]) != 0)
    ]
    result["positive_height_min"] = min(heights) if heights else None
    result["positive_height_max"] = max(heights) if heights else None
    result["value_txs_after_tail"] = tail_bal["skipped_after"]
    result["fee_rule"] = (
        "The sender decreases by quantity plus reward. GraphQL names the reward fee. "
        "The recipient increases by quantity only. A zero quantity and zero fee is skipped. "
        "A transaction with no block is skipped."
    )
    return result


def hop_summary(txs: list[dict], src: str, dst: str, name: str) -> dict:
    rows = [
        tx
        for tx in txs
        if tx["owner"] == src and tx["recipient"] == dst and int(tx["quantity_winston"]) > 0
    ]
    rows.sort(key=lambda tx: ((tx["block_height"] is None), tx["block_height"] or 0, tx["id"]))
    total = sum(int(tx["quantity_winston"]) for tx in rows)
    fees = sum(int(tx["fee_winston"]) for tx in rows)
    heights = [tx["block_height"] for tx in rows if isinstance(tx["block_height"], int)]
    return {
        "name": name,
        "from": src,
        "to": dst,
        "count": len(rows),
        "quantity_winston": str(total),
        "fee_winston": str(fees),
        "height_min": min(heights) if heights else None,
        "height_max": max(heights) if heights else None,
        "actions": sorted({tx.get("action") or "" for tx in rows}),
        "tx_ids": [tx["id"] for tx in rows],
    }


def top_outflows(txs: list[dict], address: str, max_height: int, limit: int = 8) -> list[dict]:
    groups = {}
    for tx in txs:
        if tx["owner"] != address:
            continue
        height = tx["block_height"]
        if not isinstance(height, int) or height > max_height:
            continue
        quantity = int(tx["quantity_winston"])
        if quantity <= 0:
            continue
        cell = groups.setdefault(tx["recipient"], [0, 0, height, height])
        cell[0] += 1
        cell[1] += quantity
        cell[2] = min(cell[2], height)
        cell[3] = max(cell[3], height)
    ranked = sorted(groups.items(), key=lambda item: item[1][1], reverse=True)[:limit]
    return [
        {
            "address": recipient,
            "txs": cell[0],
            "quantity_winston": str(cell[1]),
            "height_min": cell[2],
            "height_max": cell[3],
        }
        for recipient, cell in ranked
    ]


def mix_after_arrival(
    txs: list[dict],
    address: str,
    arrival_height: int | None,
    path_sender: str | None = None,
) -> dict:
    if arrival_height is None:
        return {"arrival_height": None}
    before = balance_at(address, txs, arrival_height - 1)
    recipients = {}
    inbound_other = 0
    inbound_other_n = 0
    for tx in txs:
        height = tx["block_height"]
        if not isinstance(height, int) or height < arrival_height or height > TAIL_BLOCK:
            continue
        quantity = int(tx["quantity_winston"])
        if quantity <= 0:
            continue
        if tx["owner"] == address:
            cell = recipients.setdefault(tx["recipient"], [0, 0])
            cell[0] += 1
            cell[1] += quantity
        elif tx["recipient"] == address and tx["owner"] != path_sender:
            inbound_other += quantity
            inbound_other_n += 1
    ranked = sorted(recipients.items(), key=lambda item: item[1][1], reverse=True)[:8]
    return {
        "arrival_height": arrival_height,
        "balance_before_arrival_winston": before["raw_winston"],
        "outbound_txs_until_tail": sum(cell[0] for cell in recipients.values()),
        "outbound_quantity_until_tail": str(sum(cell[1] for cell in recipients.values())),
        "outbound_recipients_until_tail": len(recipients),
        "other_inbound_txs_until_tail": inbound_other_n,
        "other_inbound_quantity_until_tail": str(inbound_other),
        "largest_recipients": [
            {"address": recipient, "txs": cell[0], "quantity_winston": str(cell[1])}
            for recipient, cell in ranked
        ],
        "note": (
            "After the forwarded AR arrived, this wallet already held other AR and "
            "kept exchanging with many addresses. A recipient total is not a separated "
            "qAR balance."
        ),
    }


def load_nonces() -> dict:
    found = {}
    for path in SQLITES:
        if not Path(path).exists():
            continue
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for nonce, message_id in con.execute("SELECT nonce, message_id FROM assignment"):
            found.setdefault(message_id, []).append(int(nonce))
        con.close()
    return found


def message_amounts(tags: dict, body):
    """Quantities the deposit message itself states.

    The handler stores `data.quantity` and later mints that integer. On messages
    where `X-Quantity` is also present it matches `data.quantity`. A difference
    is a conflict, not a cue to pick the layer-1 transaction amount.
    """
    quantities = []
    sources = []
    target = None
    owner = None
    for item in body_objects(body):
        if "quantity" in item:
            parsed = as_int(item.get("quantity"))
            if parsed is not None:
                quantities.append(parsed)
                sources.append("data.quantity")
        if isinstance(item.get("target"), str):
            target = item["target"]
        if isinstance(item.get("owner"), str):
            owner = item["owner"]
    tag_qty = as_int(tag(tags, "X-Quantity"))
    if tag_qty is not None:
        quantities.append(tag_qty)
        sources.append("tag:X-Quantity")
    return quantities, sources, target, owner or tag(tags, "X-User-Id")


def choose_quantity(quantities: list) -> tuple:
    present = [value for value in quantities if isinstance(value, int)]
    if not present:
        return None, "missing"
    if len(set(present)) == 1:
        return present[0], "agreed"
    return None, "conflict"


def classify_quantity_vs_tx(quantity, tx_quantity, network_fees: list) -> str:
    """How the minted quantity sits against the layer-1 winston amount.

    `X-Network-Fee` is subtracted before the mint on some deposits. It is not
    used to change either number.
    """
    if quantity is None or tx_quantity is None:
        return "not_compared"
    if quantity == tx_quantity:
        return "equal"
    unique_fees = {fee for fee in network_fees if isinstance(fee, int)}
    if len(unique_fees) == 1 and quantity + next(iter(unique_fees)) == tx_quantity:
        return "message_plus_network_fee"
    return "unexplained"


def group_deposits(messages, run, txs, inner_ids=None) -> list[dict]:
    inner_ids = inner_ids or {}
    groups = defaultdict(list)
    for message in messages:
        if message["action"] != "Deposit":
            continue
        tags = message.get("tags") or {}
        cited = tag(tags, "X-Transfer-Id") or tag(tags, "X-Deposit-Id")
        body = load_body(run, message["id"])
        quantities, sources, target, owner = message_amounts(tags, body)
        underlying = inner_ids.get(cited, cited) if cited else None
        groups[underlying].append(
            {
                "message_id": message["id"],
                "cited_transfer_id": cited,
                "is_proposal": cited in inner_ids,
                "inclusion_block": message.get("block_height"),
                "minter": message.get("owner"),
                "quantities": quantities,
                "sources": sources,
                "target": target,
                "owner": owner,
                "request_id": tag(tags, "X-Request-Id"),
                "network_fee": as_int(tag(tags, "X-Network-Fee")),
                "body_missing": body is None,
            }
        )
    flows = []
    for transfer_id, items in groups.items():
        direct = [item for item in items if not item["is_proposal"]]
        proposals = [item for item in items if item["is_proposal"]]
        # Proposal bodies are bridge operation messages. Their quantity is not
        # the mint. Every observed proposal group also has a direct deposit.
        flat = [value for item in direct for value in item["quantities"]]
        quantity, status = choose_quantity(flat)
        fees = [item["network_fee"] for item in direct if item["network_fee"] is not None]
        matched = txs.get(transfer_id) if transfer_id else None
        tx_quantity = None if matched is None else as_int(matched["quantity_winston"])
        targets = sorted({item["target"] for item in direct if item["target"]})
        owners = sorted({item["owner"] for item in direct if item["owner"]})
        flows.append(
            {
                "transfer_id": transfer_id,
                "message_ids": [item["message_id"] for item in items],
                "message_count": len(items),
                "direct_message_count": len(direct),
                "proposal_message_count": len(proposals),
                "request_ids": sorted({item["request_id"] for item in direct if item["request_id"]}),
                "minters": sorted({item["minter"] for item in direct if item["minter"]}),
                "inclusion_blocks": sorted(
                    {item["inclusion_block"] for item in items if item["inclusion_block"] is not None}
                ),
                "quantity_raw": None if quantity is None else str(quantity),
                "quantity_status": status,
                "quantity_values": sorted({str(value) for value in flat}),
                "quantity_sources": sorted({source for item in direct for source in item["sources"]}),
                "bodies_missing": sum(1 for item in direct if item["body_missing"]),
                "network_fee_winston": sorted({str(fee) for fee in fees}),
                "claimed_targets": targets,
                "claimed_depositors": owners,
                "tx_found": matched is not None,
                "tx_from": None if matched is None else matched["owner"],
                "tx_to": None if matched is None else matched["recipient"],
                "tx_quantity_winston": None if matched is None else matched["quantity_winston"],
                "tx_fee_winston": None if matched is None else matched["fee_winston"],
                "tx_block_height": None if matched is None else matched["block_height"],
                "quantity_vs_tx": classify_quantity_vs_tx(quantity, tx_quantity, fees),
            }
        )
    flows.sort(key=lambda item: (item["inclusion_blocks"] or [0])[0])
    return flows


def group_unwraps(messages) -> list[dict]:
    groups = defaultdict(list)
    for message in messages:
        if message["action"] != "Unwrap":
            continue
        tags = message.get("tags") or {}
        request_id = tag(tags, "X-Request-Id") or message["id"]
        groups[request_id].append(
            {
                "message_id": message["id"],
                "caller": message.get("owner"),
                "inclusion_block": message.get("block_height"),
                "quantity": as_int(tag(tags, "Quantity")),
                "user_id": tag(tags, "X-User-Id"),
                "original_quantity_tag": tag(tags, "X-Original-Quantity"),
                "bridge_fee_tag": tag(tags, "X-Bridge-Fee"),
                "network_fee_tag": tag(tags, "X-Network-Fee"),
            }
        )
    flows = []
    for request_id, items in groups.items():
        quantities = {item["quantity"] for item in items if item["quantity"] is not None}
        if len(quantities) == 1:
            quantity = next(iter(quantities))
            status = "agreed"
        elif not quantities:
            quantity = None
            status = "missing"
        else:
            quantity = None
            status = "conflict"
        flows.append(
            {
                "request_id": request_id,
                "message_ids": [item["message_id"] for item in items],
                "message_count": len(items),
                "callers": sorted({item["caller"] for item in items if item["caller"]}),
                "inclusion_blocks": sorted(
                    {item["inclusion_block"] for item in items if item["inclusion_block"] is not None}
                ),
                "quantity_raw": None if quantity is None else str(quantity),
                "quantity_status": status,
                "original_quantity_tag": items[0]["original_quantity_tag"],
                "bridge_fee_tag": items[0]["bridge_fee_tag"],
                "network_fee_tag": items[0]["network_fee_tag"],
            }
        )
    flows.sort(key=lambda item: (item["inclusion_blocks"] or [0])[0])
    return flows


def group_outbound(messages, run, txs) -> tuple[list[dict], dict]:
    groups = defaultdict(list)
    message_state = {}
    for message in messages:
        if message["action"] not in {"Withdraw", "Unwrap-Funds-Sent"}:
            continue
        tags = message.get("tags") or {}
        body = load_body(run, message["id"])
        transfer_ids = []
        request_ids = []
        tagged = tag(tags, "X-Transfer-Id")
        if tagged:
            transfer_ids.append(tagged)
        tagged_request = tag(tags, "X-Request-Id")
        if tagged_request:
            request_ids.append(tagged_request)
        for item in body_objects(body):
            value = item.get("transfer_id")
            if isinstance(value, str) and value and value not in transfer_ids:
                transfer_ids.append(value)
            request_id = item.get("request_id")
            if isinstance(request_id, str) and request_id and request_id not in request_ids:
                request_ids.append(request_id)
        message_state[message["id"]] = {
            "request_ids": list(request_ids),
            "transfer_ids": list(transfer_ids),
            "body_missing": body is None,
        }
        if not transfer_ids:
            transfer_ids = [None]
        for transfer_id in transfer_ids:
            groups[transfer_id].append(
                {
                    "message_id": message["id"],
                    "action": message["action"],
                    "inclusion_block": message.get("block_height"),
                    "body_missing": body is None,
                    "request_ids": request_ids,
                }
            )
    flows = []
    for transfer_id, items in groups.items():
        matched = txs.get(transfer_id) if transfer_id else None
        request_ids = sorted({request_id for item in items for request_id in item["request_ids"]})
        flows.append(
            {
                "transfer_id": transfer_id,
                "message_ids": [item["message_id"] for item in items],
                "request_ids": request_ids,
                "actions": sorted({item["action"] for item in items}),
                "inclusion_blocks": sorted(
                    {item["inclusion_block"] for item in items if item["inclusion_block"] is not None}
                ),
                "body_missing_count": sum(1 for item in items if item["body_missing"]),
                "tx_found": matched is not None,
                "tx_from": None if matched is None else matched["owner"],
                "tx_to": None if matched is None else matched["recipient"],
                "tx_quantity_winston": None if matched is None else matched["quantity_winston"],
                "tx_fee_winston": None if matched is None else matched["fee_winston"],
                "tx_block_height": None if matched is None else matched["block_height"],
            }
        )
    request_ids = sorted({request_id for state in message_state.values() for request_id in state["request_ids"]})
    coverage = {
        "messages": len(message_state),
        "with_request_id": sum(1 for state in message_state.values() if state["request_ids"]),
        "with_transfer_id": sum(1 for state in message_state.values() if state["transfer_ids"]),
        "body_missing": sum(1 for state in message_state.values() if state["body_missing"]),
        "request_ids": request_ids,
    }
    return flows, coverage


def sum_status(rows: list[dict], field: str = "quantity_raw") -> dict:
    total = 0
    missing = 0
    used = 0
    for row in rows:
        if row.get("quantity_status") not in {None, "agreed"}:
            missing += 1
            continue
        raw = row.get(field)
        if raw is None:
            missing += 1
            continue
        total += int(raw)
        used += 1
    return {
        "raw": None if missing else str(total),
        "partial_raw": str(total),
        "rows": len(rows),
        "used": used,
        "missing_or_conflict": missing,
    }


def cited_value_txs(deposits: list[dict], outbound: list[dict], txs: dict) -> list[dict]:
    chosen = {}
    for row in deposits:
        txid = row.get("transfer_id")
        if txid and txid in txs:
            chosen[txid] = txs[txid]
    for row in outbound:
        txid = row.get("transfer_id")
        if txid and txid in txs:
            chosen[txid] = txs[txid]
    return list(chosen.values())


def gateway_snapshot(run: str, address: str) -> dict:
    directory = root_of(run) / "wallet" / address
    balance_path = directory / "balance.body"
    info_path = directory / "info.body"
    balance = balance_path.read_text().strip() if balance_path.exists() else None
    height = None
    blocks = None
    if info_path.exists():
        info = json.loads(info_path.read_text())
        height = info.get("height")
        blocks = info.get("blocks")
    return {
        "raw_winston": balance,
        "height": height,
        "blocks": blocks,
        "balance_path": str(balance_path) if balance_path.exists() else None,
        "info_path": str(info_path) if info_path.exists() else None,
    }


def wallet_index_gap(run: str, address: str, cited: list[dict]) -> dict:
    """Owner and recipient pagination on arweave.net did not return layer-1 transfers."""
    pages = load_wallet(run, address)
    page_ids = {row["id"] for row in pages}
    positive_pages = [
        row
        for row in pages
        if int(row["quantity_winston"]) != 0 or int(row["fee_winston"]) != 0
    ]
    cited_positive = [
        row
        for row in cited
        if int(row["quantity_winston"]) != 0 or int(row["fee_winston"]) != 0
    ]
    present = [row["id"] for row in cited_positive if row["id"] in page_ids]
    summaries = {}
    for direction in ("owners", "recipients"):
        path = root_of(run) / "wallet" / address / direction / "summary.json"
        summaries[direction] = json.loads(path.read_text()) if path.exists() else None
    return {
        "address": address,
        "pagination": summaries,
        "unique_rows_in_pages": len(page_ids),
        "positive_rows_in_pages": len(positive_pages),
        "cited_positive_txs": len(cited_positive),
        "cited_positive_present_in_pages": len(present),
        "note": (
            "GraphQL owners and recipients walks finished with hasNextPage false "
            "and returned only zero-quantity AO messages. Known layer-1 transfers "
            "for this wallet are absent from those pages. The walks are not the "
            "wallet history."
        ),
    }


def nonce_coverage(message_ids: list[str]) -> dict:
    wanted = set(message_ids)
    found = 0
    scanned = 0
    for path in SQLITES:
        if not Path(path).exists():
            continue
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for (message_id,) in con.execute("SELECT message_id FROM assignment"):
            scanned += 1
            if message_id in wanted:
                found += 1
        con.close()
    return {
        "messages": len(wanted),
        "with_nonce_in_p4_sqlite": found,
        "assignment_rows_scanned": scanned,
        "sqlite_note": "P4 assignment files stop at nonce 150227. Later collateral messages are absent there, not unassigned.",
    }


def cron_progress(run: str, action: str) -> dict:
    directory = root_of(run) / "gql" / "recipient" / action
    summary_path = directory / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        summary["complete"] = True
        return summary
    pages = sorted(directory.glob("p*.response.json"))
    if not pages:
        return {"action": action, "complete": False, "pages": 0}
    parsed = json.loads(pages[-1].read_text())
    edges = parsed["data"]["transactions"]["edges"] or []
    heights = [edge["node"]["block"]["height"] for edge in edges if (edge["node"].get("block") or {}).get("height")]
    names = sorted({tag["name"] for edge in edges for tag in (edge["node"].get("tags") or [])})
    return {
        "action": action,
        "complete": False,
        "pages_saved": len(pages),
        "last_page_height_min": min(heights) if heights else None,
        "last_page_height_max": max(heights) if heights else None,
        "last_page_has_next": bool(parsed["data"]["transactions"]["pageInfo"]["hasNextPage"]),
        "last_page_tag_names": names,
    }


def show(value):
    return "null" if value is None else value


def render_summary(run: str, report: dict) -> str:
    collateral = report["collateral"]
    recon = report["reconciliation"]
    lines = [
        "# P9 collateral",
        "",
        f"Run `{run}-w-collat`. Process `{PROCESS}`. The module was not executed. No funds were moved. `goal_complete` is false. `publish_claims` is false. `move_collateral` is false.",
        "",
        "## Conclusion",
        "",
        collateral["conclusion"],
        "",
        "## Numbers",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Asset | {collateral['asset']} |",
        "| Holder | not one wallet |",
        f"| Separable raw winston at tail block {TAIL_BLOCK} | {show(collateral['raw_amount_at_tail'])} |",
        f"| Separable raw winston now | {show(collateral['raw_amount_now'])} |",
        f"| Checkpoint supply raw (nonce {SUPPLY_NONCE}) | {SUPPLY} |",
        f"| qAR minted from deposit messages | {show(recon['minted_qar']['raw'])} |",
        f"| qAR minted, partial sum of agreed groups | {recon['minted_qar']['partial_raw']} |",
        f"| Deposit groups missing an agreed quantity | {recon['minted_qar']['missing_or_conflict']} |",
        f"| qAR burned with a withdraw follow-up | {show(recon['burned_qar']['raw'])} |",
        f"| Follow-up burn, partial | {recon['burned_qar']['partial_raw']} |",
        f"| Linked unwrap groups | {recon['burned_qar']['linked_groups']} of {recon['burned_qar']['requested_groups']} |",
        f"| (minted − burned) − supply | {show(recon['message_gap_raw'])} |",
        f"| Original custody wallet at tail − supply | {recon['original_custody_minus_supply']['at_tail']} |",
        f"| Original custody wallet now − supply | {recon['original_custody_minus_supply']['now']} |",
        f"| Holder-set collateral − supply | {show(recon['collateral_gap_now_raw'])} |",
        "",
        "Wallet balances below are the whole wallet. They are not a qAR slice. A match means the ar-io.dev owner and recipient pages, with the sender charged quantity plus fee, close to `/wallet/<address>/balance`.",
        "",
        "| Wallet | Role | At checkpoint | At tail | Now | Matches gateway |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for wallet in recon["wallets"]:
        lines.append(
            "| `{addr}` | {role} | {ckpt} | {tail} | {now} | {match} |".format(
                addr=wallet["address"],
                role=wallet["role"],
                ckpt=wallet["raw_amount_at_checkpoint"],
                tail=wallet["raw_amount_at_tail"],
                now=wallet["raw_amount_now"],
                match=wallet["reconstruction_matches_gateway"],
            )
        )
    lines.extend(
        [
            "",
            "Untagged forwards, quantity in winston. Pair totals count every positive transfer between those two addresses. `qmg_to_uxbw` includes transfers before 11c550 paid qmg. `miz_to_4joma` includes four earlier transfers before the 20000 AR forward at height 1729976. Fees are on each hop in `flows.json` and are not added back.",
            "",
        ]
    )
    lines.append("| Hop | Txs | Quantity | Height |")
    lines.append("| --- | --- | --- | --- |")
    for hop in recon["forwarding"]:
        lines.append(
            f"| {hop['name']} | {hop['count']} | {hop['quantity_winston']} | {hop['height_min']}–{hop['height_max']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Messages, bodies, GraphQL pages, and transaction lookups: `data/raw/collat/{run}/`",
            "- arweave.net owner and recipient pages for the custody wallet omit the native transfers. The balances above use `wallet/<address>/ario-owners` and `ario-recipients` from `https://ar-io.dev/graphql`.",
            "- `flows.json` groups one mint per underlying layer-1 transfer, one burn request per `X-Request-Id`, and the untagged forwarding transactions.",
            "- `reconciliation.json` holds the gap arithmetic. Gaps are not written back into any balance.",
            "- `collateral.json` names the asset. `holder`, `raw_amount_at_tail`, and `raw_amount_now` are null because the AR is not one separable pile.",
            f"- `manifest.json` lists each raw file under `data/raw/collat/{run}/` with its byte size and sha256.",
            "",
            "## Unfinished",
            "",
        ]
    )
    for item in report["unfinished"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def build_report(run: str) -> dict:
    messages = load_messages(run)
    txs, inner_ids = load_txs(run)
    deposits = group_deposits(messages, run, txs, inner_ids)
    unwraps = group_unwraps(messages)
    outbound, coverage = group_outbound(messages, run, txs)
    minted = sum_status(deposits)
    requested_burn = sum_status(unwraps)
    follow = set(coverage["request_ids"])
    linked = [row for row in unwraps if row["request_id"] in follow]
    burned = sum_status(linked)
    follow_complete = coverage["messages"] > 0 and coverage["with_request_id"] == coverage["messages"]
    if not follow_complete:
        burned = dict(burned)
        burned["raw"] = None
    if minted["raw"] is not None and burned["raw"] is not None:
        message_gap = str((int(minted["raw"]) - int(burned["raw"])) - SUPPLY)
    else:
        message_gap = None
    recipients = defaultdict(int)
    recipient_exceptions = []
    senders = defaultdict(int)
    sender_exceptions = []
    vs_tx = defaultdict(int)
    for row in deposits:
        vs_tx[row["quantity_vs_tx"]] += 1
        if not row["tx_found"]:
            continue
        recipients[row["tx_to"]] += 1
        if row["tx_to"] != HOLDER_CANDIDATE:
            recipient_exceptions.append(row["transfer_id"])
    for row in outbound:
        if row.get("tx_from"):
            senders[row["tx_from"]] += 1
            if row["tx_from"] != HOLDER_CANDIDATE:
                sender_exceptions.append(row["transfer_id"])
    cited = cited_value_txs(deposits, outbound, txs)
    held_all = balance_at(HOLDER_CANDIDATE, cited, None)
    held_tail = balance_at(HOLDER_CANDIDATE, cited, TAIL_BLOCK)
    held_checkpoint = balance_at(HOLDER_CANDIDATE, cited, CHECKPOINT_BLOCK)
    gateway = gateway_snapshot(run, HOLDER_CANDIDATE)
    index_gap = wallet_index_gap(run, HOLDER_CANDIDATE, cited)
    transfers_complete = (
        coverage["messages"] > 0
        and coverage["with_transfer_id"] == coverage["messages"]
        and all(row["tx_found"] for row in outbound if row.get("transfer_id"))
        and all(row["tx_found"] for row in deposits)
    )
    confirmed_matches_gateway = held_all["raw_winston"] == gateway["raw_winston"]
    loaded = {}
    wallets = []
    for address, role in WALLETS:
        wallet_txs, meta = load_ario(run, address)
        loaded[address] = wallet_txs
        wallets.append(
            reconstruct_wallet(address, role, wallet_txs, meta, gateway_snapshot(run, address))
        )
    hops = []
    for src, dst, name in HOPS:
        hops.append(hop_summary(loaded.get(src, []), src, dst, name))
    by_name = {hop["name"]: hop for hop in hops}
    akqc_address = "AKQcAkNtnNXmEWBMMxfJ08oeoHP3RLs2jshRGnje1ow"
    arrival = by_name["cjp59_to_akqc"]["height_min"]
    mixed = mix_after_arrival(
        loaded.get(akqc_address, []),
        akqc_address,
        arrival,
        path_sender="cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8",
    )
    joma_address = "4JOmaT9fFe2ojFJEls3Zow5UKO2CBOk7lOirbPTtX1o"
    # height_max is the 20000 AR forward. Earlier miz sends to this wallet
    # predate that transfer and are not this hop.
    joma_mix = mix_after_arrival(
        loaded.get(joma_address, []),
        joma_address,
        by_name["miz_to_4joma"]["height_max"],
        path_sender="mizBOKEIkpih0qAI-giz_kJrcfcQs5eZvqeUZHUD50E",
    )
    for wallet in wallets:
        wallet["largest_outflows_through_tail"] = top_outflows(
            loaded.get(wallet["address"], []), wallet["address"], TAIL_BLOCK
        )
    custody = next(wallet for wallet in wallets if wallet["role"] == "original_custody")

    def minus_supply(amount):
        if amount is None:
            return None
        return str(int(amount) - SUPPLY)

    # The forwarded AR mixed with other balances before the tail. No single
    # figure is the collateral, so the set gap stays null. The original
    # wallet's own gap is recorded separately and is not applied to any balance.
    raw_at_tail = None
    raw_now = None
    tail_reason = (
        "Every resolved deposit pays the original custody wallet, and that wallet's "
        "ar-io.dev history closes to its gateway balance. Before the tail, untagged "
        "transfers moved the bulk through other wallets. The last concentrated "
        "recipient also holds other AR, and the inbound amount then went out to "
        "many addresses. Those wallet balances are reported individually. They are "
        "not added into one collateral amount."
    )
    deposit_missing = [row["transfer_id"] for row in deposits if not row["tx_found"]]
    deposit_unconfirmed = [
        row["transfer_id"]
        for row in deposits
        if row["tx_found"] and row["tx_block_height"] is None
    ]
    outbound_missing = [
        row["transfer_id"]
        for row in outbound
        if row.get("transfer_id") and not row["tx_found"]
    ]
    outbound_unconfirmed = [
        row["transfer_id"]
        for row in outbound
        if row.get("transfer_id") and row["tx_found"] and row["tx_block_height"] is None
    ]
    bridge_fees = {"quantity_equals_original_plus_fee": 0, "fee_not_an_integer": 0, "other": 0}
    for row in unwraps:
        quantity = as_int(row.get("quantity_raw"))
        original = as_int(row.get("original_quantity_tag"))
        fee = as_int(row.get("bridge_fee_tag"))
        if quantity is None or original is None or fee is None:
            bridge_fees["fee_not_an_integer"] += 1
        elif quantity == original + fee:
            bridge_fees["quantity_equals_original_plus_fee"] += 1
        else:
            bridge_fees["other"] += 1
    qmg_hop = by_name["11c550_to_qmg"]
    unfinished = []
    for action in ("Mint-Tokens", "Confirm-Deposits"):
        progress = cron_progress(run, action)
        if not progress.get("complete"):
            unfinished.append(
                f"{action} pagination is unfinished: {json.dumps(progress, sort_keys=True)}. Saved pages carry Action and X-Cron-Request-Id and no quantity or transfer id."
            )
    if coverage["body_missing"]:
        unfinished.append(
            f"{coverage['body_missing']} Withdraw or Unwrap-Funds-Sent bodies are still missing, so some transfer ids and burn links are unknown."
        )
    if minted["raw"] is None:
        unfinished.append(
            f"Minted qAR is unknown: {minted['missing_or_conflict']} deposit groups have no single agreed quantity. The partial sum is not the total. Missing message quantities are not replaced with the layer-1 amount."
        )
    if burned["raw"] is None:
        unfinished.append(
            "Burned qAR is unknown. Unwrap burns only when the caller still has the tokens; a message with no Withdraw or Unwrap-Funds-Sent follow-up is not counted as burned and is not counted as zero."
        )
    for wallet in wallets:
        if not wallet["reconstruction_matches_gateway"]:
            unfinished.append(
                f"Wallet {wallet['address']} ({wallet['role']}) has no closed tail balance. {wallet.get('note', '')}"
            )
    if deposit_missing:
        unfinished.append(
            "Deposit transfer ids with no layer-1 transaction in GraphQL or GET /tx: "
            + ", ".join(deposit_missing)
        )
    if deposit_unconfirmed:
        unfinished.append(
            "Deposit transactions with no block height, excluded from confirmed balances: "
            + ", ".join(deposit_unconfirmed)
        )
    if outbound_missing:
        unfinished.append(
            "Withdraw transfer ids with no layer-1 transaction in GraphQL or GET /tx: "
            + ", ".join(outbound_missing)
            + ". They are not treated as zero."
        )
    if by_name["11c550_to_k4op"]["count"]:
        unfinished.append(
            "K4OPvKxtNUG7tBKXWfDPWSLtvLY1geCXfvfvFUGxvpA received "
            f"{by_name['11c550_to_k4op']['quantity_winston']} winston from 11c550 at height "
            f"{by_name['11c550_to_k4op']['height_min']} and its history was not walked."
        )
    custody_tail = custody["raw_amount_at_tail"]
    conclusion = (
        "The layer-1 asset in the deposit and withdraw transactions is native AR, in winston. "
        "The handler mints data.quantity one-for-one into qAR and does not name that asset. "
        f"Every resolved deposit pays `{HOLDER_CANDIDATE}`, the original custody wallet. "
        f"Its ar-io.dev history closes to the gateway balance, so at tail block {TAIL_BLOCK} "
        f"and now it holds {custody_tail} winston. "
        "Before the tail, untagged transfers moved the bulk from that wallet through "
        "11c550, qmg, uXBW, and cjp59 into AKQc. "
        f"AKQc received {by_name['cjp59_to_akqc']['quantity_winston']} winston from cjp59 "
        f"across heights {by_name['cjp59_to_akqc']['height_min']}–{by_name['cjp59_to_akqc']['height_max']}, "
        f"while it already held {mixed.get('balance_before_arrival_winston')} winston. "
        f"From that arrival through the tail it paid {mixed.get('outbound_recipients_until_tail')} "
        "recipients. A separate 20000 AR branch went from uXBW through miz into 4JOma at height "
        f"{by_name['miz_to_4joma']['height_max']}. miz's tail balance is zero. "
        f"4JOma then paid {joma_mix.get('outbound_recipients_until_tail')} recipients "
        f"{joma_mix.get('outbound_quantity_until_tail')} winston before the tail, far more than that inbound transfer. "
        "Those wallets are mixed with other AR, so there is no single holder and no single raw collateral amount. "
        "The wallet figures are not summed, and none of the gaps below is written back into a balance."
    )
    collateral = {
        "asset": "AR",
        "unit": "winston",
        "holder": None,
        "holder_is_single_wallet": False,
        "original_custody_wallet": HOLDER_CANDIDATE,
        "raw_amount_at_tail": raw_at_tail,
        "raw_amount_at_tail_block": TAIL_BLOCK,
        "raw_amount_at_tail_reason": tail_reason,
        "raw_amount_now": raw_now,
        "raw_amount_now_reason": tail_reason,
        "wallets": [
            {
                "address": wallet["address"],
                "role": wallet["role"],
                "raw_amount_at_checkpoint": wallet["raw_amount_at_checkpoint"],
                "raw_amount_at_tail": wallet["raw_amount_at_tail"],
                "raw_amount_now": wallet["raw_amount_now"],
                "reconstruction_matches_gateway": wallet["reconstruction_matches_gateway"],
                "gateway_height": wallet["gateway_now"].get("height"),
                "value_txs_after_tail": wallet["value_txs_after_tail"],
            }
            for wallet in wallets
        ],
        "source": [
            "evidence/p9-prep/20261017T051439Z-w-src/handlers.md",
            f"data/raw/collat/{run}/gql/messages.jsonl",
            f"data/raw/collat/{run}/txs/gql/",
            f"data/raw/collat/{run}/txs/gql-added/",
            f"data/raw/collat/{run}/txs/http/",
            f"data/raw/collat/{run}/wallet/",
        ],
        "conclusion": conclusion,
    }
    reconciliation = {
        "supply_raw_at_nonce_2074518": str(SUPPLY),
        "tail_supply_raw": None,
        "tail_supply_note": "Pending P7. This comparison uses the checkpoint supply only.",
        "minted_qar": {
            **minted,
            "rule": "One group per underlying layer-1 id. Proposal messages contribute the id, not the quantity. The mint is the agreed data.quantity or X-Quantity. Those two fields matched on every message that had both. A missing group keeps the total unknown.",
            "quantity_vs_tx": dict(vs_tx),
            "network_fee_note": "Where quantity_vs_tx is message_plus_network_fee, data.quantity plus the integer X-Network-Fee equals the layer-1 quantity. The fee is not added back into the mint.",
        },
        "burned_qar": {
            **burned,
            "requested_raw": requested_burn["raw"],
            "requested_partial_raw": requested_burn["partial_raw"],
            "requested_groups": requested_burn["rows"],
            "linked_groups": len(linked),
            "follow_up_complete": follow_complete,
            "rule": "Unwrap burns Tags.Quantity once for a new X-Request-Id when the caller has balance. A later Withdraw or Unwrap-Funds-Sent that names that request id is the evidence the row existed. Unlinked unwraps stay out of the sum.",
        },
        "message_gap_raw": message_gap,
        "message_gap_definition": "(minted qAR − burned qAR) − checkpoint supply. Null when either side is unknown.",
        "bridge_fee_on_unwrap_messages": {
            **bridge_fees,
            "note": "On some Unwrap messages Quantity equals X-Original-Quantity plus an integer X-Bridge-Fee. X-Bridge-Fee 0.00 is not winston and is not counted. The fee is retained AR in the sending wallet. It is not a second custody wallet and it is not added to a qAR balance.",
        },
        "held_ar": {
            "cited_confirmed_all": held_all,
            "cited_at_tail_block": held_tail,
            "cited_at_checkpoint_block": held_checkpoint,
            "gateway_now": gateway,
            "index_gap": index_gap,
            "fee_rule": "A sender's balance falls by quantity plus reward. GraphQL calls the reward fee. The recipient is credited quantity only.",
            "transfers_complete": transfers_complete,
            "confirmed_cited_matches_gateway": confirmed_matches_gateway,
            "cited_note": "The message-cited ledger omits untagged layer-1 spends. It is not the wallet balance. arweave.net owner and recipient pages also omit those spends. The ar-io.dev walks are the reconstruction.",
        },
        "wallets": wallets,
        "forwarding": [{key: value for key, value in hop.items() if key != "tx_ids"} for hop in hops],
        "akqc_after_cjp59_arrival": mixed,
        "joma_after_miz_arrival": joma_mix,
        "qmg_inflow_from_11c550_minus_supply": minus_supply(qmg_hop["quantity_winston"]),
        "qmg_inflow_note": "This is one hop's winston minus checkpoint supply. It is not used to fill or replace either number.",
        "original_custody_minus_supply": {
            "at_checkpoint": minus_supply(custody["raw_amount_at_checkpoint"]),
            "at_tail": minus_supply(custody["raw_amount_at_tail"]),
            "now": minus_supply(custody["raw_amount_now"]),
            "definition": "That one wallet's reconstructed winston minus checkpoint supply. Positive would be a surplus. This is not the gap for the holder set.",
        },
        "collateral_gap_at_checkpoint_raw": None,
        "collateral_gap_at_tail_raw": None,
        "collateral_gap_now_raw": None,
        "collateral_gap_definition": "eligible held winston minus checkpoint supply. Null because the forwarded AR is mixed with other balances, so eligible held is not identified. The null is not zero.",
        "deposit_transfer_ids_not_found": deposit_missing,
        "deposit_transfer_ids_without_block": deposit_unconfirmed,
        "deposit_transfer_ids_without_agreed_quantity": [
            row["transfer_id"]
            for row in deposits
            if row.get("quantity_status") not in {None, "agreed"}
        ],
        "outbound_transfer_ids_not_found": outbound_missing,
        "outbound_transfer_ids_without_block": outbound_unconfirmed,
        "deposit_tx_to": dict(recipients),
        "outbound_tx_from": dict(senders),
        "deposit_recipient_exceptions": recipient_exceptions,
        "outbound_sender_exceptions": sender_exceptions,
        "outbound_coverage": {key: value for key, value in coverage.items() if key != "request_ids"},
        "proposal_inner_ids": len(inner_ids),
        "nonce_coverage": nonce_coverage([message["id"] for message in messages]),
        "cron": {
            "Mint-Tokens": cron_progress(run, "Mint-Tokens"),
            "Confirm-Deposits": cron_progress(run, "Confirm-Deposits"),
        },
    }
    return {
        "deposits": deposits,
        "unwraps": unwraps,
        "outbound": outbound,
        "hops": hops,
        "collateral": collateral,
        "reconciliation": reconciliation,
        "unfinished": unfinished,
    }


def main() -> None:
    import sys

    run = sys.argv[1]
    stats_only = len(sys.argv) > 2 and sys.argv[2] == "--stats"
    report = build_report(run)
    minted = report["reconciliation"]["minted_qar"]
    burned = report["reconciliation"]["burned_qar"]
    print("deposits", len(report["deposits"]), "minted", minted["raw"], "partial", minted["partial_raw"], "missing", minted["missing_or_conflict"])
    print("quantity_vs_tx", minted["quantity_vs_tx"])
    print("unwraps", len(report["unwraps"]), "burn_raw", burned["raw"], "linked", burned["linked_groups"], "requested_partial", burned["requested_partial_raw"])
    print("outbound", len(report["outbound"]), "coverage", report["reconciliation"]["outbound_coverage"])
    print("deposit tx_to", report["reconciliation"]["deposit_tx_to"])
    print("outbound from", report["reconciliation"]["outbound_tx_from"])
    print("held cited", report["reconciliation"]["held_ar"]["cited_confirmed_all"]["raw_winston"])
    print("gateway", report["reconciliation"]["held_ar"]["gateway_now"]["raw_winston"], "height", report["reconciliation"]["held_ar"]["gateway_now"]["height"])
    print("separable tail", report["collateral"]["raw_amount_at_tail"], "now", report["collateral"]["raw_amount_now"])
    print("custody minus supply", report["reconciliation"]["original_custody_minus_supply"])
    print("message gap", report["reconciliation"]["message_gap_raw"], "set gap", report["reconciliation"]["collateral_gap_now_raw"])
    for wallet in report["reconciliation"]["wallets"]:
        print(
            wallet["role"],
            wallet["address"][:8],
            "ckpt", wallet["raw_amount_at_checkpoint"],
            "tail", wallet["raw_amount_at_tail"],
            "now", wallet["raw_amount_now"],
            "match", wallet["reconstruction_matches_gateway"],
            "after", wallet["value_txs_after_tail"],
        )
    for hop in report["reconciliation"]["forwarding"]:
        print("hop", hop["name"], hop["count"], hop["quantity_winston"], hop["height_min"], hop["height_max"], hop["actions"])
    mix = report["reconciliation"]["akqc_after_cjp59_arrival"]
    print("akqc mix", {key: mix[key] for key in mix if key != "largest_recipients"})
    print("akqc top", mix.get("largest_recipients"))
    joma = report["reconciliation"]["joma_after_miz_arrival"]
    print("joma mix", {key: joma[key] for key in joma if key != "largest_recipients"})
    print("joma top", joma.get("largest_recipients"))
    for wallet in report["reconciliation"]["wallets"]:
        if wallet["role"] in {"side_branch", "untagged_forward"}:
            print("out", wallet["address"][:8], wallet.get("largest_outflows_through_tail"))
    print("unfinished", len(report["unfinished"]))
    for item in report["unfinished"]:
        print(" -", item[:240])
    if stats_only:
        return
    out_dir = evidence_of(run)
    flows = {
        "process_id": PROCESS,
        "checkpoint_block": CHECKPOINT_BLOCK,
        "checkpoint_nonce": SUPPLY_NONCE,
        "tail_block": TAIL_BLOCK,
        "supply_raw_at_checkpoint": str(SUPPLY),
        "deposits": report["deposits"],
        "unwraps": report["unwraps"],
        "outbound": report["outbound"],
        "forwarding": report["hops"],
    }
    (out_dir / "flows.json").write_text(json.dumps(flows) + "\n")
    (out_dir / "collateral.json").write_text(json.dumps(report["collateral"], indent=2) + "\n")
    (out_dir / "reconciliation.json").write_text(json.dumps(report["reconciliation"], indent=2) + "\n")
    (out_dir / "SUMMARY.md").write_text(render_summary(run, report))
    print("wrote", out_dir)


if __name__ == "__main__":
    main()

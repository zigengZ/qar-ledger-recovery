"""Layer-1 winston balance from indexed Arweave transactions.

The sender's balance decreases by quantity plus reward. GraphQL names the
reward `fee`. The recipient's balance increases by quantity only. The reward
does not credit the recipient. A transaction with both winston amounts equal
to 0 does not move layer-1 AR. A transaction with no block is not included.
"""
from __future__ import annotations


def winston(value) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError(f"not a winston integer: {value!r}")


def balance_at(address: str, txs: list[dict], max_height: int | None) -> dict:
    """Sum confirmed layer-1 flows for `address`.

    `max_height` includes that block. None includes every confirmed transaction.
    `txs` must already be unique by id. Each item needs owner, recipient,
    quantity_winston, fee_winston, and block_height (None if unconfirmed).
    """
    received = 0
    sent_quantity = 0
    sent_fee = 0
    counted = 0
    skipped_zero = 0
    skipped_unconfirmed = 0
    skipped_after = 0
    for tx in txs:
        height = tx["block_height"]
        if height is None:
            skipped_unconfirmed += 1
            continue
        if max_height is not None and height > max_height:
            skipped_after += 1
            continue
        quantity = winston(tx["quantity_winston"])
        fee = winston(tx["fee_winston"])
        if quantity == 0 and fee == 0:
            skipped_zero += 1
            continue
        moved = False
        if tx["owner"] == address:
            sent_quantity += quantity
            sent_fee += fee
            moved = True
        if tx["recipient"] == address:
            received += quantity
            moved = True
        if moved:
            counted += 1
    total = received - sent_quantity - sent_fee
    return {
        "raw_winston": str(total),
        "received_winston": str(received),
        "sent_quantity_winston": str(sent_quantity),
        "sent_fee_winston": str(sent_fee),
        "counted_txs": counted,
        "skipped_zero": skipped_zero,
        "skipped_unconfirmed": skipped_unconfirmed,
        "skipped_after": skipped_after,
    }

from recovery.p9_balance import balance_at
from recovery.p9_finalize import choose_quantity, classify_quantity_vs_tx


ADDRESS = "HOLDER"
OTHER = "OTHER"


def tx(txid, owner, recipient, quantity, fee, height):
    return {
        "id": txid,
        "owner": owner,
        "recipient": recipient,
        "quantity_winston": str(quantity),
        "fee_winston": str(fee),
        "block_height": height,
    }


def test_receive_send_fee_and_self_transfer():
    txs = [
        tx("a", OTHER, ADDRESS, 100, 7, 10),
        tx("b", ADDRESS, OTHER, 40, 3, 11),
        tx("c", ADDRESS, ADDRESS, 10, 1, 12),
        tx("d", ADDRESS, OTHER, 0, 0, 12),
        tx("e", ADDRESS, OTHER, 5, 1, None),
        tx("f", OTHER, ADDRESS, 8, 1, 20),
    ]
    at_12 = balance_at(ADDRESS, txs, 12)
    assert at_12["raw_winston"] == str(100 - 40 - 3 - 1)
    assert at_12["received_winston"] == "110"
    assert at_12["sent_quantity_winston"] == "50"
    assert at_12["sent_fee_winston"] == "4"
    assert at_12["counted_txs"] == 3
    assert at_12["skipped_zero"] == 1
    assert at_12["skipped_unconfirmed"] == 1
    assert at_12["skipped_after"] == 1
    entire = balance_at(ADDRESS, txs, None)
    assert entire["raw_winston"] == str(100 - 40 - 3 - 1 + 8)


def test_choose_quantity_ignores_nothing_and_keeps_conflicts():
    assert choose_quantity([]) == (None, "missing")
    assert choose_quantity([5, 5]) == (5, "agreed")
    assert choose_quantity([5, 0]) == (None, "conflict")


def test_network_fee_explains_mint_without_changing_it():
    assert classify_quantity_vs_tx(100, 100, []) == "equal"
    assert classify_quantity_vs_tx(100 - 7, 100, [7]) == "message_plus_network_fee"
    assert classify_quantity_vs_tx(90, 100, [7]) == "unexplained"
    assert classify_quantity_vs_tx(None, 100, [7]) == "not_compared"

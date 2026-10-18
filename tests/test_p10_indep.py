import unittest

from recovery.p10_indep.ledger import RuleError, first_tag, message_from, parse_quantity, transfer


def _move(balances, sender, recipient, quantity, **flags):
    options = {"stopped": False, "transfers_enabled": True}
    options.update(flags)
    return transfer(balances, sender, recipient, quantity, **options)


class LedgerTest(unittest.TestCase):
    def test_parse_decimal_hex_and_reject(self):
        self.assertEqual(parse_quantity("00010"), 10)
        self.assertEqual(parse_quantity("+10"), 10)
        self.assertEqual(parse_quantity("0x10"), 16)
        self.assertEqual(parse_quantity("-0b10"), -2)
        with self.assertRaises(RuleError):
            parse_quantity("1.5")
        with self.assertRaises(RuleError):
            parse_quantity(None)

    def test_transfer_moves_and_keeps_zero(self):
        balances = {"alice": 5, "bob": 1}
        outcome = _move(balances, "alice", "bob", "5")
        self.assertEqual(outcome["result"], "ok")
        self.assertEqual(balances, {"alice": 0, "bob": 6})

    def test_zero_quantity_creates_recipient(self):
        balances = {"alice": 0}
        outcome = _move(balances, "alice", "new", "0")
        self.assertTrue(outcome["created_recipient"])
        self.assertEqual(balances["new"], 0)
        self.assertEqual(balances["alice"], 0)

    def test_rejections_do_not_write(self):
        balances = {"alice": 4}
        cases = [
            ("alice", "bob", "5", "insufficient balance"),
            ("missing", "bob", "1", "No balance"),
            ("alice", "alice", "1", "same as the Recipient"),
            ("alice", "bob", "-1", "greater than 0"),
            ("alice", None, "1", "must be a string"),
        ]
        for sender, recipient, quantity, text in cases:
            with self.assertRaises(RuleError) as caught:
                _move(dict(balances), sender, recipient, quantity)
            self.assertIn(text, caught.exception.reason)
        self.assertEqual(balances, {"alice": 4})
        with self.assertRaises(RuleError):
            _move(dict(balances), "alice", "bob", "1", stopped=True)
        with self.assertRaises(RuleError):
            _move(dict(balances), "alice", "bob", "1", transfers_enabled=False)

    def test_first_tag_and_from_process(self):
        tags = [
            {"name": "Quantity", "value": "1"},
            {"name": "Quantity", "value": "9"},
            {"name": "From-Process", "value": "proc"},
        ]
        self.assertEqual(first_tag(tags, "Quantity"), "1")
        self.assertEqual(message_from(tags, "owner"), "proc")
        self.assertEqual(message_from([{"name": "Action", "value": "Transfer"}], "owner"), "owner")


if __name__ == "__main__":
    unittest.main()

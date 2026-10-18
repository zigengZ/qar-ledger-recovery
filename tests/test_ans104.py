import unittest

from recovery.ans104 import (
    assignment_tags,
    item_for_offset,
    nested_assignments,
    parse_bundle_header,
    read_doubled_tag,
    signature_id,
)


SAMPLE = (
    b"\x0eProcessVNG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
    b"\nEpoch\x020"
    b"\nNonce\x085770"
    b"\x14Hash-ChainVhUGbfy3fgirLSqypAa58eWZpc0b8gbnWgMI8Yequ0dA"
    b"\x18Block-Height\x18000001543161"
    b"\x12Timestamp\x1a1731014461281"
    b"\x1aData-Protocol\x04ao"
    b"\x08Type\x14Assignment"
    b"\x0eVariant\x0eao.TN.1"
    b"\x0eMessageVoGBo28mcefya2OXDVxMnlbggQM56pZG-W7WYucglbDs"
)


class Ans104Test(unittest.TestCase):
    def test_sample_record_reads_nonce_5770(self):
        name, value, index = read_doubled_tag(SAMPLE, 0)
        self.assertEqual(name, "Process")
        self.assertEqual(value, "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8")
        tags = assignment_tags(b"junk" + SAMPLE)
        self.assertIsNotNone(tags)
        assert tags is not None
        self.assertEqual(tags["Nonce"], "5770")
        self.assertEqual(tags["Epoch"], "0")
        self.assertEqual(tags["Hash-Chain"], "hUGbfy3fgirLSqypAa58eWZpc0b8gbnWgMI8Yequ0dA")
        self.assertEqual(tags["Message"], "oGBo28mcefya2OXDVxMnlbggQM56pZG-W7WYucglbDs")
        self.assertEqual(tags["Block-Height"], "000001543161")
        self.assertEqual(index, 1 + 7 + 1 + 43)

    def test_nested_bundle_returns_the_inner_assignment_id(self):
        signature = b"\x11" * 512
        child = (1).to_bytes(2, "little") + signature + b"\x00" * 80 + SAMPLE
        item_id = signature_id(child)
        payload = (1).to_bytes(32, "little")
        payload += len(child).to_bytes(32, "little") + bytes.fromhex(
            # placeholder replaced below
            "00" * 32
        )
        # Rebuild the header with the real id bytes.
        import base64
        pad = "=" * ((4 - len(item_id) % 4) % 4)
        raw_id = base64.urlsafe_b64decode(item_id + pad)
        payload = (1).to_bytes(32, "little")
        payload += len(child).to_bytes(32, "little") + raw_id
        payload += child
        found = nested_assignments(payload)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["assignment_id"], item_id)
        self.assertEqual(found[0]["nonce"], 5770)
        self.assertEqual(found[0]["message_id"], "oGBo28mcefya2OXDVxMnlbggQM56pZG-W7WYucglbDs")

    def test_header_places_the_second_item_after_the_first(self):
        header = (2).to_bytes(32, "little")
        header += (10).to_bytes(32, "little") + b"a" * 32
        header += (4).to_bytes(32, "little") + b"b" * 32
        items = parse_bundle_header(header)
        self.assertEqual(items[0][0], 32 + 128)
        self.assertEqual(items[0][1], 10)
        self.assertEqual(items[1][0], 32 + 128 + 10)
        self.assertEqual(item_for_offset(items, items[1][0] + 1)[2], items[1][2])
        self.assertIsNone(item_for_offset(items, items[1][0] + 4))


if __name__ == "__main__":
    unittest.main()

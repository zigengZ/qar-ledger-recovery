import hashlib
import unittest

from recovery.ans104_item import build_data_item, deep_hash, serialize_tags, signature_id, signature_valid
from recovery.bundle_scan import nonce_needle


class Ans104ItemTest(unittest.TestCase):
    def test_short_tag_length_matches_the_bundle_needle(self):
        raw = serialize_tags([{"name": "Nonce", "value": "2075923"}])
        self.assertIn(nonce_needle(2075923), raw)
        self.assertTrue(raw.endswith(b"\x00"))

    def test_empty_tags_are_zero_bytes(self):
        self.assertEqual(serialize_tags([]), b"")

    def test_item_id_is_sha256_of_the_signature(self):
        signature = b"\x11" * 512
        owner = b"\x22" * 512
        item = build_data_item(
            signature,
            owner,
            b"\x33" * 32,
            b"",
            [{"name": "Type", "value": "Message"}],
            b"hi",
        )
        self.assertEqual(item[:2], b"\x01\x00")
        self.assertEqual(item[2:514], signature)
        self.assertEqual(signature_id(signature), signature_id(item[2:514]))
        self.assertEqual(hashlib.sha256(item[2:514]).digest(), bytes.fromhex(
            hashlib.sha256(signature).hexdigest()
        ))
        self.assertFalse(signature_valid(item))

    def test_deep_hash_of_a_list_is_48_bytes(self):
        self.assertEqual(len(deep_hash([b"dataitem", b"1"])), 48)


if __name__ == "__main__":
    unittest.main()

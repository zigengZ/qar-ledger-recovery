import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from recovery.arweave_sig import (
    b64url_encode,
    dataitem_signature_data,
    owner_address,
    serialize_ans104_tags,
    sha256,
    verify_rsa_pss,
)


class ArweaveSigTest(unittest.TestCase):
    def test_rsa_pss_accepts_its_own_ans104_message_and_rejects_a_changed_byte(self):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        owner_numbers = private.public_key().public_numbers()
        byte_len = (owner_numbers.n.bit_length() + 7) // 8
        owner = owner_numbers.n.to_bytes(byte_len, "big")
        tags = [(b"Type", b"Checkpoint"), (b"Nonce", b"1")]
        data = b"memory-bytes"
        message = dataitem_signature_data(owner, b"", b"", tags, data)
        signature = private.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        self.assertTrue(verify_rsa_pss(owner, signature, message))
        self.assertFalse(verify_rsa_pss(owner, signature, message + b"\x00"))
        self.assertEqual(owner_address(owner), b64url_encode(sha256(owner)))
        encoded = serialize_ans104_tags(tags)
        # Two tags, then the Avro length of the four-byte name "Type".
        self.assertEqual(encoded[0], 4)
        self.assertEqual(encoded[1], 8)
        self.assertEqual(encoded[2:6], b"Type")
        # The signed message changes when the tag bytes change.
        other = dataitem_signature_data(owner, b"", b"", [(b"Type", b"Other")], data)
        self.assertNotEqual(message, other)
        self.assertFalse(verify_rsa_pss(owner, signature, other))


if __name__ == "__main__":
    unittest.main()

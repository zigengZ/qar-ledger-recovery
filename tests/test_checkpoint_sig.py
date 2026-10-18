import json
import unittest
from pathlib import Path

from recovery.arweave_sig import (
    b64url_decode,
    b64url_encode,
    dataitem_signature_data,
    owner_address,
    sha256,
    verify_rsa_pss,
)

TX = Path("evidence/p5/20261017T053304Z-p5-checkpoints/selected-tx.json")
REPLAY = Path("evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json")


class CheckpointSigTest(unittest.TestCase):
    def test_selected_checkpoint_id_owner_and_signature(self):
        tx = json.loads(TX.read_text())
        replay = json.loads(REPLAY.read_text())
        owner = b64url_decode(tx["owner"]["key"])
        signature = b64url_decode(tx["signature"])
        self.assertEqual(owner_address(owner), tx["owner"]["address"])
        self.assertEqual(owner_address(owner), replay["signer"])
        self.assertEqual(b64url_encode(sha256(signature)), tx["id"])
        self.assertEqual(tx["id"], replay["id"])
        gzip_path = Path(replay["raw_gzip"])
        if not gzip_path.is_file():
            self.skipTest("checkpoint gzip is local-only")
        payload = gzip_path.read_bytes()
        self.assertEqual(len(payload), replay["gzip_bytes"])
        tags = [(tag["name"].encode(), tag["value"].encode()) for tag in tx["tags"]]
        message = dataitem_signature_data(owner, b"", b"", tags, payload)
        self.assertTrue(verify_rsa_pss(owner, signature, message))


if __name__ == "__main__":
    unittest.main()

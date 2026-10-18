import base64
import hashlib
import unittest

from recovery.ans104 import b64url, signature_id
from recovery.assignments import Assignment
from recovery.bundle_recover import (
    anchored_link_report,
    assignments_for_hits,
    commit_if_links_match,
    recover_closed_scan,
    recover_scan_payload,
)
from recovery.hashchain import gen_hash_chain
from recovery.p4_range import open_db


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


def _assignment_child(signature: bytes) -> bytes:
    return (1).to_bytes(2, "little") + signature + b"\x00" * 80 + SAMPLE


def _wrapper(signature: bytes, data: bytes) -> bytes:
    return (
        (1).to_bytes(2, "little")
        + signature
        + (b"\x22" * 512)
        + b"\x00\x00"
        + (0).to_bytes(8, "little")
        + (0).to_bytes(8, "little")
        + data
    )


def _bundle(items: list[tuple[bytes, bytes]]) -> bytes:
    raw = len(items).to_bytes(32, "little")
    for payload, item_id in items:
        raw += len(payload).to_bytes(32, "little") + item_id
    for payload, _item_id in items:
        raw += payload
    return raw


def _nested_blob():
    child = _assignment_child(b"\x11" * 512)
    inner_id = hashlib.sha256(child[2:2 + 512]).digest()
    inner = _bundle([(child, inner_id)])
    wrapped = _wrapper(b"\x44" * 512, inner)
    wrapper_id = b"\xab" * 32
    outer = _bundle([(wrapped, wrapper_id)])
    return outer, child, wrapper_id


class BundleRecoverTest(unittest.TestCase):
    def test_hit_offset_returns_the_inner_assignment_id(self):
        outer, child, wrapper_id = _nested_blob()
        needle = b"Nonce\x085770"
        offset = outer.find(needle)
        self.assertGreaterEqual(offset, 0)
        ranges = []

        def read(start, end):
            ranges.append((start, end))
            return outer[start:end]

        found = assignments_for_hits(read, [{"nonce": 5770, "offset": offset}], size=len(outer))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["assignment_id"], signature_id(child))
        self.assertNotEqual(found[0]["assignment_id"], b64url(wrapper_id))
        self.assertEqual(found[0]["wrapper_id"], b64url(wrapper_id))
        self.assertEqual(found[0]["nonce"], 5770)
        self.assertEqual(found[0]["message_id"], "oGBo28mcefya2OXDVxMnlbggQM56pZG-W7WYucglbDs")
        self.assertEqual(found[0]["hash_chain"], "hUGbfy3fgirLSqypAa58eWZpc0b8gbnWgMI8Yequ0dA")
        # The reader is asked for the header and the one item, not a made-up id.
        self.assertTrue(any(start == 0 for start, _end in ranges))
        self.assertTrue(all(end <= len(outer) for _start, end in ranges))

    def test_unclosed_scan_is_not_recovered(self):
        with self.assertRaises(RuntimeError):
            recover_closed_scan({"closed": False, "bytes": 1, "error": "HTTP Error 404"}, lambda a, b: b"")

    def test_scan_payload_uses_the_chunk_reader(self):
        outer, child, wrapper_id = _nested_blob()
        offset = outer.find(b"Nonce\x085770")

        def fetch(url):
            if url.endswith("/offset"):
                return {"offset": str(len(outer)), "size": str(len(outer))}
            cursor = int(url.rsplit("/", 1)[-1])
            file_off = cursor - 1
            aligned = file_off - (file_off % 64)
            raw = outer[aligned:aligned + 64]
            chunk_start = 1 + aligned
            return {
                "packing": "unpacked",
                "chunk_size": str(len(raw)),
                "chunk": base64.urlsafe_b64encode(raw).decode().rstrip("="),
                "absolute_end_offset": str(chunk_start + len(raw) - 1),
            }

        scan = {
            "closed": True,
            "bytes": len(outer),
            "id": "bundle-id",
            "block": 1552577,
            "nonce_hits": [{"nonce": 5770, "offset": offset}],
        }
        found = recover_scan_payload(scan, fetch=fetch)
        self.assertEqual(found[0]["assignment_id"], signature_id(child))
        self.assertEqual(found[0]["wrapper_id"], b64url(wrapper_id))
        self.assertEqual(found[0]["inclusion_height"], 1552577)
        self.assertEqual(found[0]["bundle_id"], "bundle-id")

    def test_commit_keeps_a_row_only_when_the_neighbor_link_matches(self):
        import tempfile
        from pathlib import Path

        from recovery.p4_range import insert_rows

        previous = Assignment(
            base64.urlsafe_b64encode(b"\x01" * 32).decode().rstrip("="),
            10,
            "0",
            base64.urlsafe_b64encode(b"\x02" * 32).decode().rstrip("="),
            "1000",
            base64.urlsafe_b64encode(b"\x03" * 32).decode().rstrip("="),
            "1500000",
            1500001,
            None,
            {},
        )
        good_chain = gen_hash_chain(previous.hash_chain, previous.assignment_id)
        good = {
            "assignment_id": base64.urlsafe_b64encode(b"\x04" * 32).decode().rstrip("="),
            "nonce": 11,
            "epoch": "0",
            "message_id": base64.urlsafe_b64encode(b"\x05" * 32).decode().rstrip("="),
            "timestamp_ms": "2000",
            "hash_chain": good_chain,
            "assignment_block_height": "1500002",
            "inclusion_height": 1500003,
        }
        bad = dict(good)
        bad["hash_chain"] = base64.urlsafe_b64encode(b"\x07" * 32).decode().rstrip("=")
        with tempfile.TemporaryDirectory() as directory:
            conn = open_db(Path(directory) / "assignments.sqlite")
            insert_rows(conn, [previous], "seed")
            refused = commit_if_links_match(conn, [bad], "inner-assignment-of:bundle")
            self.assertFalse(refused["anchored"])
            self.assertEqual(refused["inserted"], 0)
            self.assertIsNone(conn.execute("SELECT nonce FROM assignment WHERE nonce=11").fetchone())
            accepted = commit_if_links_match(conn, [good], "inner-assignment-of:bundle")
            self.assertTrue(accepted["anchored"])
            self.assertEqual(accepted["inserted"], 1)
            stored = conn.execute(
                "SELECT assignment_id, source_file FROM assignment WHERE nonce=11"
            ).fetchone()
            self.assertEqual(stored[0], good["assignment_id"])
            self.assertEqual(stored[1], "inner-assignment-of:bundle")
        lone = Assignment(
            base64.urlsafe_b64encode(b"\x08" * 32).decode().rstrip("="),
            30, "0", good["message_id"], "1", good["hash_chain"], None, None, None, {},
        )
        report = anchored_link_report([], [lone])
        self.assertFalse(report["anchored"])
        self.assertEqual(report["unanchored"], [30])


if __name__ == "__main__":
    unittest.main()

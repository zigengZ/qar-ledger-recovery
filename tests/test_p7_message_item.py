import unittest

from recovery.ans104 import b64url, signature_id
from recovery.arweave_sig import serialize_ans104_tags
from recovery.p7.message_item import header_around_id, parse_data_item, raw_id, scan_reader


def data_item(signature: bytes, data: bytes, tags: list[tuple[bytes, bytes]]) -> bytes:
    owner = b"\x33" * 512
    tag_bytes = serialize_ans104_tags(tags)
    raw = (1).to_bytes(2, "little") + signature + owner + b"\x00" + b"\x00"
    raw += len(tags).to_bytes(8, "little") + len(tag_bytes).to_bytes(8, "little")
    raw += tag_bytes + data
    return raw


def two_item_bundle(first: bytes, second: bytes) -> bytes:
    first_id = raw_id(signature_id(first))
    second_id = raw_id(signature_id(second))
    header = (2).to_bytes(32, "little")
    header += len(first).to_bytes(32, "little") + first_id
    header += len(second).to_bytes(32, "little") + second_id
    return header + first + second


class MemoryTx:
    def __init__(self, data: bytes, piece: int = 80):
        self.data = data
        self.size = len(data)
        self.piece = piece
        self.gaps: list[list[int]] = []

    def read(self, start: int, end: int) -> bytes:
        if start < 0 or end > self.size or end < start:
            raise ValueError(f"range {start}:{end} outside 0..{self.size}")
        return self.data[start:end]

    def iter_pieces(self):
        self.gaps = []
        for off in range(0, self.size, self.piece):
            yield off, self.data[off:off + self.piece]


class MessageItemTest(unittest.TestCase):
    def test_scan_reads_the_message_whose_id_sits_across_a_piece_boundary(self):
        message = data_item(b"\x44" * 512, b"1937", [(b"Action", b"Unwrap"), (b"Quantity", b"10000000000")])
        other = data_item(b"\x55" * 512, b"nope", [(b"Action", b"Other")])
        bundle = b"prefix-junk" + two_item_bundle(other, message) + b"tail"
        message_id = signature_id(message)
        id_at = bundle.find(raw_id(message_id))
        self.assertGreaterEqual(id_at, 0)
        piece = 80
        pad = ((piece - 10) - (id_at % piece)) % piece
        bundle = b"\x00" * pad + bundle
        id_at = bundle.find(raw_id(message_id))
        self.assertEqual(id_at % piece, piece - 10)
        reader = MemoryTx(bundle, piece=piece)
        result = scan_reader(reader, {raw_id(message_id): message_id})
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["gaps"], [])
        found = result["found"][message_id]
        self.assertEqual(found["id"], message_id)
        self.assertEqual(found["data"], b"1937")
        self.assertEqual(found["tags"], [
            {"name": "Action", "value": "Unwrap"},
            {"name": "Quantity", "value": "10000000000"},
        ])
        again = parse_data_item(message)
        self.assertEqual(again["owner"], found["owner"])
        self.assertEqual(again["signature"], found["signature"])

    def test_absent_id_stays_missing_when_the_reader_has_a_gap(self):
        message = data_item(b"\x66" * 512, b"present", [(b"Action", b"Mint")])
        bundle = two_item_bundle(message, message)
        present = signature_id(message)
        absent = b64url(b"\x99" * 32)

        class Gapped(MemoryTx):
            def iter_pieces(self):
                self.gaps = [[0, 4]]
                yield 4, self.data[4:]

        result = scan_reader(Gapped(bundle, piece=64), {raw_id(absent): absent, raw_id(present): present})
        self.assertIn(absent, result["missing"])
        self.assertNotIn(absent, result["found"])
        self.assertEqual(result["gaps"], [[0, 4]])
        self.assertEqual(result["found"][present]["data"], b"present")

    def test_header_around_id_rejects_a_random_32_byte_run(self):
        window = b"\x01" * 200
        self.assertIsNone(header_around_id(window, 40))


if __name__ == "__main__":
    unittest.main()

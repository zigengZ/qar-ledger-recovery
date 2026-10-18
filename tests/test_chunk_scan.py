import base64
import io
import json
import unittest
import urllib.error

from recovery.bundle_scan import PROCESS_ID, nonce_needle
from recovery.chunk_scan import TxBytes, decode_chunk_body, fetch_json, scan_tx_chunks, slice_chunk


class ChunkScanTest(unittest.TestCase):
    def test_slice_drops_bytes_before_the_cursor_and_after_the_tx(self):
        raw = b"abcdefghij"
        # chunk covers 90..99, cursor is 93, tx ends at 96
        self.assertEqual(slice_chunk(raw, 90, 93, 96), b"defg")
        with self.assertRaises(ValueError):
            slice_chunk(raw, 95, 93, 96)

    def test_decode_rejects_packed_chunks_and_checks_length(self):
        raw = b"abc"
        payload = {
            "packing": "unpacked",
            "chunk_size": "3",
            "chunk": base64.urlsafe_b64encode(raw).decode().rstrip("="),
        }
        self.assertEqual(decode_chunk_body(payload), raw)
        payload["packing"] = "spora_2_5"
        with self.assertRaises(ValueError):
            decode_chunk_body(payload)

    def test_ranged_read_seeks_to_the_first_requested_byte(self):
        # Weave end 200, size 100 => file byte 0 lives at weave offset 101.
        file_bytes = bytes(range(100))
        calls = []

        def fetch(url):
            if url.endswith("/offset"):
                return {"offset": "200", "size": "100"}
            cursor = int(url.rsplit("/", 1)[-1])
            calls.append(cursor)
            file_off = cursor - 101
            aligned = file_off - (file_off % 16)
            raw = file_bytes[aligned:aligned + 16]
            chunk_start = 101 + aligned
            return {
                "packing": "unpacked",
                "chunk_size": str(len(raw)),
                "chunk": base64.urlsafe_b64encode(raw).decode().rstrip("="),
                "absolute_end_offset": str(chunk_start + len(raw) - 1),
            }

        reader = TxBytes("range-tx", fetch=fetch)
        self.assertEqual(reader.read(10, 25), file_bytes[10:25])
        self.assertEqual(calls, [111, 117])
        self.assertNotIn(101, calls)
        again = len(calls)
        self.assertEqual(reader.read(12, 22), file_bytes[12:22])
        self.assertEqual(len(calls), again)
        self.assertEqual(reader.read(90, 100), file_bytes[90:100])
        with self.assertRaises(ValueError):
            reader.read(90, 101)

    def test_fetch_retries_then_returns_the_json_body(self):
        calls = []
        slept = []

        class Body:
            def read(self):
                return json.dumps({"ok": True}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def opener(request, timeout=None):
            calls.append(request.full_url)
            if len(calls) < 3:
                raise TimeoutError("temporary")
            return Body()

        self.assertEqual(
            fetch_json("https://example.test/chunk/1", sleep=slept.append, opener=opener),
            {"ok": True},
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(slept, [1, 2])

        def always_fail(request, timeout=None):
            raise TimeoutError("down")

        with self.assertRaises(RuntimeError):
            fetch_json("https://example.test/chunk/2", attempts=3, sleep=slept.append, opener=always_fail)
        self.assertEqual(slept, [1, 2, 1, 2])

    def test_fetch_closes_http_error_responses(self):
        closed = []

        class ClosingError(urllib.error.HTTPError):
            def __init__(self):
                super().__init__(
                    "https://example.test/chunk/9",
                    404,
                    "Not Found",
                    {},
                    io.BytesIO(b"missing"),
                )

            def close(self):
                closed.append(self.code)
                super().close()

        def opener(request, timeout=None):
            raise ClosingError()

        with self.assertRaises(RuntimeError):
            fetch_json("https://example.test/chunk/9", attempts=2, sleep=lambda _seconds: None, opener=opener)
        self.assertEqual(closed, [404, 404])

    def test_missing_chunk_is_a_gap_and_later_nonce_keeps_its_offset(self):
        prefix = b"\x0eProcessV" + PROCESS_ID.encode() + b"\nEpoch\x020\n" + nonce_needle(88429)
        chunk_b = prefix + (b"z" * (128 - len(prefix)))
        self.assertEqual(len(chunk_b), 128)

        def fetch(url):
            if url.endswith("/offset"):
                return {"offset": "659", "size": "160"}
            cursor = int(url.rsplit("/", 1)[-1])
            if 516 <= cursor <= 531:
                raise RuntimeError(f"{url} failed: HTTP Error 404: Not Found")
            if 500 <= cursor <= 515:
                raw = b"a" * 16
                end = 515
            elif 532 <= cursor <= 659:
                raw = chunk_b
                end = 659
            else:
                raise RuntimeError(f"{url} failed: HTTP Error 404: Not Found")
            return {
                "packing": "unpacked",
                "chunk_size": str(len(raw)),
                "chunk": base64.urlsafe_b64encode(raw).decode().rstrip("="),
                "absolute_end_offset": str(end),
            }

        found = scan_tx_chunks("gap-tx", {88429, 87659}, fetch=fetch, probe_step=16)
        self.assertFalse(found["closed"])
        self.assertEqual(found["gaps"], [[16, 32]])
        self.assertEqual(found["bytes"], 144)
        self.assertEqual([hit["nonce"] for hit in found["nonce_hits"]], [88429])
        self.assertEqual(found["nonce_hits"][0]["offset"], 32 + prefix.index(nonce_needle(88429)))
        self.assertNotIn(87659, [hit["nonce"] for hit in found["nonce_hits"]])


if __name__ == "__main__":
    unittest.main()

import unittest

from recovery.bundle_scan import (
    PROCESS_ID,
    find_plaintext_nonces,
    find_process_offsets,
    nonce_needle,
    scan_stream,
)


class BundleScanTest(unittest.TestCase):
    def test_two_byte_nonce_tag_and_process_id_are_found_across_chunks(self):
        # Observed framing: name, then one byte = 2 * digit count, then digits.
        blob = b"xxxx" + b"Nonce\x085769" + b"yyyy" + PROCESS_ID.encode() + b"Nonce\x085770" + b"zz"
        # Split inside the second nonce tag so a short overlap would drop it.
        cut = blob.index(b"5770") - 2
        report = scan_stream([blob[:cut], blob[cut:]], {5769, 5770, 5793}, overlap=80)
        self.assertEqual(report["bytes"], len(blob))
        # 5769 is a bare nonce tag. Only 5770 sits on this process id.
        self.assertEqual(sorted(hit["nonce"] for hit in report["nonce_hits"]), [5770])
        self.assertEqual(report["process_hit_count"], 1)
        self.assertEqual(find_process_offsets(blob), [blob.index(PROCESS_ID.encode())])
        self.assertEqual(
            [hit.nonce for hit in find_plaintext_nonces(blob, {5770})],
            [5770],
        )

    def test_unwanted_nonce_and_json_digits_are_not_tags(self):
        data = b'":5796.737535770784,"metadata"' + b"Nonce\x0e1743125" + b"Nonce\x085749"
        hits = find_plaintext_nonces(data, set(range(5770, 5794)))
        self.assertEqual(hits, [])
        seven = find_plaintext_nonces(data, {1743125})
        self.assertEqual([hit.nonce for hit in seven], [1743125])

    def test_same_nonce_on_another_process_is_not_a_hit(self):
        foreign = b"1J-YEAF_j0DieqA7Jy_SoH4ZsC2sIF4nxol0YvoPoW0"
        nonce = nonce_needle(88429)
        ours = b"\x0eProcessV" + PROCESS_ID.encode() + b"\nEpoch\x020\n" + nonce_needle(99053)
        other = b"\x0eProcessV" + foreign + b"\nEpoch\x020\n" + nonce
        blob = ours + (b"x" * 200) + other
        report = scan_stream([blob], {88429, 99053})
        self.assertEqual([hit["nonce"] for hit in report["nonce_hits"]], [99053])
        # The process id is split from the nonce tag across two chunks.
        cut = blob.index(PROCESS_ID.encode()) + 10
        split = scan_stream([blob[:cut], blob[cut:]], {88429, 99053})
        self.assertEqual([hit["nonce"] for hit in split["nonce_hits"]], [99053])


if __name__ == "__main__":
    unittest.main()

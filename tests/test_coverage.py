import tempfile
import unittest
from pathlib import Path

from recovery.assignments import Assignment
from recovery.coverage import coverage_report, missing_ranges, window_passed_end
from recovery.p4_range import copy_nonce_range, open_db


class CoverageTest(unittest.TestCase):
    def test_missing_ranges_compress_holes(self):
        self.assertEqual(missing_ranges([1, 2, 3, 7, 9]), [[1, 3], [7, 7], [9, 9]])

    def test_count_match_with_a_hole_is_not_complete(self):
        # 0..3 expected. Nonce 1 is absent and nonce 5 is an extra outside the range.
        # Unique in-range count is 3, not equal to 4, and must not be called complete
        # even if someone compared it with a different total.
        report = coverage_report(0, 3, {
            0: ["a"],
            2: ["b"],
            3: ["c"],
            5: ["d"],
        })
        self.assertEqual(report["missing_ranges"], [[1, 1]])
        self.assertFalse(report["complete"])
        self.assertEqual(report["outside_range_nonce_count"], 1)
        self.assertEqual(report["unique_count"], 3)

    def test_two_ids_are_a_conflict_not_a_filled_nonce(self):
        report = coverage_report(0, 1, {0: ["a", "b"], 1: ["c"]})
        self.assertFalse(report["complete"])
        self.assertEqual(report["conflicts"], {"0": ["a", "b"]})
        self.assertEqual(report["missing_count"], 0)
        self.assertEqual(report["unique_count"], 1)

    def test_copy_keeps_only_the_requested_nonce_range(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = open_db(root / "source.sqlite")
            source.executemany(
                "INSERT INTO assignment (nonce, epoch, assignment_id, message_id, timestamp_ms, assignment_block_height, inclusion_height, inclusion_timestamp, hash_chain, source_file) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    (49999, "0", "a" * 43, "m", "1", "1", 1, None, "h", "src"),
                    (50000, "0", "b" * 43, "m", "1", "1", 2, None, "h", "src"),
                    (50001, "0", "c" * 43, "m", "1", "1", 2, None, "h", "src"),
                ],
            )
            source.commit()
            dest = open_db(root / "dest.sqlite")
            copied = copy_nonce_range(source, dest, 50000, 99999)
            self.assertEqual(copied, 2)
            nonces = [row[0] for row in dest.execute("SELECT nonce FROM assignment ORDER BY nonce")]
            self.assertEqual(nonces, [50000, 50001])
            source.close()
            dest.close()

    def test_out_of_window_low_nonce_does_not_keep_the_scan_open(self):
        rows = [
            Assignment("a" * 43, 10, "0", "m", "1", "h", None, 100, None, {}),
            Assignment("b" * 43, 50010, "0", "m", "1", "h", None, 200, None, {}),
        ]
        self.assertTrue(window_passed_end(rows, 200, 220, 49999))
        self.assertFalse(window_passed_end(rows, 100, 220, 49999))
        self.assertFalse(window_passed_end([], 200, 220, 49999))

    def test_full_unique_range_is_complete(self):
        report = coverage_report(0, 2, {0: ["a"], 1: ["b"], 2: ["c"]})
        self.assertTrue(report["complete"])
        self.assertEqual(report["expected_count"], 3)


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

from recovery.p10.build_report import load_range_account

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = ROOT / "evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json"
NON_AO = ROOT / "evidence/p4/20261017T033409Z-p4-50000-non-ao/finding.json"
LARGEST = ROOT / "evidence/p4/20261016T203902Z-p4-50000-largest-false/finding.json"
NONBINARY = ROOT / "evidence/p4/20261017T034025Z-p4-50000-nonbinary/finding.json"
HOLE = ROOT / "evidence/p4/20261017T1726Z-p4-hole-87659/hole.json"
FAILURE = ROOT / "evidence/p4/20261017T1726Z-p4-hole-87659/failure.json"


class Hole87659Test(unittest.TestCase):
    def test_first_missing_nonce_stays_unresolved(self) -> None:
        account = load_range_account(BLOCKED)
        blocked = json.loads(BLOCKED.read_text(encoding="utf-8"))
        non_ao = json.loads(NON_AO.read_text(encoding="utf-8"))
        largest = json.loads(LARGEST.read_text(encoding="utf-8"))
        nonbinary = json.loads(NONBINARY.read_text(encoding="utf-8"))
        hole = json.loads(HOLE.read_text(encoding="utf-8"))
        failure = json.loads(FAILURE.read_text(encoding="utf-8"))

        self.assertEqual(account["missing_nonces"][0], 87659)
        self.assertEqual(blocked["missing_ranges"][0], [87659, 87659])
        self.assertEqual(hole["hole"]["nonce_start"], account["missing_nonces"][0])
        self.assertEqual(hole["hole"]["nonce_end"], account["missing_nonces"][0])
        self.assertIsNone(hole["hole"]["assignment_id"])
        self.assertIsNone(hole["hole"]["message_id"])
        self.assertIsNone(hole["hole"]["raw_amount"])
        self.assertIsNone(failure["raw_amount"])
        self.assertIsNone(failure["actual_delta"])
        self.assertFalse(hole["proven_absent"])
        self.assertFalse(hole["schedule_covered"])
        self.assertFalse(hole["inputs_complete"])
        self.assertFalse(hole["goal_complete"])
        self.assertFalse(failure["goal_complete"])
        self.assertEqual(hole["range_still_missing"], blocked["still_missing"])
        self.assertGreater(hole["range_still_missing"], 1)

        window = next(item for item in non_ao["windows"] if item["window"] == "87659-cluster")
        self.assertEqual(hole["neighbor_blocks"], window["blocks"])
        self.assertEqual(hole["non_ao_window"]["non_ao_bundles"], window["non_ao_bundles"])
        self.assertEqual(hole["non_ao_window"]["fully_read_without_wanted_nonce"], window["fully_read_without_wanted_nonce"])
        self.assertEqual(hole["non_ao_window"]["unclosed"], window["unclosed"])

        cited = {(row["block"], row["id"], row["process_hits"]) for row in hole["largest_bundles_without_process_hits"]}
        source_rows = [
            row for row in largest["closed_bundles_without_wanted_nonce_bytes"]
            if row["block"] in window["blocks"]
        ]
        self.assertEqual(cited, {(row["block"], row["id"], row["process_hits"]) for row in source_rows})

        unclosed = next(
            row for row in nonbinary["ao_bundles_still_unclosed_in_hole_windows"]
            if row["id"] == hole["unclosed_bundle"]["id"]
        )
        self.assertFalse(unclosed["bundle_closed"])
        self.assertEqual(hole["unclosed_bundle"]["gap_count"], unclosed["gap_count"])
        self.assertEqual(hole["unclosed_bundle"]["bytes_read"], unclosed["bytes_read"])
        self.assertEqual(
            hole["unclosed_bundle"]["paired_wanted_nonces_in_readable_bytes"],
            unclosed["paired_wanted_nonces_in_readable_bytes"],
        )
        probed = next(row for row in blocked["bundles"] if row["id"] == unclosed["id"])
        self.assertEqual(hole["unclosed_bundle"]["chunk_offsets_probed"], probed["chunk_offsets_probed"])
        self.assertEqual(hole["unclosed_bundle"]["readable_chunks_in_that_probe"], blocked["readable_chunks"])
        self.assertEqual(hole["unclosed_bundle"]["http_404_in_that_probe"], blocked["http_404"])

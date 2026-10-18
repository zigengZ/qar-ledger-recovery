import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDERS = ROOT / "evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json"
FINDING = ROOT / "evidence/p8/20261017T1712Z-p8-unknown-sources/finding.json"


class UnknownSourceTest(unittest.TestCase):
    def test_unknown_processes_stay_unknown(self) -> None:
        holders = json.loads(HOLDERS.read_text(encoding="utf-8"))["holders"]
        finding = json.loads(FINDING.read_text(encoding="utf-8"))
        by_address = {row["address"]: row for row in holders}
        unknown = [row for row in holders if row["role"] == "unknown_process"]
        self.assertEqual(len(unknown), 369)
        self.assertEqual(finding["unknown_process_count"], 369)
        self.assertEqual(finding["config_id_hits"], 0)
        self.assertFalse(finding["classification_sourced"])
        self.assertEqual(finding["unknown_relabeled"], 0)
        self.assertEqual(finding["wallet_relabeled_end_user"], 0)
        self.assertEqual(len(finding["rows"]), 369)
        for row in finding["rows"]:
            self.assertEqual(row["role"], "unknown_process")
            self.assertNotIn(row["role"], {"user", "end_user"})
            self.assertFalse(row["config_hit"])
            self.assertEqual(by_address[row["address"]]["role"], "unknown_process")
            self.assertEqual(by_address[row["address"]]["raw_balance"], row["raw_balance"])

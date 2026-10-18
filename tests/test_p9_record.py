import json
import unittest
from pathlib import Path

from recovery.p10.build_report import interpret_collateral

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evidence/p9/20261017T1720Z-p9-record/collateral-for-report.json"
SUPPLY = 189487568412204611


class CollateralRecordTest(unittest.TestCase):
    def test_separable_amount_stays_unknown(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.assertIsNone(record["raw_amount_at_tail"])
        self.assertIsNone(record["raw_amount_now"])
        self.assertIsNone(record["eligible_held_raw"])
        self.assertIsNone(record["holder"])
        self.assertEqual(record["asset"], "AR")
        self.assertFalse(record["original_custody_wallet_is_eligible_collateral"])
        result = interpret_collateral(record, SUPPLY)
        self.assertIsNone(result["delta_raw"])
        self.assertIsNone(result["raw_amount"])
        self.assertNotEqual(result["delta_raw"], 0)
        self.assertNotEqual(result["delta_raw"], "0")
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(record["collateral_sourced"])
        self.assertFalse(record["collateral_reconciled"])
        self.assertFalse(record["goal_complete"])

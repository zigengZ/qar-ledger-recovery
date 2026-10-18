import hashlib
import json
import unittest
from pathlib import Path

from recovery.assignments import _transactions
from recovery.p10.build_report import load_range_account

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = ROOT / "evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json"
RUN = ROOT / "evidence/p4/20261017T1747Z-p4-hole-after-88893"


class Hole88894Test(unittest.TestCase):
    def test_exact_query_does_not_prove_absence(self) -> None:
        account = load_range_account(BLOCKED)
        nonce = next(item for item in account["missing_nonces"] if item > 88893)
        self.assertLess(nonce, 150000)
        finding = json.loads((RUN / "finding.json").read_text(encoding="utf-8"))
        failure = json.loads((RUN / "failure.json").read_text(encoding="utf-8"))
        request = json.loads((RUN / "request-1.json").read_text(encoding="utf-8"))
        body = (RUN / "page-1.json").read_bytes()
        parsed = json.loads(body)
        transactions = _transactions(parsed)
        edges = transactions.get("edges") or []
        has_next = bool((transactions.get("pageInfo") or {}).get("hasNextPage"))

        self.assertEqual(finding["nonce"], nonce)
        self.assertEqual(finding["prior_hole"], 88893)
        self.assertEqual(request["variables"]["nonces"], [str(nonce)])
        self.assertEqual(finding["pages"][0]["body_sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(finding["pages"][0]["http_status"], 200)
        self.assertEqual(finding["pages"][0]["edge_count"], len(edges))
        self.assertEqual(finding["pages"][0]["has_next_page"], has_next)
        self.assertTrue(finding["closed"])
        self.assertFalse(has_next)
        self.assertEqual(edges, [])
        self.assertIsNone(finding["assignment_id"])
        self.assertIsNone(finding["message_id"])
        self.assertIsNone(finding["raw_amount"])
        self.assertIsNone(failure["raw_amount"])
        self.assertIsNone(failure["actual_delta"])
        self.assertFalse(finding["proven_absent"])
        self.assertFalse(finding["schedule_covered"])
        self.assertFalse(finding["goal_complete"])
        self.assertFalse(failure["goal_complete"])
        self.assertEqual(failure["missing_range"], [nonce, nonce])

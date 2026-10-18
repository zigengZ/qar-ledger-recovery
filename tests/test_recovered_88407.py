import json
import unittest
from pathlib import Path

from recovery.assignments import Assignment
from recovery.hashchain import link_matches

EVIDENCE = Path("evidence/p4/20261016T234433Z-p4-50000-88407/recovered.json")


class Recovered88407Test(unittest.TestCase):
    def test_inner_ids_link_from_88406_through_88431(self):
        payload = json.loads(EVIDENCE.read_text())
        self.assertFalse(payload["bundle_closed"])
        self.assertFalse(payload["complete"])
        self.assertGreater(payload["gap_count"], 0)
        self.assertEqual(payload["inserted"], 24)
        self.assertEqual(payload["still_missing"], 163)
        chain = payload["chain"]
        self.assertEqual([row["nonce"] for row in chain], list(range(88406, 88432)))
        rows = [
            Assignment(
                row["assignment_id"],
                row["nonce"],
                row["epoch"],
                row["message_id"],
                row["timestamp_ms"],
                row["hash_chain"],
                row["assignment_block_height"],
                row["inclusion_height"],
                None,
                {},
            )
            for row in chain
        ]
        for previous, current in zip(rows, rows[1:]):
            self.assertTrue(link_matches(previous, current), current.nonce)
        recovered = [row for row in chain if row["nonce"] not in (88406, 88431)]
        self.assertTrue(all(row["assignment_id"] != row["wrapper_id"] for row in recovered))


if __name__ == "__main__":
    unittest.main()

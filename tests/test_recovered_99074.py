import json
import unittest
from pathlib import Path

from recovery.assignments import Assignment
from recovery.hashchain import link_matches

EVIDENCE = Path("evidence/p4/20261016T210139Z-p4-50000-99074/recovered.json")


class Recovered99074Test(unittest.TestCase):
    def test_inner_ids_link_from_99073_through_99098(self):
        payload = json.loads(EVIDENCE.read_text())
        self.assertFalse(payload["bundle_closed"])
        self.assertFalse(payload["complete"])
        self.assertGreater(payload["gap_count"], 0)
        self.assertEqual(payload["inserted"], 24)
        self.assertEqual(payload["still_missing"], 237)
        chain = payload["chain"]
        self.assertEqual([row["nonce"] for row in chain], list(range(99073, 99099)))
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
        recovered = [row for row in chain if row["nonce"] != 99073 and row["nonce"] != 99098]
        self.assertTrue(all(row["assignment_id"] != row["wrapper_id"] for row in recovered))


if __name__ == "__main__":
    unittest.main()

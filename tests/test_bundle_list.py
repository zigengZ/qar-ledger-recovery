import unittest

from recovery.bundle_list import list_ao_bundles
from recovery.gql import GqlResponse


def _response(edges, has_next, *, ok=True):
    body = b"{}"
    parsed = {"data": {"transactions": {"pageInfo": {"hasNextPage": has_next}, "edges": edges}}}
    return GqlResponse("https://example.test/graphql", 200 if ok else 572, 1, 1, body, parsed if ok else None, None if ok else "http 572")


def _edge(tx_id, height, size, cursor, *, binary=True):
    tags = [{"name": "Bundle-Format", "value": "binary" if binary else "json"}]
    return {
        "cursor": cursor,
        "node": {
            "id": tx_id,
            "data": {"size": str(size)},
            "block": {"height": height},
            "tags": tags,
        },
    }


class BundleListTest(unittest.TestCase):
    def test_second_page_is_merged_and_a_failed_page_stays_open(self):
        calls = []

        def post(query, variables, endpoint="https://arweave.net/graphql"):
            calls.append(variables["after"])
            if variables["after"] is None:
                return _response([
                    _edge("plain", 10, 1, "c0", binary=False),
                    _edge("one", 10, 5, "c1"),
                ], True)
            return _response([_edge("two", 11, 8, "c2")], False)

        found = list_ao_bundles(10, 11, post=post, max_pages=5)
        self.assertTrue(found["closed"])
        self.assertEqual([row["id"] for row in found["bundles"]], ["one", "two"])
        self.assertEqual(found["bundles"][1]["block"], 11)
        self.assertEqual(found["bundles"][1]["size"], 8)
        self.assertEqual(calls, [None, "c1"])

        def fail_second(query, variables, endpoint="https://arweave.net/graphql"):
            if variables["after"] is None:
                return _response([_edge("one", 10, 5, "c1")], True)
            return _response([], True, ok=False)

        partial = list_ao_bundles(10, 11, post=fail_second, max_pages=5)
        self.assertFalse(partial["closed"])
        self.assertEqual([row["id"] for row in partial["bundles"]], ["one"])
        self.assertIn("572", partial["error"])

    def test_page_budget_does_not_claim_the_window_is_empty(self):
        def post(query, variables, endpoint="https://arweave.net/graphql"):
            return _response([_edge("one", 10, 5, "c1")], True)

        found = list_ao_bundles(10, 10, post=post, max_pages=1)
        self.assertFalse(found["closed"])
        self.assertEqual(len(found["bundles"]), 1)
        self.assertIn("page budget", found["error"])


if __name__ == "__main__":
    unittest.main()
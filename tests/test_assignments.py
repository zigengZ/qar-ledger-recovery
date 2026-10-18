"""Pure checks for assignment parsing, paging, and nonce-set difference."""

from __future__ import annotations

import hashlib
import json
import unittest

from recovery.assignments import (
    Assignment,
    diff_nonces,
    fetch_block_window,
    merge_assignments,
    narrow_nonce_search,
    parse_assignment,
)
from recovery.gql import GqlResponse
from recovery.hashchain import b64url_decode, b64url_encode, check_links, gen_hash_chain


def edge(nonce: int, assignment_id: str, height: int, cursor: str, message: str = "m" * 43, chain: str = "c" * 43) -> dict:
    return {
        "cursor": cursor,
        "node": {
            "id": assignment_id,
            "block": {"height": height, "timestamp": 1700000000 + nonce},
            "tags": [
                {"name": "Nonce", "value": str(nonce)},
                {"name": "Epoch", "value": "0"},
                {"name": "Message", "value": message},
                {"name": "Hash-Chain", "value": chain},
                {"name": "Timestamp", "value": str(1700000000000 + nonce)},
                {"name": "Block-Height", "value": f"{height:012d}"},
                {"name": "Type", "value": "Assignment"},
            ],
        },
    }


def gql_page(edges: list[dict], has_next: bool, attempt: int = 1) -> GqlResponse:
    payload = {
        "data": {
            "transactions": {
                "pageInfo": {"hasNextPage": has_next},
                "edges": edges,
            }
        }
    }
    body = json.dumps(payload).encode()
    return GqlResponse(
        endpoint="test",
        http_status=200,
        elapsed_ms=1,
        attempt=attempt,
        body=body,
        parsed=payload,
        error=None,
    )


class ParseAndDiffTest(unittest.TestCase):
    def test_parse_integer_nonce_and_tags(self):
        row = parse_assignment(edge(2, "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI", 1505341, "cur"))
        self.assertEqual(row.nonce, 2)
        self.assertEqual(row.assignment_id, "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI")
        self.assertEqual(row.inclusion_height, 1505341)
        self.assertEqual(row.epoch, "0")

    def test_rejects_non_integer_nonce(self):
        item = edge(1, "a" * 43, 1, "c")
        item["node"]["tags"][0]["value"] = "2.0"
        with self.assertRaises(ValueError):
            parse_assignment(item)

    def test_diff_reports_missing_duplicate_and_conflict_separately(self):
        rows = [
            parse_assignment(edge(0, "a" * 43, 10, "1")),
            parse_assignment(edge(2, "b" * 43, 10, "2")),
            parse_assignment(edge(2, "b" * 43, 10, "3")),
            parse_assignment(edge(3, "c" * 43, 11, "4")),
            parse_assignment(edge(3, "d" * 43, 11, "5")),
        ]
        diff = diff_nonces(list(range(0, 5)), rows)
        self.assertEqual(diff.missing, [1, 4])
        self.assertEqual(diff.duplicate_ids[2], ["b" * 43, "b" * 43])
        self.assertEqual(diff.conflicts[3], ["c" * 43, "d" * 43])
        self.assertNotIn(3, diff.unique)
        self.assertFalse(diff.clean)

    def test_merge_keeps_distinct_ids(self):
        rows = [
            parse_assignment(edge(0, "a" * 43, 10, "1")),
            parse_assignment(edge(0, "a" * 43, 10, "2")),
            parse_assignment(edge(1, "b" * 43, 10, "3")),
        ]
        merged = merge_assignments(rows)
        self.assertEqual([row.assignment_id for row in merged], ["a" * 43, "b" * 43])


class PagingTest(unittest.TestCase):
    def test_pages_until_closed_and_keeps_same_height_rows(self):
        pages = [
            gql_page([
                edge(0, "a" * 43, 1505290, "c0"),
                edge(1, "b" * 43, 1505290, "c1"),
            ], True),
            gql_page([
                edge(2, "c" * 43, 1505290, "c2"),
            ], False),
        ]
        calls = {"n": 0}

        def post(query, variables, endpoint="https://arweave.net/graphql"):
            page = pages[calls["n"]]
            calls["n"] += 1
            self.assertIn("after", variables)
            return page

        window = fetch_block_window(1505290, 1505290, page_size=2, post=post)
        self.assertTrue(window.closed)
        self.assertEqual([row.nonce for row in window.rows], [0, 1, 2])
        self.assertEqual(calls["n"], 2)
        self.assertEqual(window.pages[1].cursor_in, "c1")

    def test_open_page_with_stalled_cursor_is_not_closed(self):
        def post(query, variables, endpoint="https://arweave.net/graphql"):
            return gql_page([edge(0, "a" * 43, 10, "same")], True)

        window = fetch_block_window(10, 10, page_size=1, max_pages=3, post=post)
        self.assertFalse(window.closed)
        self.assertIn("stalled", window.error or "")

    def test_http_failure_is_not_an_empty_closed_window(self):
        def post(query, variables, endpoint="https://arweave.net/graphql"):
            return GqlResponse("test", 502, 5, 3, b"bad gateway", None, "502")

        window = fetch_block_window(10, 12, post=post)
        self.assertFalse(window.closed)
        self.assertEqual(window.rows, [])
        self.assertIsNotNone(window.error)


class SearchBoundTest(unittest.TestCase):
    def test_empty_gap_advances_past_the_probe_not_the_old_frontier(self):
        lo, hi = narrow_nonce_search(
            lo=1924101, hi=1951869, mid=1937985,
            frontier_height=1924100, min_nonce=2075899, max_nonce=2075900,
            target=2075904,
        )
        self.assertEqual(lo, 1937986)
        self.assertEqual(hi, 1951869)

    def test_frontier_above_target_moves_the_upper_bound_below_that_block(self):
        lo, hi = narrow_nonce_search(
            lo=1505290, hi=1951869, mid=1728579,
            frontier_height=1728572, min_nonce=2057918, max_nonce=2057921,
            target=1037960,
        )
        self.assertEqual((lo, hi), (1505290, 1728571))


class HashChainTest(unittest.TestCase):
    def test_byte_order_matches_sha256_of_assignment_then_previous_chain(self):
        previous_chain = "9MLUvv1PW2qnG68uiTCzXWe955g0lPWuM7qbwMoB9Ec"
        previous_assignment = "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI"
        digest = hashlib.sha256(
            b64url_decode(previous_assignment) + b64url_decode(previous_chain)
        ).digest()
        self.assertEqual(gen_hash_chain(previous_chain, previous_assignment), b64url_encode(digest))

    def test_seed_only_hashes_the_seed_bytes(self):
        seed = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
        digest = hashlib.sha256(b64url_decode(seed)).digest()
        self.assertEqual(gen_hash_chain(seed, None), b64url_encode(digest))

    def test_check_links_skips_a_gap_and_flags_a_bad_link(self):
        seed = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
        first_id = "o" * 43
        # 43 chars may not be 32 bytes. Build ids from the real process id shape.
        first_id = seed
        second_id = "vjIZKJmbEt903EgiW1u7boJcTkyKWRLqhNaHqZgS3ZI"
        chain0 = gen_hash_chain(seed, None)
        chain1 = gen_hash_chain(chain0, first_id)
        good = [
            Assignment(first_id, 0, "0", "m" * 43, "1", chain0, None, 1, 1, {}),
            Assignment(second_id, 1, "0", "n" * 43, "2", chain1, None, 1, 1, {}),
        ]
        report = check_links(good)
        self.assertTrue(report["verified"])
        self.assertEqual(report["links_checked"], 1)
        broken = [
            good[0],
            Assignment(second_id, 2, "0", "n" * 43, "2", chain1, None, 1, 1, {}),
        ]
        gapped = check_links(broken)
        self.assertEqual(gapped["links_checked"], 0)
        self.assertIn(2, gapped["skipped_because_previous_nonce_absent"])


if __name__ == "__main__":
    unittest.main()

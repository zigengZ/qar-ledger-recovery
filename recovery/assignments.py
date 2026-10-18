"""Parse AO assignment rows and compare them with an expected nonce set.

GraphQL tag filters are exact values, not numeric ranges. Block-height windows
are fully paginated, then merged by integer nonce. A window with
`hasNextPage` still true is not closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from recovery.gql import GqlResponse, post_graphql

PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
SPAWN_BLOCK = 1505290
TAIL_INCLUSION_BLOCK = 1951869
TAIL_NONCE = 2075923

ASSIGNMENT_FIELDS = """
id
block { height timestamp }
tags { name value }
"""

BLOCK_WINDOW_QUERY = """
query($min:Int!, $max:Int!, $first:Int!, $after:String) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    block: { min: $min, max: $max }
    tags: [
      { name: "Data-Protocol", values: ["ao"] }
      { name: "Type", values: ["Assignment"] }
      { name: "Process", values: ["%s"] }
    ]
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node { %s }
    }
  }
}
""" % (PROCESS_ID, ASSIGNMENT_FIELDS)

EXACT_NONCE_QUERY = """
query($nonces:[String!]!, $first:Int!, $after:String) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    tags: [
      { name: "Data-Protocol", values: ["ao"] }
      { name: "Type", values: ["Assignment"] }
      { name: "Process", values: ["%s"] }
      { name: "Epoch", values: ["0"] }
      { name: "Nonce", values: $nonces }
    ]
  ) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node { %s }
    }
  }
}
""" % (PROCESS_ID, ASSIGNMENT_FIELDS)

TX_QUERY = """
query($id:ID!) {
  transaction(id: $id) {
    id
    owner { address }
    anchor
    signature
    block { height timestamp }
    tags { name value }
  }
}
"""


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    nonce: int
    epoch: str
    message_id: str
    timestamp_ms: str
    hash_chain: str
    assignment_block_height: str | None
    inclusion_height: int | None
    inclusion_timestamp: int | None
    tags: dict[str, str]
    cursor: str | None = None

    def to_json(self) -> dict:
        return {
            "assignment_id": self.assignment_id,
            "epoch": self.epoch,
            "nonce": self.nonce,
            "message_id": self.message_id,
            "timestamp_ms": self.timestamp_ms,
            "hash_chain": self.hash_chain,
            "assignment_block_height": self.assignment_block_height,
            "inclusion_height": self.inclusion_height,
            "inclusion_timestamp": self.inclusion_timestamp,
            "cursor": self.cursor,
            "tags": self.tags,
        }


@dataclass
class Page:
    request: dict
    response: GqlResponse
    edges: list[dict]
    has_next_page: bool
    cursor_in: str | None
    cursor_out: str | None


@dataclass
class WindowFetch:
    min_height: int
    max_height: int
    page_size: int
    pages: list[Page]
    rows: list[Assignment]
    closed: bool
    error: str | None = None


@dataclass
class NonceDiff:
    expected: list[int]
    unique: dict[int, Assignment]
    missing: list[int]
    duplicate_ids: dict[int, list[str]]
    conflicts: dict[int, list[str]]

    @property
    def clean(self) -> bool:
        return not self.missing and not self.duplicate_ids and not self.conflicts


def parse_assignment(edge: dict) -> Assignment:
    node = edge["node"]
    tags = {item["name"]: item["value"] for item in node.get("tags") or []}
    if "Nonce" not in tags:
        raise ValueError(f"assignment {node.get('id')} has no Nonce tag")
    nonce_text = tags["Nonce"]
    if not nonce_text.isdigit():
        raise ValueError(f"assignment {node.get('id')} nonce is not an integer string: {nonce_text!r}")
    block = node.get("block") or {}
    return Assignment(
        assignment_id=node["id"],
        nonce=int(nonce_text),
        epoch=tags.get("Epoch", ""),
        message_id=tags.get("Message", ""),
        timestamp_ms=tags.get("Timestamp", ""),
        hash_chain=tags.get("Hash-Chain", ""),
        assignment_block_height=tags.get("Block-Height"),
        inclusion_height=block.get("height"),
        inclusion_timestamp=block.get("timestamp"),
        tags=tags,
        cursor=edge.get("cursor"),
    )


def diff_nonces(expected: list[int], rows: list[Assignment]) -> NonceDiff:
    """Set difference on integer nonces. Same id twice is a duplicate page hit.

    Two different assignment ids for one nonce are a conflict, not a duplicate
    to be collapsed.
    """
    grouped: dict[int, list[Assignment]] = {}
    for row in rows:
        grouped.setdefault(row.nonce, []).append(row)
    unique: dict[int, Assignment] = {}
    duplicate_ids: dict[int, list[str]] = {}
    conflicts: dict[int, list[str]] = {}
    for nonce, items in grouped.items():
        ids = [item.assignment_id for item in items]
        distinct = list(dict.fromkeys(ids))
        if len(distinct) == 1:
            unique[nonce] = items[0]
            if len(ids) > 1:
                duplicate_ids[nonce] = ids
        else:
            conflicts[nonce] = distinct
    missing = [nonce for nonce in expected if nonce not in unique and nonce not in conflicts]
    return NonceDiff(
        expected=list(expected),
        unique=unique,
        missing=missing,
        duplicate_ids=duplicate_ids,
        conflicts=conflicts,
    )


def merge_assignments(rows: list[Assignment]) -> list[Assignment]:
    """Stable de-duplication by assignment id. Does not drop distinct ids."""
    seen: set[str] = set()
    merged: list[Assignment] = []
    for row in rows:
        if row.assignment_id in seen:
            continue
        seen.add(row.assignment_id)
        merged.append(row)
    return merged


def _transactions(parsed: dict) -> dict:
    data = (parsed or {}).get("data") or {}
    tx = data.get("transactions")
    if not isinstance(tx, dict):
        raise ValueError("GraphQL payload has no transactions object")
    return tx


def fetch_block_window(
    min_height: int,
    max_height: int,
    *,
    page_size: int = 100,
    max_pages: int = 50,
    endpoint: str = "https://arweave.net/graphql",
    post=post_graphql,
) -> WindowFetch:
    """Page a block window until `hasNextPage` is false.

    The next window must start at `max_height + 1` only after `closed` is true.
    Splitting on the last seen block plus one while a page remains open drops
    same-height rows.
    """
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be 1..100")
    if min_height > max_height:
        raise ValueError("min_height > max_height")
    pages: list[Page] = []
    rows: list[Assignment] = []
    cursor: str | None = None
    while True:
        if len(pages) >= max_pages:
            return WindowFetch(
                min_height, max_height, page_size, pages, rows, closed=False,
                error=f"page budget {max_pages} exhausted before hasNextPage=false",
            )
        variables = {
            "min": min_height,
            "max": max_height,
            "first": page_size,
            "after": cursor,
        }
        response = post(BLOCK_WINDOW_QUERY, variables, endpoint=endpoint)
        if not response.ok or response.parsed is None:
            pages.append(Page(variables, response, [], False, cursor, None))
            return WindowFetch(
                min_height, max_height, page_size, pages, rows, closed=False,
                error=response.error or f"http {response.http_status}",
            )
        try:
            tx = _transactions(response.parsed)
        except ValueError as exc:
            pages.append(Page(variables, response, [], False, cursor, None))
            return WindowFetch(
                min_height, max_height, page_size, pages, rows, closed=False, error=str(exc)
            )
        edges = tx.get("edges") or []
        has_next = bool((tx.get("pageInfo") or {}).get("hasNextPage"))
        cursor_out = edges[-1].get("cursor") if edges else None
        pages.append(Page(variables, response, edges, has_next, cursor, cursor_out))
        for edge in edges:
            rows.append(parse_assignment(edge))
        if not has_next:
            return WindowFetch(min_height, max_height, page_size, pages, rows, closed=True)
        if not edges or not cursor_out or cursor_out == cursor:
            return WindowFetch(
                min_height, max_height, page_size, pages, rows, closed=False,
                error="open page produced an empty edge list or a stalled cursor",
            )
        cursor = cursor_out


def fetch_exact_nonces(
    nonces: list[int],
    *,
    page_size: int = 100,
    max_pages: int = 10,
    endpoint: str = "https://arweave.net/graphql",
    post=post_graphql,
) -> WindowFetch:
    """Exact Nonce tag match. `nonces` must stay small; this is not a range query."""
    if not nonces:
        raise ValueError("nonces is empty")
    if len(nonces) > 20:
        raise ValueError("refusing to send more than 20 nonce values in one tag filter")
    pages: list[Page] = []
    rows: list[Assignment] = []
    cursor: str | None = None
    nonce_strings = [str(n) for n in nonces]
    while True:
        if len(pages) >= max_pages:
            return WindowFetch(
                -1, -1, page_size, pages, rows, closed=False,
                error=f"page budget {max_pages} exhausted",
            )
        variables = {"nonces": nonce_strings, "first": page_size, "after": cursor}
        response = post(EXACT_NONCE_QUERY, variables, endpoint=endpoint)
        if not response.ok or response.parsed is None:
            pages.append(Page(variables, response, [], False, cursor, None))
            return WindowFetch(
                -1, -1, page_size, pages, rows, closed=False,
                error=response.error or f"http {response.http_status}",
            )
        tx = _transactions(response.parsed)
        edges = tx.get("edges") or []
        has_next = bool((tx.get("pageInfo") or {}).get("hasNextPage"))
        cursor_out = edges[-1].get("cursor") if edges else None
        pages.append(Page(variables, response, edges, has_next, cursor, cursor_out))
        for edge in edges:
            rows.append(parse_assignment(edge))
        if not has_next:
            return WindowFetch(-1, -1, page_size, pages, merge_assignments(rows), closed=True)
        if not edges or not cursor_out or cursor_out == cursor:
            return WindowFetch(
                -1, -1, page_size, pages, rows, closed=False,
                error="open exact-nonce page stalled",
            )
        cursor = cursor_out


def fetch_transaction(tx_id: str, *, endpoint: str = "https://arweave.net/graphql", post=post_graphql) -> GqlResponse:
    return post(TX_QUERY, {"id": tx_id}, endpoint=endpoint)


def narrow_nonce_search(
    lo: int,
    hi: int,
    mid: int,
    frontier_height: int,
    min_nonce: int,
    max_nonce: int,
    target: int,
) -> tuple[int, int]:
    """Shrink an inclusion-height search after fully paging the frontier block.

    If every assignment at or before `mid` is still below `target`, the next
    lower bound is `mid + 1`. Stopping at `frontier_height + 1` loops when the
    blocks between the frontier and `mid` are empty.
    """
    if max_nonce < target:
        return max(lo, mid + 1), hi
    if min_nonce > target:
        return lo, min(hi, frontier_height - 1)
    return frontier_height, frontier_height


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

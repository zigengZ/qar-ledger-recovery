"""List binary bundles in a closed block window.

The gateway tag index returns no rows for these historical blocks, even when
the transaction tags include `Bundle-Format: binary`. This list pages every
transaction in the window and keeps that tag itself. A window is complete
only when `hasNextPage` is false. A transport failure stays `closed: false`.
"""

from __future__ import annotations

from recovery.gql import DEFAULT_ENDPOINT, post_graphql

BUNDLE_QUERY = """
query($min: Int!, $max: Int!, $first: Int!, $after: String) {
  transactions(block: {min: $min, max: $max}, first: $first, after: $after) {
    pageInfo { hasNextPage }
    edges {
      cursor
      node {
        id
        data { size }
        block { height }
        tags { name value }
      }
    }
  }
}
"""


def _tag_map(node: dict) -> dict:
    return {item.get("name"): item.get("value") for item in node.get("tags") or []}


def list_ao_bundles(
    min_height: int,
    max_height: int,
    *,
    page_size: int = 100,
    max_pages: int = 30,
    endpoint: str = DEFAULT_ENDPOINT,
    post=post_graphql,
) -> dict:
    """Page one block window. `bundles` may be partial when `closed` is false."""
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be 1..100")
    if min_height > max_height:
        raise ValueError("min_height > max_height")
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")
    bundles: list[dict] = []
    cursor = None
    pages = 0
    while True:
        if pages >= max_pages:
            return {
                "min_height": min_height,
                "max_height": max_height,
                "closed": False,
                "pages": pages,
                "bundles": bundles,
                "error": f"page budget {max_pages} exhausted before hasNextPage=false",
            }
        variables = {"min": min_height, "max": max_height, "first": page_size, "after": cursor}
        response = post(BUNDLE_QUERY, variables, endpoint=endpoint)
        pages += 1
        if not response.ok or response.parsed is None:
            return {
                "min_height": min_height,
                "max_height": max_height,
                "closed": False,
                "pages": pages,
                "bundles": bundles,
                "error": response.error or f"http {response.http_status}",
            }
        tx = ((response.parsed.get("data") or {}).get("transactions"))
        if not isinstance(tx, dict):
            return {
                "min_height": min_height,
                "max_height": max_height,
                "closed": False,
                "pages": pages,
                "bundles": bundles,
                "error": "GraphQL payload has no transactions object",
            }
        edges = tx.get("edges") or []
        for edge in edges:
            node = edge.get("node") or {}
            tags = _tag_map(node)
            if tags.get("Bundle-Format") != "binary":
                continue
            data = node.get("data") or {}
            block = node.get("block") or {}
            if not node.get("id") or block.get("height") is None or data.get("size") is None:
                return {
                    "min_height": min_height,
                    "max_height": max_height,
                    "closed": False,
                    "pages": pages,
                    "bundles": bundles,
                    "error": "binary bundle is missing id, height, or size",
                }
            bundles.append({
                "id": node["id"],
                "block": int(block["height"]),
                "size": int(data["size"]),
                "ao_bundler": tags.get("Bundler-App-Name") == "AO",
            })
        has_next = bool((tx.get("pageInfo") or {}).get("hasNextPage"))
        if not has_next:
            return {
                "min_height": min_height,
                "max_height": max_height,
                "closed": True,
                "pages": pages,
                "bundles": bundles,
                "error": None,
            }
        cursor_out = edges[-1].get("cursor") if edges else None
        if not cursor_out or cursor_out == cursor:
            return {
                "min_height": min_height,
                "max_height": max_height,
                "closed": False,
                "pages": pages,
                "bundles": bundles,
                "error": "open page produced an empty edge list or a stalled cursor",
            }
        cursor = cursor_out

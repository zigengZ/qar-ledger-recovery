"""Arweave GraphQL client used by the recovery index.

Retries are finite. A gateway 429, timeout, or GraphQL error is not an empty
result. Raw response bytes are returned to the caller so they can be flushed
before any cursor advances.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_ENDPOINT = "https://arweave.net/graphql"
USER_AGENT = "qar-ledger-recovery"


@dataclass(frozen=True)
class GqlResponse:
    endpoint: str
    http_status: int
    elapsed_ms: int
    attempt: int
    body: bytes
    parsed: dict | None
    error: str | None

    @property
    def ok(self) -> bool:
        return self.http_status == 200 and self.parsed is not None and not self.parsed.get("errors")


def _retry_delay(attempt: int, status: int, error: str | None) -> float:
    """429 and 5xx wait longer. The gateway's retry-after is a lower bound."""
    delay = float(min(8, 2 ** (attempt - 1)))
    if status == 0 or status == 429 or status >= 500:
        delay = float(min(30, 2 ** (attempt - 1)))
    if status == 429 and error:
        try:
            hinted = int(json.loads(error).get("retry-after") or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            hinted = 0
        if hinted > delay:
            delay = float(min(60, hinted))
    return delay


def post_graphql(
    query: str,
    variables: dict | None = None,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_s: float = 90,
    max_attempts: int = 3,
    sleep=time.sleep,
    opener=None,
) -> GqlResponse:
    """POST one GraphQL document. At most `max_attempts` tries, exponential backoff.

    The last response is returned even when every attempt failed. Callers decide
    whether that is `temporarily_unavailable`. This function never turns a
    transport failure into an empty transaction list.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    data = json.dumps(payload).encode("utf-8")
    last: GqlResponse | None = None
    urlopen = opener or urllib.request.urlopen
    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urlopen(request, timeout=timeout_s) as response:
                body = response.read()
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
        except Exception as exc:  # noqa: BLE001 — recorded, not swallowed as empty
            elapsed = int((time.monotonic() - started) * 1000)
            last = GqlResponse(
                endpoint=endpoint,
                http_status=0,
                elapsed_ms=elapsed,
                attempt=attempt,
                body=b"",
                parsed=None,
                error=f"{type(exc).__name__}: {exc}",
            )
            if attempt < max_attempts:
                sleep(_retry_delay(attempt, last.http_status, last.error))
            continue
        elapsed = int((time.monotonic() - started) * 1000)
        parsed = None
        error = None
        if status == 200:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError as exc:
                error = f"JSONDecodeError: {exc}"
            if parsed is not None and parsed.get("errors"):
                error = json.dumps(parsed["errors"])[:500]
        else:
            error = body[:300].decode("utf-8", errors="replace")
        last = GqlResponse(
            endpoint=endpoint,
            http_status=status,
            elapsed_ms=elapsed,
            attempt=attempt,
            body=body,
            parsed=parsed,
            error=error,
        )
        if last.ok:
            return last
        if attempt < max_attempts:
            sleep(_retry_delay(attempt, status, error))
    assert last is not None
    return last

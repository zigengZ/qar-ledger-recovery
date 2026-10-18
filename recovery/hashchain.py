"""Assignment hash-chain candidate from permaweb/ao SU `gen_hash_chain`.

Source read: permaweb/ao commit 7ba5df7b2e3c8f7e891481b4fe1b0489647cf607
`servers/su/src/domain/core/scheduler.rs` function `gen_hash_chain`.
That tree is current main, not the 2024 scheduler that wrote these assignments.
A chain matches only when every consecutive sample link matches. A mismatch
is recorded and is not treated as verified.
"""

from __future__ import annotations

import base64
import hashlib

from recovery.assignments import Assignment


def b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def gen_hash_chain(previous_or_seed: str, previous_assignment_id: str | None = None) -> str:
    """SHA-256 over the previous assignment id bytes, then the previous chain bytes.

    When `previous_assignment_id` is omitted, the digest is only the seed bytes.
    The SU uses that form for the first nonce when the process id is the seed.
    """
    previous = b64url_decode(previous_or_seed)
    if len(previous) != 32:
        raise ValueError(f"seed/hash-chain is {len(previous)} bytes, expected 32")
    digest = hashlib.sha256()
    if previous_assignment_id is not None:
        identifier = b64url_decode(previous_assignment_id)
        if len(identifier) != 32:
            raise ValueError(f"assignment id is {len(identifier)} bytes, expected 32")
        digest.update(identifier)
    digest.update(previous)
    return b64url_encode(digest.digest())


def link_matches(previous: Assignment, current: Assignment) -> bool:
    expected = gen_hash_chain(previous.hash_chain, previous.assignment_id)
    return expected == current.hash_chain


def check_links(rows: list[Assignment]) -> dict:
    """Check each nonce N against nonce N-1 when both are present. Gaps are skipped links."""
    ordered = sorted(rows, key=lambda row: (row.nonce, row.assignment_id))
    by_nonce: dict[int, Assignment] = {}
    conflicts: list[int] = []
    for row in ordered:
        if row.nonce in by_nonce and by_nonce[row.nonce].assignment_id != row.assignment_id:
            conflicts.append(row.nonce)
            continue
        by_nonce.setdefault(row.nonce, row)
    checked = 0
    matched = 0
    mismatches: list[dict] = []
    skipped_gaps: list[int] = []
    nonces = sorted(by_nonce)
    for nonce in nonces:
        previous_nonce = nonce - 1
        if previous_nonce not in by_nonce:
            if nonces and nonce != nonces[0]:
                skipped_gaps.append(nonce)
            continue
        checked += 1
        if link_matches(by_nonce[previous_nonce], by_nonce[nonce]):
            matched += 1
        else:
            mismatches.append({
                "nonce": nonce,
                "previous_nonce": previous_nonce,
                "assignment_id": by_nonce[nonce].assignment_id,
                "actual_hash_chain": by_nonce[nonce].hash_chain,
                "predicted_hash_chain": gen_hash_chain(
                    by_nonce[previous_nonce].hash_chain,
                    by_nonce[previous_nonce].assignment_id,
                ),
            })
    return {
        "algorithm": "sha256(previous_assignment_id_bytes || previous_hash_chain_bytes), base64url",
        "source": "permaweb/ao 7ba5df7b2e3c8f7e891481b4fe1b0489647cf607 servers/su/src/domain/core/scheduler.rs gen_hash_chain",
        "historical_scheduler_verified": False,
        "links_checked": checked,
        "links_matched": matched,
        "links_mismatched": len(mismatches),
        "mismatch_sample": mismatches[:10],
        "skipped_because_previous_nonce_absent": skipped_gaps,
        "nonce_conflicts": conflicts,
        "verified": checked > 0 and not mismatches and not conflicts,
    }

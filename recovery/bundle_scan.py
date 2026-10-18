"""Search raw ANS-104 bundle bytes for assignment nonce tags.

GraphQL can miss a data item that is still inside a bundle. This scanner reads
the bundle payload once and looks for the process id and for 2-byte-length
Nonce tags. A tx counts as searched only when the byte count matches the
gateway Content-Length.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass

PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"
PROCESS_BYTES = PROCESS_ID.encode("ascii")
# Process, Epoch, then Nonce. The process id ends about 52 bytes before "Nonce".
PROCESS_NONCE_WINDOW = 80


def nonce_needle(nonce: int) -> bytes:
    """ANS-104 tag as stored in these bundles.

    Samples from block 1543163 show the name immediately followed by one byte
    whose value is twice the digit count, then the ASCII digits. 5749 is
    ``Nonce\\x085749`` and 1743125 is ``Nonce\\x0e1743125``.
    """
    text = str(nonce).encode("ascii")
    if not text.isdigit() or len(text) > 127:
        raise ValueError(f"not a nonce tag value: {nonce}")
    return b"Nonce" + bytes([2 * len(text)]) + text


@dataclass(frozen=True)
class BundleHit:
    nonce: int | None
    process_offset: int | None
    nonce_offset: int | None
    nonce_text: str | None


def find_plaintext_nonces(data: bytes, wanted: set[int]) -> list[BundleHit]:
    """Return Nonce tags whose value is in `wanted`.

    In these bundles the name is followed by one byte, twice the digit count,
    then the ASCII digits. Pair a hit with `find_process_offsets` before
    treating it as this process.
    """
    hits: list[BundleHit] = []
    for nonce in sorted(wanted):
        needle = nonce_needle(nonce)
        start = 0
        while True:
            index = data.find(needle, start)
            if index < 0:
                break
            hits.append(BundleHit(nonce, None, index, str(nonce)))
            start = index + 1
    hits.sort(key=lambda hit: hit.nonce_offset or 0)
    return hits


def find_process_offsets(data: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        index = data.find(PROCESS_BYTES, start)
        if index < 0:
            return offsets
        offsets.append(index)
        start = index + 1


def paired_nonce(data: bytes, nonce_offset: int, *, window: int = PROCESS_NONCE_WINDOW) -> bool:
    """True when this process id sits in the tag list just before the nonce."""
    start = nonce_offset - window
    if start < 0:
        start = 0
    return PROCESS_BYTES in data[start:nonce_offset]


def _collect_hits(data: bytes, base: int, wanted: set[int], seen_process: set[int], seen_nonce: set[int], process_offsets: list[int], nonce_hits: list[dict]) -> None:
    for offset in find_process_offsets(data):
        absolute = base + offset
        if absolute not in seen_process:
            seen_process.add(absolute)
            process_offsets.append(absolute)
    for hit in find_plaintext_nonces(data, wanted):
        local = hit.nonce_offset or 0
        if not paired_nonce(data, local):
            continue
        absolute = base + local
        if absolute not in seen_nonce:
            seen_nonce.add(absolute)
            nonce_hits.append({"nonce": hit.nonce, "offset": absolute})


def scan_stream(chunks, wanted: set[int], overlap: int = PROCESS_NONCE_WINDOW) -> dict:
    """Scan a sequence of bytes chunks.

    A nonce tag counts only when this process id appears within
    `PROCESS_NONCE_WINDOW` bytes before it. The same digits on another
    process are not a hit. `overlap` must cover that window.
    """
    if overlap < PROCESS_NONCE_WINDOW:
        raise ValueError("overlap shorter than the process/nonce window")
    window = b""
    total = 0
    process_offsets: list[int] = []
    nonce_hits: list[dict] = []
    seen_process: set[int] = set()
    seen_nonce: set[int] = set()
    for chunk in chunks:
        if not isinstance(chunk, (bytes, bytearray)):
            raise TypeError("chunk must be bytes")
        data = window + bytes(chunk)
        base = total - len(window)
        _collect_hits(data, base, wanted, seen_process, seen_nonce, process_offsets, nonce_hits)
        total += len(chunk)
        window = data[-overlap:]
    return {
        "bytes": total,
        "gaps": [],
        "process_hit_count": len(process_offsets),
        "process_offsets": process_offsets,
        "nonce_hits": nonce_hits,
    }


def scan_indexed(pieces, wanted: set[int], overlap: int = PROCESS_NONCE_WINDOW) -> dict:
    """Scan `(file_offset, bytes)` pieces. A hole between pieces is a gap.

    Offsets stay file offsets. The overlap window does not cross a gap, and
    a gap is not scanned as if it were empty data.
    """
    if overlap < PROCESS_NONCE_WINDOW:
        raise ValueError("overlap shorter than the process/nonce window")
    total = 0
    process_offsets: list[int] = []
    nonce_hits: list[dict] = []
    seen_process: set[int] = set()
    seen_nonce: set[int] = set()
    gaps: list[list[int]] = []
    tail = b""
    tail_at: int | None = None
    expected: int | None = None
    for file_off, chunk in pieces:
        if not isinstance(chunk, (bytes, bytearray)):
            raise TypeError("chunk must be bytes")
        file_off = int(file_off)
        chunk = bytes(chunk)
        if expected is not None and file_off > expected:
            gaps.append([expected, file_off])
            tail = b""
            tail_at = None
        elif expected is not None and file_off < expected:
            raise ValueError(f"piece at {file_off} overlaps the previous piece")
        if tail and tail_at is not None and tail_at + len(tail) == file_off:
            data = tail + chunk
            base = tail_at
        else:
            data = chunk
            base = file_off
        _collect_hits(data, base, wanted, seen_process, seen_nonce, process_offsets, nonce_hits)
        total += len(chunk)
        expected = file_off + len(chunk)
        tail = data[-overlap:]
        tail_at = base + len(data) - len(tail)
    return {
        "bytes": total,
        "gaps": gaps,
        "process_hit_count": len(process_offsets),
        "process_offsets": process_offsets,
        "nonce_hits": nonce_hits,
    }


def scan_tx(tx_id: str, wanted: set[int], *, expected_size: int | None = None, attempts: int = 3) -> dict:
    """Download one raw payload and search it. A short read is not a closed search."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            holder = {"status": None, "expected": expected_size}

            def pulling():
                for item_status, length, chunk in iter_raw(tx_id):
                    holder["status"] = item_status
                    if holder["expected"] is None:
                        holder["expected"] = length
                    yield chunk

            report = scan_stream(pulling(), wanted)
            closed = holder["expected"] is not None and report["bytes"] == holder["expected"]
            return {
                "tx_id": tx_id,
                "attempt": attempt,
                "http_status": holder["status"],
                "expected_bytes": holder["expected"],
                "bytes": report["bytes"],
                "closed": closed,
                "process_hit_count": report["process_hit_count"],
                "process_offsets": report["process_offsets"][:20],
                "nonce_hits": report["nonce_hits"],
                "error": None if closed else "byte count did not match content-length",
            }
        except Exception as exc:  # noqa: BLE001 — recorded, retried, not treated as empty
            last_error = f"{type(exc).__name__}: {exc}"
    return {
        "tx_id": tx_id,
        "attempt": attempts,
        "http_status": None,
        "expected_bytes": expected_size,
        "bytes": 0,
        "closed": False,
        "process_hit_count": 0,
        "process_offsets": [],
        "nonce_hits": [],
        "error": last_error,
    }


def iter_raw(tx_id: str, *, timeout_s: float = 180, chunk_size: int = 1 << 20):
    request = urllib.request.Request(
        f"https://arweave.net/raw/{tx_id}",
        headers={"User-Agent": "qar-ledger-recovery", "Accept": "application/octet-stream"},
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        length = response.headers.get("content-length")
        expected = int(length) if length else None
        status = int(response.status)
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            yield status, expected, chunk

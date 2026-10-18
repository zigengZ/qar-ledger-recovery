"""Walk Arweave data chunks in order and search them with the bundle scanner.

`/raw/{id}` stalls on multi-gigabyte transactions. `/tx/{id}/offset` plus
`/chunk/{offset}` returns unpacked 256KiB chunks. A chunk is accepted only when
`packing` is `unpacked`.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from recovery.bundle_scan import scan_indexed

CHUNK_SPAN = 262144


def decode_chunk_body(payload: dict) -> bytes:
    if payload.get("packing") not in (None, "unpacked"):
        raise ValueError(f"packed chunk is not raw data: {payload.get('packing')}")
    raw = base64.urlsafe_b64decode(payload["chunk"] + "===")
    declared = int(payload["chunk_size"])
    if len(raw) != declared:
        raise ValueError(f"chunk_size {declared} but decoded {len(raw)}")
    return raw


def slice_chunk(raw: bytes, chunk_start: int, cursor: int, end: int) -> bytes:
    """Bytes of this chunk that belong to the transaction at or after `cursor`."""
    if chunk_start > cursor:
        raise ValueError(f"gap between {cursor} and chunk start {chunk_start}")
    if cursor > end:
        raise ValueError("cursor past end")
    skip = cursor - chunk_start
    take = end - cursor + 1
    return raw[skip:skip + take]


def fetch_json(
    url: str,
    *,
    timeout_s: float = 40,
    attempts: int = 3,
    sleep=time.sleep,
    opener=None,
) -> dict:
    """GET one JSON document. At most `attempts` tries, with exponential backoff.

    The last error is raised. A failed GET is never turned into an empty body.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    urlopen = opener or urllib.request.urlopen
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "qar-ledger-recovery"})
            with urlopen(request, timeout=timeout_s) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            # HTTPError is the response body. Leaving it open sticks the socket in CLOSE-WAIT.
            last = exc
            try:
                exc.close()
            except Exception:
                pass
            if attempt + 1 < attempts:
                sleep(2 ** attempt)
        except Exception as exc:  # noqa: BLE001 — finite retries, then the caller records the error
            last = exc
            if attempt + 1 < attempts:
                sleep(2 ** attempt)
    raise RuntimeError(f"{url} failed: {last}")


class TxBytes:
    """Random-access reader for one unpacked transaction.

    `read(file_start, file_end)` seeks to that file offset. It does not walk
    from byte 0. Chunk bodies are cached so a later read of an overlapping
    range does not fetch them again.
    """

    def __init__(self, tx_id: str, *, fetch=fetch_json):
        meta = fetch(f"https://arweave.net/tx/{tx_id}/offset")
        self.tx_id = tx_id
        self.end = int(meta["offset"])
        self.size = int(meta["size"])
        self.weave_start = self.end - self.size + 1
        self._fetch = fetch
        self._chunks: dict[int, bytes] = {}

    def _chunk(self, cursor: int) -> tuple[bytes, int]:
        for chunk_start, raw in self._chunks.items():
            if chunk_start <= cursor < chunk_start + len(raw):
                return raw, chunk_start
        payload = self._fetch(f"https://arweave.net/chunk/{cursor}")
        raw = decode_chunk_body(payload)
        absolute_end = int(payload["absolute_end_offset"])
        chunk_start = absolute_end - len(raw) + 1
        self._chunks[chunk_start] = raw
        return raw, chunk_start

    def read(self, file_start: int, file_end: int) -> bytes:
        if file_start < 0 or file_end < file_start or file_end > self.size:
            raise ValueError(f"range {file_start}:{file_end} outside 0..{self.size}")
        if file_start == file_end:
            return b""
        cursor = self.weave_start + file_start
        need = file_end - file_start
        parts: list[bytes] = []
        while need > 0:
            raw, chunk_start = self._chunk(cursor)
            piece = slice_chunk(raw, chunk_start, cursor, self.end)
            if not piece:
                raise ValueError(f"empty chunk at {cursor}")
            parts.append(piece[:need])
            need -= len(parts[-1])
            cursor += len(piece)
        return b"".join(parts)

    def iter_pieces(self, *, probe_step: int = CHUNK_SPAN, max_probes: int = 32):
        """Yield `(file_offset, bytes)` in order.

        A chunk URL that returns 404 is a hole. The reader probes forward by
        `probe_step` and continues at the next chunk the gateway does have.
        The skipped file range is recorded on `self.gaps` and is not returned
        as bytes. `read` still fails on a 404; it does not skip.
        """
        if probe_step < 1 or max_probes < 1:
            raise ValueError("probe_step and max_probes must be >= 1")
        self.gaps: list[list[int]] = []
        cursor = self.weave_start
        while cursor <= self.end:
            try:
                raw, chunk_start = self._chunk(cursor)
            except RuntimeError as exc:
                if "404" not in str(exc):
                    raise
                found = None
                probe = cursor
                for _ in range(max_probes):
                    probe += probe_step
                    if probe > self.end:
                        break
                    try:
                        raw, chunk_start = self._chunk(probe)
                    except RuntimeError as exc2:
                        if "404" not in str(exc2):
                            raise
                        continue
                    if chunk_start + len(raw) <= cursor:
                        continue
                    found = (raw, chunk_start)
                    break
                if found is None:
                    self.gaps.append([cursor - self.weave_start, self.size])
                    return
                raw, chunk_start = found
                if chunk_start > cursor:
                    self.gaps.append([cursor - self.weave_start, chunk_start - self.weave_start])
                    cursor = chunk_start
            if chunk_start > cursor:
                self.gaps.append([cursor - self.weave_start, chunk_start - self.weave_start])
                cursor = chunk_start
            piece = slice_chunk(raw, chunk_start, cursor, self.end)
            if not piece:
                raise ValueError(f"empty chunk at {cursor}")
            yield cursor - self.weave_start, piece
            cursor += len(piece)


def read_tx_range(tx_id: str, file_start: int, file_end: int, *, fetch=fetch_json) -> bytes:
    """Return file bytes `[file_start, file_end)` without walking earlier chunks."""
    return TxBytes(tx_id, fetch=fetch).read(file_start, file_end)


def iter_unpacked_chunks(tx_id: str):
    reader = TxBytes(tx_id)
    cursor = reader.weave_start
    while cursor <= reader.end:
        raw, chunk_start = reader._chunk(cursor)
        piece = slice_chunk(raw, chunk_start, cursor, reader.end)
        if not piece:
            raise ValueError(f"empty chunk at {cursor}")
        yield cursor, piece, reader.weave_start, reader.end
        cursor += len(piece)


def scan_tx_chunks(tx_id: str, wanted: set[int], *, fetch=fetch_json, probe_step: int = CHUNK_SPAN) -> dict:
    """Search one transaction. A 404 chunk is a gap, not an empty result.

    Nonce hits found in readable chunks are kept. `closed` is true only when
    every file byte was read.
    """
    chunks = []
    reader = None
    try:
        reader = TxBytes(tx_id, fetch=fetch)

        def generate():
            for file_off, raw in reader.iter_pieces(probe_step=probe_step):
                chunks.append(len(raw))
                if len(chunks) % 200 == 0:
                    print(f"  {tx_id[:8]} chunks {len(chunks)} bytes {sum(chunks)}", flush=True)
                yield file_off, raw

        report = scan_indexed(generate(), wanted)
        gaps = report["gaps"]
        # iter_pieces records the same holes, including a tail the piece list
        # cannot see once iteration stops.
        for gap in getattr(reader, "gaps", []):
            if gap not in gaps:
                gaps.append(gap)
        closed = not gaps and report["bytes"] == reader.size
        if closed:
            error = None
        elif gaps:
            error = "unreadable chunk gap"
        else:
            error = "byte count did not match tx size"
        return {
            "tx_id": tx_id,
            "bytes": report["bytes"],
            "expected_bytes": reader.size,
            "closed": closed,
            "gaps": gaps,
            "chunks": len(chunks),
            "process_hit_count": report["process_hit_count"],
            "process_offsets": report["process_offsets"][:20],
            "nonce_hits": report["nonce_hits"],
            "error": error,
        }
    except Exception as exc:  # noqa: BLE001 — one bundle must not erase the others
        return {
            "tx_id": tx_id,
            "bytes": sum(chunks),
            "expected_bytes": None if reader is None else reader.size,
            "closed": False,
            "gaps": list(getattr(reader, "gaps", []) or []),
            "chunks": len(chunks),
            "process_hit_count": 0,
            "process_offsets": [],
            "nonce_hits": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

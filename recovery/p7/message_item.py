"""Pull one ANS-104 message out of a nested bundle.

AO puts the assignment and its message in a small inner bundle. The message id
is the raw 32-byte id in that inner header, and it is also sha256 of the
message signature. A byte range the reader did not return stays missing.
"""

from __future__ import annotations

import base64

from recovery.ans104 import SIG_LEN, b64url, parse_bundle_header, signature_id
from recovery.arweave_sig import b64url_encode, owner_address


def raw_id(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    raw = base64.urlsafe_b64decode(text + pad)
    if len(raw) != 32:
        raise ValueError(f"id {text} is {len(raw)} bytes")
    return raw


def read_avro_long(buf: bytes, index: int) -> tuple[int, int]:
    shift = 0
    zigzag = 0
    while True:
        if index >= len(buf):
            raise ValueError("truncated avro long")
        byte = buf[index]
        index += 1
        zigzag |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            break
        shift += 7
        if shift > 63:
            raise ValueError("avro long is too wide")
    value = (zigzag >> 1) ^ -(zigzag & 1)
    return value, index


def read_avro_tags(buf: bytes) -> list[dict[str, str]]:
    """Inverse of recovery.arweave_sig.serialize_ans104_tags."""
    tags: list[dict[str, str]] = []
    index = 0
    while index < len(buf):
        count, index = read_avro_long(buf, index)
        if count == 0:
            break
        if count < 0:
            raise ValueError("negative tag group")
        for _ in range(count):
            name_len, index = read_avro_long(buf, index)
            name = buf[index:index + name_len]
            index += name_len
            value_len, index = read_avro_long(buf, index)
            value = buf[index:index + value_len]
            index += value_len
            if len(name) != name_len or len(value) != value_len:
                raise ValueError("truncated avro tag")
            tags.append({"name": name.decode("utf-8"), "value": value.decode("utf-8")})
    return tags


def parse_data_item(raw: bytes) -> dict:
    """Split one data item into signature, owner address, tags, and data."""
    if len(raw) < 2:
        raise ValueError("data item is shorter than the signature type")
    sigtype = int.from_bytes(raw[:2], "little")
    if sigtype not in SIG_LEN:
        raise ValueError(f"unsupported signature type {sigtype}")
    sig_len, owner_len = SIG_LEN[sigtype]
    index = 2
    signature = raw[index:index + sig_len]
    index += sig_len
    owner = raw[index:index + owner_len]
    index += owner_len
    if index >= len(raw):
        raise ValueError("data item ends before target")
    if raw[index] == 1:
        target = raw[index + 1:index + 33]
        index += 33
    elif raw[index] == 0:
        target = b""
        index += 1
    else:
        raise ValueError(f"bad target flag {raw[index]}")
    if raw[index] == 1:
        anchor = raw[index + 1:index + 33]
        index += 33
    elif raw[index] == 0:
        anchor = b""
        index += 1
    else:
        raise ValueError(f"bad anchor flag {raw[index]}")
    tag_count = int.from_bytes(raw[index:index + 8], "little")
    index += 8
    nbytes = int.from_bytes(raw[index:index + 8], "little")
    index += 8
    tag_bytes = raw[index:index + nbytes]
    if len(tag_bytes) != nbytes:
        raise ValueError("truncated tag bytes")
    index += nbytes
    data = raw[index:]
    tags = read_avro_tags(tag_bytes)
    if tag_count != len(tags):
        raise ValueError(f"tag count {tag_count} but avro parsed {len(tags)}")
    return {
        "id": signature_id(raw),
        "signature": b64url_encode(signature),
        "owner": owner_address(owner),
        "target": b64url_encode(target) if target else "",
        "anchor": b64url_encode(anchor) if anchor else "",
        "tags": tags,
        "data": data,
    }


def header_around_id(window: bytes, id_index: int) -> tuple[int, list[tuple[int, int, str]]] | None:
    """Find a small bundle header in `window` whose item id starts at `id_index`."""
    if id_index < 0 or id_index + 32 > len(window):
        return None
    raw = window[id_index:id_index + 32]
    for prior in range(6):
        header_start = id_index - 64 - prior * 64
        if header_start < 0:
            continue
        count = int.from_bytes(window[header_start:header_start + 32], "little")
        if not 1 <= count <= 8 or prior >= count:
            continue
        header_len = 32 + 64 * count
        if header_start + header_len > len(window):
            continue
        try:
            items = parse_bundle_header(window[header_start:header_start + header_len])
        except ValueError:
            continue
        if prior >= len(items) or items[prior][2] != b64url(raw):
            continue
        if any(size <= 0 or size > 5_000_000 for _, size, _ in items):
            continue
        return header_start, items
    return None


def scan_reader(reader, wanted: dict[bytes, str]) -> dict:
    """Search `reader` for wanted raw ids.

    `wanted` maps raw id bytes to the base64url message id. The return value
    has `found` and `missing`. Readable gaps are listed and are not filled.
    """
    found: dict[str, dict] = {}
    seen: set[int] = set()
    carry = b""
    for file_off, piece in reader.iter_pieces():
        if not wanted or len(found) == len(wanted):
            break
        buf = carry + piece
        base = file_off - len(carry)
        for raw, message_id in list(wanted.items()):
            if message_id in found:
                continue
            start = 0
            while True:
                idx = buf.find(raw, start)
                if idx < 0:
                    break
                id_at = base + idx
                start = idx + 1
                if id_at in seen or id_at < 0:
                    continue
                seen.add(id_at)
                window_start = max(0, id_at - 512)
                window_end = min(reader.size, id_at + 32)
                window = reader.read(window_start, window_end)
                located = header_around_id(window, id_at - window_start)
                if located is None:
                    continue
                header_start, items = located
                header_at = window_start + header_start
                header_len = 32 + 64 * len(items)
                total = header_len + sum(size for _, size, _ in items)
                if header_at + total > reader.size:
                    continue
                bundle = reader.read(header_at, header_at + total)
                for data_offset, size, item_id in items:
                    if item_id != message_id:
                        continue
                    item = bundle[data_offset:data_offset + size]
                    if len(item) != size:
                        continue
                    parsed = parse_data_item(item)
                    if parsed["id"] != message_id:
                        continue
                    found[message_id] = parsed
                    break
        carry = buf[-31:]
    gaps = list(getattr(reader, "gaps", []) or [])
    missing = [message_id for raw, message_id in wanted.items() if message_id not in found]
    return {"found": found, "missing": missing, "gaps": gaps}

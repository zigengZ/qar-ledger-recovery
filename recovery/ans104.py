"""Parse the ANS-104 bundles that carry AO assignments.

Indexed assignments are not the top-level bundle entry. Each top-level entry
is itself a two-item bundle: the signed assignment, then its message. The
assignment id is sha256 of that inner signature, which is also the id in the
inner header.

Tag lengths inside those assignment items are one byte equal to twice the
UTF-8 length. The bundle header is a 32-byte item count, then 32-byte size
and 32-byte id pairs.
"""

from __future__ import annotations

import base64
import hashlib

from recovery.bundle_scan import PROCESS_ID

# signature type -> (signature length, owner length)
SIG_LEN = {1: (512, 512), 2: (64, 32), 3: (65, 65), 4: (64, 32)}


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_bundle_header(header: bytes) -> list[tuple[int, int, str]]:
    """Return (data_offset, size, assignment_id) for every item.

    `data_offset` is relative to the start of the bundle payload.
    """
    if len(header) < 32:
        raise ValueError("header shorter than the count field")
    count = int.from_bytes(header[:32], "little")
    need = 32 + 64 * count
    if len(header) < need:
        raise ValueError(f"header has {len(header)} bytes, {count} items need {need}")
    items: list[tuple[int, int, str]] = []
    data_offset = need
    for index in range(count):
        entry = 32 + 64 * index
        size = int.from_bytes(header[entry:entry + 32], "little")
        item_id = b64url(header[entry + 32:entry + 64])
        if size < 0:
            raise ValueError("negative item size")
        items.append((data_offset, size, item_id))
        data_offset += size
    return items


def read_doubled_tag(buf: bytes, index: int) -> tuple[str, str, int]:
    """Read one tag whose length bytes are twice the byte length."""
    if index >= len(buf):
        raise ValueError("tag starts past the buffer")
    name_units = buf[index]
    if name_units % 2:
        raise ValueError(f"odd name length byte {name_units}")
    name_len = name_units // 2
    index += 1
    name = buf[index:index + name_len]
    if len(name) != name_len:
        raise ValueError("truncated tag name")
    index += name_len
    value_units = buf[index]
    if value_units % 2:
        raise ValueError(f"odd value length byte {value_units}")
    value_len = value_units // 2
    index += 1
    value = buf[index:index + value_len]
    if len(value) != value_len:
        raise ValueError("truncated tag value")
    index += value_len
    return name.decode("utf-8"), value.decode("utf-8"), index


def assignment_tags(buf: bytes) -> dict[str, str] | None:
    """Parse the tag list that starts at the Process tag, if this buffer has one."""
    marker = b"\x0eProcess"
    start = buf.find(marker)
    if start < 0:
        return None
    tags: dict[str, str] = {}
    index = start
    # Ten tags are present on the recovered sample. Stop if the framing breaks.
    for _ in range(16):
        try:
            name, value, index = read_doubled_tag(buf, index)
        except (ValueError, UnicodeDecodeError):
            break
        tags[name] = value
        if name == "Message":
            break
    if tags.get("Process") != PROCESS_ID or "Nonce" not in tags:
        return None
    return tags


def data_field(raw: bytes) -> bytes:
    """Payload of one ANS-104 data item. Tag bytes are skipped, not decoded."""
    sigtype = int.from_bytes(raw[:2], "little")
    if sigtype not in SIG_LEN:
        raise ValueError(f"unsupported signature type {sigtype}")
    sig_len, owner_len = SIG_LEN[sigtype]
    index = 2 + sig_len + owner_len
    index += 33 if raw[index] == 1 else 1
    index += 33 if raw[index] == 1 else 1
    index += 8  # tag count
    nbytes = int.from_bytes(raw[index:index + 8], "little")
    index += 8 + nbytes
    return raw[index:]


def signature_id(raw: bytes) -> str:
    sigtype = int.from_bytes(raw[:2], "little")
    sig_len = SIG_LEN[sigtype][0]
    return b64url(hashlib.sha256(raw[2:2 + sig_len]).digest())


def nested_assignments(bundle_data: bytes) -> list[dict]:
    """Assignment items inside a bundle payload.

    The returned id is the inner header id. It must equal sha256(signature).
    """
    items = parse_bundle_header(bundle_data)
    found = []
    for data_offset, size, item_id in items:
        child = bundle_data[data_offset:data_offset + size]
        if len(child) != size:
            raise ValueError(f"short child at {data_offset}")
        tags = assignment_tags(child)
        if not tags or tags.get("Type") != "Assignment":
            continue
        if signature_id(child) != item_id:
            raise ValueError(f"signature id does not match header id {item_id}")
        if not tags["Nonce"].isdigit():
            raise ValueError(f"nonce is not an integer string: {tags['Nonce']}")
        found.append({
            "assignment_id": item_id,
            "nonce": int(tags["Nonce"]),
            "epoch": tags["Epoch"],
            "message_id": tags["Message"],
            "timestamp_ms": tags["Timestamp"],
            "hash_chain": tags["Hash-Chain"],
            "assignment_block_height": tags["Block-Height"],
            "process": tags["Process"],
        })
    return found


def item_for_offset(items: list[tuple[int, int, str]], offset: int) -> tuple[int, int, str] | None:
    for data_offset, size, item_id in items:
        if data_offset <= offset < data_offset + size:
            return data_offset, size, item_id
    return None

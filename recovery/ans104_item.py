"""Build and check an ANS-104 data item from indexed fields.

The binary layout and the Avro tag bytes follow Irys arbundles
`DataItem` / `serializeTags`. The signed payload is arweave-js `deepHash`
using SHA-384, which is what verified a 2026 message from this process.
The RSA-PSS check is SHA-256. The salt length is taken from the signature.

The id of the item is sha256 of the signature bytes, base64url, with no padding.
"""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from recovery.hashchain import b64url_encode


def encode_long(value: int) -> bytes:
    """Avro zigzag long, the same arithmetic arbundles uses for short tags."""
    if value >= 0:
        folded = value << 1
    else:
        folded = ((~value) << 1) | 1
    out = bytearray()
    while True:
        byte = folded & 0x7F
        folded >>= 7
        if folded:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def serialize_tags(tags: list[dict[str, str]]) -> bytes:
    """Avro array of {name, value} records. An empty list is zero bytes."""
    if not tags:
        return b""
    parts = [encode_long(len(tags))]
    for tag in tags:
        name = tag["name"].encode("utf-8")
        value = tag["value"].encode("utf-8")
        parts.append(encode_long(len(name)))
        parts.append(name)
        parts.append(encode_long(len(value)))
        parts.append(value)
    parts.append(encode_long(0))
    return b"".join(parts)


def deep_hash(data: bytes | list) -> bytes:
    """arweave-js deepHash. The hash inside the tree is SHA-384."""
    if isinstance(data, list):
        tag = b"list" + str(len(data)).encode("utf-8")
        acc = hashlib.sha384(tag).digest()
        for item in data:
            acc = hashlib.sha384(acc + deep_hash(item)).digest()
        return acc
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"deepHash chunk must be bytes or a list, got {type(data).__name__}")
    raw = bytes(data)
    tag = b"blob" + str(len(raw)).encode("utf-8")
    return hashlib.sha384(hashlib.sha384(tag).digest() + hashlib.sha384(raw).digest()).digest()


def build_data_item(
    signature: bytes,
    owner: bytes,
    target: bytes,
    anchor: bytes,
    tags: list[dict[str, str]],
    data: bytes,
) -> bytes:
    """RSA-4096 ANS-104 item. Target and anchor are raw bytes, or empty."""
    if len(signature) != 512 or len(owner) != 512:
        raise ValueError(
            f"RSA-4096 item needs 512-byte signature and owner, got {len(signature)} and {len(owner)}"
        )
    if len(target) not in (0, 32) or len(anchor) not in (0, 32):
        raise ValueError(f"target is {len(target)} bytes and anchor is {len(anchor)} bytes")
    raw_tags = serialize_tags(tags)
    out = bytearray()
    out += (1).to_bytes(2, "little")
    out += signature
    out += owner
    out += (b"\x01" + target) if target else b"\x00"
    out += (b"\x01" + anchor) if anchor else b"\x00"
    out += len(tags).to_bytes(8, "little")
    out += len(raw_tags).to_bytes(8, "little")
    out += raw_tags
    out += data
    return bytes(out)


def signature_id(signature: bytes) -> str:
    return b64url_encode(hashlib.sha256(signature).digest())


def _split_optional(raw: bytes, index: int) -> tuple[bytes, int] | None:
    if index >= len(raw):
        return None
    if raw[index] == 0:
        return b"", index + 1
    if raw[index] == 1 and index + 33 <= len(raw):
        return raw[index + 1:index + 33], index + 33
    return None


def signed_payload(raw: bytes) -> bytes | None:
    """Return the deep hash a type-1 item should have been signed, or None."""
    if len(raw) < 2 + 512 + 512 + 2 + 16:
        return None
    if int.from_bytes(raw[:2], "little") != 1:
        return None
    owner = raw[514:1026]
    index = 1026
    target_pair = _split_optional(raw, index)
    if target_pair is None:
        return None
    target, index = target_pair
    anchor_pair = _split_optional(raw, index)
    if anchor_pair is None:
        return None
    anchor, index = anchor_pair
    if index + 16 > len(raw):
        return None
    tag_len = int.from_bytes(raw[index + 8:index + 16], "little")
    tag_start = index + 16
    tag_end = tag_start + tag_len
    if tag_end > len(raw):
        return None
    return deep_hash([
        b"dataitem",
        b"1",
        b"1",
        owner,
        target,
        anchor,
        raw[tag_start:tag_end],
        raw[tag_end:],
    ])


def signature_valid(raw: bytes) -> bool:
    """True when the type-1 signature matches the item bytes."""
    payload = signed_payload(raw)
    if payload is None or len(raw) < 1026:
        return False
    signature = raw[2:514]
    owner = raw[514:1026]
    try:
        public = rsa.RSAPublicNumbers(65537, int.from_bytes(owner, "big")).public_key()
        public.verify(
            signature,
            payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.AUTO),
            hashes.SHA256(),
        )
    except Exception:
        return False
    return True

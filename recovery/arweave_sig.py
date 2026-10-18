"""Verify an Arweave format-2 transaction signature.

The signed message is the deep hash used by arweave-js for format 2.
The owner field is the RSA modulus. The public exponent is 65537.
RSA-PSS with SHA-256 and a salt length of 32 is the padding that verifies
the LegacyNet CU data items. The deep hash itself is SHA-384.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def b64url_decode(text: str) -> bytes:
    if not text:
        return b""
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sha256(raw: bytes) -> bytes:
    return hashlib.sha256(raw).digest()


def sha384(raw: bytes) -> bytes:
    return hashlib.sha384(raw).digest()


def deep_hash(data: bytes | list) -> bytes:
    """Arweave deep hash (SHA-384), as used by current arweave-js and arbundles.

    A blob is SHA-384(SHA-384(b"blob" || length) || SHA-384(bytes)).
    A list starts from SHA-384(b"list" || count) and folds each child in order.
    """
    if isinstance(data, list):
        acc = sha384(b"list" + str(len(data)).encode("utf-8"))
        for item in data:
            acc = sha384(acc + deep_hash(item))
        return acc
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("deep hash chunk must be bytes or a list")
    raw = bytes(data)
    tag = sha384(b"blob" + str(len(raw)).encode("utf-8"))
    return sha384(tag + sha384(raw))


def owner_address(owner: bytes) -> str:
    return b64url_encode(sha256(owner))


def format2_signature_data(tx: dict) -> bytes:
    """Bytes that a format-2 transaction signature covers.

    Tag name and value strings in `tx["tags"]` are base64url, as returned by
    `GET /tx/{id}`. Empty target and anchor fields hash as empty blobs.
    """
    if int(tx.get("format", 0)) != 2:
        raise ValueError(f"unsupported transaction format {tx.get('format')}")
    tags = []
    for tag in tx.get("tags") or []:
        tags.append([b64url_decode(tag["name"]), b64url_decode(tag["value"])])
    return deep_hash([
        b"2",
        b64url_decode(tx.get("owner") or ""),
        b64url_decode(tx.get("target") or ""),
        str(tx.get("quantity") or "0").encode("utf-8"),
        str(tx.get("reward") or "0").encode("utf-8"),
        b64url_decode(tx.get("last_tx") or ""),
        tags,
        str(tx.get("data_size") or "0").encode("utf-8"),
        b64url_decode(tx.get("data_root") or ""),
    ])


def _avro_long(value: int) -> bytes:
    """Avro zig-zag signed long, the length encoding used by ANS-104 tags."""
    if value < 0:
        zigzag = ((-value) << 1) - 1
    else:
        zigzag = value << 1
    out = bytearray()
    while True:
        byte = zigzag & 0x7F
        zigzag >>= 7
        if zigzag:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def serialize_ans104_tags(tags: list[tuple[bytes, bytes]]) -> bytes:
    """ANS-104 raw tag bytes.

    Avro long count, then each name and value as an Avro long length plus
    UTF-8 bytes, then a terminating Avro long 0. This is the `rawTags` buffer
    covered by the data-item signature.
    """
    parts = [_avro_long(len(tags))]
    for name, value in tags:
        parts.append(_avro_long(len(name)))
        parts.append(name)
        parts.append(_avro_long(len(value)))
        parts.append(value)
    parts.append(_avro_long(0))
    return b"".join(parts)


def dataitem_signature_data(
    owner: bytes,
    target: bytes,
    anchor: bytes,
    tags: list[tuple[bytes, bytes]],
    data: bytes,
    *,
    signature_type: str = "1",
) -> bytes:
    """Deep hash signed by an ANS-104 data item.

    `tags` are raw name/value bytes in header order. `data` is the item payload,
    not the header. Signature type `1` is the RSA-PSS owner used by the CU.
    """
    return deep_hash([
        b"dataitem",
        b"1",
        signature_type.encode("utf-8"),
        owner,
        target,
        anchor,
        serialize_ans104_tags(tags),
        data,
    ])


def verify_rsa_pss(owner: bytes, signature: bytes, message: bytes) -> bool:
    """RSA-PSS SHA-256 with a salt of 32 bytes. A bad signature returns False.

    32 is the SHA-256 digest length. Node's `crypto.sign` uses that salt when
    the caller does not set one. Arweave's older salt length of 0 does not
    verify the LegacyNet CU checkpoint.
    """
    try:
        public = rsa.RSAPublicNumbers(65537, int.from_bytes(owner, "big")).public_key()
        public.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
    except Exception:
        return False
    return True


def verify_format2(tx: dict) -> bool:
    """Return whether `tx` carries a valid format-2 RSA-PSS signature.

    A missing field or a bad key returns False. It does not raise for a
    rejected signature.
    """
    try:
        owner = b64url_decode(tx["owner"])
        signature = b64url_decode(tx["signature"])
        message = format2_signature_data(tx)
        public = rsa.RSAPublicNumbers(65537, int.from_bytes(owner, "big")).public_key()
        public.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=0),
            hashes.SHA256(),
        )
    except Exception:
        return False
    expected = tx.get("id")
    if expected and b64url_encode(sha256(signature)) != expected:
        return False
    return True

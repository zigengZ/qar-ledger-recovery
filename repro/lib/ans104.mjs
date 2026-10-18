/**
 * ANS-104 data-item signatures and binary bundle headers.
 * RSA-PSS SHA-256. The salt length is taken from the signature.
 */
import { createHash, createPublicKey, verify, constants } from "node:crypto";

export function b64url(buf) {
  return Buffer.from(buf).toString("base64url");
}

export function b64urlDecode(text) {
  if (!text) return Buffer.alloc(0);
  return Buffer.from(text, "base64url");
}

export function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

function sha384(buf) {
  return createHash("sha384").update(buf).digest();
}

export function deepHash(data) {
  if (Array.isArray(data)) {
    let acc = sha384(Buffer.concat([Buffer.from("list"), Buffer.from(String(data.length))]));
    for (const item of data) acc = sha384(Buffer.concat([acc, deepHash(item)]));
    return acc;
  }
  const raw = Buffer.isBuffer(data) ? data : Buffer.from(data);
  const tag = sha384(Buffer.concat([Buffer.from("blob"), Buffer.from(String(raw.length))]));
  return sha384(Buffer.concat([tag, sha384(raw)]));
}

function avroLong(value) {
  if (!Number.isSafeInteger(value)) throw new Error(`avro long ${value} is not a safe integer`);
  let zigzag = value < 0 ? (-value) * 2 - 1 : value * 2;
  const out = [];
  while (true) {
    const byte = zigzag & 0x7f;
    zigzag = Math.floor(zigzag / 128);
    if (zigzag) out.push(byte | 0x80);
    else {
      out.push(byte);
      return Buffer.from(out);
    }
  }
}

export function serializeTags(tags) {
  const parts = [avroLong(tags.length)];
  for (const tag of tags) {
    const name = Buffer.from(tag.name, "utf8");
    const value = Buffer.from(tag.value, "utf8");
    parts.push(avroLong(name.length), name, avroLong(value.length), value);
  }
  parts.push(avroLong(0));
  return Buffer.concat(parts);
}

export function ownerAddress(owner) {
  return b64url(createHash("sha256").update(owner).digest());
}

export function rsaPssVerify(owner, signature, message) {
  const key = createPublicKey({
    key: { kty: "RSA", n: b64url(owner), e: "AQAB" },
    format: "jwk",
  });
  return verify(
    "sha256",
    message,
    { key, padding: constants.RSA_PKCS1_PSS_PADDING, saltLength: constants.RSA_PSS_SALTLEN_AUTO },
    signature,
  );
}

export function dataItemSigningBytes(owner, target, anchor, tagBytes, data) {
  return deepHash([
    Buffer.from("dataitem"),
    Buffer.from("1"),
    Buffer.from("1"),
    owner,
    target,
    anchor,
    tagBytes,
    data,
  ]);
}

function readU256(buf, offset) {
  for (let i = 8; i < 32; i += 1) {
    if (buf[offset + i] !== 0) throw new Error("32-byte integer does not fit");
  }
  return Number(buf.readBigUInt64LE(offset));
}

export function parseBundle(buf) {
  if (!buf || buf.length < 32) return null;
  let count;
  try {
    count = readU256(buf, 0);
  } catch {
    return null;
  }
  if (count < 1 || count > 1_000_000) return null;
  const headerLen = 32 + 64 * count;
  if (buf.length < headerLen) return null;
  const items = [];
  let dataOffset = headerLen;
  for (let i = 0; i < count; i += 1) {
    const entry = 32 + 64 * i;
    let size;
    try {
      size = readU256(buf, entry);
    } catch {
      return null;
    }
    if (dataOffset + size > buf.length) return null;
    items.push({
      offset: dataOffset,
      size,
      id: b64url(buf.subarray(entry + 32, entry + 64)),
    });
    dataOffset += size;
  }
  if (dataOffset !== buf.length) return null;
  return items;
}

function readAvroLong(buf, index) {
  let shift = 0;
  let zigzag = 0;
  while (true) {
    if (index >= buf.length) throw new Error("truncated avro long");
    const byte = buf[index];
    index += 1;
    zigzag += (byte & 0x7f) * 2 ** shift;
    if ((byte & 0x80) === 0) break;
    shift += 7;
    if (shift > 63) throw new Error("avro long is too wide");
  }
  const decoded = zigzag % 2 === 0 ? zigzag / 2 : -(zigzag + 1) / 2;
  return { value: decoded, index };
}

function readAvroTags(buf) {
  const tags = [];
  let index = 0;
  while (index < buf.length) {
    const count = readAvroLong(buf, index);
    index = count.index;
    if (count.value === 0) break;
    if (count.value < 0) throw new Error("negative tag group");
    for (let n = 0; n < count.value; n += 1) {
      const nameLen = readAvroLong(buf, index);
      index = nameLen.index;
      const name = buf.subarray(index, index + nameLen.value);
      index += nameLen.value;
      const valueLen = readAvroLong(buf, index);
      index = valueLen.index;
      const value = buf.subarray(index, index + valueLen.value);
      index += valueLen.value;
      if (name.length !== nameLen.value || value.length !== valueLen.value) {
        throw new Error("truncated avro tag");
      }
      tags.push({ name: name.toString("utf8"), value: value.toString("utf8") });
    }
  }
  return tags;
}

function splitOptional(raw, index) {
  if (index >= raw.length) return null;
  if (raw[index] === 0) return { bytes: Buffer.alloc(0), index: index + 1 };
  if (raw[index] === 1 && index + 33 <= raw.length) {
    return { bytes: raw.subarray(index + 1, index + 33), index: index + 33 };
  }
  return null;
}

export function parseDataItem(raw) {
  if (raw.length < 2 + 512 + 512) throw new Error("data item is too short");
  const sigtype = raw.readUInt16LE(0);
  if (sigtype !== 1) throw new Error(`unsupported signature type ${sigtype}`);
  const signature = raw.subarray(2, 514);
  const owner = raw.subarray(514, 1026);
  let index = 1026;
  const target = splitOptional(raw, index);
  if (!target) throw new Error("bad target");
  index = target.index;
  const anchor = splitOptional(raw, index);
  if (!anchor) throw new Error("bad anchor");
  index = anchor.index;
  if (index + 16 > raw.length) throw new Error("truncated tag header");
  const tagCount = Number(raw.readBigUInt64LE(index));
  const tagBytesLen = Number(raw.readBigUInt64LE(index + 8));
  index += 16;
  const tagBytes = raw.subarray(index, index + tagBytesLen);
  if (tagBytes.length !== tagBytesLen) throw new Error("truncated tag bytes");
  index += tagBytesLen;
  const data = raw.subarray(index);
  const tags = readAvroTags(tagBytes);
  if (tags.length !== tagCount) throw new Error(`tag count ${tagCount} but parsed ${tags.length}`);
  const id = b64url(createHash("sha256").update(signature).digest());
  return {
    id,
    signature,
    owner,
    target: target.bytes,
    anchor: anchor.bytes,
    tagBytes,
    tags,
    data,
  };
}

export function verifyRawItem(raw) {
  const item = parseDataItem(raw);
  const message = dataItemSigningBytes(item.owner, item.target, item.anchor, item.tagBytes, item.data);
  const valid = rsaPssVerify(item.owner, item.signature, message);
  return { item, valid };
}

export function verifyReconstructed(ownerB64, signatureB64, targetB64, anchorB64, tags, data) {
  const owner = b64urlDecode(ownerB64);
  const signature = b64urlDecode(signatureB64);
  const target = decodeField(targetB64);
  const anchor = decodeField(anchorB64);
  if (owner.length !== 512 || signature.length !== 512) {
    throw new Error(`owner ${owner.length} or signature ${signature.length} is not 512 bytes`);
  }
  const tagBytes = serializeTags(tags);
  const message = dataItemSigningBytes(owner, target, anchor, tagBytes, data);
  return rsaPssVerify(owner, signature, message);
}

function decodeField(value) {
  if (!value) return Buffer.alloc(0);
  const url = Buffer.from(value, "base64url");
  if (url.length === 32) return url;
  const std = Buffer.from(value, "base64");
  if (std.length === 32) return std;
  throw new Error(`field is ${url.length} bytes, expected 32 or empty`);
}

export function graphqlAnchor(raw) {
  if (!raw || raw.length === 0) return "";
  return Buffer.from(raw).toString("base64").replace(/=+$/, "");
}

export function findBundledItem(buf, wantId, depth = 0) {
  if (depth > 6) return null;
  const bundle = parseBundle(buf);
  if (bundle) {
    for (const entry of bundle) {
      const child = buf.subarray(entry.offset, entry.offset + entry.size);
      if (entry.id === wantId) return child;
      const nested = findBundledItem(child, wantId, depth + 1);
      if (nested) return nested;
    }
    return null;
  }
  if (buf.length > 1026 && buf.readUInt16LE(0) === 1) {
    try {
      const item = parseDataItem(buf);
      if (item.id === wantId) return buf;
      if (item.data.length) return findBundledItem(item.data, wantId, depth + 1);
    } catch {
      return null;
    }
  }
  return null;
}

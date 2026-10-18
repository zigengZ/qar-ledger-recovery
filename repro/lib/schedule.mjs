/**
 * Cron and assignment messages for the tail replay.
 *
 * Cron Block-Height follows the CU rule in permaweb/ao loadMessages.js
 * (cronMessagesBetweenWith): start at the left boundary and step one second.
 * The height advances when the tick's second reaches the next gateway block.
 * The process block second is phase 8 mod 300. isTimestampOnCron uses phase
 * 283. Origin is the process block second minus 25s, which lands on that
 * phase. Plus 275s selects the same ticks.
 */
import { createHash } from "node:crypto";
import { b64urlDecode } from "./ans104.mjs";

export const CRON_SECONDS = 300;
const CRON_ID = "0-5-minutes";
const PHASE_SHIFT_SECONDS = 25;

export function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

export function genHashChain(previousHash, previousAssignmentId) {
  const previous = b64urlDecode(previousHash);
  if (previous.length !== 32) throw new Error(`hash-chain is ${previous.length} bytes`);
  const hash = createHash("sha256");
  if (previousAssignmentId != null) {
    const identifier = b64urlDecode(previousAssignmentId);
    if (identifier.length !== 32) throw new Error(`assignment id is ${identifier.length} bytes`);
    hash.update(identifier);
  }
  hash.update(previous);
  return hash.digest().toString("base64url");
}

export function originMs(processBlockTimestamp) {
  return (processBlockTimestamp - PHASE_SHIFT_SECONDS) * 1000;
}

function toSeconds(ms) {
  return Math.floor(ms / 1000);
}

export function isTimestampOnCron(timestamp, origin) {
  const t = toSeconds(timestamp);
  const start = toSeconds(origin);
  if (t === start) return false;
  return (t - start) % CRON_SECONDS === 0;
}

export function cronsBetween(left, rightTimestamp, blocks, origin) {
  const inRange = blocks.filter((block) => block.timestamp > left.timestamp && block.timestamp < rightTimestamp);
  let cur = { height: left.height, timestamp: left.timestamp };
  let index = 0;
  const out = [];
  for (let ts = left.timestamp; ts < rightTimestamp; ts += 1000) {
    if (index < inRange.length && toSeconds(ts) >= toSeconds(inRange[index].timestamp)) {
      cur = inRange[index];
      index += 1;
    }
    if (isTimestampOnCron(ts, origin)) {
      out.push({
        kind: "cron",
        cron: CRON_ID,
        timestamp: ts,
        height: cur.height,
      });
    }
  }
  return out;
}

function mapFrom(tags, owner) {
  const tag = tags.find((item) => item.name === "From-Process");
  if (!tag || !tag.value) return owner;
  return tag.value;
}

function mapForwardedBy(tags, owner) {
  const tag = tags.find((item) => item.name === "From-Process");
  if (!tag) return undefined;
  return owner;
}

export function decodeAnchor(anchor) {
  if (!anchor) return null;
  const raw = Buffer.from(anchor, "base64");
  const text = raw.toString("utf8");
  const roundTrip = Buffer.from(text, "utf8").toString("base64").replace(/=+$/, "");
  if (roundTrip === anchor.replace(/=+$/, "") && /^[\x20-\x7e]+$/.test(text)) return text;
  return anchor;
}

export function assignmentMessage(row, stored, processId) {
  const forwardedBy = mapForwardedBy(stored.tags, stored.owner);
  const message = {
    Id: stored.id,
    Signature: stored.signature,
    Data: stored.data,
    Owner: stored.owner,
    Target: stored.target || processId,
    Anchor: decodeAnchor(stored.anchor),
    From: mapFrom(stored.tags, stored.owner),
  };
  if (forwardedBy) message["Forwarded-By"] = forwardedBy;
  message.Tags = stored.tags;
  message.Epoch = row.epoch;
  message.Nonce = row.nonce;
  message.Timestamp = row.timestamp;
  message["Block-Height"] = row.height;
  message["Hash-Chain"] = row.hashChain;
  message.Cron = false;
  message["Read-Only"] = false;
  return message;
}

export function cronMessage(item, processOwner, processId) {
  return {
    Owner: processOwner,
    Target: processId,
    From: processOwner,
    Tags: [{ name: "Action", value: "Cron" }],
    Timestamp: item.timestamp,
    "Block-Height": item.height,
    Cron: true,
    "Read-Only": false,
  };
}

export function buildStream(options) {
  const {
    checkpoint,
    assignments,
    messages,
    blocksSeconds,
    processOwner,
    processId,
    origin,
    heightOffset,
    dry,
  } = options;
  const blocks = blocksSeconds
    .map((block) => ({ height: block.height, timestamp: block.timestamp * 1000 }))
    .sort((a, b) => a.height - b.height);
  const items = [];
  let left = { timestamp: checkpoint.timestamp, height: checkpoint.height };
  for (const row of assignments) {
    const point = {
      id: row.assignment_id,
      nonce: row.nonce,
      epoch: Number(row.epoch),
      timestamp: Number(row.timestamp_ms),
      height: Number(row.assignment_block_height),
      hashChain: row.hash_chain,
      messageId: row.message_id,
    };
    if (!Number.isInteger(point.timestamp) || !Number.isInteger(point.height)) {
      throw new Error(`nonce ${row.nonce} has a bad timestamp or height`);
    }
    for (const cron of cronsBetween(left, point.timestamp, blocks, origin)) {
      if (cron.timestamp === left.timestamp) continue;
      const height = cron.height + heightOffset;
      if (!Number.isInteger(height) || height < 0) {
        throw new Error(`cron height ${height} is not a usable block height`);
      }
      const fixed = { ...cron, height };
      items.push({ ...fixed, message: cronMessage(fixed, processOwner, processId) });
    }
    const stored = dry
      ? {
        id: row.message_id,
        owner: processOwner,
        signature: "",
        target: processId,
        anchor: "",
        tags: [],
        data: "",
      }
      : messages.get(row.message_id);
    if (!stored) throw new Error(`missing message ${row.message_id} for nonce ${row.nonce}`);
    items.push({
      kind: "assignment",
      nonce: point.nonce,
      timestamp: point.timestamp,
      height: point.height,
      message: assignmentMessage(point, stored, processId),
    });
    left = { timestamp: point.timestamp, height: point.height };
  }
  return items;
}

export function canonicalBalances(map) {
  const entries = [];
  for (const [address, value] of Object.entries(map)) {
    if (typeof value !== "string" || !/^-?\d+$/.test(value)) {
      throw new Error(`balance for ${address} is not a raw integer string`);
    }
    if (BigInt(value) === 0n) continue;
    entries.push([address, value]);
  }
  entries.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const ordered = {};
  for (const [address, value] of entries) ordered[address] = value;
  return `${JSON.stringify(ordered)}\n`;
}

export function sumBalances(map) {
  let sum = 0n;
  for (const value of Object.values(map)) {
    if (typeof value !== "string" || !/^-?\d+$/.test(value)) {
      throw new Error("balance map contains a value that is not a raw integer string");
    }
    sum += BigInt(value);
  }
  return sum;
}

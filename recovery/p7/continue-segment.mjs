/**
 * Continue a P7 replay from a saved memory snapshot.
 * Cron boundaries are assignment Timestamps. Handler errors keep the previous memory.
 */
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { foldCuResult } from "./cu-fold.mjs";

const require = createRequire(new URL("../p6/package.json", import.meta.url));
const AoLoader = require("@permaweb/ao-loader");
const ROOT = new URL("../../", import.meta.url);
const readJson = (path) => JSON.parse(readFileSync(new URL(path, ROOT)));

const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";
const runId = process.env.P7_RUN_ID;
const messagesPath = process.env.P7_MESSAGES;
const blocksPath = process.env.P7_BLOCKS;
const memoryPath = process.env.P7_MEMORY;
const left = JSON.parse(process.env.P7_LEFT);
if (!runId || !messagesPath || !blocksPath || !memoryPath || left.height == null || left.timestamp == null) {
  throw new Error("P7_RUN_ID, P7_MESSAGES, P7_BLOCKS, P7_MEMORY, and P7_LEFT are required");
}

function toSeconds(millis) {
  return Math.floor(millis / 1000);
}
function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
function memoryBytes(memory) {
  if (memory instanceof Uint8Array) return memory;
  if (ArrayBuffer.isView(memory)) return new Uint8Array(memory.buffer, memory.byteOffset, memory.byteLength);
  return new Uint8Array(memory);
}
function cronsBetween(leftBoundary, right, blocks, origin, owner) {
  const blocksInRange = blocks.filter(
    (block) => block.timestamp > leftBoundary.timestamp && block.timestamp < right.timestamp,
  );
  const out = [];
  let cursor = 0;
  let current = leftBoundary;
  for (let tick = leftBoundary.timestamp; tick < right.timestamp; tick += 1000) {
    const next = blocksInRange[cursor];
    if (next && toSeconds(tick) >= toSeconds(next.timestamp)) {
      current = next;
      cursor += 1;
    }
    const timestamp = toSeconds(tick);
    const originTimestamp = toSeconds(origin.timestamp);
    if (timestamp !== originTimestamp && (timestamp - originTimestamp) % 300 === 0) {
      out.push({
        Owner: owner,
        Target: PROCESS_ID,
        From: owner,
        Tags: [{ name: "Action", value: "Cron" }],
        Timestamp: tick,
        "Block-Height": current.height,
        Cron: true,
      });
    }
  }
  return out;
}

const processTx = readJson("data/raw/p7/process-tx.json");
const processTags = readJson("data/raw/p7/process-tags.json");
const moduleDoc = readJson("evidence/p2/20261017T1645Z-p2a/module.json");
const messages = readJson(messagesPath);
const blockRows = readJson(blocksPath)
  .map((block) => ({ height: block.height, timestamp: block.timestamp * 1000 }))
  .sort((a, b) => a.height - b.height);
const byHeight = new Map(blockRows.map((block) => [block.height, block]));
const origin = { height: 1505290, timestamp: 1726164008 * 1000 };
const owner = processTx.owner.address;
const env = {
  Process: { Id: PROCESS_ID, Owner: owner, Tags: processTags },
  Module: {
    Id: MODULE_ID,
    Owner: moduleDoc.owner,
    Tags: Object.entries(moduleDoc.tags).map(([name, value]) => ({ name, value })),
  },
};
function blockOf(message) {
  const height = Number(message.assignment_block_height);
  const found = byHeight.get(height);
  if (!found) throw new Error(`missing block ${height}`);
  return found;
}
function scheduled(message) {
  const fromProcess = message.tags.find((tag) => tag.name === "From-Process");
  return {
    Id: message.message_id,
    Signature: message.signature,
    Owner: message.owner,
    Target: PROCESS_ID,
    From: fromProcess?.value || message.owner,
    "Forwarded-By": fromProcess ? message.owner : undefined,
    Anchor: message.anchor || undefined,
    Tags: message.tags,
    Data: message.data || "",
    Epoch: Number(message.epoch),
    Nonce: Number(message.nonce),
    Timestamp: Number(message.timestamp_ms),
    "Block-Height": Number(message.assignment_block_height),
    "Hash-Chain": message.hash_chain,
    Cron: false,
  };
}

const wasm = readFileSync(new URL("data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm", ROOT));
const handle = await AoLoader(wasm, {
  format: moduleDoc.tags["Module-Format"],
  inputEncoding: moduleDoc.tags["Input-Encoding"],
  outputEncoding: moduleDoc.tags["Output-Encoding"],
  memoryLimit: "524288000",
  computeLimit: Number(moduleDoc.tags["Compute-Limit"]),
  extensions: [],
});
let memory = readFileSync(new URL(memoryPath, ROOT));
const openedSha = sha256(memory);
console.log("open", memory.length, openedSha);
let cronApplied = 0;
let cronErrors = 0;
let firstCronError = null;
let appliedCount = 0;
let handlerErrorCount = 0;
let previous = { height: Number(left.height), timestamp: Number(left.timestamp) };
let evaluatorCrash = null;
const log = [];
for (const message of messages) {
  const block = blockOf(message);
  const right = { height: block.height, timestamp: Number(message.timestamp_ms) };
  const crons = cronsBetween(previous, right, blockRows, origin, owner);
  for (const cron of crons) {
    let result;
    try {
      result = await handle(memory, cron, env);
    } catch (error) {
      evaluatorCrash = { kind: "cron", timestamp: cron.Timestamp, error: String(error).slice(0, 500) };
      break;
    }
    const folded = foldCuResult(memory, result);
    memory = Buffer.from(memoryBytes(folded.memory));
    if (folded.handler_error) {
      cronErrors += 1;
      if (!firstCronError) firstCronError = folded.handler_error.slice(0, 300);
    } else cronApplied += 1;
  }
  if (evaluatorCrash) break;
  let result;
  try {
    result = await handle(memory, scheduled(message), env);
  } catch (error) {
    evaluatorCrash = { kind: "assignment", nonce: Number(message.nonce), error: String(error).slice(0, 500) };
    break;
  }
  const before = sha256(memory);
  const folded = foldCuResult(memory, result);
  memory = Buffer.from(memoryBytes(folded.memory));
  if (folded.eval_applied) appliedCount += 1;
  else handlerErrorCount += 1;
  const row = {
    kind: "assignment",
    nonce: Number(message.nonce),
    action: message.action,
    message_id: message.message_id,
    crons_before: crons.length,
    sha256: sha256(memory),
    bytes: memory.length,
    memory_unchanged: sha256(memory) === before,
    eval_applied: folded.eval_applied,
    error: folded.handler_error ? folded.handler_error.slice(0, 500) : null,
  };
  log.push(row);
  console.log("nonce", row.nonce, row.action, "crons", crons.length, row.sha256.slice(0, 16), row.eval_applied ? "applied" : "handler-error");
  previous = right;
}
const dir = new URL(`data/raw/p7/${runId}/`, ROOT);
mkdirSync(dir, { recursive: true });
writeFileSync(new URL("memory.bin", dir), memory);
const report = {
  run_id: runId,
  opened_memory_sha256: openedSha,
  segment_evaluated: evaluatorCrash ? false : log.length === messages.length,
  evaluator_crash: evaluatorCrash,
  next_nonce: evaluatorCrash ? (evaluatorCrash.nonce ?? null) : (log.at(-1) ? log.at(-1).nonce + 1 : null),
  left_boundary: previous && log.length ? { height: Number(left.height), timestamp: Number(left.timestamp) } : null,
  right_boundary: log.length ? { height: previous.height, timestamp: previous.timestamp } : null,
  cron_applied: cronApplied,
  cron_handler_errors: cronErrors,
  first_cron_error: firstCronError,
  assignments_applied: appliedCount,
  assignments_handler_errors: handlerErrorCount,
  assignments_evaluated: log.length,
  memory_bytes: memory.length,
  memory_sha256: sha256(memory),
  handler_error_is_not_success: true,
  log,
};
writeFileSync(new URL(`data/raw/p7/${runId}.json`, ROOT), JSON.stringify(report));
console.log(`P7_REPORT ${JSON.stringify({ ...report, log: undefined })}`);
if (evaluatorCrash) process.exitCode = 1;

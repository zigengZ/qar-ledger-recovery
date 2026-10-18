/**
 * P7 genesis segment: cold start, then assignments 0..19.
 *
 * The nonce 2074518 checkpoint failed the P6 memory overlap check, so this
 * replay starts at genesis. Cron insertion follows permaweb/ao 0db88a45
 * loadMessages.js for the process tag Cron-Interval=5-minutes.
 *
 * A handler Error keeps the previous memory and the schedule continues.
 * That is the CU worker rule. It is not a successful Eval.
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
const lastNonce = process.env.P7_LAST_NONCE == null ? 19 : Number(process.env.P7_LAST_NONCE);
const runId = process.env.P7_RUN_ID || "20261017T0615Z-p7-genesis-0-19";

function toSeconds(millis) {
  return Math.floor(millis / 1000);
}
function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
function memoryBytes(memory) {
  if (memory instanceof Uint8Array) return memory;
  if (ArrayBuffer.isView(memory)) {
    return new Uint8Array(memory.buffer, memory.byteOffset, memory.byteLength);
  }
  return new Uint8Array(memory);
}
function cronsBetween(left, right, blocks, origin, owner) {
  const blocksInRange = blocks.filter(
    (block) => block.timestamp > left.timestamp && block.timestamp < right.timestamp,
  );
  const out = [];
  let cursor = 0;
  let current = left;
  for (let tick = left.timestamp; tick < right.timestamp; tick += 1000) {
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
const processData = readFileSync(new URL("data/raw/p7/process-data.bin", ROOT)).toString("utf8");
const moduleDoc = readJson("evidence/p2/20261017T1645Z-p2a/module.json");
const messages = readJson("data/raw/p7/segment-0-19.json").filter(
  (message) => Number(message.nonce) <= lastNonce,
);
const blockRows = readJson("data/raw/p7/blocks-0-19.json")
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

const boot = {
  Id: PROCESS_ID,
  Signature: processTx.signature,
  Owner: owner,
  Target: PROCESS_ID,
  Anchor: processTx.anchor || undefined,
  From: owner,
  Tags: processTags,
  Data: processData,
  Timestamp: origin.timestamp,
  "Block-Height": origin.height,
  Cron: false,
};
let bootResult;
try {
  bootResult = await handle(null, boot, env);
} catch (error) {
  throw new Error(`evaluator crash on boot: ${error}`);
}
const bootFold = foldCuResult(null, { ...bootResult, Memory: bootResult.Memory && memoryBytes(bootResult.Memory) });
if (!bootFold.eval_applied) {
  throw new Error(`boot handler error: ${bootFold.handler_error}`);
}
let memory = Buffer.from(memoryBytes(bootFold.memory));
const bootSha = sha256(memory);
console.log("boot", memory.length, bootSha);

let cronCount = 0;
let cronErrors = 0;
let firstCronError = null;
let appliedCount = 0;
let handlerErrorCount = 0;
const log = [{ kind: "boot", sha256: bootSha, bytes: memory.length, error: null, eval_applied: true }];
// CU loadMessages uses the assignment Timestamp as the cron boundary.
// The block height still comes from the assignment, and Block-Height advances
// when the tick passes the next Arweave block.
let previousBoundary = { height: origin.height, timestamp: origin.timestamp };
let evaluatorCrash = null;
for (const message of messages) {
  const block = blockOf(message);
  const right = { height: block.height, timestamp: Number(message.timestamp_ms) };
  const crons = cronsBetween(previousBoundary, right, blockRows, origin, owner);
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
    } else cronCount += 1;
  }
  if (evaluatorCrash) break;
  let result;
  try {
    result = await handle(memory, scheduled(message), env);
  } catch (error) {
    evaluatorCrash = { kind: "assignment", nonce: message.nonce, error: String(error).slice(0, 500) };
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
  console.log(
    "nonce",
    row.nonce,
    row.action,
    "crons",
    crons.length,
    row.bytes,
    row.sha256.slice(0, 16),
    row.eval_applied ? "applied" : "handler-error",
  );
  previousBoundary = right;
}

const supplyMessage = messages.at(-1);
let supplyText = null;
let supplyError = null;
if (!evaluatorCrash && supplyMessage) {
  const supply = await handle(Buffer.from(memory), {
    Owner: owner,
    Target: PROCESS_ID,
    From: owner,
    Tags: [{ name: "Action", value: "Total-Supply" }],
    Data: "",
    Timestamp: Number(supplyMessage.timestamp_ms),
    "Block-Height": Number(supplyMessage.assignment_block_height),
    Cron: false,
  }, env);
  const supplyFold = foldCuResult(memory, supply);
  supplyText = typeof supply.Output === "string" ? supply.Output : JSON.stringify(supply.Output);
  supplyError = supplyFold.handler_error;
}

const dir = new URL(`data/raw/p7/0-19/${runId}/`, ROOT);
mkdirSync(dir, { recursive: true });
writeFileSync(new URL("memory.bin", dir), memory);
const evaluated = log.filter((row) => row.kind === "assignment");
const lastEvaluated = evaluated.at(-1) || null;
const report = {
  run_id: runId,
  segment_requested: [0, lastNonce],
  segment_evaluated: evaluatorCrash ? false : evaluated.length === messages.length,
  evaluator_crash: evaluatorCrash,
  next_nonce: evaluatorCrash
    ? (evaluatorCrash.nonce ?? null)
    : (lastEvaluated ? lastEvaluated.nonce + 1 : 0),
  boot_sha256: bootSha,
  boot_bytes: log[0].bytes,
  cron_applied: cronCount,
  cron_handler_errors: cronErrors,
  first_cron_error: firstCronError,
  assignments_applied: appliedCount,
  assignments_handler_errors: handlerErrorCount,
  assignments_evaluated: evaluated.length,
  memory_bytes: memory.length,
  memory_sha256: sha256(memory),
  total_supply_output: supplyText,
  total_supply_error: supplyError ? String(supplyError).slice(0, 500) : null,
  total_supply_is_shutdown_balance: false,
  handler_error_is_not_success: true,
  log,
};
writeFileSync(new URL(`data/raw/p7/${runId}.json`, ROOT), JSON.stringify(report, null, 2));
console.log(`P7_REPORT ${JSON.stringify({ ...report, log: evaluated })}`);
if (evaluatorCrash) process.exitCode = 1;

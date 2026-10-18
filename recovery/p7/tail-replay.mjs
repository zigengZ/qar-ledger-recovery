/**
 * Replay nonce 2074519..2075923 from the accepted 2074518 checkpoint.
 *
 * Cron construction is the exported w-eval replay. Block-Height is the
 * gateway block timestamp rule. Handler errors keep the previous memory.
 */
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import {
  CHECKPOINTS,
  PROCESS_ID,
  assignmentMessage,
  cronMessage,
  cronsBetween,
  sha256,
} from "../p6/replay.mjs";

const require = createRequire(new URL("../p6/package.json", import.meta.url));
const AoLoader = require("@permaweb/ao-loader");

const ROOT = new URL("../../", import.meta.url);
const preferred = new URL("data/raw/p7/tail-2074518/", ROOT);
const legacy = new URL("./data/raw/p7/tail-2074518/", import.meta.url);
const RAW = existsSync(new URL("cursor.json", legacy)) && !existsSync(new URL("cursor.json", preferred))
  ? legacy
  : preferred;
const TAIL_NONCE = 2075923;
const START = CHECKPOINTS[2074518];
const SAVE_EVERY = 400;

function readJson(url) {
  return JSON.parse(readFileSync(url, "utf8"));
}
function signatureOf(item) {
  return Buffer.from(item.subarray(2, 514)).toString("base64url");
}

const processTx = readJson(new URL("data/raw/p7/process-tx.json", ROOT));
const processTags = readJson(new URL("data/raw/p7/process-tags.json", ROOT));
const moduleDoc = readJson(new URL("evidence/p2/20261017T1645Z-p2a/module.json", ROOT));
const aoGlobal = {
  Process: { Id: PROCESS_ID, Owner: processTx.owner.address, Tags: processTags },
  Module: {
    Id: "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0",
    Owner: moduleDoc.owner,
    Tags: Object.entries(moduleDoc.tags).map(([name, value]) => ({ name, value })),
  },
};

const manifest = readJson(new URL("evidence/p4-tail/20261017T052614Z-w-tail/messages-manifest.json", ROOT));
const byMessage = new Map(manifest.files.map((row) => [row.message_id, row]));
const assignments = readJson(new URL("evidence/p4-tail/20261017T052614Z-w-tail/assignments.json", ROOT))
  .filter((row) => row.nonce > START.nonce && row.nonce <= TAIL_NONCE)
  .sort((a, b) => a.nonce - b.nonce);
if (assignments.length !== TAIL_NONCE - START.nonce) {
  throw new Error(`expected ${TAIL_NONCE - START.nonce} assignments, got ${assignments.length}`);
}
const blocks = readJson(new URL("data/raw/p7/tail-blocks/blocks.json", ROOT))
  .map((block) => ({ height: block.height, timestamp: block.timestamp * 1000 }))
  .sort((a, b) => a.height - b.height);

function storedMessage(row) {
  const meta = byMessage.get(row.message_id);
  if (!meta || !meta.stored) throw new Error(`missing stored message for nonce ${row.nonce}`);
  const data = readFileSync(meta.data_path);
  const item = readFileSync(meta.path);
  return {
    id: row.message_id,
    owner: meta.owner_address,
    signature: signatureOf(item),
    target: meta.target || PROCESS_ID,
    anchor: meta.anchor || "",
    tags: meta.tags,
    data: data.toString("utf8"),
  };
}

function buildItems() {
  const items = [];
  let left = { timestamp: START.timestamp, height: START.height };
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
    for (const cron of cronsBetween(left, point.timestamp, blocks)) {
      // The checkpoint memory already includes a cron at its own timestamp.
      if (cron.timestamp === left.timestamp) continue;
      items.push({ ...cron, message: cronMessage(cron, aoGlobal) });
    }
    const stored = storedMessage(row);
    items.push({
      kind: "assignment",
      nonce: point.nonce,
      timestamp: point.timestamp,
      height: point.height,
      message: assignmentMessage(point, stored, PROCESS_ID),
    });
    left = { timestamp: point.timestamp, height: point.height };
  }
  return items;
}

const dry = process.argv.includes("--dry-run");
const items = buildItems();
const summary = {
  height_source: "gateway block timestamps, cronsBetween from recovery/p6/replay.mjs",
  from_nonce: START.nonce,
  to_nonce: TAIL_NONCE,
  messages: items.length,
  crons: items.filter((item) => item.kind === "cron").length,
  assignments: items.filter((item) => item.kind === "assignment").length,
  first: items[0] && { kind: items[0].kind, timestamp: items[0].timestamp, height: items[0].height, nonce: items[0].nonce ?? null },
  last: items.at(-1) && { kind: items.at(-1).kind, nonce: items.at(-1).nonce ?? null, timestamp: items.at(-1).timestamp },
};
if (dry) {
  console.log(JSON.stringify(summary, null, 2));
  process.exit(0);
}

mkdirSync(RAW, { recursive: true });
const cursorPath = new URL("cursor.json", RAW);
let index = 0;
let memory;
let applied = 0;
let handlerErrors = 0;
if (existsSync(cursorPath)) {
  const cursor = readJson(cursorPath);
  index = cursor.next_index;
  applied = cursor.applied;
  handlerErrors = cursor.handler_errors;
  memory = readFileSync(new URL(cursor.memory_file, RAW));
  if (sha256(memory) !== cursor.memory_sha256) throw new Error("resume memory hash mismatch");
  console.log(JSON.stringify({ resume: index, sha256: cursor.memory_sha256, applied }));
} else {
  memory = gunzipSync(readFileSync(new URL(`data/raw/checkpoints/${START.id}.bin`, ROOT)));
  if (sha256(memory) !== START.sha256) throw new Error("checkpoint gunzip sha mismatch");
  console.log(JSON.stringify({ start: START.sha256, bytes: memory.length }));
}

const wasm = readFileSync(new URL("data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm", ROOT));
const handle = await AoLoader(wasm, {
  format: "wasm32-unknown-emscripten",
  inputEncoding: "JSON-1",
  outputEncoding: "JSON-1",
  memoryLimit: "524288000",
  computeLimit: 9000000000000,
  extensions: [],
});

const logPath = new URL("steps.jsonl", RAW);
let sinceSave = 0;
function save(nextIndex) {
  const file = "memory.bin";
  writeFileSync(new URL(file, RAW), memory);
  writeFileSync(cursorPath, JSON.stringify({
    next_index: nextIndex,
    memory_file: file,
    memory_sha256: sha256(memory),
    memory_bytes: memory.length,
    applied,
    handler_errors: handlerErrors,
    height_source: summary.height_source,
  }));
}

for (; index < items.length; index += 1) {
  const item = items[index];
  const before = Buffer.from(memory);
  let result;
  let thrown = null;
  try {
    result = await handle(memory, item.message, aoGlobal);
  } catch (error) {
    thrown = String(error && error.message ? error.message : error);
    result = { Error: thrown, Memory: before };
  }
  if (result && result.Error) {
    memory = before;
    handlerErrors += 1;
  } else {
    memory = Buffer.from(result.Memory);
    applied += 1;
  }
  sinceSave += 1;
  if (item.kind === "assignment" || result.Error || sinceSave >= SAVE_EVERY) {
    const row = {
      index,
      kind: item.kind,
      nonce: item.nonce ?? null,
      timestamp: item.timestamp,
      height: item.height,
      bytes: memory.length,
      sha256: sha256(memory),
      applied: !(result && result.Error),
      error: result && result.Error ? String(result.Error).slice(0, 240) : null,
    };
    writeFileSync(logPath, `${JSON.stringify(row)}\n`, { flag: "a" });
    if (item.kind === "assignment" || result.Error) console.log(JSON.stringify(row));
    if (sinceSave >= SAVE_EVERY || result.Error) {
      save(index + 1);
      sinceSave = 0;
    }
  }
}
save(items.length);
const owner = processTx.owner.address;
async function readAction(action) {
  const result = await handle(Buffer.from(memory), {
    Owner: owner,
    From: owner,
    Target: PROCESS_ID,
    Tags: [{ name: "Action", value: action }],
    Data: "",
    Timestamp: items.at(-1).timestamp,
    "Block-Height": items.at(-1).height,
    Cron: false,
    "Read-Only": true,
  }, aoGlobal);
  const data = (result.Messages || []).map((message) => (message.Data == null ? "" : String(message.Data))).join("");
  return {
    error: result.Error ? String(result.Error).slice(0, 400) : null,
    output: typeof result.Output === "string" ? result.Output : JSON.stringify(result.Output ?? null),
    data,
  };
}
const supply = await readAction("Total-Supply");
const balances = await readAction("Balances");
let balanceMap = null;
let balanceError = balances.error;
try {
  balanceMap = JSON.parse(balances.data);
} catch (error) {
  balanceError = balanceError || String(error.message);
}
let sum = null;
let addresses = null;
if (balanceMap && typeof balanceMap === "object" && !Array.isArray(balanceMap)) {
  addresses = Object.keys(balanceMap).length;
  sum = 0n;
  for (const value of Object.values(balanceMap)) sum += BigInt(value);
  writeFileSync(new URL("balances.json", RAW), JSON.stringify(balanceMap));
}
const report = {
  ...summary,
  memory_sha256: sha256(memory),
  memory_bytes: memory.length,
  applied,
  handler_errors: handlerErrors,
  total_supply_data: supply.data,
  total_supply_error: supply.error,
  total_supply_output: supply.output,
  balance_addresses: addresses,
  balance_sum: sum == null ? null : sum.toString(),
  balance_error: balanceError,
  balance_output: balances.output,
  balances_path: "data/raw/p7/tail-2074518/balances.json",
  shutdown_claim: false,
  goal_complete: false,
};
writeFileSync(new URL("report.json", RAW), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
if (handlerErrors) process.exitCode = 2;

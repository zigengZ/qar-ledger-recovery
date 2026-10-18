/**
 * Reproduce the qAR tail ledger from public gateways.
 *
 *   node --max-old-space-size=8192 repro/run.mjs
 *   node --max-old-space-size=8192 repro/run.mjs --mode safe
 *   node --max-old-space-size=8192 repro/run.mjs --cron-height-offset 3
 */
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  fetchAssignments,
  fetchBlocks,
  fetchCheckpoint,
  fetchMessages,
  fetchModule,
  fetchProcess,
  messageForReplay,
  verifyHashChain,
} from "./lib/fetch.mjs";
import { createHandle, openHandle, readAction, replayItems, sha256 } from "./lib/replay.mjs";
import { buildStream, canonicalBalances, originMs, sumBalances } from "./lib/schedule.mjs";

// ao-loader's emscripten startup replaces Date.now and process.hrtime.
const nowNs = process.hrtime.bigint.bind(process.hrtime);
const wallNow = Date.now.bind(Date);
function msSince(start) {
  return Number(nowNs() - start) / 1e6;
}

const REPRO_DIR = dirname(fileURLToPath(import.meta.url));
const WORK = process.env.REPRO_WORK || join(REPRO_DIR, "work");
process.env.REPRO_WORK = WORK;
process.env.REPRO_HTTP_DIR = process.env.REPRO_HTTP_DIR || join(WORK, "raw/http");

function argValue(flag, fallback) {
  const index = process.argv.indexOf(flag);
  if (index === -1) return fallback;
  const value = process.argv[index + 1];
  if (value == null || value.startsWith("--")) throw new Error(`${flag} needs a value`);
  return value;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

const mode = argValue("--mode", "inplace");
const heightOffset = Number(argValue("--cron-height-offset", "0"));
const scheduleOnly = process.argv.includes("--schedule-only");
const skipProbe = process.argv.includes("--skip-probe");
if (mode !== "inplace" && mode !== "safe") fail(`unknown mode ${mode}`);
if (!Number.isInteger(heightOffset)) fail("cron height offset is not an integer");

const expected = JSON.parse(readFileSync(join(REPRO_DIR, "EXPECTED.json"), "utf8"));
if (process.version !== expected.node) fail(`Node ${expected.node} is required, found ${process.version}`);

function log(event) {
  console.log(JSON.stringify({ t: new Date(wallNow()).toISOString(), ...event }));
}

function sha256Text(text) {
  return createHash("sha256").update(text).digest("hex");
}

function offsetName(offset) {
  if (offset === 0) return "primary";
  return offset > 0 ? `offset-plus-${offset}` : `offset-minus-${-offset}`;
}

mkdirSync(WORK, { recursive: true });
const started = nowNs();
log({ step: "start", mode, cron_height_offset: heightOffset, node: process.version });

const memory = await fetchCheckpoint(WORK, expected);
const wasm = await fetchModule(WORK, expected);
const processTx = await fetchProcess(WORK, expected);
const assignments = await fetchAssignments(WORK, expected);
const chain = verifyHashChain(assignments, expected);
const messages = await fetchMessages(WORK, assignments);
const blocks = await fetchBlocks(WORK, expected);

const replayAssignments = assignments.filter((row) => row.nonce > expected.checkpoint_nonce);
if (replayAssignments.length !== expected.stream_assignments) {
  fail(`expected ${expected.stream_assignments} assignments, got ${replayAssignments.length}`);
}
const prepared = new Map();
for (const row of replayAssignments) {
  const record = messages.get(row.message_id);
  if (!record) fail(`missing prepared message ${row.message_id}`);
  prepared.set(row.message_id, messageForReplay(record, expected.process_id));
}
const items = buildStream({
  checkpoint: {
    timestamp: expected.checkpoint_timestamp_ms,
    height: expected.checkpoint_block_height,
  },
  assignments: replayAssignments,
  messages: prepared,
  blocksSeconds: blocks,
  processOwner: expected.process_owner,
  processId: expected.process_id,
  origin: originMs(expected.process_block_timestamp),
  heightOffset,
});
const crons = items.filter((item) => item.kind === "cron").length;
const assigned = items.filter((item) => item.kind === "assignment").length;
const shape = {
  items: items.length,
  crons,
  assignments: assigned,
  first: items[0] && {
    kind: items[0].kind,
    timestamp: items[0].timestamp,
    height: items[0].height,
  },
  last: items.at(-1) && {
    kind: items.at(-1).kind,
    nonce: items.at(-1).nonce ?? null,
    timestamp: items.at(-1).timestamp,
  },
};
log({ step: "stream", ...shape, hash_chain_links: chain.links });
if (items.length !== expected.stream_items) fail(`stream has ${items.length} items, expected ${expected.stream_items}`);
if (crons !== expected.stream_crons) fail(`stream has ${crons} crons`);
if (assigned !== expected.stream_assignments) fail(`stream has ${assigned} assignments`);
if (!items[0] || items[0].kind !== "cron" || items[0].timestamp !== expected.first_cron_timestamp_ms) {
  fail("first stream item is not the expected cron");
}
if (items[0].height !== expected.first_cron_block_height + heightOffset) {
  fail(`first cron height ${items[0].height}`);
}
const tail = items.at(-1);
if (!tail || tail.kind !== "assignment" || tail.nonce !== expected.nonce_to || tail.timestamp !== expected.tail_timestamp_ms) {
  fail("stream does not end on the tail assignment");
}
if (scheduleOnly) {
  log({ step: "schedule-only" });
  process.exit(0);
}

if (mode === "inplace" && heightOffset === 0 && !skipProbe && !existsSync(join(WORK, "probe.json"))) {
  log({ step: "probe" });
  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      "--max-old-space-size=8192",
      fileURLToPath(new URL("./probe.mjs", import.meta.url)),
    ], { stdio: "inherit", env: process.env });
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`probe exited ${code}`))));
  });
}

const runDir = join(WORK, "replay", offsetName(heightOffset), mode);
mkdirSync(runDir, { recursive: true });
const aoGlobal = {
  Process: { Id: expected.process_id, Owner: processTx.owner.address, Tags: processTx.tags },
  Module: { Id: expected.module_id, Owner: processTx.owner.address, Tags: [] },
};
const moduleTx = JSON.parse(readFileSync(join(WORK, "raw/module.tx.json"), "utf8"));
aoGlobal.Module = { Id: expected.module_id, Owner: moduleTx.owner.address, Tags: moduleTx.tags };

const made = await createHandle(mode, join(WORK, "ao-loader-inplace.cjs"));
const handle = await openHandle(made.AoLoader, wasm);
const replayStarted = nowNs();
const replay = await replayItems({
  handle,
  items,
  mode,
  aoGlobal,
  dir: runDir,
  initialMemory: memory,
  saveEvery: 400,
  onProgress: ({ index, item, applied, handlerErrors }) => {
    if (item.kind !== "assignment" && index % 400 !== 0) return;
    log({
      step: "replay",
      index,
      nonce: item.nonce ?? null,
      kind: item.kind,
      applied,
      handler_errors: handlerErrors,
    });
  },
});
if (replay.handlerErrors !== 0) fail(`handler errors ${replay.handlerErrors}`);
if (replay.finalRow.memory_sha256 !== sha256(readFileSync(join(runDir, "memory.bin")))) {
  fail("final memory file hash mismatch");
}

const supply = await readAction(
  handle,
  readFileSync(join(runDir, "memory.bin")),
  aoGlobal,
  expected.process_owner,
  expected.process_id,
  "Total-Supply",
  tail.timestamp,
  tail.height,
);
if (supply.error) fail(`Total-Supply error: ${supply.error}`);
if (supply.data !== expected.total_supply) fail(`Total-Supply ${supply.data}`);
const balances = await readAction(
  handle,
  readFileSync(join(runDir, "memory.bin")),
  aoGlobal,
  expected.process_owner,
  expected.process_id,
  "Balances",
  tail.timestamp,
  tail.height,
);
if (balances.error) fail(`Balances error: ${balances.error}`);
let balanceMap;
try {
  balanceMap = JSON.parse(balances.data);
} catch (error) {
  fail(`Balances data is not JSON: ${error.message}`);
}
const rawCount = Object.keys(balanceMap).length;
const sum = sumBalances(balanceMap);
if (sum.toString() !== expected.total_supply) fail(`balance sum ${sum.toString()}`);
const canonical = canonicalBalances(balanceMap);
const canonicalSha = sha256Text(canonical);
const canonicalCount = Object.keys(JSON.parse(canonical)).length;
const name = offsetName(heightOffset);
const outDir = name === "primary" ? join(WORK, "out") : join(WORK, "out", name);
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, "balances.json"), canonical);
writeFileSync(join(outDir, "balances.sha256"), `${canonicalSha}\n`);
writeFileSync(join(outDir, "memory.sha256"), `${replay.finalRow.memory_sha256}\n`);
const result = {
  mode,
  cron_height_offset: heightOffset,
  height_source: "CU gateway block timestamps",
  node: process.version,
  evaluator: expected.evaluator,
  hash_chain_links: chain.links,
  stream: shape,
  handler_errors: replay.handlerErrors,
  applied: replay.applied,
  memory_sha256: replay.finalRow.memory_sha256,
  memory_bytes: replay.finalRow.memory_bytes,
  canonical_balances_sha256: canonicalSha,
  canonical_address_count: canonicalCount,
  raw_address_count: rawCount,
  total_supply: supply.data,
  balance_sum: sum.toString(),
  sum_equals_total_supply: sum.toString() === supply.data,
  elapsed_ms: Math.round(msSince(started)),
  replay_ms: Math.round(msSince(replayStarted)),
  loader_patch: made.patch,
};
writeFileSync(join(outDir, "result.json"), `${JSON.stringify(result, null, 2)}\n`);
log({ step: "done", ...result, loader_patch: undefined });

if (heightOffset === 0) {
  if (result.memory_sha256 !== expected.memory_sha256) fail(`memory sha ${result.memory_sha256}`);
  if (canonicalSha !== expected.canonical_balances_sha256) fail(`canonical balance sha ${canonicalSha}`);
  if (canonicalCount !== expected.canonical_address_count) fail(`canonical addresses ${canonicalCount}`);
  if (rawCount !== expected.raw_address_count) fail(`raw addresses ${rawCount}`);
} else {
  const primaryShaPath = join(WORK, "out/balances.sha256");
  if (!existsSync(primaryShaPath)) fail("primary canonical hash is missing; run offset 0 first");
  const primarySha = readFileSync(primaryShaPath, "utf8").trim();
  if (canonicalSha !== primarySha) fail(`offset ${heightOffset} canonical sha ${canonicalSha} != ${primarySha}`);
  log({ step: "sensitivity", offset: heightOffset, canonical_unchanged: true, memory_sha256: result.memory_sha256 });
}

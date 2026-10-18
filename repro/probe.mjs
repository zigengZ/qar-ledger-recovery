/**
 * Compare the first 10 evaluations of the unpatched loader and the in-place patch.
 * A mismatch exits non-zero. This does not replace the full replay.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { sha256 as fileSha, createHandle, openHandle } from "./lib/replay.mjs";
import { buildStream, originMs } from "./lib/schedule.mjs";
import { messageForReplay } from "./lib/fetch.mjs";

// ao-loader's emscripten startup replaces Date.now and process.hrtime.
const nowNs = process.hrtime.bigint.bind(process.hrtime);
function msSince(start) {
  return Math.round(Number(nowNs() - start) / 1e6);
}

const REPRO_DIR = dirname(fileURLToPath(import.meta.url));
const WORK = process.env.REPRO_WORK || join(REPRO_DIR, "work");
const expected = JSON.parse(readFileSync(join(REPRO_DIR, "EXPECTED.json"), "utf8"));

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (process.version !== expected.node) fail(`Node ${expected.node} is required, found ${process.version}`);

const processTx = JSON.parse(readFileSync(join(WORK, "raw/process.tx.json"), "utf8"));
const moduleTx = JSON.parse(readFileSync(join(WORK, "raw/module.tx.json"), "utf8"));
const aoGlobal = {
  Process: { Id: expected.process_id, Owner: processTx.owner.address, Tags: processTx.tags },
  Module: { Id: expected.module_id, Owner: moduleTx.owner.address, Tags: moduleTx.tags },
};
const assignments = JSON.parse(readFileSync(join(WORK, "raw/assignments.json"), "utf8"))
  .filter((row) => row.nonce > expected.checkpoint_nonce && row.nonce <= expected.nonce_to);
const messages = new Map();
for (const row of assignments) {
  const record = JSON.parse(readFileSync(join(WORK, "raw/messages", `${row.message_id}.json`), "utf8"));
  messages.set(row.message_id, messageForReplay(record, expected.process_id));
}
const blocks = JSON.parse(readFileSync(join(WORK, "raw/blocks.json"), "utf8"));
const items = buildStream({
  checkpoint: {
    timestamp: expected.checkpoint_timestamp_ms,
    height: expected.checkpoint_block_height,
  },
  assignments,
  messages,
  blocksSeconds: blocks,
  processOwner: expected.process_owner,
  processId: expected.process_id,
  origin: originMs(expected.process_block_timestamp),
  heightOffset: 0,
});
const wasm = readFileSync(join(WORK, "raw/module.wasm"));
const checkpoint = gunzipSync(readFileSync(join(WORK, "raw/checkpoint.gz")));
if (fileSha(checkpoint) !== expected.checkpoint_uncompressed_sha256) fail("probe checkpoint hash mismatch");

const startedSafe = nowNs();
const safeMade = await createHandle("safe");
const safe = await openHandle(safeMade.AoLoader, wasm);
let memory = checkpoint;
for (let index = 0; index < 10; index += 1) {
  const result = await safe(memory, items[index].message, aoGlobal);
  if (result.Error) fail(`safe probe error at ${index}: ${result.Error}`);
  memory = result.Memory;
}
const safeSha = fileSha(memory);
const safeMs = msSince(startedSafe);

const startedFast = nowNs();
const patchDest = join(WORK, "ao-loader-inplace.cjs");
const fastMade = await createHandle("inplace", patchDest);
const fast = await openHandle(fastMade.AoLoader, wasm);
let result = await fast(checkpoint, items[0].message, aoGlobal, { copyMemory: false });
if (result.Error) fail(`inplace probe error at 0: ${result.Error}`);
for (let index = 1; index < 10; index += 1) {
  result = await fast(null, items[index].message, aoGlobal, { copyMemory: false });
  if (result.Error) fail(`inplace probe error at ${index}: ${result.Error}`);
}
const inplaceSha = fileSha(fast.exportHeap());
const inplaceMs = msSince(startedFast);
const report = {
  items: 10,
  safe_sha256: safeSha,
  inplace_sha256: inplaceSha,
  match: safeSha === inplaceSha,
  safe_ms: safeMs,
  inplace_ms: inplaceMs,
  loader_source_sha256: fastMade.patch.source_sha256,
  loader_patch_sha256: fastMade.patch.sha256,
};
mkdirSync(WORK, { recursive: true });
writeFileSync(join(WORK, "probe.json"), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report));
if (!report.match) fail("in-place probe memory does not match the unpatched loader");

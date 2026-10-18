/**
 * Faster twin of tail-replay.mjs.
 *
 * ao-loader 0.0.44 (dist/index.cjs) copies the input into WASM with
 * HEAPU8.set and returns HEAPU8.slice(). It does not write back into the
 * buffer it was given, and the sliced Memory is not the live heap, so the
 * next call cannot overwrite it. The two Buffer.from copies in tail-replay
 * are therefore redundant on the success path.
 *
 * --mode inplace skips both of those copies and also the loader's set/slice
 * pair: the heap already holds the previous result, so the next call is
 * passed a null buffer and copyMemory:false. A local patched loader is
 * written under data/raw/fast/. The main repo's node_modules are not edited.
 * Save points still copy the heap out. A handler error reloads the last
 * save and replays the open batch, which is the same "keep previous memory"
 * rule as tail-replay.mjs.
 *
 * Cron Block-Height stays on gateway block timestamps, matching the live
 * tail replay. Do not point this script at the main cursor directory.
 */
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
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
// ao-loader's emscripten startup replaces process.hrtime. Keep the original.
const nowNs = process.hrtime.bigint.bind(process.hrtime);

const REPO = join(dirname(fileURLToPath(import.meta.url)), "../..");
const DATA = join(REPO, "data/raw");
const WT = REPO;
const MAIN_RAW = join(REPO, "recovery/p7/data/raw/p7/tail-2074518");
const LOADER_SRC = join(REPO, "recovery/p6/node_modules/@permaweb/ao-loader/dist/index.cjs");
const LOADER_PATCH = join(DATA, "fast/ao-loader-inplace.cjs");
const TAIL_NONCE = 2075923;
const START = CHECKPOINTS[2074518];
const SAVE_EVERY = 400;
const LOADER_OPTIONS = {
  format: "wasm32-unknown-emscripten",
  inputEncoding: "JSON-1",
  outputEncoding: "JSON-1",
  memoryLimit: "524288000",
  computeLimit: 9000000000000,
  extensions: [],
};

const ORIGINAL_RETURN = "  return async (buffer, msg, env) => {";
const ORIGINAL_MEMORY = `      return {
        Memory: instance.HEAPU8.slice(),`;
const ORIGINAL_TAIL = `      buffer = null;
    }
  };
};
`;
const PATCHED_RETURN = "  const run = async (buffer, msg, env, opts) => {";
const PATCHED_MEMORY = `      const copyOut = !opts || opts.copyMemory !== false;
      return {
        Memory: copyOut ? instance.HEAPU8.slice() : null,`;
const PATCHED_TAIL = `      buffer = null;
    }
  };
  run.exportHeap = () => instance.HEAPU8;
  return run;
};
`;

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function msSince(start) {
  return Number(nowNs() - start) / 1e6;
}

function signatureOf(item) {
  return Buffer.from(item.subarray(2, 514)).toString("base64url");
}

function loadContext() {
  const processTx = readJson(`${DATA}/p7/process-tx.json`);
  const processTags = readJson(`${DATA}/p7/process-tags.json`);
  const moduleDoc = readJson(`${WT}/evidence/p2/20261017T1645Z-p2a/module.json`);
  const aoGlobal = {
    Process: { Id: PROCESS_ID, Owner: processTx.owner.address, Tags: processTags },
    Module: {
      Id: "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0",
      Owner: moduleDoc.owner,
      Tags: Object.entries(moduleDoc.tags).map(([name, value]) => ({ name, value })),
    },
  };
  const manifest = readJson(`${WT}/evidence/p4-tail/20261017T052614Z-w-tail/messages-manifest.json`);
  const byMessage = new Map(manifest.files.map((row) => [row.message_id, row]));
  const assignments = readJson(`${WT}/evidence/p4-tail/20261017T052614Z-w-tail/assignments.json`)
    .filter((row) => row.nonce > START.nonce && row.nonce <= TAIL_NONCE)
    .sort((a, b) => a.nonce - b.nonce);
  if (assignments.length !== TAIL_NONCE - START.nonce) {
    throw new Error(`expected ${TAIL_NONCE - START.nonce} assignments, got ${assignments.length}`);
  }
  const blocks = readJson(`${DATA}/p7/tail-blocks/blocks.json`)
    .map((block) => ({ height: block.height, timestamp: block.timestamp * 1000 }))
    .sort((a, b) => a.height - b.height);
  return { processTx, aoGlobal, byMessage, assignments, blocks };
}

function storedMessage(row, byMessage) {
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

function buildItems(ctx) {
  const items = [];
  let left = { timestamp: START.timestamp, height: START.height };
  for (const row of ctx.assignments) {
    const point = {
      id: row.assignment_id,
      nonce: row.nonce,
      epoch: Number(row.epoch),
      timestamp: Number(row.timestamp_ms),
      height: Number(row.assignment_block_height),
      hashChain: row.hash_chain,
      messageId: row.message_id,
    };
    for (const cron of cronsBetween(left, point.timestamp, ctx.blocks)) {
      if (cron.timestamp === left.timestamp) continue;
      items.push({ ...cron, message: cronMessage(cron, ctx.aoGlobal) });
    }
    const stored = storedMessage(row, ctx.byMessage);
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

function actionOf(item) {
  const tags = item.message && item.message.Tags;
  if (!tags) return null;
  const tag = tags.find((entry) => entry.name === "Action");
  return tag ? tag.value : null;
}

function assertStreamMatchesSteps(items) {
  const rows = parseJsonLines(readFileSync(`${MAIN_RAW}/steps.jsonl`, "utf8"));
  let mismatches = 0;
  const samples = [];
  for (const row of rows) {
    const item = items[row.index];
    const kindOk = item && item.kind === row.kind;
    const nonceOk = item && (item.nonce ?? null) === row.nonce;
    const timeOk = item && item.timestamp === row.timestamp;
    const heightOk = item && item.height === row.height;
    if (!kindOk || !nonceOk || !timeOk || !heightOk) {
      mismatches += 1;
      if (samples.length < 5) {
        samples.push({
          index: row.index,
          step: { kind: row.kind, nonce: row.nonce, timestamp: row.timestamp, height: row.height },
          item: item && { kind: item.kind, nonce: item.nonce ?? null, timestamp: item.timestamp, height: item.height },
        });
      }
    }
  }
  return { step_lines: rows.length, mismatches, samples, items: items.length };
}

function patchLoader() {
  const src = readFileSync(LOADER_SRC, "utf8");
  if (!src.includes(ORIGINAL_RETURN)) throw new Error("loader return pattern missing");
  if (src.split(ORIGINAL_RETURN).length !== 2) throw new Error("loader return pattern is not unique");
  if (!src.includes(ORIGINAL_MEMORY)) throw new Error("loader memory pattern missing");
  if (!src.includes(ORIGINAL_TAIL)) throw new Error("loader tail pattern missing");
  let next = src.replace(ORIGINAL_RETURN, PATCHED_RETURN);
  next = next.replace(ORIGINAL_MEMORY, PATCHED_MEMORY);
  next = next.replace(ORIGINAL_TAIL, PATCHED_TAIL);
  if (next === src) throw new Error("loader patch did not change the file");
  mkdirSync(`${DATA}/fast`, { recursive: true });
  writeFileSync(LOADER_PATCH, next);
  return {
    path: LOADER_PATCH,
    bytes: Buffer.byteLength(next),
    sha256: sha256(Buffer.from(next)),
    source_sha256: sha256(Buffer.from(src)),
  };
}

async function createHandle(inplace) {
  let loaderPath = null;
  let patch = null;
  const AoLoader = inplace
    ? (patch = patchLoader(), loaderPath = patch.path, require(loaderPath))
    : require("@permaweb/ao-loader");
  const wasm = readFileSync(`${DATA}/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm`);
  const handle = await AoLoader(wasm, LOADER_OPTIONS);
  return { handle, wasmSha256: sha256(wasm), patch, loaderPath };
}

function loadCheckpoint() {
  const memory = gunzipSync(readFileSync(`${DATA}/checkpoints/${START.id}.bin`));
  const digest = sha256(memory);
  if (digest !== START.sha256) {
    throw new Error(`checkpoint gunzip sha mismatch ${digest}`);
  }
  return memory;
}

function messageData(result) {
  return (result.Messages || []).map((message) => (message.Data == null ? "" : String(message.Data))).join("");
}

async function readAction(handle, memory, aoGlobal, owner, action, timestamp, height) {
  const result = await handle(Buffer.from(memory), {
    Owner: owner,
    From: owner,
    Target: PROCESS_ID,
    Tags: [{ name: "Action", value: action }],
    Data: "",
    Timestamp: timestamp,
    "Block-Height": height,
    Cron: false,
    "Read-Only": true,
  }, aoGlobal);
  return {
    error: result.Error ? String(result.Error).slice(0, 400) : null,
    output: typeof result.Output === "string" ? result.Output : JSON.stringify(result.Output ?? null),
    data: messageData(result),
  };
}

function parseMap(text) {
  const value = JSON.parse(text);
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Balances Data is not an address map");
  }
  return value;
}

function sumMap(map) {
  let sum = 0n;
  for (const value of Object.values(map)) sum += BigInt(value);
  return sum;
}

function diffMaps(left, right) {
  const changed = [];
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  for (const address of keys) {
    if (left[address] !== right[address]) {
      changed.push({ address, left: left[address] ?? null, right: right[address] ?? null });
    }
  }
  changed.sort((a, b) => a.address.localeCompare(b.address));
  return {
    left_addresses: Object.keys(left).length,
    right_addresses: Object.keys(right).length,
    changed: changed.length,
    sample: changed.slice(0, 12),
  };
}

function humanRaw(raw) {
  const negative = raw.startsWith("-");
  const digits = (negative ? raw.slice(1) : raw).replace(/^0+/, "") || "0";
  const padded = digits.padStart(13, "0");
  const whole = padded.slice(0, -12).replace(/^0+/, "") || "0";
  const frac = padded.slice(-12).replace(/0+$/, "");
  const text = frac ? `${whole}.${frac}` : whole;
  return negative ? `-${text}` : text;
}

function writeLedger(dir, map) {
  const addresses = Object.keys(map).sort();
  const ordered = {};
  const lines = ["address,raw_balance,human_balance_12dp"];
  for (const address of addresses) {
    ordered[address] = map[address];
    lines.push(`${address},${map[address]},${humanRaw(String(map[address]))}`);
  }
  writeFileSync(`${dir}/balances.json`, JSON.stringify(ordered));
  writeFileSync(`${dir}/balances.csv`, `${lines.join("\n")}\n`);
  return {
    balances_json: `${dir}/balances.json`,
    balances_csv: `${dir}/balances.csv`,
    balances_json_sha256: sha256(readFileSync(`${dir}/balances.json`)),
    balances_csv_sha256: sha256(readFileSync(`${dir}/balances.csv`)),
    addresses: addresses.length,
  };
}

function parseJsonLines(text) {
  const rows = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line) continue;
    try {
      rows.push(JSON.parse(line));
    } catch (error) {
      if (i === lines.length - 1) continue;
      throw error;
    }
  }
  return rows;
}

function readMainSteps() {
  const byIndex = new Map();
  for (const row of parseJsonLines(readFileSync(`${MAIN_RAW}/steps.jsonl`, "utf8"))) {
    byIndex.set(row.index, row);
  }
  return byIndex;
}

function snapshotMainCursor() {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const before = readJson(`${MAIN_RAW}/cursor.json`);
    const memory = readFileSync(`${MAIN_RAW}/${before.memory_file}`);
    const after = readJson(`${MAIN_RAW}/cursor.json`);
    const digest = sha256(memory);
    if (before.memory_sha256 === after.memory_sha256 && digest === before.memory_sha256 && before.next_index === after.next_index) {
      return { cursor: after, memory };
    }
  }
  throw new Error("main cursor changed while it was copied");
}

async function applyOne(handle, heapLoaded, memory, item, mode) {
  if (mode === "safe") {
    let thrown = null;
    let result;
    try {
      result = await handle(memory, item.message, aoGlobalHolder.current);
    } catch (error) {
      thrown = String(error && error.message ? error.message : error);
      result = { Error: thrown, Memory: memory };
    }
    if (result && result.Error) {
      return { memory, applied: false, error: String(result.Error).slice(0, 240), heapLoaded: false };
    }
    return { memory: result.Memory, applied: true, error: null, heapLoaded: false };
  }
  let thrown = null;
  let result;
  try {
    result = await handle(heapLoaded ? null : memory, item.message, aoGlobalHolder.current, { copyMemory: false });
  } catch (error) {
    thrown = String(error && error.message ? error.message : error);
    result = { Error: thrown };
  }
  if (result && result.Error) {
    return { memory, applied: false, error: String(result.Error).slice(0, 240), heapLoaded, thrown: true };
  }
  return { memory, applied: true, error: null, heapLoaded: true };
}

const aoGlobalHolder = { current: null };

async function replayRange(options) {
  const {
    handle,
    items,
    mode,
    startIndex,
    endIndex,
    memory: initialMemory,
    dir,
    logName,
  } = options;
  mkdirSync(dir, { recursive: true });
  const logPath = `${dir}/${logName}`;
  const cursorPath = `${dir}/cursor.json`;
  let memory = initialMemory;
  let heapLoaded = false;
  let applied = 0;
  let handlerErrors = 0;
  let sinceSave = 0;
  let saveIndex = startIndex;
  if (existsSync(cursorPath) && options.resume) {
    const cursor = readJson(cursorPath);
    if (sha256(readFileSync(`${dir}/${cursor.memory_file}`)) !== cursor.memory_sha256) {
      throw new Error("local resume memory hash mismatch");
    }
    memory = readFileSync(`${dir}/${cursor.memory_file}`);
    saveIndex = cursor.next_index;
    applied = cursor.applied;
    handlerErrors = cursor.handler_errors;
    sinceSave = 0;
    heapLoaded = false;
  }
  const indexStart = options.resume && existsSync(cursorPath) ? saveIndex : startIndex;
  function currentBytes() {
    if (mode === "inplace" && heapLoaded) return handle.exportHeap();
    return memory;
  }
  function persist(nextIndex) {
    const bytes = Buffer.from(currentBytes());
    writeFileSync(`${dir}/memory.bin`, bytes);
    memory = bytes;
    const row = {
      next_index: nextIndex,
      memory_file: "memory.bin",
      memory_sha256: sha256(bytes),
      memory_bytes: bytes.length,
      applied,
      handler_errors: handlerErrors,
      mode,
      height_source: "gateway block timestamps, cronsBetween from recovery/p6/replay.mjs",
    };
    writeFileSync(cursorPath, JSON.stringify(row));
    writeFileSync(`${dir}/progress.json`, JSON.stringify({ ...row, at: new Date().toISOString() }));
    return row;
  }
  function restoreToSave() {
    const heap = handle.exportHeap();
    if (heap.length !== memory.length) {
      throw new Error(`heap length ${heap.length} != saved memory ${memory.length}`);
    }
    heap.set(memory);
    heapLoaded = true;
  }
  for (let index = indexStart; index < endIndex; index += 1) {
    const item = items[index];
    const outcome = await applyOne(handle, heapLoaded, memory, item, mode);
    if (!outcome.applied && mode === "inplace") {
      restoreToSave();
      for (let redo = saveIndex; redo < index; redo += 1) {
        const again = await applyOne(handle, heapLoaded, memory, items[redo], mode);
        if (!again.applied) {
          throw new Error(`replay of saved batch failed at ${redo}: ${again.error}`);
        }
        heapLoaded = true;
      }
      handlerErrors += 1;
    } else if (!outcome.applied) {
      memory = outcome.memory;
      heapLoaded = false;
      handlerErrors += 1;
    } else {
      memory = outcome.memory;
      heapLoaded = outcome.heapLoaded;
      applied += 1;
    }
    sinceSave += 1;
    if (index % 25 === 0) {
      writeFileSync(`${dir}/progress.json`, JSON.stringify({
        index,
        next_index: index + 1,
        applied,
        handler_errors: handlerErrors,
        mode,
        at: new Date().toISOString(),
      }));
    }
    const atSave = sinceSave >= SAVE_EVERY;
    if (item.kind === "assignment" || !outcome.applied || atSave) {
      const bytes = currentBytes();
      const row = {
        index,
        kind: item.kind,
        nonce: item.nonce ?? null,
        timestamp: item.timestamp,
        height: item.height,
        bytes: bytes.length,
        sha256: sha256(bytes),
        applied: outcome.applied,
        error: outcome.error,
      };
      writeFileSync(logPath, `${JSON.stringify(row)}\n`, { flag: "a" });
      if (item.kind === "assignment" || !outcome.applied) {
        process.stdout.write(`${JSON.stringify(row)}\n`);
      }
    }
    if (atSave || !outcome.applied) {
      persist(index + 1);
      saveIndex = index + 1;
      sinceSave = 0;
      heapLoaded = mode === "inplace";
    }
  }
  const finalRow = persist(endIndex);
  return { applied, handlerErrors, finalRow, logPath };
}

function compareLogToMain(logPath) {
  const main = readMainSteps();
  const rows = parseJsonLines(readFileSync(logPath, "utf8"));
  const mismatches = [];
  const pending = [];
  for (const row of rows) {
    const other = main.get(row.index);
    if (!other) {
      pending.push(row.index);
      continue;
    }
    if (other.sha256 !== row.sha256 || other.applied !== row.applied || (other.nonce ?? null) !== (row.nonce ?? null)) {
      mismatches.push({
        index: row.index,
        kind: row.kind,
        nonce: row.nonce,
        ours: row.sha256,
        main: other.sha256,
        applied_ours: row.applied,
        applied_main: other.applied,
      });
    }
  }
  return { compared: rows.length - pending.length, pending: pending.length, mismatches };
}

async function probe(items, aoGlobal, processTx) {
  aoGlobalHolder.current = aoGlobal;
  const report = {
    loader_version: "0.0.44",
    node: process.version,
    claim: "快速估计准备。probe 不是 P7 正式结果。",
  };
  const checkpoint = loadCheckpoint();
  report.checkpoint_bytes = checkpoint.length;
  report.checkpoint_sha256 = sha256(checkpoint);
  let started = nowNs();
  const copied = Buffer.from(checkpoint);
  report.buffer_from_ms = Number(msSince(started).toFixed(1));
  started = nowNs();
  report.sha256_ms = Number(msSince(started).toFixed(1));
  report.copy_matches = sha256(copied) === report.checkpoint_sha256;

  const safe = await createHandle(false);
  report.wasm_sha256 = safe.wasmSha256;
  const first = items[0];
  const second = items[1];
  const before = sha256(checkpoint);
  started = nowNs();
  const firstResult = await safe.handle(checkpoint, first.message, aoGlobal);
  report.first_handle_ms = Number(msSince(started).toFixed(1));
  report.input_untouched = sha256(checkpoint) === before;
  report.result_is_distinct = firstResult.Memory !== checkpoint && Buffer.isBuffer(firstResult.Memory) === false;
  const firstSha = sha256(firstResult.Memory);
  started = nowNs();
  await safe.handle(firstResult.Memory, second.message, aoGlobal);
  report.second_handle_ms = Number(msSince(started).toFixed(1));
  report.first_output_stable = sha256(firstResult.Memory) === firstSha;
  report.first_error = firstResult.Error ? String(firstResult.Error).slice(0, 240) : null;

  const owner = processTx.owner.address;
  const stamp = { timestamp: first.timestamp, height: first.height };
  const beforeBalances = parseMap((await readAction(safe.handle, checkpoint, aoGlobal, owner, "Balances", stamp.timestamp, stamp.height)).data);
  const afterBalances = parseMap((await readAction(safe.handle, firstResult.Memory, aoGlobal, owner, "Balances", stamp.timestamp, stamp.height)).data);
  report.one_cron_balance_diff = diffMaps(beforeBalances, afterBalances);
  report.one_cron_sum = sumMap(beforeBalances).toString();

  let memory = checkpoint;
  started = nowNs();
  for (let index = 0; index < 10; index += 1) {
    const result = await safe.handle(memory, items[index].message, aoGlobal);
    if (result.Error) throw new Error(`safe probe error at ${index}: ${result.Error}`);
    memory = result.Memory;
  }
  report.safe10_ms = Number(msSince(started).toFixed(1));
  report.safe10_sha256 = sha256(memory);

  memory = checkpoint;
  started = nowNs();
  for (let index = 0; index < 10; index += 1) {
    const result = await safe.handle(memory, items[index].message, aoGlobal);
    if (result.Error) throw new Error(`bufferfrom probe error at ${index}: ${result.Error}`);
    memory = Buffer.from(result.Memory);
  }
  report.bufferfrom10_ms = Number(msSince(started).toFixed(1));
  report.bufferfrom10_sha256 = sha256(memory);
  report.bufferfrom_matches_safe10 = report.bufferfrom10_sha256 === report.safe10_sha256;

  const fast = await createHandle(true);
  report.loader_patch = fast.patch;
  started = nowNs();
  let result = await fast.handle(checkpoint, items[0].message, aoGlobal, { copyMemory: false });
  if (result.Error) throw new Error(`inplace probe error at 0: ${result.Error}`);
  for (let index = 1; index < 10; index += 1) {
    result = await fast.handle(null, items[index].message, aoGlobal, { copyMemory: false });
    if (result.Error) throw new Error(`inplace probe error at ${index}: ${result.Error}`);
  }
  report.inplace10_ms = Number(msSince(started).toFixed(1));
  report.inplace10_sha256 = sha256(fast.handle.exportHeap());
  report.inplace_matches_safe10 = report.inplace10_sha256 === report.safe10_sha256;

  const firstAssignment = items.findIndex((item) => item.kind === "assignment");
  const secondAssignment = items.findIndex((item, index) => index > firstAssignment && item.kind === "assignment");
  started = nowNs();
  result = await fast.handle(checkpoint, items[0].message, aoGlobal, { copyMemory: false });
  if (result.Error) throw new Error(String(result.Error));
  for (let index = 1; index <= secondAssignment; index += 1) {
    result = await fast.handle(null, items[index].message, aoGlobal, { copyMemory: false });
    if (result.Error) throw new Error(`cron-path error at ${index}: ${result.Error}`);
  }
  report.prefix_through_second_assignment_ms = Number(msSince(started).toFixed(1));
  const withCrons = Buffer.from(fast.handle.exportHeap());
  const withCronBalances = parseMap((await readAction(
    fast.handle,
    withCrons,
    aoGlobal,
    owner,
    "Balances",
    items[secondAssignment].timestamp,
    items[secondAssignment].height,
  )).data);
  result = await fast.handle(checkpoint, items[firstAssignment].message, aoGlobal, { copyMemory: true });
  if (result.Error) throw new Error(`assignment-only first error: ${result.Error}`);
  result = await fast.handle(result.Memory, items[secondAssignment].message, aoGlobal, { copyMemory: true });
  if (result.Error) throw new Error(`assignment-only second error: ${result.Error}`);
  const assignBalances = parseMap((await readAction(
    fast.handle,
    result.Memory,
    aoGlobal,
    owner,
    "Balances",
    items[secondAssignment].timestamp,
    items[secondAssignment].height,
  )).data);
  report.assignment_prefix = {
    first_index: firstAssignment,
    first_nonce: items[firstAssignment].nonce,
    first_action: actionOf(items[firstAssignment]),
    second_index: secondAssignment,
    second_nonce: items[secondAssignment].nonce,
    second_action: actionOf(items[secondAssignment]),
    items_with_crons: secondAssignment + 1,
    balance_diff_against_assignment_only: diffMaps(withCronBalances, assignBalances),
  };
  report.safe10_items_per_min = Number((10 / (report.safe10_ms / 60000)).toFixed(2));
  report.inplace10_items_per_min = Number((10 / (report.inplace10_ms / 60000)).toFixed(2));
  report.inplace_over_safe = Number((report.safe10_ms / report.inplace10_ms).toFixed(3));
  return report;
}

function argValue(flag, fallback) {
  const index = process.argv.indexOf(flag);
  if (index === -1) return fallback;
  return process.argv[index + 1];
}

async function main() {
  const started = nowNs();
  const ctx = loadContext();
  aoGlobalHolder.current = ctx.aoGlobal;
  const items = buildItems(ctx);
  const summary = {
    height_source: "gateway block timestamps, cronsBetween from recovery/p6/replay.mjs",
    from_nonce: START.nonce,
    to_nonce: TAIL_NONCE,
    messages: items.length,
    crons: items.filter((item) => item.kind === "cron").length,
    assignments: items.filter((item) => item.kind === "assignment").length,
    first: { kind: items[0].kind, timestamp: items[0].timestamp, height: items[0].height, nonce: items[0].nonce ?? null },
    last: { kind: items.at(-1).kind, nonce: items.at(-1).nonce ?? null, timestamp: items.at(-1).timestamp, action: actionOf(items.at(-1)) },
    build_ms: Number(msSince(started).toFixed(1)),
  };
  if (process.argv.includes("--dry-run")) {
    const stream = assertStreamMatchesSteps(items);
    process.stdout.write(`${JSON.stringify({ ...summary, stream }, null, 2)}\n`);
    if (stream.mismatches) process.exitCode = 2;
    return;
  }
  if (process.argv.includes("--probe")) {
    const stream = assertStreamMatchesSteps(items);
    if (stream.mismatches) throw new Error(`stream mismatch ${JSON.stringify(stream.samples)}`);
    const report = await probe(items, ctx.aoGlobal, ctx.processTx);
    report.stream = { step_lines: stream.step_lines, mismatches: stream.mismatches, items: stream.items };
    report.summary = summary;
    const out = argValue("--out", "");
    if (out) writeFileSync(out, JSON.stringify(report, null, 2));
    process.stdout.write(`${JSON.stringify(report)}\n`);
    return;
  }
  const stream = assertStreamMatchesSteps(items);
  if (stream.mismatches) throw new Error(`stream mismatch ${JSON.stringify(stream.samples)}`);
  const mode = argValue("--mode", "inplace");
  if (mode !== "inplace" && mode !== "safe") throw new Error(`unknown mode ${mode}`);
  const verify = process.argv.includes("--verify");
  const dir = verify ? `${DATA}/fast/verify` : `${DATA}/fast/tail`;
  mkdirSync(dir, { recursive: true });
  const made = await createHandle(mode === "inplace");
  let startIndex = 0;
  let memory;
  let resume = false;
  if (!verify && existsSync(`${dir}/cursor.json`)) {
    resume = true;
    startIndex = readJson(`${dir}/cursor.json`).next_index;
    memory = null;
  } else {
    const shot = snapshotMainCursor();
    writeFileSync(`${dir}/source-cursor.json`, JSON.stringify(shot.cursor, null, 2));
    copyFileSync(`${MAIN_RAW}/${shot.cursor.memory_file}`, `${dir}/memory.bin`);
    memory = shot.memory;
    startIndex = shot.cursor.next_index;
    writeFileSync(`${dir}/cursor.json`, JSON.stringify({
      next_index: startIndex,
      memory_file: "memory.bin",
      memory_sha256: shot.cursor.memory_sha256,
      memory_bytes: memory.length,
      applied: shot.cursor.applied,
      handler_errors: shot.cursor.handler_errors,
      mode,
      copied_from: MAIN_RAW,
    }));
    resume = true;
  }
  const count = verify ? Number(argValue("--count", "480")) : items.length - startIndex;
  const endIndex = Math.min(items.length, startIndex + count);
  const logName = "steps.jsonl";
  if (!resume) throw new Error("replay start missing");
  if (verify && existsSync(`${dir}/${logName}`)) {
    writeFileSync(`${dir}/${logName}`, "");
  }
  const replayStarted = nowNs();
  const outcome = await replayRange({
    handle: made.handle,
    items,
    mode,
    startIndex,
    endIndex,
    memory,
    dir,
    logName,
    resume: true,
  });
  const replayMs = msSince(replayStarted);
  let ledger = null;
  if (!verify) {
    const mem = readFileSync(`${dir}/memory.bin`);
    if (sha256(mem) !== outcome.finalRow.memory_sha256) throw new Error("final memory hash mismatch");
    const owner = ctx.processTx.owner.address;
    const last = items[endIndex - 1];
    const balances = await readAction(made.handle, mem, ctx.aoGlobal, owner, "Balances", last.timestamp, last.height);
    const supply = await readAction(made.handle, mem, ctx.aoGlobal, owner, "Total-Supply", last.timestamp, last.height);
    if (balances.error) throw new Error(`Balances read failed: ${balances.error}`);
    const map = parseMap(balances.data);
    const sum = sumMap(map);
    const supplyText = (supply.data || "").trim();
    ledger = {
      total_supply_data: supply.data,
      total_supply_error: supply.error,
      total_supply_output: supply.output,
      balance_sum: sum.toString(),
      sum_equals_supply: supplyText === sum.toString(),
      balance_output: balances.output,
      ...writeLedger(dir, map),
    };
  }
  let comparison = compareLogToMain(`${dir}/${logName}`);
  const waitMs = verify ? Number(argValue("--wait-ms", "900000")) : 0;
  const waitStart = Date.now();
  while (comparison.pending > 0 && comparison.mismatches.length === 0 && Date.now() - waitStart < waitMs) {
    await new Promise((resolve) => setTimeout(resolve, 15000));
    comparison = compareLogToMain(`${dir}/${logName}`);
  }
  const report = {
    ...summary,
    mode,
    dir,
    start_index: startIndex,
    end_index: endIndex,
    applied: outcome.applied,
    handler_errors: outcome.handlerErrors,
    memory_sha256: outcome.finalRow.memory_sha256,
    memory_bytes: outcome.finalRow.memory_bytes,
    comparison,
    loader_patch: made.patch,
    replay_ms: Number(replayMs.toFixed(1)),
    elapsed_ms: Number(msSince(started).toFixed(1)),
    items_per_min: Number(((endIndex - startIndex) / (replayMs / 60000)).toFixed(2)),
    ledger,
    fast_estimate: false,
    goal_complete: false,
  };
  writeFileSync(`${dir}/report.json`, JSON.stringify(report, null, 2));
  process.stdout.write(`${JSON.stringify(report)}\n`);
  if (comparison.mismatches.length) process.exitCode = 3;
}

const invoked = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/")) || process.argv[1] && process.argv[1].endsWith("tail-replay-fast.mjs");
if (invoked) {
  main().catch((error) => {
    process.stderr.write(`${error.stack || error}\n`);
    process.exit(1);
  });
}

export {
  DATA,
  START,
  TAIL_NONCE,
  actionOf,
  buildItems,
  createHandle,
  diffMaps,
  humanRaw,
  loadCheckpoint,
  loadContext,
  parseMap,
  readAction,
  sha256,
  sumMap,
  writeLedger,
  nowNs,
};

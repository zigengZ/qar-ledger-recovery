/**
 * Replay a short LegacyNet CU span between two qAR checkpoints.
 *
 * Semantics are pinned to permaweb/ao 0db88a45aabeb5e88471e5c263790fa51a563461
 * (2026-02-22, the main commit before checkpoint nonce 2074518):
 *   servers/cu/src/domain/lib/loadMessages.js  cronMessagesBetweenWith / parseCrons
 *   servers/cu/src/effects/ao-su.js            mapNode
 *   servers/cu/src/domain/utils.js             mapFrom / mapForwardedBy
 *   servers/cu/src/domain/lib/hydrateMessages.js
 *   servers/cu/src/effects/wasm.js             hashWasmMemory (sha256 of gunzip)
 * Evaluator: @permaweb/ao-loader 0.0.44, the exact version in that CU lockfile.
 *
 * Usage:
 *   node --max-old-space-size=8192 replay.mjs --gate A
 *   node --max-old-space-size=8192 replay.mjs --gate B
 *   node replay.mjs --dry-run
 */
import { createHash } from "node:crypto";
import { gunzipSync } from "node:zlib";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "../..");

const require = createRequire(import.meta.url);

const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";
const RAW = join(REPO, "data/raw/eval/20261017T052333Z-w-eval");
const GQL = join(RAW, "gql");
const CK = join(REPO, "data/raw/checkpoints");
const WASM = join(REPO, "data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm");
const MODULE_SHA = "164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8";

/**
 * Process block on Arweave is 1726164008 (phase 8 mod 300). The three
 * checkpoint seconds are phase 283. isTimestampOnCron uses the SU process
 * timestamp, and the current SU router returns 403 for this process, so the
 * exact millisecond is not on the gateway. Any origin second congruent to
 * 283 mod 300 selects the same crons in this window. 1726163983 is the
 * process-block second shifted by -25s onto that phase. Both -25s and +275s
 * reproduce the checkpoint timestamps and Block-Height tags.
 */
const ORIGIN_MS = (1726164008 - 25) * 1000;
const CRON_SECONDS = 300;
const CRON_ID = "0-5-minutes";

const CHECKPOINTS = {
  2074508: {
    id: "EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk",
    sha256: "50d6b10a056a00e0db01dfcb5cfc9153b141d204b5a558d5e70391100137717e",
    timestamp: 1771783783818,
    height: 1862932,
    nonce: 2074508,
    cron: CRON_ID,
  },
  2074510: {
    id: "lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg",
    sha256: "b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1",
    timestamp: 1771817683241,
    height: 1863201,
    nonce: 2074510,
    cron: CRON_ID,
  },
  2074518: {
    id: "ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk",
    sha256: "fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26",
    timestamp: 1771847683094,
    height: 1863436,
    nonce: 2074518,
    cron: CRON_ID,
  },
};

const GATES = {
  A: { from: 2074508, to: 2074510 },
  B: { from: 2074510, to: 2074518 },
};

function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

function toSeconds(ms) {
  return Math.floor(ms / 1000);
}

function isTimestampOnCron(timestamp) {
  const t = toSeconds(timestamp);
  const origin = toSeconds(ORIGIN_MS);
  if (t === origin) return false;
  return (t - origin) % CRON_SECONDS === 0;
}

function loadJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function tagsOf(node) {
  return node.tags.map((tag) => ({ name: tag.name, value: tag.value }));
}

function tagMap(tags) {
  const out = {};
  for (const tag of tags) out[tag.name] = tag.value;
  return out;
}

function loadBlocks() {
  const blocks = [];
  const seen = new Set();
  for (let i = 0; i < 9; i++) {
    const doc = loadJson(`${GQL}/blocks-p${String(i).padStart(2, "0")}.response.json`);
    for (const edge of doc.data.blocks.edges) {
      const node = edge.node;
      if (seen.has(node.height)) continue;
      seen.add(node.height);
      blocks.push({ height: node.height, timestamp: node.timestamp * 1000 });
    }
  }
  blocks.sort((a, b) => a.height - b.height);
  return blocks;
}

function loadAssignments() {
  const doc = loadJson(`${GQL}/assignments-2074508-2074519.response.json`);
  return doc.data.transactions.edges.map((edge) => {
    const tags = tagsOf(edge.node);
    const map = tagMap(tags);
    return {
      id: edge.node.id,
      nonce: Number(map.Nonce),
      epoch: Number(map.Epoch),
      timestamp: Number(map.Timestamp),
      height: Number(map["Block-Height"]),
      hashChain: map["Hash-Chain"],
      messageId: map.Message,
    };
  }).sort((a, b) => a.nonce - b.nonce);
}

function loadMessages() {
  const doc = loadJson(`${GQL}/messages-2074509-2074518.response.json`);
  const byId = new Map();
  for (const edge of doc.data.transactions.edges) {
    const node = edge.node;
    const tags = tagsOf(node);
    const file = readFileSync(`${RAW}/messages/${node.id}.bin`);
    const htmlShell = file.subarray(0, 15).toString("utf8").startsWith("<!DOCTYPE");
    const data = htmlShell ? "" : file.toString("utf8");
    byId.set(node.id, {
      id: node.id,
      owner: node.owner.address,
      signature: node.signature,
      target: node.recipient || "",
      anchor: node.anchor ?? "",
      tags,
      data,
      graphqlSize: Number(node.data.size),
      httpBytes: file.length,
      htmlShell,
    });
  }
  return byId;
}

function loadAoGlobal() {
  const doc = loadJson(`${GQL}/txs-checkpoints-process-module.response.json`);
  const byId = new Map(doc.data.transactions.edges.map((edge) => [edge.node.id, edge.node]));
  const process = byId.get(PROCESS_ID);
  const module = byId.get(MODULE_ID);
  return {
    Process: {
      Id: PROCESS_ID,
      Owner: process.owner.address,
      Tags: tagsOf(process),
    },
    Module: {
      Id: MODULE_ID,
      Owner: module.owner.address,
      Tags: tagsOf(module),
    },
  };
}

/**
 * Cron messages strictly between left.timestamp and rightTimestamp,
 * matching cronMessagesBetweenWith: start at left, step 1000, stop before right.
 * Block-Height updates when the tick's second reaches the next gateway block.
 */
function cronsBetween(left, rightTimestamp, blocks) {
  const inRange = blocks.filter((block) => block.timestamp > left.timestamp && block.timestamp < rightTimestamp);
  let cur = { height: left.height, timestamp: left.timestamp };
  let index = 0;
  const out = [];
  for (let ts = left.timestamp; ts < rightTimestamp; ts += 1000) {
    if (index < inRange.length && toSeconds(ts) >= toSeconds(inRange[index].timestamp)) {
      cur = inRange[index];
      index += 1;
    }
    if (isTimestampOnCron(ts)) {
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

function decodeAnchor(anchor) {
  // arweave.net GraphQL returns the 32-byte anchor as base64. The CU message
  // that was evaluated, and that this process stored, is the decoded ASCII
  // (zero-padded Ref_). Empty anchors are null on the checkpoint.
  if (!anchor) return null;
  const raw = Buffer.from(anchor, "base64");
  const text = raw.toString("utf8");
  const roundTrip = Buffer.from(text, "utf8").toString("base64").replace(/=+$/, "");
  if (roundTrip === anchor.replace(/=+$/, "") && /^[\x20-\x7e]+$/.test(text)) return text;
  return anchor;
}

function assignmentMessage(row, stored, processId) {
  // Key order matches messageSchema in ao 0db88a45 (model.js). The process
  // json-encodes the table in insertion order.
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

function cronMessage(item, aoGlobal) {
  return {
    Owner: aoGlobal.Process.Owner,
    Target: PROCESS_ID,
    From: aoGlobal.Process.Owner,
    Tags: [{ name: "Action", value: "Cron" }],
    Timestamp: item.timestamp,
    "Block-Height": item.height,
    Cron: true,
    "Read-Only": false,
  };
}

function loadCronHeights(toNonce) {
  // Gateway simulation matches every cron timestamp and both final checkpoint
  // heights, but 9 intermediate crons per gate are 1–3 blocks higher than the
  // Block-Height on the cron message retained in the target checkpoint.
  // The exact memory hash matches only when those recorded heights are used.
  // `REPLAY_GATEWAY_HEIGHTS=1` skips the file and keeps the simulated heights.
  if (process.env.REPLAY_GATEWAY_HEIGHTS === "1") return new Map();
  const path = join(HERE, `cron-heights-${toNonce}.json`);
  const obj = JSON.parse(readFileSync(path, "utf8"));
  const map = new Map();
  for (const [key, value] of Object.entries(obj)) map.set(Number(key), value);
  return map;
}

function buildStream(fromNonce, toNonce, blocks, assignments, messages, aoGlobal) {
  const start = CHECKPOINTS[fromNonce];
  const target = CHECKPOINTS[toNonce];
  const scheduled = assignments.filter((row) => row.timestamp > start.timestamp && row.timestamp <= target.timestamp);
  const seen = new Set([`${start.timestamp}-${start.cron}`]);
  const cronHeights = loadCronHeights(toNonce);
  const items = [];
  let heightOverrides = 0;
  let left = { timestamp: start.timestamp, height: start.height };
  const points = [
    ...scheduled.map((row) => ({ kind: "assignment", row })),
    { kind: "end", timestamp: target.timestamp + 1000 },
  ];
  for (const point of points) {
    const right = point.kind === "assignment" ? point.row.timestamp : point.timestamp;
    for (const cron of cronsBetween(left, right, blocks)) {
      const key = `${cron.timestamp}-${cron.cron}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const recorded = cronHeights.get(cron.timestamp);
      const height = recorded == null ? cron.height : recorded;
      if (height !== cron.height) heightOverrides += 1;
      const fixed = { ...cron, height };
      items.push({
        ...fixed,
        message: cronMessage(fixed, aoGlobal),
      });
      if (cron.timestamp === target.timestamp) {
        items.heightOverrides = heightOverrides;
        return items;
      }
    }
    if (point.kind === "assignment") {
      const stored = messages.get(point.row.messageId);
      if (!stored) throw new Error(`missing message ${point.row.messageId}`);
      items.push({
        kind: "assignment",
        nonce: point.row.nonce,
        timestamp: point.row.timestamp,
        height: point.row.height,
        assignmentId: point.row.id,
        messageId: point.row.messageId,
        message: assignmentMessage(point.row, stored, PROCESS_ID),
      });
      left = { timestamp: point.row.timestamp, height: point.row.height };
    }
  }
  items.heightOverrides = heightOverrides;
  return items;
}

function wasmMessageView(message) {
  const view = {};
  for (const [key, value] of Object.entries(message)) {
    if (value !== undefined) view[key] = value;
  }
  return view;
}

function outputText(result) {
  const output = result && result.Output;
  if (output == null) return "";
  if (typeof output === "string") return output;
  if (typeof output === "object" && typeof output.data === "string") return output.data;
  return JSON.stringify(output);
}

async function replayGate(name, handleFactory) {
  const gate = GATES[name];
  const blocks = loadBlocks();
  const assignments = loadAssignments();
  const messages = loadMessages();
  const aoGlobal = loadAoGlobal();
  const stream = buildStream(gate.from, gate.to, blocks, assignments, messages, aoGlobal);
  const target = CHECKPOINTS[gate.to];
  const last = stream[stream.length - 1];
  const summary = {
    gate: name,
    from: gate.from,
    to: gate.to,
    messages: stream.length,
    crons: stream.filter((item) => item.kind === "cron").length,
    assignments: stream.filter((item) => item.kind === "assignment").length,
    first: stream[0] && { kind: stream[0].kind, timestamp: stream[0].timestamp, height: stream[0].height, nonce: stream[0].nonce },
    last: last && { kind: last.kind, timestamp: last.timestamp, height: last.height, nonce: last.nonce },
    targetHeight: target.height,
    lastHeightMatches: Boolean(last && last.timestamp === target.timestamp && last.height === target.height),
    heightOverrides: stream.heightOverrides || 0,
  };
  if (process.argv.includes("--dry-run")) {
    console.log(JSON.stringify(summary, null, 2));
    return summary;
  }
  if (!summary.lastHeightMatches) {
    throw new Error(`stream does not land on the target checkpoint: ${JSON.stringify(summary)}`);
  }

  const start = CHECKPOINTS[gate.from];
  const gzip = readFileSync(`${CK}/${start.id}.bin`);
  const memory = gunzipSync(gzip);
  if (sha256(memory) !== start.sha256) {
    throw new Error(`start checkpoint ${start.id} gunzip sha mismatch`);
  }

  const wasm = readFileSync(WASM);
  if (sha256(wasm) !== MODULE_SHA) throw new Error("module sha mismatch");
  const handle = await handleFactory(wasm);

  let current = memory;
  const log = [];
  let gas = 0n;
  const started = wallNow();
  for (let i = 0; i < stream.length; i++) {
    const item = stream[i];
    const before = current;
    let result;
    let thrown = null;
    try {
      result = await handle(current, wasmMessageView(item.message), aoGlobal);
    } catch (error) {
      thrown = error && error.message ? error.message : String(error);
      result = { Error: thrown, Memory: before };
    }
    const errored = Boolean(result && result.Error);
    if (errored) current = before;
    else current = Buffer.from(result.Memory);
    if (result && result.GasUsed != null) gas += BigInt(result.GasUsed);
    const row = {
      i,
      kind: item.kind,
      nonce: item.nonce ?? null,
      timestamp: item.timestamp,
      height: item.height,
      bytes: current.length,
      error: errored ? (thrown || outputText(result) || String(result.Error)).slice(0, 300) : null,
      output: outputText(result).slice(0, 180),
    };
    log.push(row);
    if (i % 20 === 0 || i === stream.length - 1 || errored) {
      console.log(JSON.stringify({ gate: name, ...row, elapsed_ms: wallNow() - started }));
    }
  }
  const got = sha256(current);
  const report = {
    ...summary,
    startSha256: start.sha256,
    expectedSha256: target.sha256,
    gotSha256: got,
    bytes: current.length,
    expectedBytes: memory.length,
    pass: got === target.sha256,
    gas: gas.toString(),
    errors: log.filter((row) => row.error).length,
    elapsed_ms: wallNow() - started,
    origin_ms: ORIGIN_MS,
    log,
  };
  const outDir = `${RAW}/replay`;
  mkdirSync(outDir, { recursive: true });
  const tag = process.env.REPLAY_TAG || "";
  writeFileSync(`${outDir}/gate-${name}${tag}.json`, JSON.stringify(report, null, 2));
  if (!report.pass || process.env.REPLAY_SAVE_MEMORY === "1") {
    writeFileSync(`${outDir}/gate-${name}${tag}.memory`, current);
  }
  console.log(JSON.stringify({
    gate: name,
    pass: report.pass,
    gotSha256: got,
    expectedSha256: target.sha256,
    messages: report.messages,
    crons: report.crons,
    assignments: report.assignments,
    errors: report.errors,
    bytes: report.bytes,
    elapsed_ms: report.elapsed_ms,
  }));
  return report;
}

// ao-loader's emscripten build replaces Date.now with a stub. Capture wall time first.
const wallNow = Date.now.bind(Date);

const options = {
  format: "wasm32-unknown-emscripten",
  inputEncoding: "JSON-1",
  outputEncoding: "JSON-1",
  memoryLimit: 524288000,
  computeLimit: 9000000000000,
  extensions: {},
  mode: "Assignments",
  blockHeight: 100,
};

async function main() {
  const { default: AoLoader } = await import("@permaweb/ao-loader");
  const dry = process.argv.includes("--dry-run");
  const wanted = process.argv.includes("--gate")
    ? [process.argv[process.argv.indexOf("--gate") + 1]]
    : ["A", "B"];
  const factory = async (wasm) => AoLoader(wasm, options);
  for (const name of wanted) {
    if (!GATES[name]) throw new Error(`unknown gate ${name}`);
    await replayGate(name, dry ? null : factory);
  }
}

export {
  CHECKPOINTS,
  ORIGIN_MS,
  PROCESS_ID,
  assignmentMessage,
  cronMessage,
  cronsBetween,
  decodeAnchor,
  sha256,
  wasmMessageView,
};

const invoked = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invoked) {
  const pkg = require("@permaweb/ao-loader/package.json");
  console.log(JSON.stringify({ loader: pkg.version, node: process.version, origin_ms: ORIGIN_MS }));
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

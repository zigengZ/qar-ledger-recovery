/**
 * Snapshot-to-snapshot gate for nonce 2074508 -> 2074510 and 2074518.
 *
 * Semantics are the LegacyNet CU in permaweb/ao 0db88a45
 * (servers/cu/src/domain/lib/loadMessages.js): a `5-minutes` cron is inserted
 * between scheduled assignments, and each assignment is evaluated with the
 * ao-loader message shape from effects/ao-su.js.
 */
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { gunzipSync } from "node:zlib";

const require = createRequire(import.meta.url);
const AoLoader = require("@permaweb/ao-loader");

const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const PROCESS_OWNER = "6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";
const ROOT = new URL("../../", import.meta.url);

const readJson = (path) => JSON.parse(readFileSync(new URL(path, ROOT)));

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

function cronsBetween(left, right, blocks, origin) {
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
        Cron: true,
        Owner: PROCESS_OWNER,
        Target: PROCESS_ID,
        From: PROCESS_OWNER,
        Tags: [{ name: "Action", value: "Cron" }],
        Timestamp: tick,
        "Block-Height": current.height,
      });
    }
  }
  return out;
}

function scheduledMessage(assignment, meta) {
  const fromProcess = meta.tags.find((tag) => tag.name === "From-Process");
  return {
    Id: meta.id,
    Signature: meta.signature,
    Owner: meta.owner,
    Target: PROCESS_ID,
    From: fromProcess?.value || meta.owner,
    "Forwarded-By": fromProcess ? meta.owner : undefined,
    Anchor: meta.anchor || undefined,
    Tags: meta.tags,
    Data: meta.data || "",
    Epoch: Number(assignment.epoch),
    Nonce: Number(assignment.nonce),
    Timestamp: Number(assignment.timestamp_ms),
    "Block-Height": Number(assignment.assignment_block_height),
    "Hash-Chain": assignment.hash_chain,
    Cron: false,
  };
}

const processTx = readJson("data/raw/p6/process.json").data.transaction;
const moduleDoc = readJson("evidence/p2/20261017T1645Z-p2a/module.json");
const assignments = readJson("data/raw/p6/assignments-2074508-2074518.json");
const messageMeta = readJson("data/raw/p6/messages-2074509-2074518.json");
const blockDoc = readJson("data/raw/p6/blocks-1862702-1863409.json");
const blocks = blockDoc.blocks
  .map((block) => ({ height: block.height, timestamp: block.timestamp * 1000 }))
  .sort((a, b) => a.height - b.height);
const byHeight = new Map(blocks.map((block) => [block.height, block]));
const origin = {
  height: blockDoc.origin[0].height,
  timestamp: blockDoc.origin[0].timestamp * 1000,
};

function blockOf(assignment) {
  const height = Number(assignment.assignment_block_height);
  const found = byHeight.get(height);
  if (!found) throw new Error(`missing block ${height}`);
  return found;
}

const env = {
  Process: {
    Id: PROCESS_ID,
    Owner: processTx.owner.address,
    Tags: processTx.tags,
  },
  Module: {
    Id: MODULE_ID,
    Owner: moduleDoc.owner,
    Tags: Object.entries(moduleDoc.tags).map(([name, value]) => ({ name, value })),
  },
};

const wasm = readFileSync(new URL("data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm", ROOT));
const handle = await AoLoader(wasm, {
  format: moduleDoc.tags["Module-Format"],
  inputEncoding: moduleDoc.tags["Input-Encoding"],
  outputEncoding: moduleDoc.tags["Output-Encoding"],
  memoryLimit: "524288000",
  computeLimit: Number(moduleDoc.tags["Compute-Limit"]),
  extensions: [],
});

let memory = gunzipSync(readFileSync(new URL(
  "data/raw/checkpoints/EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk.gz",
  ROOT,
)));
const startSha = sha256(memory);
console.log("start", memory.length, startSha);

const targets = {
  2074510: "b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1",
  2074518: "fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26",
};
const checks = [];
let cronCount = 0;
let scheduledCount = 0;
let previous = assignments[0];

for (const assignment of assignments.slice(1)) {
  const meta = messageMeta.find((row) => row.nonce === assignment.nonce);
  const crons = process.argv.includes("--no-cron")
    ? []
    : cronsBetween(blockOf(previous), blockOf(assignment), blocks, origin);
  cronCount += crons.length;
  for (const cron of crons) {
    const result = await handle(memory, cron, env);
    if (result.Error) {
      console.log("cron error", cron.Timestamp, String(result.Error).slice(0, 200));
    }
    memory = Buffer.from(memoryBytes(result.Memory));
  }
  scheduledCount += 1;
  const message = scheduledMessage(assignment, meta);
  const result = await handle(memory, message, env);
  if (result.Error) {
    console.log("msg error", assignment.nonce, String(result.Error).slice(0, 300));
  }
  memory = Buffer.from(memoryBytes(result.Memory));
  const digest = sha256(memory);
  console.log("nonce", assignment.nonce, "crons_before", crons.length, "mem", memory.length, digest);
  if (targets[assignment.nonce]) {
    checks.push({
      nonce: assignment.nonce,
      sha256: digest,
      expected: targets[assignment.nonce],
      match: digest === targets[assignment.nonce],
      memory_bytes: memory.length,
      error: result.Error ? String(result.Error) : null,
    });
  }
  previous = assignment;
}

const report = {
  start_sha256: startSha,
  cron_count: cronCount,
  scheduled_count: scheduledCount,
  checks,
};
const outName = process.argv.includes("--no-cron") ? "data/raw/p6/gate-run-nocron.json" : "data/raw/p6/gate-run.json";
writeFileSync(new URL(outName, ROOT), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

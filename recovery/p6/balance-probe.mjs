/** Read-only views of the real 2074518 memory and the no-cron replay. */
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { gunzipSync } from "node:zlib";

const require = createRequire(import.meta.url);
const AoLoader = require("@permaweb/ao-loader");
const ROOT = new URL("../../", import.meta.url);
const readJson = (path) => JSON.parse(readFileSync(new URL(path, ROOT)));

const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const PROCESS_OWNER = "6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
function memoryBytes(memory) {
  if (memory instanceof Uint8Array) return memory;
  if (ArrayBuffer.isView(memory)) return new Uint8Array(memory.buffer, memory.byteOffset, memory.byteLength);
  return new Uint8Array(memory);
}

const processTx = readJson("data/raw/p6/process.json").data.transaction;
const moduleDoc = readJson("evidence/p2/20261017T1645Z-p2a/module.json");
const assignments = readJson("data/raw/p6/assignments-2074508-2074518.json");
const messageMeta = readJson("data/raw/p6/messages-2074509-2074518.json");
const env = {
  Process: { Id: PROCESS_ID, Owner: processTx.owner.address, Tags: processTx.tags },
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

let replay = gunzipSync(readFileSync(new URL(
  "data/raw/checkpoints/EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk.gz",
  ROOT,
)));
for (const assignment of assignments.slice(1)) {
  const meta = messageMeta.find((row) => row.nonce === assignment.nonce);
  const result = await handle(replay, scheduledMessage(assignment, meta), env);
  replay = Buffer.from(memoryBytes(result.Memory));
}
const actual = gunzipSync(readFileSync(new URL(
  "data/raw/checkpoints/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.gz",
  ROOT,
)));

async function view(label, memory) {
  const views = {};
  for (const action of ["Info", "Total-Supply", "Balances"]) {
    const result = await handle(Buffer.from(memory), {
      Owner: PROCESS_OWNER,
      Target: PROCESS_ID,
      From: PROCESS_OWNER,
      Tags: [{ name: "Action", value: action }],
      Data: "",
      Timestamp: 1771844201094,
      "Block-Height": 1863409,
      Cron: false,
    }, env);
    const output = result.Output;
    const text = typeof output === "string" ? output : JSON.stringify(output);
    views[action] = {
      error: result.Error ? String(result.Error).slice(0, 400) : null,
      output_sha256: createHash("sha256").update(text).digest("hex"),
      output_bytes: text.length,
      output_head: text.slice(0, 240),
    };
  }
  return { label, memory_sha256: sha256(memory), views };
}

const report = {
  replay: await view("replay-nocron-2074518", replay),
  actual: await view("checkpoint-2074518", actual),
};
report.views_match = {};
for (const action of ["Info", "Total-Supply", "Balances"]) {
  report.views_match[action] = report.replay.views[action].output_sha256 === report.actual.views[action].output_sha256;
}
writeFileSync(new URL("data/raw/p6/balance-probe.json", ROOT), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

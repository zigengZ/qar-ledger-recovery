/**
 * Semantic ledger gate. Reads Balances and Total-Supply from a replayed
 * memory and from the real checkpoint, on copies, and compares every address.
 *
 * The Balances handler replies with ao.send. The JSON map is Messages[].Data.
 * Output is "[]" and is not the balance table.
 *
 * Usage:
 *   node --max-old-space-size=8192 semantic.mjs
 *
 * Expects replay memories written by:
 *   REPLAY_GATEWAY_HEIGHTS=1 REPLAY_TAG=-gateway REPLAY_SAVE_MEMORY=1 node replay.mjs
 */
import { createHash } from "node:crypto";
import { gunzipSync } from "node:zlib";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import AoLoader from "@permaweb/ao-loader";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "../..");
const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";
const RAW = join(REPO, "data/raw/eval/20261017T052333Z-w-eval");
const GQL = join(RAW, "gql");
const CK = join(REPO, "data/raw/checkpoints");
const WASM = join(REPO, "data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm");
const OUT = join(RAW, "semantic");

const GATES = [
  {
    name: "A",
    nonce: 2074510,
    checkpoint: "lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg",
    replay: `${RAW}/replay/gate-A-gateway.memory`,
    timestamp: 1771817683241,
    height: 1863201,
  },
  {
    name: "B",
    nonce: 2074518,
    checkpoint: "ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk",
    replay: `${RAW}/replay/gate-B-gateway.memory`,
    timestamp: 1771847683094,
    height: 1863436,
  },
];

function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

function loadEnv() {
  const doc = JSON.parse(readFileSync(`${GQL}/txs-checkpoints-process-module.response.json`, "utf8"));
  const byId = new Map(doc.data.transactions.edges.map((edge) => [edge.node.id, edge.node]));
  const process = byId.get(PROCESS_ID);
  const module = byId.get(MODULE_ID);
  const tags = (node) => node.tags.map((tag) => ({ name: tag.name, value: tag.value }));
  return {
    Process: { Id: PROCESS_ID, Owner: process.owner.address, Tags: tags(process) },
    Module: { Id: MODULE_ID, Owner: module.owner.address, Tags: tags(module) },
    owner: process.owner.address,
  };
}

function messageData(result) {
  const messages = result.Messages || [];
  return messages.map((message) => (message.Data == null ? "" : String(message.Data))).join("");
}

async function readAction(handle, memory, env, action, timestamp, height) {
  const result = await handle(Buffer.from(memory), {
    Owner: env.owner,
    From: env.owner,
    Target: PROCESS_ID,
    Tags: [{ name: "Action", value: action }],
    Data: "",
    Timestamp: timestamp,
    "Block-Height": height,
    Cron: false,
    "Read-Only": true,
  }, env);
  return {
    error: result.Error ? String(result.Error).slice(0, 400) : null,
    output: typeof result.Output === "string" ? result.Output : JSON.stringify(result.Output ?? null),
    data: messageData(result),
    messages: (result.Messages || []).length,
  };
}

function parseMap(text, label) {
  let value;
  try {
    value = JSON.parse(text);
  } catch (error) {
    throw new Error(`${label} Balances Data is not JSON (${text.length} bytes): ${error.message}`);
  }
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} Balances Data is not an address map`);
  }
  return value;
}

function sumMap(map) {
  let sum = 0n;
  for (const value of Object.values(map)) sum += BigInt(value);
  return sum;
}

function compareMaps(replay, checkpoint) {
  const onlyReplay = [];
  const onlyCheckpoint = [];
  const different = [];
  const keys = new Set([...Object.keys(replay), ...Object.keys(checkpoint)]);
  for (const address of keys) {
    const left = replay[address];
    const right = checkpoint[address];
    if (left == null) onlyCheckpoint.push({ address, checkpoint: right });
    else if (right == null) onlyReplay.push({ address, replay: left });
    else if (left !== right) different.push({ address, replay: left, checkpoint: right });
  }
  onlyReplay.sort((a, b) => a.address.localeCompare(b.address));
  onlyCheckpoint.sort((a, b) => a.address.localeCompare(b.address));
  different.sort((a, b) => a.address.localeCompare(b.address));
  return { onlyReplay, onlyCheckpoint, different };
}

function ascii(buf, start, end) {
  const slice = buf.subarray(start, end);
  let text = "";
  for (const byte of slice) text += byte >= 32 && byte < 127 ? String.fromCharCode(byte) : ".";
  return text.slice(0, 180);
}

function digits(text) {
  return text.match(/\d{8,}/g) || [];
}

function diffMemories(replay, checkpoint) {
  if (replay.length !== checkpoint.length) {
    return { sameLength: false, replayBytes: replay.length, checkpointBytes: checkpoint.length };
  }
  let diffBytes = 0;
  let runs = 0;
  let binaryRuns = 0;
  let textRuns = 0;
  let digitRuns = 0;
  const examples = [];
  const digitExamples = [];
  let index = 0;
  while (index < replay.length) {
    if (replay[index] === checkpoint[index]) {
      index += 1;
      continue;
    }
    const start = index;
    while (index < replay.length && replay[index] !== checkpoint[index]) index += 1;
    // Fold a short equal gap into the same region so one string is not split.
    while (index < replay.length) {
      let gap = index;
      while (gap < replay.length && gap - index < 24 && replay[gap] === checkpoint[gap]) gap += 1;
      if (gap >= replay.length || replay[gap] === checkpoint[gap]) break;
      index = gap;
      while (index < replay.length && replay[index] !== checkpoint[index]) index += 1;
    }
    runs += 1;
    // This count includes equal gaps shorter than 24 bytes that were folded in.
    // classify_regions.py records the exact differing-byte count.
    diffBytes += index - start;
    const windowStart = Math.max(0, start - 24);
    const windowEnd = Math.min(replay.length, index + 24);
    const left = ascii(replay, windowStart, windowEnd);
    const right = ascii(checkpoint, windowStart, windowEnd);
    const leftDigits = new Set(digits(left));
    const rightDigits = new Set(digits(right));
    const digitDelta = [...leftDigits].filter((value) => !rightDigits.has(value))
      .concat([...rightDigits].filter((value) => !leftDigits.has(value)));
    const printable = [...left, ...right].filter((char) => char !== ".").length;
    const binary = printable < (left.length + right.length) / 5;
    if (binary) binaryRuns += 1;
    else textRuns += 1;
    if (digitDelta.length) {
      digitRuns += 1;
      if (digitExamples.length < 12) {
        digitExamples.push({ start, length: index - start, digitDelta: digitDelta.slice(0, 6), replay: left, checkpoint: right });
      }
    }
    if (examples.length < 8) {
      examples.push({ start, length: index - start, binary, replay: left, checkpoint: right });
    }
  }
  return {
    sameLength: true,
    bytes: replay.length,
    diffBytes,
    runs,
    binaryRuns,
    textRuns,
    digitRuns,
    examples,
    digitExamples,
  };
}

async function main() {
  const env = loadEnv();
  const wasm = readFileSync(WASM);
  const handle = await AoLoader(wasm, {
    format: "wasm32-unknown-emscripten",
    inputEncoding: "JSON-1",
    outputEncoding: "JSON-1",
    memoryLimit: 524288000,
    computeLimit: 9000000000000,
    extensions: {},
  });
  mkdirSync(OUT, { recursive: true });
  const gates = [];
  for (const gate of GATES) {
    const replay = readFileSync(gate.replay);
    const checkpoint = gunzipSync(readFileSync(`${CK}/${gate.checkpoint}.bin`));
    const replayViews = {
      balances: await readAction(handle, replay, env, "Balances", gate.timestamp, gate.height),
      supply: await readAction(handle, replay, env, "Total-Supply", gate.timestamp, gate.height),
    };
    const checkpointViews = {
      balances: await readAction(handle, checkpoint, env, "Balances", gate.timestamp, gate.height),
      supply: await readAction(handle, checkpoint, env, "Total-Supply", gate.timestamp, gate.height),
    };
    const replayMap = parseMap(replayViews.balances.data, `${gate.name} replay`);
    const checkpointMap = parseMap(checkpointViews.balances.data, `${gate.name} checkpoint`);
    const compared = compareMaps(replayMap, checkpointMap);
    const replaySum = sumMap(replayMap);
    const checkpointSum = sumMap(checkpointMap);
    const replaySupply = replayViews.supply.data.trim();
    const checkpointSupply = checkpointViews.supply.data.trim();
    writeFileSync(`${OUT}/gate-${gate.name}-balances-replay.json`, JSON.stringify(replayMap));
    writeFileSync(`${OUT}/gate-${gate.name}-balances-checkpoint.json`, JSON.stringify(checkpointMap));
    const regions = diffMemories(replay, checkpoint);
    const report = {
      gate: gate.name,
      nonce: gate.nonce,
      checkpoint: gate.checkpoint,
      replaySha256: sha256(replay),
      checkpointSha256: sha256(checkpoint),
      byteMatch: sha256(replay) === sha256(checkpoint),
      addresses: {
        replay: Object.keys(replayMap).length,
        checkpoint: Object.keys(checkpointMap).length,
      },
      balanceDataSha256: {
        replay: sha256(replayViews.balances.data),
        checkpoint: sha256(checkpointViews.balances.data),
      },
      onlyReplay: compared.onlyReplay.length,
      onlyCheckpoint: compared.onlyCheckpoint.length,
      different: compared.different.length,
      differences: compared.different.slice(0, 50),
      onlyReplaySample: compared.onlyReplay.slice(0, 20),
      onlyCheckpointSample: compared.onlyCheckpoint.slice(0, 20),
      sum: { replay: replaySum.toString(), checkpoint: checkpointSum.toString(), match: replaySum === checkpointSum },
      totalSupply: {
        replay: replaySupply,
        checkpoint: checkpointSupply,
        match: replaySupply === checkpointSupply,
        replayOutput: replayViews.supply.output.slice(0, 180),
        balancesOutputIsEmptyList: replayViews.balances.output === "[]" && checkpointViews.balances.output === "[]",
      },
      sumEqualsSupply: {
        replay: replaySum.toString() === replaySupply,
        checkpoint: checkpointSum.toString() === checkpointSupply,
      },
      errors: {
        replayBalances: replayViews.balances.error,
        checkpointBalances: checkpointViews.balances.error,
        replaySupply: replayViews.supply.error,
        checkpointSupply: checkpointViews.supply.error,
      },
      regions,
      semanticPass: compared.onlyReplay.length === 0
        && compared.onlyCheckpoint.length === 0
        && compared.different.length === 0
        && replaySupply === checkpointSupply
        && replaySum.toString() === replaySupply
        && checkpointSum.toString() === checkpointSupply,
    };
    writeFileSync(`${OUT}/gate-${gate.name}.json`, JSON.stringify(report, null, 2));
    console.log(JSON.stringify({
      gate: gate.name,
      semanticPass: report.semanticPass,
      byteMatch: report.byteMatch,
      addresses: report.addresses,
      different: report.different,
      onlyReplay: report.onlyReplay,
      onlyCheckpoint: report.onlyCheckpoint,
      sum: report.sum,
      totalSupply: report.totalSupply,
      sumEqualsSupply: report.sumEqualsSupply,
      diffBytes: regions.diffBytes,
      runs: regions.runs,
      digitRuns: regions.digitRuns,
    }));
    gates.push(report);
  }
  const summary = {
    semanticPass: gates.every((gate) => gate.semanticPass),
    byteGatePass: gates.every((gate) => gate.byteMatch),
    gates: gates.map((gate) => ({
      gate: gate.gate,
      semanticPass: gate.semanticPass,
      byteMatch: gate.byteMatch,
      different: gate.different,
      totalSupply: gate.totalSupply.match,
      sumEqualsSupply: gate.sumEqualsSupply,
    })),
  };
  writeFileSync(`${OUT}/summary.json`, JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

/**
 * Read-only view of Unwraps and Deposits.
 *
 * Copies are opened from data/raw/unwrap. The fast-tail and checkpoint
 * files are not written. ao-loader 0.0.44 copies the buffer into WASM and
 * does not write it back. This script hashes that buffer again after the
 * calls. The probe is an Eval whose expression is require('json').encode.
 * Eval matches only when From is the process owner. Balances is read on
 * the input copy and on the memory the probe returns.
 *
 *   node --max-old-space-size=8192 --expose-gc probe.mjs tail
 *   node --max-old-space-size=8192 --expose-gc probe.mjs checkpoint
 */
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(join(REPO, "recovery/p6/package.json"));
const AoLoader = require("@permaweb/ao-loader");

const PROCESS_ID = "NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8";
const OWNER = "6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es";
const MODULE_ID = "1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0";
const RUN = "20261017T105845Z-w-unwrap";
const RAW = join(REPO, "data/raw/unwrap", RUN);
const WASM = join(REPO, "data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm");

const TARGETS = {
  tail: {
    label: "tail-2075923",
    path: `${RAW}/tail-memory.bin`,
    sha256: "25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a",
    timestamp: Date.parse("2026-07-04T06:19:55.380Z"),
    height: 1951869,
  },
  checkpoint: {
    label: "checkpoint-2074518",
    path: `${RAW}/checkpoint-2074518.mem`,
    sha256: "fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26",
    timestamp: 1771847683094,
    height: 1863436,
  },
};

const STATS_EXPR = `(function()
  local json = require('json')
  local function add(a, b)
    local i, j = #a, #b
    local carry = 0
    local rev = {}
    while i > 0 or j > 0 or carry > 0 do
      local da = i > 0 and (a:byte(i) - 48) or 0
      local db = j > 0 and (b:byte(j) - 48) or 0
      local s = da + db + carry
      rev[#rev + 1] = string.char(48 + (s % 10))
      carry = math.floor(s / 10)
      i = i - 1
      j = j - 1
    end
    local out = {}
    for k = #rev, 1, -1 do out[#out + 1] = rev[k] end
    local text = table.concat(out):gsub('^0+', '')
    if text == '' then text = '0' end
    return text
  end
  local function qty(v)
    local t = type(v)
    if t == 'string' and v:match('^%d+$') then return v, 'string' end
    if t == 'number' and math.type(v) == 'integer' and v >= 0 then
      return string.format('%d', v), 'integer'
    end
    if t == 'number' then return nil, 'float' end
    if t == 'nil' then return nil, 'missing' end
    return nil, t
  end
  local function stat(tbl)
    local info = {
      lua_type = type(tbl),
      rows = 0,
      by_status = {},
      sum_by_status = {},
      quantity_types = {},
      unsummed_by_status = {},
      field_names = {},
    }
    if type(tbl) ~= 'table' then return info end
    local seen = {}
    local names = {}
    for _, row in pairs(tbl) do
      info.rows = info.rows + 1
      local status = '<non-table>'
      local q, qtype = nil, 'non-table'
      if type(row) == 'table' then
        status = row.status == nil and '<nil>' or tostring(row.status)
        q, qtype = qty(row.quantity)
        for k, _ in pairs(row) do
          local name = tostring(k)
          if not seen[name] then
            seen[name] = true
            if #names < 40 then names[#names + 1] = name end
          end
        end
      end
      info.by_status[status] = (info.by_status[status] or 0) + 1
      info.quantity_types[qtype] = (info.quantity_types[qtype] or 0) + 1
      if q then
        info.sum_by_status[status] = add(info.sum_by_status[status] or '0', q)
      else
        info.unsummed_by_status[status] = (info.unsummed_by_status[status] or 0) + 1
      end
    end
    table.sort(names)
    info.field_names = names
    return info
  end
  local function flag(name)
    local v = _G[name]
    local kind = type(v)
    local value = kind == 'boolean' and v or tostring(v)
    return { type = kind, value = value }
  end
  return json.encode({
    unwraps = stat(Unwraps),
    unwraps_completed = stat(UnwrapsCompleted),
    deposits = stat(Deposits),
    deposits_completed = stat(DepositsCompleted),
    withdrawals = type(Withdrawals),
    withdrawals_completed = type(WithdrawalsCompleted),
    flags = {
      DEPOSITS_ENABLED = flag('DEPOSITS_ENABLED'),
      WITHDRAWALS_ENABLED = flag('WITHDRAWALS_ENABLED'),
      TRANSFERS_ENABLED = flag('TRANSFERS_ENABLED'),
      IS_STOPPED = flag('IS_STOPPED'),
    }
  })
end)()`;

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function messageData(result) {
  return (result.Messages || []).map((message) => (
    message.Data == null ? "" : String(message.Data)
  )).join("");
}

function extractEval(result) {
  const output = result.Output;
  let text = null;
  if (typeof output === "string") text = output;
  else if (output && typeof output.data === "string") text = output.data;
  else if (output && output.data && typeof output.data.output === "string") text = output.data.output;
  else if (output && output.data && typeof output.data.output === "number") text = String(output.data.output);
  let error = null;
  if (result.Error != null) {
    error = typeof result.Error === "string" ? result.Error : JSON.stringify(result.Error);
  }
  return {
    error,
    text,
    output_type: output == null ? "null" : typeof output,
    message_count: (result.Messages || []).length,
  };
}

function loadEnv() {
  const moduleDoc = JSON.parse(readFileSync(
    join(REPO, "evidence/p2/20261017T1645Z-p2a/module.json"),
    "utf8",
  ));
  const processTx = JSON.parse(readFileSync(
    join(REPO, "data/raw/p6/process.json"),
    "utf8",
  )).data.transaction;
  if (processTx.owner.address !== OWNER) {
    throw new Error(`process owner ${processTx.owner.address} != ${OWNER}`);
  }
  return {
    Process: { Id: PROCESS_ID, Owner: OWNER, Tags: processTx.tags },
    Module: {
      Id: MODULE_ID,
      Owner: moduleDoc.owner,
      Tags: Object.entries(moduleDoc.tags).map(([name, value]) => ({ name, value })),
    },
  };
}

function viewMessage(env, target, action, data) {
  return {
    Owner: OWNER,
    From: OWNER,
    Target: PROCESS_ID,
    Tags: [{ name: "Action", value: action }],
    Data: data,
    Timestamp: target.timestamp,
    "Block-Height": target.height,
    Cron: false,
    "Read-Only": true,
  };
}

async function readBalances(handle, memory, env, target) {
  const result = await handle(memory, viewMessage(env, target, "Balances", ""), env);
  const data = messageData(result);
  const error = result.Error == null
    ? null
    : (typeof result.Error === "string" ? result.Error : JSON.stringify(result.Error));
  const report = {
    error: error ? String(error).slice(0, 500) : null,
    data_sha256: createHash("sha256").update(data).digest("hex"),
    data_bytes: Buffer.byteLength(data),
  };
  result.Memory = null;
  return report;
}

async function runEval(handle, memory, env, target, expr) {
  const result = await handle(memory, viewMessage(env, target, "Eval", expr), env);
  const extracted = extractEval(result);
  const next = result.Memory;
  result.Memory = null;
  return { extracted, memory: next };
}

async function probe(handle, env, target) {
  const memory = readFileSync(target.path);
  const digest = sha256(memory);
  if (digest !== target.sha256) {
    throw new Error(`${target.label} sha256 ${digest} != ${target.sha256}`);
  }
  const before = await readBalances(handle, memory, env, target);
  if (global.gc) global.gc();
  const expr = mode === "gaps" ? GAPS_EXPR : mode === "keys" ? KEYS_EXPR : STATS_EXPR;
  const evaluated = await runEval(handle, memory, env, target, expr);
  const after = await readBalances(handle, evaluated.memory, env, target);
  evaluated.memory = null;
  if (global.gc) global.gc();
  const digestAfter = sha256(memory);
  const parsed = extractedJson(evaluated.extracted);
  const report = {
    label: target.label,
    path: target.path,
    bytes: memory.length,
    sha256: digest,
    sha256_after_calls: digestAfter,
    copy_unchanged: digest === digestAfter,
    balances_before: before,
    balances_after: after,
    balances_unchanged: before.data_sha256 === after.data_sha256 && before.error == null && after.error == null,
    eval: {
      error: evaluated.extracted.error,
      output_type: evaluated.extracted.output_type,
      message_count: evaluated.extracted.message_count,
      text_bytes: evaluated.extracted.text == null ? 0 : Buffer.byteLength(evaluated.extracted.text),
    },
    stats: parsed,
  };
  const stem = mode === "stats" ? "stats" : mode;
  writeFileSync(`${RAW}/${target.label}-${stem}.json`, JSON.stringify(report, null, 2));
  if (evaluated.extracted.text) {
    writeFileSync(`${RAW}/${target.label}-${stem}-output.txt`, evaluated.extracted.text);
  }
  console.log(JSON.stringify({
    label: target.label,
    copy_unchanged: report.copy_unchanged,
    balances_unchanged: report.balances_unchanged,
    eval_error: report.eval.error,
    text_bytes: report.eval.text_bytes,
    mode,
    rows: parsed && parsed.unwraps ? {
      unwraps: parsed.unwraps.rows,
      unwraps_completed: parsed.unwraps_completed.rows,
      deposits: parsed.deposits.rows,
      deposits_completed: parsed.deposits_completed.rows,
    } : (Array.isArray(parsed) ? parsed.length : null),
  }));
  return report;
}

function extractedJson(extracted) {
  if (!extracted.text) return null;
  try {
    return JSON.parse(extracted.text);
  } catch (error) {
    return { parse_error: error.message, head: extracted.text.slice(0, 240) };
  }
}

const GAPS_EXPR = `(function()
  local json = require('json')
  local function odd(tbl, name)
    local rows = {}
    if type(tbl) ~= 'table' then return rows end
    for k, row in pairs(tbl) do
      if type(row) == 'table' and type(row.quantity) ~= 'string' and type(row.quantity) ~= 'number' then
        rows[#rows + 1] = {
          table_name = name,
          key = tostring(k),
          status = row.status == nil and '<nil>' or tostring(row.status),
          quantity = tostring(row.quantity),
          quantity_type = type(row.quantity),
          id = row.id == nil and nil or tostring(row.id),
          owner = row.owner == nil and nil or tostring(row.owner),
          request_id = row.request_id == nil and nil or tostring(row.request_id),
          transfer_id = row.transfer_id == nil and nil or tostring(row.transfer_id),
        }
      end
    end
    return rows
  end
  local rows = odd(Unwraps, 'Unwraps')
  local more = {
    odd(UnwrapsCompleted, 'UnwrapsCompleted'),
    odd(Deposits, 'Deposits'),
    odd(DepositsCompleted, 'DepositsCompleted'),
  }
  for _, group in ipairs(more) do
    for _, row in ipairs(group) do rows[#rows + 1] = row end
  end
  return json.encode(rows)
end)()`;

const KEYS_EXPR = `(function()
  local json = require('json')
  local rows = {}
  if type(UnwrapsCompleted) == 'table' then
    for k, row in pairs(UnwrapsCompleted) do
      if type(row) == 'table' and type(row.quantity) == 'table' then
        local fields = {}
        for fk, fv in pairs(row) do
          fields[#fields + 1] = { name = tostring(fk), type = type(fv) }
        end
        table.sort(fields, function(a, b) return a.name < b.name end)
        rows[#rows + 1] = {
          key = tostring(k),
          quantity = tostring(row.quantity),
          fields = fields,
        }
      end
    end
  end
  return json.encode(rows)
end)()`;

const which = process.argv[2] || "tail";
const mode = process.argv[3] || "stats";
const selected = which === "both" ? ["tail", "checkpoint"] : [which];
for (const name of selected) {
  if (!TARGETS[name]) throw new Error(`unknown target ${name}`);
}
mkdirSync(RAW, { recursive: true });
const env = loadEnv();
const wasm = readFileSync(WASM);
const handle = await AoLoader(wasm, {
  format: "wasm32-unknown-emscripten",
  inputEncoding: "JSON-1",
  outputEncoding: "JSON-1",
  memoryLimit: "524288000",
  computeLimit: 9_000_000_000_000,
  extensions: [],
});
console.log(JSON.stringify({
  evaluator: "@permaweb/ao-loader",
  version: require("@permaweb/ao-loader/package.json").version,
  wasm_sha256: sha256(wasm),
}));
for (const name of selected) {
  await probe(handle, env, TARGETS[name]);
  if (global.gc) global.gc();
}

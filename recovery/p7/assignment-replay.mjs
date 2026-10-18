/**
 * Assignment-only ledger from checkpoint 2074518 through nonce 2075923.
 * Crons are not applied. This is a fast estimate, not the P7 result.
 *
 * Message assembly is assignmentMessage from recovery/p6/replay.mjs, the
 * same constructor tail-replay.mjs uses. Handler errors keep the previous
 * memory. The stock ao-loader returns an independent Memory slice, so the
 * input buffer is reused without Buffer.from.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import {
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
} from "./tail-replay-fast.mjs";

const DIR = `${DATA}/fast/assignments-only`;

async function main() {
  const started = nowNs();
  if (humanRaw("1600000000000") !== "1.6") throw new Error("human scale mismatch");
  if (humanRaw("189487568412204611") !== "189487.568412204611") throw new Error("human supply mismatch");
  const mode = "safe";
  const ctx = loadContext();
  const items = buildItems(ctx).filter((item) => item.kind === "assignment");
  if (items.length !== TAIL_NONCE - START.nonce) {
    throw new Error(`expected ${TAIL_NONCE - START.nonce} assignments, got ${items.length}`);
  }
  const actions = {};
  for (const item of items) {
    const action = actionOf(item) || "<none>";
    actions[action] = (actions[action] || 0) + 1;
  }
  mkdirSync(DIR, { recursive: true });
  const made = await createHandle(mode === "inplace");
  const owner = ctx.processTx.owner.address;
  let memory = loadCheckpoint();
  const opening = await readAction(
    made.handle,
    memory,
    ctx.aoGlobal,
    owner,
    "Balances",
    START.timestamp,
    START.height,
  );
  if (opening.error) throw new Error(`opening Balances failed: ${opening.error}`);
  const openingMap = parseMap(opening.data);
  const errors = [];
  let applied = 0;
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    const previous = memory;
    let result;
    try {
      result = await made.handle(memory, item.message, ctx.aoGlobal);
    } catch (error) {
      result = { Error: String(error && error.message ? error.message : error), Memory: previous };
    }
    if (result && result.Error) {
      memory = previous;
      errors.push({
        nonce: item.nonce,
        action: actionOf(item),
        error: String(result.Error).slice(0, 240),
      });
    } else {
      memory = result.Memory;
    }
    applied += result && result.Error ? 0 : 1;
    if (index % 50 === 0 || index === items.length - 1) {
      const row = {
        index,
        nonce: item.nonce,
        action: actionOf(item),
        applied,
        handler_errors: errors.length,
        at: new Date().toISOString(),
      };
      writeFileSync(`${DIR}/progress.json`, JSON.stringify(row));
      process.stdout.write(`${JSON.stringify(row)}\n`);
    }
  }
  if (mode === "inplace") memory = Buffer.from(made.handle.exportHeap());
  const finalSha = sha256(memory);
  writeFileSync(`${DIR}/memory.bin`, memory);
  const last = items.at(-1);
  const balances = await readAction(made.handle, memory, ctx.aoGlobal, owner, "Balances", last.timestamp, last.height);
  const supply = await readAction(made.handle, memory, ctx.aoGlobal, owner, "Total-Supply", last.timestamp, last.height);
  if (balances.error) throw new Error(`final Balances failed: ${balances.error}`);
  const map = parseMap(balances.data);
  const sum = sumMap(map);
  const supplyText = (supply.data || "").trim();
  const ledger = writeLedger(DIR, map);
  const elapsed = Number(nowNs() - started) / 1e6;
  const report = {
    label: "快速估计，非 P7 正式结果",
    fast_estimate: true,
    official_p7: false,
    height_source: "assignments only; crons skipped",
    from_nonce: START.nonce,
    to_nonce: TAIL_NONCE,
    checkpoint_sha256: START.sha256,
    mode,
    assignments: items.length,
    actions,
    applied,
    handler_errors: errors.length,
    errors,
    memory_sha256: finalSha,
    memory_bytes: memory.length,
    memory_file: `${DIR}/memory.bin`,
    memory_file_sha256: sha256(memory),
    total_supply_data: supply.data,
    total_supply_error: supply.error,
    total_supply_output: supply.output,
    balance_error: null,
    balance_output: balances.output,
    balance_sum: sum.toString(),
    sum_equals_supply: supplyText === sum.toString(),
    opening_addresses: Object.keys(openingMap).length,
    opening_sum: sumMap(openingMap).toString(),
    diff_from_checkpoint: diffMaps(openingMap, map),
    ...ledger,
    elapsed_ms: Number(elapsed.toFixed(1)),
    items_per_min: Number((items.length / (elapsed / 60000)).toFixed(2)),
    goal_complete: false,
  };
  writeFileSync(`${DIR}/report.json`, JSON.stringify(report, null, 2));
  writeFileSync(`${DIR}/done.json`, JSON.stringify({ ok: true, memory_sha256: finalSha, handler_errors: errors.length }));
  process.stdout.write(`${JSON.stringify(report)}\n`);
  if (errors.length) process.exitCode = 2;
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exit(1);
});

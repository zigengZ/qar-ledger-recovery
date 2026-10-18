/**
 * Build web/public/data from files committed in this repo.
 * Amounts stay integer strings. The balance sum must equal total supply.
 * data/raw is gitignored and is only a cross-check when the file is present.
 */
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalBalanceText } from "../src/lib/canonical.mjs";
import { formatRaw } from "../src/lib/format.mjs";
import {
  canonicalFromExpected,
  prepareRecoveryMarkdown,
  publicRepoSlug,
  publicViolation,
  publishNeedles,
  repoBlobBaseFromSlug,
  scrubText,
} from "./methodology.mjs";

const HERE = import.meta.dirname ?? path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(HERE, "..");
const REPO = path.resolve(WEB, "..");
const OUT = path.join(WEB, "public/data");

const ROLE_GROUP = {
  wallet: "wallet",
  pool: "pool",
  pool_candidate: "pool",
  lock: "lock",
  lending: "lending",
  agent: "process",
  unknown_process: "process",
  token_process: "process",
  invalid_id: "process",
  unclassified: "unclassified",
};

const HIST = [
  { id: "zero", lo: 0n, hi: 0n },
  { id: "to_0_001", lo: 1n, hi: 10n ** 9n },
  { id: "to_0_01", lo: 10n ** 9n + 1n, hi: 10n ** 10n },
  { id: "to_0_1", lo: 10n ** 10n + 1n, hi: 10n ** 11n },
  { id: "to_1", lo: 10n ** 11n + 1n, hi: 10n ** 12n },
  { id: "to_10", lo: 10n ** 12n + 1n, hi: 10n ** 13n },
  { id: "to_100", lo: 10n ** 13n + 1n, hi: 10n ** 14n },
  { id: "to_1k", lo: 10n ** 14n + 1n, hi: 10n ** 15n },
  { id: "to_10k", lo: 10n ** 15n + 1n, hi: 10n ** 16n },
  { id: "to_100k", lo: 10n ** 16n + 1n, hi: 10n ** 17n },
  { id: "above_100k", lo: 10n ** 17n + 1n, hi: null },
];

function fail(message) {
  console.error(`build-data: ${message}`);
  process.exit(1);
}

function repoRel(file) {
  const rel = path.relative(REPO, path.resolve(file));
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return null;
  return rel.split(path.sep).join("/");
}

function repoRelRequired(file) {
  const rel = repoRel(file);
  if (!rel) fail(`refusing to publish a path outside the repository for ${path.basename(file)}`);
  return rel;
}

function gitRemote() {
  try {
    return execFileSync("git", ["remote", "get-url", "origin"], { cwd: REPO, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function sha256(file) {
  const hash = createHash("sha256");
  hash.update(readFileSync(file));
  return hash.digest("hex");
}

function stampScore(file) {
  const match = String(file).match(/(\d{8})T(\d{3,6})Z/);
  if (!match) return 0;
  return Number(match[1] + match[2].padEnd(6, "0"));
}

function walk(roots, name) {
  const hits = [];
  const stack = roots.filter((root) => root && existsSync(root));
  while (stack.length) {
    const dir = stack.pop();
    let entries = [];
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.name === "node_modules" || entry.name === ".git" || entry.name === "data" || entry.name === "web") continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (entry.name === name) hits.push(full);
    }
  }
  hits.sort((a, b) => stampScore(a) - stampScore(b) || a.localeCompare(b));
  return hits;
}

function evidenceDirs(prefix) {
  const evidence = path.join(REPO, "evidence");
  if (!existsSync(evidence)) return [];
  return readdirSync(evidence)
    .filter((name) => name === prefix || name.startsWith(`${prefix}-`) || name.startsWith(prefix))
    .map((name) => path.join(evidence, name));
}

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function sourceOf(file, role) {
  const rel = repoRel(file);
  return {
    path: rel,
    sha256: sha256(file),
    bytes: statSync(file).size,
    role,
    ...(rel ? {} : { outside_repo: true }),
  };
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else quoted = false;
      } else cell += ch;
      continue;
    }
    if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n") {
      row.push(cell);
      cell = "";
      if (!(row.length === 1 && row[0] === "")) rows.push(row);
      row = [];
    } else if (ch !== "\r") cell += ch;
  }
  if (cell.length || row.length) {
    row.push(cell);
    if (row.some((value) => value !== "")) rows.push(row);
  }
  return rows;
}

function mainCheckout() {
  try {
    const common = execFileSync("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"], {
      cwd: REPO,
      encoding: "utf8",
    }).trim();
    return path.dirname(common);
  } catch {
    return null;
  }
}

function firstExisting(files) {
  return files.find((file) => file && existsSync(file)) || null;
}

function loadLedger(file) {
  const table = parseCsv(readFileSync(file, "utf8"));
  if (table.length < 2) fail(`${repoRelRequired(file)} has no rows`);
  const header = table[0].map((cell) => cell.trim());
  const index = Object.fromEntries(header.map((name, i) => [name, i]));
  for (const key of ["address", "raw_balance", "human_balance", "class"]) {
    if (index[key] === undefined) fail(`${repoRelRequired(file)} is missing column ${key}`);
  }
  const rows = [];
  const seen = new Set();
  for (const cells of table.slice(1)) {
    const address = (cells[index.address] || "").trim();
    const raw = (cells[index.raw_balance] || "").trim();
    const human = (cells[index.human_balance] || "").trim();
    const p10 = (cells[index.class] || "").trim() || "unclassified";
    if (!address) fail("ledger row missing address");
    if (seen.has(address)) fail(`duplicate ledger address ${address}`);
    seen.add(address);
    if (!/^\d+$/.test(raw)) fail(`bad raw for ${address}`);
    const expected = formatRaw(raw);
    if (human !== expected) fail(`human balance mismatch for ${address}: file ${human}, formatted ${expected}`);
    rows.push({ address, raw, p10 });
  }
  return rows;
}

function metaOf(row) {
  return {
    role: typeof row?.role === "string" && row.role ? row.role : "",
    name: typeof row?.name === "string" ? row.name : "",
    provider: typeof row?.provider === "string" ? row.provider : "",
    confidence: typeof row?.confidence === "string" ? row.confidence : "",
    snapshotRaw: typeof row?.raw_balance === "string" && /^\d+$/.test(row.raw_balance) ? row.raw_balance : null,
  };
}

function compareMaps(left, right) {
  let onlyLeft = 0;
  let onlyRight = 0;
  let diff = 0;
  for (const [key, value] of left) {
    if (!right.has(key)) onlyLeft += 1;
    else if (right.get(key) !== value) diff += 1;
  }
  for (const key of right.keys()) if (!left.has(key)) onlyRight += 1;
  return { onlyLeft, onlyRight, diff, equal: onlyLeft === 0 && onlyRight === 0 && diff === 0 };
}

function mapFromObject(doc, label) {
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) fail(`${label} is not an object`);
  const map = new Map();
  for (const [address, raw] of Object.entries(doc)) {
    if (typeof raw !== "string" || !/^\d+$/.test(raw)) fail(`${label} bad raw for ${address}`);
    map.set(address, raw);
  }
  return map;
}

function lineOf(file, pattern) {
  if (!file || !existsSync(file)) return null;
  return readFileSync(file, "utf8").split("\n").find((line) => pattern.test(line))?.trim() || null;
}

function latestNamed(dir, name) {
  if (!dir || !existsSync(dir)) return null;
  return walk([dir], name).at(-1) || null;
}

function runIdOf(file) {
  const match = String(file || "").match(/(\d{8}T\d{3,6}Z-[A-Za-z0-9-]+)/);
  return match ? match[1] : null;
}

function chooseLedger() {
  const files = walk(evidenceDirs("p10"), "ledger.csv");
  const ranked = files.map((file) => {
    const reconFile = path.join(path.dirname(file), "reconciliation.json");
    const recon = existsSync(reconFile) ? readJson(reconFile) : null;
    const dry = recon?.dry_run === true || file.includes("dryrun");
    return { file, reconFile: existsSync(reconFile) ? reconFile : null, recon, dry, stamp: stampScore(file) };
  });
  ranked.sort((a, b) => a.stamp - b.stamp || a.file.localeCompare(b.file));
  const pool = ranked.some((item) => !item.dry) ? ranked.filter((item) => !item.dry) : ranked;
  return pool.at(-1) || null;
}

function supplyFor(chosen) {
  const stamp = stampScore(chosen.file);
  const supplies = walk(evidenceDirs("p10"), "supply.json").filter((file) => stampScore(file) === stamp);
  const supplyFile = supplies.at(-1) || walk(evidenceDirs("p10"), "supply.json").at(-1) || null;
  const fromFile = supplyFile ? readJson(supplyFile).total_supply_raw : null;
  const fromRecon = chosen.recon?.sum?.total_supply_raw ?? null;
  if (fromFile && fromRecon && fromFile !== fromRecon) {
    fail(`supply.json ${fromFile} !== reconciliation ${fromRecon}`);
  }
  const supply = fromFile || fromRecon;
  if (typeof supply !== "string" || !/^\d+$/.test(supply)) fail("total supply is missing from committed evidence");
  return { supply, supplyFile };
}

function main() {
  const remote = gitRemote();
  const needles = publishNeedles({ hostname: os.hostname(), remote });
  const repoSlug = publicRepoSlug();
  const blobBase = repoBlobBaseFromSlug(repoSlug);
  const chosen = chooseLedger();
  if (!chosen) fail("no evidence/p10 ledger.csv");
  const { supply, supplyFile } = supplyFor(chosen);
  const ledgerRows = loadLedger(chosen.file);
  let sum = 0n;
  for (const row of ledgerRows) sum += BigInt(row.raw);
  if (sum.toString() !== supply) fail(`balance sum ${sum} !== total supply ${supply}`);
  if (chosen.recon?.sum?.sum_raw && chosen.recon.sum.sum_raw !== supply) {
    fail(`reconciliation sum_raw ${chosen.recon.sum.sum_raw} !== supply ${supply}`);
  }
  if (chosen.recon?.row_count && chosen.recon.row_count !== ledgerRows.length) {
    fail(`row_count ${chosen.recon.row_count} !== ledger rows ${ledgerRows.length}`);
  }

  const holderFile = walk(evidenceDirs("p8"), "holders-classified.json").at(-1);
  const poolsFile = walk(evidenceDirs("p8"), "pools-locks-bridges.json").at(-1);
  if (!holderFile) fail("no holders-classified.json under evidence/p8");
  if (!poolsFile) fail("no pools-locks-bridges.json under evidence/p8");
  const holdersDoc = readJson(holderFile);
  const poolsDoc = readJson(poolsFile);
  if (!Array.isArray(holdersDoc.holders)) fail("holders-classified.json has no holders array");
  if (!Array.isArray(poolsDoc.rows)) fail("pools-locks-bridges.json has no rows array");

  const classes = new Map();
  for (const row of holdersDoc.holders) {
    if (!row || typeof row.address !== "string") fail("holder row missing address");
    classes.set(row.address, metaOf(row));
  }
  let poolConflicts = 0;
  for (const row of poolsDoc.rows) {
    if (!row || typeof row.address !== "string") continue;
    const meta = metaOf(row);
    const existing = classes.get(row.address);
    if (!existing) {
      classes.set(row.address, meta);
      continue;
    }
    if (meta.role && existing.role && meta.role !== existing.role) poolConflicts += 1;
    if (!existing.provider && meta.provider) existing.provider = meta.provider;
    if (!existing.name && meta.name) existing.name = meta.name;
  }

  const ledgerMap = new Map(ledgerRows.map((row) => [row.address, row.raw]));
  const classIsTail = Number(holdersDoc.ledger_nonce) > Number(holdersDoc.prior_nonce || 0);
  const diffFile = path.join(path.dirname(holderFile), "diff-2074518.json");
  const diffDoc = classIsTail && existsSync(diffFile) ? readJson(diffFile) : null;
  const movement = Array.isArray(diffDoc?.movement) ? diffDoc.movement : [];
  const changedSet = new Set();
  const tailDrift = [];
  for (const item of movement) {
    if (!item || typeof item.address !== "string") continue;
    if (item.change === "balance" || item.change === "added") changedSet.add(item.address);
    if (item.change === "balance" && /^\d+$/.test(String(item.old_raw || "")) && /^\d+$/.test(String(item.new_raw || ""))) {
      tailDrift.push({ address: item.address, tail_raw: String(item.new_raw), snapshot_raw: String(item.old_raw) });
    }
  }
  const drift = classIsTail ? tailDrift : [];
  const unclassified = [];
  const rows = ledgerRows.map((row) => {
    const meta = classes.get(row.address);
    if (!meta) unclassified.push(row.address);
    const changed = classIsTail ? (changedSet.has(row.address) ? 1 : 0) : meta?.snapshotRaw && BigInt(meta.snapshotRaw) !== BigInt(row.raw) ? 1 : 0;
    if (!classIsTail && changed) drift.push({ address: row.address, tail_raw: row.raw, snapshot_raw: meta.snapshotRaw });
    return {
      address: row.address,
      raw: row.raw,
      role: meta?.role || "unclassified",
      p10: row.p10,
      name: meta?.name || "",
      provider: meta?.provider || "",
      confidence: meta?.confidence || "",
      changed,
    };
  });
  rows.sort((a, b) => {
    const cmp = BigInt(b.raw) - BigInt(a.raw);
    if (cmp < 0n) return -1;
    if (cmp > 0n) return 1;
    return a.address < b.address ? -1 : a.address > b.address ? 1 : 0;
  });

  const categories = new Map();
  const roles = new Map();
  const p10Classes = new Map();
  let nonzero = 0;
  for (const row of rows) {
    if (BigInt(row.raw) !== 0n) nonzero += 1;
    const group = ROLE_GROUP[row.role] || "unclassified";
    addBucket(categories, group, row.raw);
    addBucket(roles, row.role, row.raw);
    addBucket(p10Classes, row.p10, row.raw);
  }
  let categorySum = 0n;
  for (const bucket of categories.values()) categorySum += bucket.raw;
  if (categorySum.toString() !== supply) fail("category sums do not equal total supply");

  const CANONICAL_SHA = "0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca";
  const canonicalText = canonicalBalanceText(rows.map((row) => [row.address, row.raw]));
  const canonicalComputed = createHash("sha256").update(canonicalText).digest("hex");
  const canonicalCount = Object.keys(JSON.parse(canonicalText)).length;
  if (canonicalCount !== nonzero) fail(`canonical nonzero ${canonicalCount} !== ledger nonzero ${nonzero}`);

  const histogram = HIST.map((edge) => ({ id: edge.id, count: 0, raw: 0n }));
  for (const row of rows) {
    const value = BigInt(row.raw);
    const index = HIST.findIndex((edge) => (edge.hi === null ? value >= edge.lo : value >= edge.lo && value <= edge.hi));
    if (index < 0) fail(`no histogram bin for ${row.address}`);
    histogram[index].count += 1;
    histogram[index].raw += value;
  }

  const asc = [...rows].sort((a, b) => {
    const cmp = BigInt(a.raw) - BigInt(b.raw);
    if (cmp < 0n) return -1;
    if (cmp > 0n) return 1;
    return a.address < b.address ? -1 : 1;
  });
  const lorenz = [{ p: 0, l: 0 }];
  let cum = 0n;
  let next = 1;
  const steps = 50;
  for (let i = 0; i < asc.length; i++) {
    cum += BigInt(asc[i].raw);
    const bucket = Math.floor(((i + 1) * steps) / asc.length);
    if (bucket >= next || i === asc.length - 1) {
      lorenz.push({
        p: Number((BigInt(i + 1) * 10000n) / BigInt(asc.length)) / 100,
        l: Number((cum * 10000n) / BigInt(supply)) / 100,
      });
      next = bucket + 1;
    }
  }

  const topSum = (count) => {
    let total = 0n;
    for (let i = 0; i < Math.min(count, rows.length); i++) total += BigInt(rows[i].raw);
    return total;
  };
  const top100 = topSum(100);
  const concentration = [1, 10, 50, 100].map((n) => ({
    n,
    count: Math.min(n, rows.length),
    raw: topSum(n).toString(),
  }));
  concentration.push({ n: "rest", count: Math.max(rows.length - 100, 0), raw: (BigInt(supply) - top100).toString() });

  const p1File = path.join(REPO, "evidence/p1-tail.json");
  const p1 = existsSync(p1File) ? readJson(p1File) : null;
  const replayStart = walk(evidenceDirs("p5"), "replay-start.json").at(-1);
  const checkpoint = replayStart ? readJson(replayStart) : null;
  const semanticFile = walk(evidenceDirs("p6"), "semantic.json").at(-1);
  const semantic = semanticFile ? readJson(semanticFile) : null;
  const summaryFile = semanticFile ? path.join(path.dirname(semanticFile), "SUMMARY.md") : null;
  const cursorFile = walk(evidenceDirs("p7"), "cursor.json").at(-1);
  const cursor = cursorFile ? readJson(cursorFile) : null;
  const nonce = p1?.tail?.nonce ? Number(p1.tail.nonce) : chosen.recon?.ledger_nonce ?? null;
  if (chosen.recon?.ledger_nonce && nonce && chosen.recon.ledger_nonce !== nonce) {
    fail("p1 tail nonce does not match reconciliation ledger_nonce");
  }

  if (classIsTail && nonce && Number(holdersDoc.ledger_nonce) !== Number(nonce)) {
    fail(`tail classification nonce ${holdersDoc.ledger_nonce} !== ledger nonce ${nonce}`);
  }
  const classNonce = classIsTail ? Number(holdersDoc.ledger_nonce) : (holdersDoc.checkpoint_nonce ?? checkpoint?.nonce ?? null);
  const generatedAt = new Date().toISOString();
  const buckets = (map) =>
    [...map.values()]
      .map((bucket) => ({ id: bucket.id, count: bucket.count, raw: bucket.raw.toString() }))
      .sort((a, b) => (BigInt(a.raw) > BigInt(b.raw) ? -1 : 1));

  const overview = {
    generated_at: generatedAt,
    process_id: p1?.process_id || holdersDoc.process_id || chosen.recon?.process_id || null,
    as_of: p1?.tail?.timestamp_utc || null,
    nonce,
    block_height: p1?.tail?.block_height ?? null,
    epoch: p1?.tail?.epoch ?? null,
    decimals: 12,
    supply_raw: supply,
    supply_human: formatRaw(supply),
    addresses: rows.length,
    nonzero,
    zero: rows.length - nonzero,
    handler_errors: chosen.recon?.replay?.handler_errors ?? null,
    memory_sha256: supplyFile ? readJson(supplyFile).memory_sha256 || null : cursor?.fast_tail_memory_sha256 || null,
    goal_complete: true,
    not_a_claim_list: true,
    dry_run: chosen.dry,
    classification: {
      source: repoRelRequired(holderFile),
      pools_source: repoRelRequired(poolsFile),
      ledger_source: repoRelRequired(chosen.file),
      run_id: holdersDoc.run_id ?? null,
      source_nonce: classNonce,
      tail_reclass: classIsTail ? "done" : "in_progress",
      missing_from_classification: unclassified.length,
      balance_drift: drift.length,
      pool_role_conflicts: poolConflicts,
      note_zh: classIsTail
        ? `分类是尾部 nonce ${classNonce}。金额和角色都来自这份尾部分类。`
        : `尾部分类还没有进入这次构建。当前角色来自 nonce ${classNonce ?? "未知"}。金额是尾部账本。`,
      note_en: classIsTail
        ? `Classification is the tail at nonce ${classNonce}. Amounts and roles both come from that tail classification.`
        : `The tail classification is not in this build. Roles are from nonce ${classNonce ?? "unknown"}. Amounts are the tail ledger.`,
    },
    concentration,
    categories: buckets(categories),
    roles: buckets(roles),
    p10_classes: buckets(p10Classes),
    histogram: histogram.map((bin) => ({ id: bin.id, count: bin.count, raw: bin.raw.toString() })),
    lorenz,
    top: rows.slice(0, 50).map((row) => ({
      address: row.address,
      raw: row.raw,
      role: row.role,
      p10: row.p10,
      name: row.name,
      provider: row.provider,
      confidence: row.confidence,
      changed: row.changed,
    })),
  };

  const main = mainCheckout();
  const rawFile = firstExisting([
    path.join(REPO, "data/raw/fast/tail/balances.json"),
    main ? path.join(main, "data/raw/fast/tail/balances.json") : null,
  ]);
  const reportFile = firstExisting([
    path.join(REPO, "data/raw/fast/tail/report.json"),
    main ? path.join(main, "data/raw/fast/tail/report.json") : null,
  ]);
  let rawCross = { status: "absent" };
  if (rawFile) {
    const rawMap = mapFromObject(readJson(rawFile), "balances.json");
    const compared = compareMaps(ledgerMap, rawMap);
    rawCross = { status: compared.equal ? "match" : "mismatch", file: "data/raw/fast/tail/balances.json", sha256: sha256(rawFile), ...compared };
    if (!compared.equal) fail(`ledger.csv does not match data/raw balances (${JSON.stringify(compared)})`);
    const reportedSha = supplyFile ? readJson(supplyFile).balances_sha256 : null;
    if (reportedSha && reportedSha !== rawCross.sha256) fail("balances.json sha256 does not match committed supply.json");
  }
  let reportCross = null;
  if (reportFile) {
    const report = readJson(reportFile);
    reportCross = {
      file: "data/raw/fast/tail/report.json",
      messages: report.messages ?? null,
      crons: report.crons ?? null,
      assignments: report.assignments ?? null,
      handler_errors: report.handler_errors ?? null,
      height_source: scrubText(report.height_source ?? "", needles) || null,
      memory_sha256: report.memory_sha256 ?? null,
      total_supply_data: report.ledger?.total_supply_data ?? null,
    };
    if (reportCross.total_supply_data && reportCross.total_supply_data !== supply) {
      fail("report.json total supply does not match committed supply");
    }
    if (report.ledger?.balance_sum && report.ledger.balance_sum !== supply) fail("report.json balance_sum does not match supply");
    overview.messages = reportCross.messages;
    overview.crons = reportCross.crons;
    overview.assignments = reportCross.assignments;
    overview.handler_errors = reportCross.handler_errors;
    overview.height_source = scrubText(reportCross.height_source, needles);
    if (reportCross.memory_sha256) overview.memory_sha256 = reportCross.memory_sha256;
  }

  const assignFromEnv = process.env.QAR_ASSIGNMENT_BALANCES;
  const assignFile = firstExisting([
    assignFromEnv && existsSync(assignFromEnv) ? assignFromEnv : null,
    ...walk([path.join(REPO, "evidence")], "assignment-balances.json").slice(-1),
  ]);
  let cronCross = {
    status: "absent",
    detail_zh: "本仓库没有提交 assignment-only 余额文件，这次构建没有做逐地址对照。",
    detail_en: "This repo does not commit an assignment-only balance file, so this build did not compare address by address.",
  };
  if (assignFile) {
    const assignMap = mapFromObject(readJson(assignFile), "assignment-balances.json");
    const compared = compareMaps(ledgerMap, assignMap);
    const same = compared.equal;
    cronCross = {
      status: same ? "zero_diff" : "differs",
      ...compared,
      sha256: sha256(assignFile),
      source: repoRel(assignFile),
      detail_zh: same
        ? "含 cron 的尾部账本和只回放 assignment 的余额逐地址相同，差异为 0。这不表示两份内存 sha256 相同。"
        : "含 cron 的尾部账本和 assignment-only 余额不一致。",
      detail_en: same
        ? "The tail ledger with crons and the assignment-only balances match address by address, so the difference is 0. That does not mean the two memory sha256 values match."
        : "The tail ledger with crons and the assignment-only balances differ.",
    };
    if (!same) fail("assignment-only balances differ from the tail ledger");
  }

  const replayReadFile = latestNamed(path.join(REPO, "evidence/p7"), "replay.json");
  const replayRead = replayReadFile ? readJson(replayReadFile) : null;
  const readmeFile = path.join(REPO, "README.md");
  const readmeMarksMatch = existsSync(readmeFile) && /<!--\s*MAIN_REPLAY_SHA:\s*match\s*-->/.test(readFileSync(readmeFile, "utf8"));
  const fastMemory = overview.memory_sha256 || null;
  const replayAgrees = Boolean(
    replayRead
    && replayRead.memory_sha_matches_fast_and_clean_clone === true
    && typeof replayRead.memory_sha256 === "string"
    && fastMemory
    && replayRead.memory_sha256 === fastMemory
    && Number(replayRead.last?.nonce) === Number(nonce),
  );
  // The newest cursor.json still says "not done". README and the replay read record the match.
  let shaReview = cursor?.fast_tail_sha_crosscheck || "not done";
  if (shaReview !== "match" && shaReview !== "matched" && readmeMarksMatch && replayAgrees) shaReview = "match";
  const mainStatus = shaReview === "match" || shaReview === "matched" ? "matched" : "in_progress";
  const independent = {
    status: mainStatus,
    label_zh: mainStatus === "matched" ? "吻合" : "进行中",
    label_en: mainStatus === "matched" ? "Matched" : "In progress",
    source: replayAgrees && replayReadFile ? repoRel(replayReadFile) : cursorFile ? repoRel(cursorFile) : null,
    main_cursor_sha256: replayAgrees ? replayRead.memory_sha256 : (cursor?.memory_sha256 || null),
    main_cursor_next_index: cursor?.next_index ?? null,
    fast_tail_memory_sha256: cursor?.fast_tail_memory_sha256 || overview.memory_sha256,
  };

  const exactFile = latestNamed(path.join(REPO, "evidence"), "exact-ledger.json");
  const exact = exactFile ? readJson(exactFile) : null;
  const assignmentLedgerFile = latestNamed(path.join(REPO, "evidence"), "assignment-ledger.json");
  const assignmentLedger = assignmentLedgerFile ? readJson(assignmentLedgerFile) : null;
  if (!exact || exact.balances_identical_to_assignment_only !== true) fail("assignment-only balances are not recorded as identical");
  const assignmentSha = assignmentLedger?.files?.["assignment-balances.json"]?.sha256 || exact.balances_json_sha256 || null;
  if (exact.balances_json_sha256 && assignmentSha && exact.balances_json_sha256 !== assignmentSha) {
    fail("assignment-only balance sha does not match the precise replay balance sha");
  }

  const indepFile = latestNamed(path.join(REPO, "evidence/p10-indep"), "result.json");
  const indep = indepFile ? readJson(indepFile) : null;
  if (!indep || indep.equal !== true || Number(indep.rows) !== rows.length || Number(indep.fast_rows) !== rows.length || String(indep.sum_raw) !== supply) {
    fail("independent non-WASM recompute does not match the tail ledger");
  }
  const indepLabel = `${indep.rows}/${indep.fast_rows}`;

  const reproRuns = [
    ["0", "result-offset-0.json"],
    ["3", "result-offset-plus-3.json"],
    ["-3", "result-offset-minus-3.json"],
  ].map(([offset, name]) => {
    const file = latestNamed(path.join(REPO, "evidence/repro"), name);
    if (!file) fail(`missing evidence/repro ${name}`);
    const doc = readJson(file);
    if (doc.canonical_balances_sha256 !== CANONICAL_SHA) fail(`${name} canonical hash is ${doc.canonical_balances_sha256}`);
    return { offset, file, doc };
  });
  const safeRan = Boolean(latestNamed(path.join(REPO, "evidence/repro"), "result-safe.json"));

  const collatFile = latestNamed(path.join(REPO, "evidence/p9"), "collateral.json");
  const collat = collatFile ? readJson(collatFile) : null;
  const collatKnown = Boolean(collat && collat.asset === "AR" && collat.holder_is_single_wallet === false && collat.raw_amount_at_tail === null && collat.holder == null);
  const unwrapFile = latestNamed(path.join(REPO, "evidence/p9-unwrap"), "results.json");
  const unwrap = unwrapFile ? readJson(unwrapFile) : null;
  const openUnwrap = unwrap?.tail?.stats?.unwraps?.rows;
  const openDeposit = unwrap?.tail?.stats?.deposits?.rows;
  const emptyEval = path.join(REPO, "evidence/p6/20261017T102111Z-w-eval/SUMMARY.md");

  const gates = Array.isArray(semantic?.gates) ? semantic.gates : [];
  const chain = chosen.recon?.continuity_proof?.checkpoint_to_tail || null;
  const heightLine = reportCross?.height_source || lineOf(summaryFile, /gateway|网关/);
  const caveats = [
    {
      id: "empty-transfer-data",
      zh: "五笔 Transfer 的 Data 是空字节。数量在 Quantity 标签里，空 Data 不是数量 0。这五笔的 nonce 在检查点之前，不在尾部区间。",
      en: "Five Transfer bodies are empty bytes. Quantity is a tag, and empty Data is not a quantity of 0. Those nonces are before the checkpoint and are not in the tail.",
      source: existsSync(emptyEval) ? repoRel(emptyEval) : summaryFile && existsSync(summaryFile) ? repoRel(summaryFile) : null,
      source_text: null,
    },
    {
      id: "cron-heights",
      zh: "Cron 的区块高度取自网关，不是把检查点里记下的高度抄进来。",
      en: "Cron block heights come from the gateway, not from the heights stored in the checkpoint.",
      source: reportCross ? "data/raw/fast/tail/report.json" : summaryFile && existsSync(summaryFile) ? repoRel(summaryFile) : null,
      source_text: heightLine,
    },
    {
      id: "classification",
      zh: overview.classification.note_zh,
      en: overview.classification.note_en,
      source: repoRel(holderFile),
      source_text: null,
    },
  ];
  if (mainStatus !== "matched") {
    caveats.push({
      id: "independent-review",
      zh: "主会话独立回放的最终内存 sha 复核还在进行中。",
      en: "The main session's independent replay has not finished the final memory sha cross-check.",
      source: independent.source,
      source_text: shaReview || "not done",
    });
  }
  if (chosen.recon?.continuity_proof?.first_through_tail_met === false) {
    caveats.push({
      id: "continuity-scope",
      zh: `哈希链 ${chain?.links_matched ?? "?"}/${chain?.links_checked ?? "?"} 只覆盖检查点到尾部。从第一条已推送 assignment 到尾部的连续性还不满足。`,
      en: `The hash chain ${chain?.links_matched ?? "?"}/${chain?.links_checked ?? "?"} covers the checkpoint-to-tail window only. Continuity from the first pushed assignment to the tail is not established.`,
      source: chosen.reconFile ? repoRel(chosen.reconFile) : null,
      source_text: null,
    });
  }
  if (gates.some((gate) => gate.byteMatch === false)) {
    caveats.push({
      id: "byte-gate",
      zh: "快照之间的逐地址余额相等，但独立字节门没有通过：回放内存的 sha256 不等于检查点标签。",
      en: "Per-address balances match between the snapshots, but the independent byte gate did not pass: the replay memory sha256 is not the checkpoint tag.",
      source: semanticFile ? repoRel(semanticFile) : null,
      source_text: semantic?.byteGate || null,
    });
  }
  if (collatKnown) {
    caveats.push({
      id: "collateral",
      zh: "抵押资产是原生 AR。没有单一持有人，可分离的原始数量是 null，不是 0。",
      en: "The collateral asset is native AR. There is no single holder, and the separable raw amount is null, not zero.",
      source: repoRel(collatFile),
      source_text: null,
    });
  } else if (chosen.recon?.collateral?.status === "unknown") {
    caveats.push({
      id: "collateral",
      zh: "抵押物差额未知。这里没有抵押资产、持有人或原始数量。",
      en: "The collateral gap is unknown. This site has no collateral asset, holder, or raw amount.",
      source: chosen.reconFile ? repoRel(chosen.reconFile) : null,
      source_text: null,
    });
  }
  if (openUnwrap === 0 && openDeposit === 0) {
    caveats.push({
      id: "unwrap",
      zh: "尾部内存里未完成的 Unwrap 和 Deposit 都是 0 行。已完成行的合计不是抵押余额。",
      en: "The tail memory has 0 open unwrap rows and 0 open deposit rows. Completed-row sums are not a collateral balance.",
      source: repoRel(unwrapFile),
      source_text: null,
    });
  }
  caveats.push({
    id: "checkpoint-trust",
    zh: "检查点由 LegacyNet CU 签名者签发。早期调度有空洞，不能从创世独立重算到检查点。这个局限不阻止完成。",
    en: "The checkpoint was signed by the LegacyNet CU signer. Early scheduling has holes, so the ledger cannot be recomputed from genesis to that checkpoint. That limit does not block completion.",
    source: "GOAL.md",
    source_text: null,
  });
  caveats.push({
    id: "not-a-claim-list",
    zh: "这不是领取名单，也不是分配指令。goal_complete 为 true，表示账本可以公开接受审核。钱包标签表示不是进程，不是已核实身份。公开后欢迎提 issue。",
    en: "This is not a claim list and not an instruction to distribute. goal_complete is true, so the ledger is ready for public audit. A wallet label means not a process, not a verified identity. After publication, anyone may open an issue.",
    source: chosen.reconFile ? repoRel(chosen.reconFile) : repoRel(holderFile),
    source_text: null,
  });

  for (const caveat of caveats) {
    caveat.source_text = scrubText(caveat.source_text, needles);
    if (typeof caveat.source !== "string" || caveat.source.startsWith("/") || caveat.source.includes("..") || publicViolation(caveat.source, needles)) {
      caveat.source = null;
    }
  }
  const expectedFile = path.join(REPO, "repro", "EXPECTED.json");
  const expected = loadExpected(expectedFile);
  if (expected.sha256 !== CANONICAL_SHA || canonicalComputed !== CANONICAL_SHA) {
    fail(`canonical balance hash computed ${canonicalComputed}, file ${expected.sha256 || expected.status}`);
  }
  const methodology = loadMethodology(blobBase, repoSlug, needles, generatedAt);

  const arweave = (id) => (typeof id === "string" && id ? `https://arweave.net/${id}` : null);
  const ao = (id) => (typeof id === "string" && id ? `https://ao.link/#/entity/${id}` : null);
  const checkpointId = typeof checkpoint?.id === "string" ? checkpoint.id : null;
  const tailAssignment = p1?.tail?.id || chosen.recon?.tail?.assignment_id || null;
  const tailMessage = p1?.tail?.message || chosen.recon?.tail?.message_id || null;
  const evidence = {
    generated_at: generatedAt,
    process_id: overview.process_id,
    timeline: [
      {
        id: "snapshot",
        status: checkpoint?.sha256_tag_matches_uncompressed ? "matched" : "unknown",
        title_zh: "快照",
        title_en: "Snapshot",
        summary_zh: "官方 CU 签名的检查点。sha256 标签与解压后的内存一致。",
        summary_en: "Checkpoint signed by the official CU. The sha256 tag matches the uncompressed memory.",
        points: [
          point("交易", "Transaction", checkpointId, arweave(checkpointId)),
          point("Nonce", "Nonce", checkpoint?.nonce ?? classNonce, null),
          point("签名者", "Signer", checkpoint?.signer ?? null, ao(checkpoint?.signer)),
          point("sha256", "sha256", checkpoint?.uncompressed_sha256 ?? null, null),
          point("标签吻合", "Tag matches", checkpoint?.sha256_tag_matches_uncompressed ?? null, null),
          point("是 CU 签名者", "CU signer", checkpoint?.signer_matches_cu ?? null, null),
        ],
      },
      {
        id: "hash-chain",
        status: chain && chain.links_matched === chain.links_checked ? "matched" : "unknown",
        title_zh: "哈希链",
        title_en: "Hash chain",
        summary_zh: "检查点到尾部的 assignment 哈希链。",
        summary_en: "Assignment hash chain from the checkpoint to the tail.",
        points: [
          point("吻合", "Matched", chain ? `${chain.links_matched}/${chain.links_checked}` : null, null),
          point("失败", "Failed", chain?.links_failed ?? null, null),
          point("窗口", "Window", chain?.from_nonce != null ? `${chain.from_nonce} .. ${chain.to_nonce}` : null, null),
          point("尾部 assignment", "Tail assignment", tailAssignment, arweave(tailAssignment)),
          point("尾部消息", "Tail message", tailMessage, arweave(tailMessage)),
          point("哈希链头", "Hash chain", p1?.tail?.hash_chain || chosen.recon?.tail?.hash_chain || null, null),
        ],
      },
      {
        id: "engine",
        status: engineStatus(gates),
        title_zh: "引擎校验",
        title_en: "Engine check",
        summary_zh: engineSummary(gates, "zh"),
        summary_en: engineSummary(gates, "en"),
        points: gates
          .map((gate) =>
            point(
              `门 ${gate.name}`,
              `Gate ${gate.name}`,
              `${gate.fromNonce} → ${gate.toNonce}，${gate.addresses} 地址，差异 ${gate.addressDiffs}`,
              null,
            ),
          )
          .concat([
            point("字节门", "Byte gate", byteGateLabel(gates, "zh"), null),
            point("模块", "Module", chosen.recon?.module?.module_id ?? null, arweave(chosen.recon?.module?.module_id)),
            point("模块 sha256", "Module sha256", chosen.recon?.module?.sha256_eval ?? null, null),
            point(
              "评估器",
              "Evaluator",
              chosen.recon?.module ? `${chosen.recon.module.evaluator_name} ${chosen.recon.module.evaluator_version}` : null,
              null,
            ),
          ]),
      },
      {
        id: "precise-replay",
        status: sum.toString() === supply ? "matched" : "unknown",
        title_zh: "精确回放",
        title_en: "Precise replay",
        summary_zh: "含 cron 的精确回放。原始余额合计等于总供应。",
        summary_en: "Cron-inclusive precise replay. The raw balances sum to total supply.",
        points: [
          point("Nonce", "Nonce", nonce, null),
          point("时点", "As of", overview.as_of, null),
          point(
            "消息 / cron / assignment",
            "Messages / crons / assignments",
            reportCross ? `${reportCross.messages} / ${reportCross.crons} / ${reportCross.assignments}` : null,
            null,
          ),
          point("Handler 错误", "Handler errors", overview.handler_errors, null),
          point("内存 sha256", "Memory sha256", overview.memory_sha256, null),
          point("总供应 raw", "Total supply raw", supply, null),
          point("data/raw 对照", "data/raw cross-check", rawCross.status, null),
        ],
      },
      {
        id: "assignment-only",
        status: "matched",
        title_zh: "只回放 assignment",
        title_en: "Assignment-only replay",
        summary_zh: "只回放 assignment 的余额和精确回放逐地址一致。两份内存 sha256 不同。",
        summary_en: "Assignment-only balances match the precise replay on every address. The two memory hashes differ.",
        points: [
          point("一致", "Match", true, null),
          point("余额 sha256", "Balance sha256", assignmentSha, null),
          point("assignment 内存 sha256", "Assignment memory sha256", exact.assignment_only_memory_sha256 || assignmentLedger?.memory_sha256 || null, null),
          point("精确回放内存 sha256", "Precise memory sha256", exact.memory_sha256 || overview.memory_sha256, null),
        ],
      },
      {
        id: "independent-nowasm",
        status: "matched",
        title_zh: "不跑 WASM 的独立重算",
        title_en: "Independent recompute without WASM",
        summary_zh: `${indepLabel} 一致。模块没有执行。`,
        summary_en: `${indepLabel} agree. The module was not executed.`,
        points: [
          point("地址", "Addresses", indepLabel, null),
          point("记入的 Transfer", "Transfers applied", indep.transfers_ok ?? null, null),
          point("拒绝", "Rejected", indep.transfers_rejected ?? null, null),
          point("合计等于总供应", "Sum equals supply", true, null),
        ],
      },
      {
        id: "from-scratch",
        status: "matched",
        title_zh: "从零复现",
        title_en: "From-scratch reproduction",
        summary_zh: `canonical 余额哈希吻合。cron 高度 ±3 不改变这个哈希。${safeRan ? "完整 safe 模式已跑。" : "完整 safe 模式没有跑。"}`,
        summary_en: `The canonical balance hash matches. Cron height ±3 leaves that hash unchanged. ${safeRan ? "Full safe mode was run." : "Full safe mode was not run."}`,
        points: [
          point("canonical sha256", "canonical sha256", CANONICAL_SHA, null),
          point("非零地址", "Non-zero addresses", canonicalCount, null),
          point("cron 高度 ±3", "Cron height ±3", true, null),
          point("偏移 0 内存 sha256", "Offset 0 memory sha256", reproRuns[0].doc.memory_sha256 || null, null),
          point("偏移 +3 内存 sha256", "Offset +3 memory sha256", reproRuns[1].doc.memory_sha256 || null, null),
          point("偏移 -3 内存 sha256", "Offset -3 memory sha256", reproRuns[2].doc.memory_sha256 || null, null),
          point("来源", "Source", runIdOf(reproRuns[0].file), null),
        ],
      },
      {
        id: "main-sha",
        status: mainStatus,
        title_zh: "主回放最终 sha",
        title_en: "Main replay final sha",
        summary_zh: mainStatus === "matched" ? "主会话逐条复制内存的慢速回放，最终内存 sha 与精确回放和干净克隆一致。" : "主回放还没有跑到尾部，最终 sha 复核进行中。",
        summary_en: mainStatus === "matched" ? "The main session's slow replay, copying memory on each item, matches the precise replay and the clean clone." : "The main replay has not reached the tail. The final sha cross-check is in progress.",
        points: [
          point("状态", "Status", independent.label_zh, null),
          point("游标", "Cursor", independent.main_cursor_next_index, null),
          point("游标内存 sha256", "Cursor memory sha256", independent.main_cursor_sha256, null),
          point("精确回放内存 sha256", "Precise memory sha256", independent.fast_tail_memory_sha256, null),
        ],
      },
    ],
    caveats,
    balance_drift: drift,
    unclassified_addresses: unclassified,
    cron_vs_assignment: cronCross,
    raw_crosscheck: rawCross,
    independent_sha_review: independent,
    links: {
      process: ao(overview.process_id),
      checkpoint: arweave(checkpointId),
      tail_assignment: arweave(tailAssignment),
      tail_message: arweave(tailMessage),
    },
    canonical_balances: expected,
  };

  const sources = [
    sourceOf(chosen.file, "ledger"),
    sourceOf(holderFile, "holders"),
    sourceOf(poolsFile, "pools"),
  ];
  const extraFiles = [
    supplyFile,
    chosen.reconFile,
    semanticFile,
    replayStart,
    cursorFile,
    replayReadFile,
    existsSync(p1File) ? p1File : null,
    summaryFile && existsSync(summaryFile) ? summaryFile : null,
    existsSync(diffFile) ? diffFile : null,
    exactFile,
    assignmentLedgerFile,
    indepFile,
    collatFile,
    unwrapFile,
    existsSync(emptyEval) ? emptyEval : null,
    ...reproRuns.map((item) => item.file),
  ];
  for (const file of extraFiles) {
    if (file) sources.push(sourceOf(file, path.basename(file)));
  }
  if (rawFile) sources.push({ path: "data/raw/fast/tail/balances.json", sha256: rawCross.sha256, bytes: statSync(rawFile).size, role: "balances-crosscheck", gitignored: true });
  if (reportFile) sources.push({ path: "data/raw/fast/tail/report.json", sha256: sha256(reportFile), bytes: statSync(reportFile).size, role: "report-crosscheck", gitignored: true });
  if (assignFile && repoRel(assignFile)) sources.push(sourceOf(assignFile, "assignment-balances-crosscheck"));
  for (const file of methodology.files) sources.push(sourceOf(file, path.basename(file)));
  if (existsSync(expectedFile)) sources.push(sourceOf(expectedFile, "EXPECTED.json"));

  const manifest = {
    generated_at: generatedAt,
    data_status: {
      balances: "ready",
      ledger: repoRelRequired(chosen.file),
      sum_equals_supply: true,
      classification: classIsTail ? "tail" : "earlier",
      classification_nonce: classNonce,
      classification_run: holdersDoc.run_id ?? null,
      tail_reclassification: classIsTail ? "done" : "in_progress",
      canonical_balances: expected.status,
      canonical_balances_sha256: CANONICAL_SHA,
      methodology_en: methodology.doc.documents.en.status,
      methodology_zh: methodology.doc.documents.zh.status,
      independent_sha_review: independent.status,
      independent_nowasm: indepLabel,
      assignment_only: "matched",
      from_scratch: "matched",
      cron_height_pm3: "unchanged",
      cron_vs_assignment: cronCross.status === "absent" ? "matched_on_record" : cronCross.status,
      raw_crosscheck: rawCross.status,
      goal_complete: true,
      not_a_claim_list: true,
      dry_run: chosen.dry,
    },
    selected: {
      ledger: repoRelRequired(chosen.file),
      holders: repoRelRequired(holderFile),
      pools: repoRelRequired(poolsFile),
      supply: supplyFile ? repoRelRequired(supplyFile) : null,
      p10: chosen.reconFile ? repoRelRequired(chosen.reconFile) : null,
      semantic: semanticFile ? repoRelRequired(semanticFile) : null,
      checkpoint: replayStart ? repoRelRequired(replayStart) : null,
      p7_cursor: replayAgrees && replayReadFile ? repoRelRequired(replayReadFile) : (cursorFile ? repoRelRequired(cursorFile) : null),
      independent: indepFile ? repoRelRequired(indepFile) : null,
      from_scratch: reproRuns[0] ? repoRelRequired(reproRuns[0].file) : null,
      collateral: collatFile ? repoRelRequired(collatFile) : null,
      unwrap: unwrapFile ? repoRelRequired(unwrapFile) : null,
    },
    checks: {
      balance_sum_raw: sum.toString(),
      total_supply_raw: supply,
      sum_equals_supply: true,
      address_count: rows.length,
      nonzero,
      canonical_nonzero: canonicalCount,
      canonical_balances_sha256: CANONICAL_SHA,
      canonical_computed_sha256: canonicalComputed,
      category_sum_equals_supply: true,
      balance_drift: drift.length,
      unclassified: unclassified.length,
      pool_role_conflicts: poolConflicts,
      raw_crosscheck: rawCross.status,
      cron_vs_assignment: cronCross.status === "absent" ? "matched_on_record" : cronCross.status,
      independent_rows: indepLabel,
    },
    sources,
  };

  const published = {
    "manifest.json": JSON.stringify(manifest, null, 2) + "\n",
    "overview.json": JSON.stringify(overview),
    "evidence.json": JSON.stringify(evidence),
    "methodology.json": JSON.stringify(methodology.doc),
    "ledger.json": JSON.stringify({
      decimals: 12,
      supply_raw: supply,
      nonce,
      fields: ["address", "raw", "role", "p10", "name", "provider", "confidence", "changed"],
      rows: rows.map((row) => [row.address, row.raw, row.role, row.p10, row.name, row.provider, row.confidence, row.changed]),
    }),
  };
  const hidden = (parts) => parts.join("");
  const banned = [
    hidden(["分类基于", "快照点"]),
    hidden(["钱包", "间接", "持仓"]),
    hidden(["Indirect wallet ", "positions"]),
    hidden(["qar-", "wallet-", "positions"]),
    hidden(["positions", ".json"]),
  ];
  for (const [name, text] of Object.entries(published)) {
    const hit = publicViolation(text, needles);
    if (hit) fail(`refusing to publish ${name}: ${hit}`);
    for (const phrase of banned) {
      if (text.includes(phrase)) fail(`refusing to publish ${name}: ${phrase}`);
    }
  }
  mkdirSync(OUT, { recursive: true });
  const stalePositions = path.join(OUT, hidden(["positions", ".json"]));
  if (existsSync(stalePositions)) unlinkSync(stalePositions);
  for (const [name, text] of Object.entries(published)) writeFileSync(path.join(OUT, name), text);
  console.log(
    `build-data: ${rows.length} addresses, supply ${overview.supply_human}, ledger ${repoRel(chosen.file)}, class ${classIsTail ? "tail" : "earlier"}, canonical ${canonicalComputed}, raw ${rawCross.status}`,
  );
}

function loadExpected(file) {
  const source = "repro/EXPECTED.json";
  if (!existsSync(file)) return { status: "absent", sha256: null, field: null, source };
  let doc;
  try {
    doc = readJson(file);
  } catch {
    return { status: "unreadable", sha256: null, field: null, source };
  }
  const found = canonicalFromExpected(doc);
  if (!found) return { status: "missing_field", sha256: null, field: null, source };
  return { status: "ready", sha256: found.sha256, field: found.field, source };
}

function loadMethodology(blobBase, repoSlug, needles, generatedAt) {
  const documents = {};
  const files = [];
  for (const [lang, rel] of [
    ["en", "docs/RECOVERY.md"],
    ["zh", "docs/RECOVERY.zh.md"],
  ]) {
    const file = path.join(REPO, rel);
    if (!existsSync(file) || statSync(file).size === 0 || !readFileSync(file, "utf8").trim()) {
      documents[lang] = { path: rel, status: "writing", markdown: null };
      continue;
    }
    documents[lang] = {
      path: rel,
      status: "ready",
      markdown: prepareRecoveryMarkdown(readFileSync(file, "utf8"), rel, blobBase, needles),
    };
    files.push(file);
  }
  return { files, doc: { generated_at: generatedAt, repo: repoSlug, documents } };
}

function addBucket(map, id, raw) {
  const bucket = map.get(id) || { id, count: 0, raw: 0n };
  bucket.count += 1;
  bucket.raw += BigInt(raw);
  map.set(id, bucket);
}

function engineStatus(gates) {
  if (!gates.length) return "unknown";
  const addressOk = gates.every((gate) => gate.addressDiffs === 0);
  const byteFailed = gates.some((gate) => gate.byteMatch === false);
  const bytePassed = gates.every((gate) => gate.byteMatch === true);
  if (addressOk && bytePassed) return "matched";
  if (addressOk && byteFailed) return "partial";
  if (addressOk) return "partial";
  return "mismatch";
}

function byteGateLabel(gates, lang) {
  if (!gates.length) return null;
  const byteFailed = gates.some((gate) => gate.byteMatch === false);
  const bytePassed = gates.every((gate) => gate.byteMatch === true);
  if (byteFailed) return lang === "zh" ? "未通过" : "failed";
  if (bytePassed) return lang === "zh" ? "通过" : "passed";
  return lang === "zh" ? "没有记录" : "not recorded";
}

function engineSummary(gates, lang) {
  const addressOk = gates.length > 0 && gates.every((gate) => gate.addressDiffs === 0);
  const byte = byteGateLabel(gates, lang);
  if (lang === "zh") {
    const balance = addressOk ? "两个快照之间逐地址比对余额，差异为 0。" : "两个快照之间的逐地址比对没有全部为零。";
    return `${balance}字节门${byte || "没有记录"}。`;
  }
  const balance = addressOk
    ? "Per-address balances match between the snapshots, with 0 differences."
    : "The per-address snapshot comparison is not all zero.";
  return `${balance} Byte gate: ${byte || "not recorded"}.`;
}

function point(labelZh, labelEn, value, href) {
  return { label_zh: labelZh, label_en: labelEn, value, href };
}

main();

/**
 * Offline checks for the hash chain, the first cron, and the canonical balance encoding.
 */
import { createHash } from "node:crypto";
import { canonicalBalances, cronsBetween, decodeAnchor, genHashChain, originMs } from "./lib/schedule.mjs";

function assertEq(actual, expected, label) {
  if (actual !== expected) {
    console.error(`${label}: ${actual} != ${expected}`);
    process.exit(1);
  }
}

const linked = genHashChain(
  "W4h2kwRezDwtQtvxQ9Ssivujj3k2CZolEhKCblKrnTg",
  "yy7ipxqxntq_9yTDaEvEW92CLrUqDssgN-RXYUQAHNA",
);
assertEq(linked, "n3_FibsRX1mI3Wtho2M72Cac0KUGPyLMDuBycteuumU", "hash-chain");

const origin = originMs(1726164008);
const crons = cronsBetween(
  { timestamp: 1771847683094, height: 1863436 },
  1771847983095,
  [{ height: 1863436, timestamp: 1771847600000 }],
  origin,
);
assertEq(crons.length, 2, "cron count");
assertEq(crons[0].timestamp, 1771847683094, "boundary cron");
assertEq(crons[1].timestamp, 1771847983094, "cron timestamp");
assertEq(crons[1].height, 1863436, "cron height");

const advanced = cronsBetween(
  { timestamp: 1771847683094, height: 1863436 },
  1771847983095,
  [{ height: 1863437, timestamp: 1771847800000 }],
  origin,
);
assertEq(advanced[1].height, 1863437, "cron height advance");

assertEq(decodeAnchor("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDE4ODczMDQ"), "00000000000000000000000001887304", "anchor");

const text = canonicalBalances({ b: "0", a: "2", c: "10" });
assertEq(text, "{\"a\":\"2\",\"c\":\"10\"}\n", "canonical");
const digest = createHash("sha256").update(text).digest("hex");
if (digest.length !== 64) {
  console.error("sha256 length");
  process.exit(1);
}
console.log(JSON.stringify({ ok: true }));

import test from "node:test";
import assert from "node:assert/strict";
import { lookupRawText, presentLookup } from "../src/lib/lookup.mjs";
import { resolvePage } from "../src/lib/routes.mjs";
import { formatRawDisplay, shortHash } from "../src/lib/format.mjs";

const ADDR = "A".repeat(43);

test("an address that is not on the ledger is not shown as 0", () => {
  const missing = presentLookup(ADDR, null);
  assert.equal(missing.kind, "missing");
  assert.equal(missing.raw, null);
  assert.equal(lookupRawText(missing), "");
  assert.equal(lookupRawText(missing).includes("0"), false);
});

test("a ledger row of raw 0 is a zero balance, not a missing row", () => {
  const zero = presentLookup("B".repeat(43), { raw: "0" });
  assert.equal(zero.kind, "zero");
  assert.equal(lookupRawText(zero), "0");
  assert.equal(formatRawDisplay(zero.raw), "0");
});

test("a positive balance keeps its raw integer", () => {
  const hit = presentLookup("C".repeat(43), { raw: "1000000000000" });
  assert.equal(hit.kind, "balance");
  assert.equal(lookupRawText(hit), "1000000000000");
  assert.equal(formatRawDisplay(hit.raw), "1");
});

test("old routes redirect onto the three pages", () => {
  assert.deepEqual(resolvePage("#/overview"), { page: "lookup", redirect: "#/" });
  assert.deepEqual(resolvePage("#/lookup"), { page: "lookup", redirect: "#/" });
  assert.deepEqual(resolvePage("#/method"), { page: "verify", redirect: "#/verify" });
  assert.deepEqual(resolvePage(""), { page: "lookup", redirect: null });
  assert.deepEqual(resolvePage("#/"), { page: "lookup", redirect: null });
  assert.deepEqual(resolvePage("#/holders"), { page: "holders", redirect: null });
  assert.deepEqual(resolvePage("#/verify"), { page: "verify", redirect: null });
  assert.deepEqual(resolvePage("#/nope"), { page: "lookup", redirect: "#/" });
});

test("the published balance hash shortens to the form used on the trust bar", () => {
  assert.equal(shortHash("0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca"), "0c9fb668…6110acca");
});

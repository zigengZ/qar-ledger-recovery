import test from "node:test";
import assert from "node:assert/strict";
import { formatRaw, formatFraction, formatPercent, formatPercentFixed, formatRawDisplay, formatRawGrouped, formatRawRounded } from "../src/lib/format.mjs";

test("zero raw is 12 decimal places", () => {
  assert.equal(formatRaw("0"), "0.000000000000");
});

test("one raw unit is the last decimal place", () => {
  assert.equal(formatRaw("1"), "0.000000000001");
});

test("one whole token", () => {
  assert.equal(formatRaw("1000000000000"), "1.000000000000");
});

test("tail total supply", () => {
  assert.equal(formatRaw("189487568412204611"), "189487.568412204611");
});

test("oQAR snapshot raw", () => {
  assert.equal(formatRaw("7725686192460"), "7.725686192460");
});

test("leading zeros do not change the value", () => {
  assert.equal(formatRaw("0000000000001"), "0.000000000001");
});

test("negative one token", () => {
  assert.equal(formatRaw("-1000000000000"), "-1.000000000000");
});

test("rejects values that are not integer strings", () => {
  assert.throws(() => formatRaw("1.2"));
  assert.throws(() => formatRaw(""));
  assert.throws(() => formatRaw("1e2"));
  assert.throws(() => formatRaw("12 "));
  assert.throws(() => formatRaw(189487568412204611));
});

test("grouped display keeps the 12 decimal places", () => {
  assert.equal(formatRawGrouped("189487568412204611"), "189,487.568412204611");
});

test("full supply is the whole fraction", () => {
  assert.equal(formatFraction("189487568412204611", "189487568412204611", 12), "1.000000000000");
});

test("percent stays exact for the zero and the full supply", () => {
  assert.equal(formatPercent("0", "189487568412204611"), "0%");
  assert.equal(formatPercent("189487568412204611", "189487568412204611"), "100%");
});

test("kpi supply rounds half up to 2 places", () => {
  assert.equal(formatRawRounded("189487568412204611", 2), "189,487.57");
  assert.equal(formatRawRounded("500000000000000", 2), "500.00");
  assert.equal(formatRawRounded("1005000000000", 2), "1.01");
});

test("display amount uses thousands separators and drops trailing zeros", () => {
  assert.equal(formatRawDisplay("189487568412204611"), "189,487.568412204611");
  assert.equal(formatRawDisplay("1000000000000"), "1");
  assert.equal(formatRawDisplay("1500000000000"), "1.5");
  assert.equal(formatRawDisplay("1000000000001"), "1.000000000001");
  assert.equal(formatRawDisplay("1"), "0.000000000001");
  assert.equal(formatRawDisplay("0"), "0");
  assert.equal(formatRawDisplay("-2500000000000"), "-2.5");
});

test("display percent keeps fixed places and hides dust", () => {
  const supply = "189487568412204611";
  assert.equal(formatPercentFixed("0", supply, 4), "—");
  assert.equal(formatPercentFixed("1", supply, 4), "<0.0001%");
  assert.equal(formatPercentFixed("180398401009414645", supply, 2), "95.20%");
  assert.equal(formatPercentFixed("180398401009414645", supply, 4), "95.2032%");
  assert.equal(formatPercentFixed(supply, supply, 2), "100.00%");
});

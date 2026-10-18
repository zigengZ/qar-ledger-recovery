import assert from "node:assert/strict";
import test from "node:test";
import { canonicalBalanceText } from "../src/lib/canonical.mjs";
import { FORBIDDEN_TAGS, TYPOGRAPHY_TAGS } from "../src/lib/sanitize-policy.mjs";

test("canonical text sorts addresses, drops zeros, and ends with a newline", () => {
  const text = canonicalBalanceText([
    ["b", "1"],
    ["a", "2"],
    ["c", "0"],
    { address: "d", raw: "10" },
  ]);
  assert.equal(text, '{"a":"2","b":"1","d":"10"}\n');
});

test("markdown policy keeps typography and drops active tags", () => {
  for (const tag of ["form", "input", "button", "svg", "math", "iframe"]) {
    assert.equal(TYPOGRAPHY_TAGS.includes(tag), false);
    assert.equal(FORBIDDEN_TAGS.includes(tag), true);
  }
  for (const tag of TYPOGRAPHY_TAGS) assert.equal(FORBIDDEN_TAGS.includes(tag), false);
});

import assert from "node:assert/strict";
import test from "node:test";
import {
  canonicalFromExpected,
  prepareRecoveryMarkdown,
  publicRepoSlug,
  publicViolation,
  publishNeedles,
  repoBlobBaseFromSlug,
  repoSlugFromRemote,
  scrubText,
} from "./methodology.mjs";

const ID = "ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk";
const BLOB = "https://github.com/zigengZ/qar-ledger-recovery/blob/main";
const SHA = "ab".repeat(32);

test("chain id length used by the linker", () => {
  assert.equal(ID.length, 43);
});

test("relative links point at repository files and bare ids point at arweave", () => {
  const out = prepareRecoveryMarkdown(
    `See [ledger](../evidence/p10/ledger.csv) and ${ID}.\n\nAlready [tx](https://arweave.net/${ID}).\n`,
    "docs/RECOVERY.md",
    BLOB,
    [],
  );
  assert.match(out, /https:\/\/github\.com\/zigengZ\/qar-ledger-recovery\/blob\/main\/evidence\/p10\/ledger\.csv/);
  assert.match(out, new RegExp(`\\[${ID}\\]\\(https://arweave\\.net/${ID}\\)`));
  assert.equal(out.match(new RegExp(`arweave\\.net/${ID}`, "g")).length, 2);
});

test("an existing arweave url is not rewritten into a nested link", () => {
  const out = prepareRecoveryMarkdown(`https://arweave.net/${ID}`, "docs/RECOVERY.md", BLOB, []);
  assert.equal(out, `https://arweave.net/${ID}`);
});

test("without a repository base, a relative link stays a repo path", () => {
  const out = prepareRecoveryMarkdown("[ledger](../evidence/a.json)", "docs/RECOVERY.md", null, []);
  assert.equal(out, "`evidence/a.json`");
});

test("links that leave the repository are not published", () => {
  const out = prepareRecoveryMarkdown("[secret](../../../../etc/passwd)", "docs/RECOVERY.md", BLOB, []);
  assert.equal(out, "secret");
});

test("local paths, addresses, and host names are removed", () => {
  const local = `/${"root"}/codes/secret`;
  const mail = ["a", "b.co"].join("@");
  const out = scrubText(`box ${local} at 10.1.2.3 mail ${mail} host box-1`, ["box-1"]);
  assert.equal(publicViolation(out, ["box-1"]), null);
  assert.match(out, /\[redacted\]/);
  assert.doesNotMatch(out, /\/root\/|10\.1\.2\.3|a@b\.co|box-1/);
});

test("a supply amount is not treated as an address", () => {
  assert.equal(publicViolation("189487.568412204611"), null);
});

test("canonical balance hash is preferred over other sha256 fields", () => {
  assert.deepEqual(
    canonicalFromExpected({ canonical_balances_sha256: SHA, memory_sha256: "cd".repeat(32) }),
    { sha256: SHA, field: "canonical_balances_sha256" },
  );
  assert.equal(canonicalFromExpected({ memory_sha256: "cd".repeat(32) }), null);
  assert.equal(canonicalFromExpected({ canonical: { sha256: SHA } }).field, "canonical.sha256");
});

test("ssh remotes yield the repository slug and not the ssh alias", () => {
  assert.equal(repoSlugFromRemote("git@example-alias:zigengZ/qar-ledger-recovery.git"), "zigengZ/qar-ledger-recovery");
  assert.equal(publicViolation(repoSlugFromRemote("git@example-alias:zigengZ/qar-ledger-recovery.git"), ["example-alias"]), null);
});

test("blob links use the public slug while needles keep the real remote", () => {
  const remote = "git@example-alias:zigengZ/qar-ledger-recovery-private.git";
  assert.equal(publicRepoSlug({}), "zigengZ/qar-ledger-recovery");
  assert.equal(publicRepoSlug({ PUBLIC_REPO_SLUG: "  " }), "zigengZ/qar-ledger-recovery");
  assert.equal(publicRepoSlug({ PUBLIC_REPO_SLUG: "octo/other" }), "octo/other");
  assert.equal(
    repoBlobBaseFromSlug(publicRepoSlug({})),
    "https://github.com/zigengZ/qar-ledger-recovery/blob/main",
  );
  assert.equal(repoSlugFromRemote(remote), "zigengZ/qar-ledger-recovery-private");
  assert.notEqual(repoBlobBaseFromSlug(publicRepoSlug({})), `https://github.com/${repoSlugFromRemote(remote)}/blob/main`);
  assert.deepEqual(publishNeedles({ hostname: "build-host", remote }), ["build-host", "example-alias"]);
  assert.throws(() => publicRepoSlug({ PUBLIC_REPO_SLUG: "not a slug" }), /owner\/repo/);
});

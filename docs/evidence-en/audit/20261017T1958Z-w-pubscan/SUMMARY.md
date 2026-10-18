> English translation of [`evidence/audit/20261017T1958Z-w-pubscan/SUMMARY.md`](../../../../evidence/audit/20261017T1958Z-w-pubscan/SUMMARY.md). The original is authoritative.

# w-pubscan

Review before the public export. First, the public copy already prepared was compared read-only (1290 files, branch master, author Zigza). Fixes are on `worker/w-pubscan`. The re-check used `audit/make-public-export.sh` to write into a temporary directory, which was deleted after confirmation. The final export has 1291 files, default branch `main`, and `audit/scan.sh --strict` must-fix 0. The exported bytes equal the working tree, and the export script did not rewrite paths again.

## 1. Identity leaks

The private word list (host names, ssh aliases, user names, private project names, screen ids, IPs) was checked word by word, case-insensitively. These words appear 0 times in the final export.

The remaining hits are not host names:

- `zigza` appears in `https://qar-balances.zigza.xyz`. The encoding name `zigzag` contains the same letters; that is Avro integer encoding, not a host name.
- `hyperbeam` appears only as the public protocol name HyperBEAM in `RECOVERY_PLAN.md`, in a sentence saying not to use it in place of the historical module.
- `m8` falls inside transaction ids (`_m8`, `-M8`), not a host name.
- `inbox` stays as an AO process tag in test fixtures under `vendor/drive-cu`. The private inbox path was changed to `private-config/`.

Regex checks: no email addresses, no paths under the local root, home directory, or drive letters, no screen, tmux, ssh directories, or status completion markers. The ssh alias was removed from `STATE.md`. One documented test IP exists only in a site sanitizer fixture. The 17 should-fix items from `scan.sh` are all the allowed GitHub login `zigengZ`.

## 2. Directories after placeholders

No directory names follow `<local-root>/`, `<worktrees>/`, or `<home>/`. Gitignored raw downloads are still written as `<repo>/data/raw/...`. Worker directories and inbox paths were changed to repository-relative paths or `private-config/`.

## 3. Holder wallets

The 14 addresses still appear as ledger rows, transfer records, and the `owner_address` of messages. `owner_address` is the ANS-104 signer field, not "someone's own wallet". They are not labeled as a personal list, and there are no position file names or indirect holding lists. The earlier personal-list wording in `STATE.md` was rewritten.

## 4. Credentials

No PEM, JWK private keys, seed phrases, `ghp_`, `github_pat_`, `AKIA`, `xox`, `sk-`, Bearer, basic auth, `.env` secrets, Cloudflare tokens, nginx/systemd configs, certificates, webhooks, ssh public keys, or deploy keys. Apart from `qar-balances.zigza.xyz`, there is no other `*.zigza.xyz`.

The binary files are two test wasm files under `vendor/drive-cu` (about 291 KB). Files larger than 5MB are the holder classification, the collateral flows, and the P5 candidate checkpoint JSON, all smaller than 100MB. No file exceeds 100MB.

## 5. Hash chain

Every `(path, sha256[, bytes])` recorded in manifest, reconciliation, SUMMARY, `audit/REDACTIONS.md`, `repro/EXPECTED.json`, and `web/public/data/manifest.json` whose target is in the export tree was re-checked and matches. On the final export, the in-tree check is 249 matching and 0 mismatching. Entries for `data/raw/` point to gitignored downloads that are not in the tree, which is expected.

The earlier mismatches were caused by the export replacing absolute paths with placeholders. The working tree now applies the same replacement first, and the manifests and `audit/REDACTIONS.md` were updated. The three `ledger.csv` files at 0954, 1047, and 1720 still have 7615 rows, and the raw balance total is still `189487568412204611`. The 0906 holder file still has 7614 entries, and 1031 still has 7615.

## 6. README

The relative links in `README.md`, `README.zh.md`, and `docs/PUBLICATION.md` all exist. The English README has no Chinese, and no "pending" or "Another session is writing this file". The text saying the canonical hash is still pending and the main replay is not yet cross-checked was removed. Both languages state that the main replay matches.

Running the 3-line Python from the README at the export root prints `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`.

## 7. Work logs

A "this is a work log" line was added at the top of `STATE.md`, `GOAL.md`, `STOP.md`, `RECOVERY_PLAN.md`, `AGENTS.md`, `SUMMARY.md`, `web/SUMMARY.md`, and each evidence `SUMMARY.md`. `docs/RECOVERY.md` and `docs/RECOVERY.zh.md` gained the current results, and no longer describe the canonical hash as pending or the main replay as in progress. In `STATE.md`, wording naming "the user" as the decision maker was changed to later decision.

## 8. Does it run

In the final export directory:

- `python3 -m unittest discover -s tests -t .`: 202 tests, 2 skipped, passed. The skips are the missing gitignored `data/raw/p7/process-tx.json` and one pre-existing skip.
- `bash -n` passes for every `.sh`.
- `node --check` passes for `.mjs` / `.js` outside `vendor/` and `node_modules/`.
- `cd web && npm ci --ignore-scripts && npm test && npm run build` passes. Node is v22.22.0. Without an `origin`, the build prints `No such remote 'origin'`, then uses the default repository slug, and the build still succeeds. Without `data/raw`, the `raw` cross-check is recorded as absent.
- `repro/run.sh` and `repro/README.md` start from the repository root and have no placeholder paths. The download was not actually run.

`recovery/p6/replay.mjs` loads `@permaweb/ao-loader` only when run as the entry point, so the cron unit test does not need that package installed first.

## 9. Other

The README states that the memory sha256 of the main replay, the fast replay, and the clean clone match, and states the trust assumption on the checkpoint signer. `LICENSE` is MIT, and `vendor/drive-cu` stays BUSL-1.1. There is no `.github`. The export script was changed to `git init -b main`, consistent with the `blob/main` links in the docs. The 120 hole directories under `evidence/p4/` are explained in one sentence in each README: each directory is one exact query that closed empty, not a missing ledger row.

`goal_complete` is still false. The separable collateral raw amount is still null. `classification_sourced` is still false. Nonce coverage from genesis is still incomplete. These are ledger conclusions, not publication blockers.

## What was fixed

- Absolute local paths in evidence and scripts were changed to export placeholders or repository-relative paths.
- sha256 values and byte counts in manifests, SUMMARY files, and `audit/REDACTIONS.md` were updated to the current files.
- README, RECOVERY, site data, and build scripts were changed to say the main replay is complete.
- ssh aliases, private host names, and personal wallet list wording were removed.
- Site scripts use `node` and no longer hard-code a local install path.

## What remains

- `data/raw/` is not in the repository; its sha256 values must be checked after downloading again.
- Set `PUBLIC_GIT_NAME` and `PUBLIC_GIT_EMAIL` for the real publication. The script's default author is `qar-ledger`, not Zigza as in the existing public copy.
- Do not push the private branch history directly. Publish through the squash export.

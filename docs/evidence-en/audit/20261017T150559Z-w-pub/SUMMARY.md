> English translation of [`evidence/audit/20261017T150559Z-w-pub/SUMMARY.md`](../../../../evidence/audit/20261017T150559Z-w-pub/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# w-pub pre-publication cleanup

`bash audit/scan.sh` exits 0, must-fix 0, should-fix 69084. The full output is in `scan.txt`. The should-fix items are absolute paths under the local root and the GitHub login. The absolute paths are left for the export script to replace. The login mentions in `RECOVERY_PLAN.md` and `web/` were not changed.

## Evidence redaction

The tail copy was redacted the same way as `evidence/p8/20261017T0906Z-w-p8/`. Private pool keys, fee rates, private repository paths, and short git shas in source sentences were replaced with placeholders. Addresses, raw balances, human-readable balances, classes, and row counts were not changed.

| File | Result |
| --- | --- |
| `holders-classified.json` | Still 7615 entries. No difference in non-source fields. 19 pool sentences, 1 lending sentence. |
| `pools-locks-bridges.json` | Still 2341 rows. No difference in non-source fields. The same 19 + 1 source sentences. |
| `local-configs.json` | Config keys and fee rates changed to `redacted`. Private file line numbers and short git shas emptied. Paths changed to `private-config`. Addresses, dex names, and excerpt line numbers kept. |
| `ledger.csv` | Still 7615 data rows, 7616 lines with the header. The raw balance total is still `189487568412204611`. 19 pool sentences, 1 lending sentence. No difference in the address, raw balance, human balance, and class columns. |

`query-manifest.json` and `stats.json` in `evidence/p8/20261017T1031Z-w-p8-tail/` do not hash these four files, so their hash fields were not changed. The manifests that reference the new bytes are `manifest.json`, `reconciliation.json`, and `SUMMARY.md` in `evidence/p10/20261017T1047Z-fast-tail/`, plus `web/public/data/manifest.json`. Old and new values are in the "w-pub addendum" section of `audit/REDACTIONS.md`.

Three email-shaped strings: the pattern text in two SUMMARY files was changed to `local-part [at] domain.tld`. The fixture in `web/scripts/methodology.test.mjs` was changed to `["a", "b.co"].join("@")`.

## Public export

`audit/make-public-export.sh` still defaults to squash, and still refuses to write into this repository or into an existing directory. After unpacking, it deletes `web/shots/`, `audit/scan.sh`, `audit/make-public-export.sh`, and `audit/PUBLIC-READINESS.md`. `audit/REDACTIONS.md` is kept. The strict scan now runs the source repository's `audit/scan.sh --strict` after `git init && git add -A` in the target directory. If it fails, nothing is committed, the exit code is 1, and the directory is left in place. The procedure is in `docs/PUBLICATION.md`.

Site blob links no longer follow the git remote. `PUBLIC_REPO_SLUG` can override them, and the default is `zigengZ/qar-ledger-recovery`. `publishNeedles` still uses the real remote and host names.

## Tests

`cd web && npm test`: 25 passed, including the email fixture and the public slug.

`python3 -m unittest discover tests`: of 76, 74 passed, 1 skipped, 1 failed. The failure is `test_p7_nonce0`. It requires the boot memory sha256 to equal `72db7b1e8806d7621fe1d2fe8a3274f0cbef2105da5facb7da94c3141ba2d5ac`. This run got `9f32451c2dfd87ca547dd92797a280365666a32a49a83cb88ac33fe98d2ccc51`, with the same size of 7602176 bytes. The nonce 0 Eval is still a handler error, and this message did not rewrite memory. The script paths inside the two memories differ: the recorded run used the main checkout, and this run used `genesis-segment.mjs` in this worktree. The expected hash in the test was not changed.

`audit/make-public-export.sh /tmp/qar-pub-test` exits 0. The target has no `web/shots`, `audit/scan.sh`, `audit/make-public-export.sh`, or `audit/PUBLIC-READINESS.md`. `audit/REDACTIONS.md` and `docs/PUBLICATION.md` are present. `git log` has exactly 1 commit, with the script's default author `qar-ledger` and email `dev@localhost`. Scanning that directory with the source repository's `audit/scan.sh --strict --lines`: exit 0, must-fix 0, should-fix 16, all GitHub login mentions. `/tmp/qar-pub-test` was deleted after the check. The export script did not change the source repository.

> English translation of [`evidence/audit/20261017T105101Z-w-audit/SUMMARY.md`](../../../../evidence/audit/20261017T105101Z-w-audit/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# w-audit 20261017T105101Z

## Conclusion

The pre-publication must-fix items in this branch's working tree are cleared. `bash audit/scan.sh` exits 0: must-fix 0, should-fix 26519 (GitHub login 2, absolute paths under the local root 26517).

The existing history cannot be published. After the commit entered the object store, `bash audit/scan.sh --history` was run again: exit 1, must-fix 901, should-fix 118177. All 901 come from historical blobs. The 118177 include absolute paths left in the current tree and in this commit's new blobs, plus repeat counts from old blobs on other branches. This commit did not add any must-fix. `953ff3a` on `main` still has an unredacted ledger `evidence/p10/20261017T1047Z-fast-tail/ledger.csv` (18 fee rates, 97 private markers). `evidence/p8/20261017T1031Z-w-p8-tail/` at `75aec06` is another full copy. Neither of these is on this branch.

The recommended publication path is a squash export, not filter-repo, and not publishing other branches. `audit/make-public-export.sh` is written. By default it writes to a new directory. It was not run this time.

## Numbers

- This branch starts at `f90d6f5` and has 57 commits. At the time of writing, `git log --all` has 67 commits.
- About 280 tracked files.
- Credentials: PEM, JWK private keys, AKIA, GitHub tokens, Slack tokens, database URLs with passwords, and seed phrases are 0 in both the current tree and the history. `WALLET` in `.env.example` is 5 asterisks.
- Evidence identity: 7614 holders, 2341 pool rows, 7615 ledger rows. The raw balance total `189487568412204611` is unchanged.
- License: `vendor/drive-cu/LICENSE` is 2941 bytes, sha256 `2c736f1951109b205d4d394285f46e7ceb4bf8a57149ce08c37452aed6e6775d`.
- Tests: `python3 -m unittest tests.test_p8_classify`, 4 passed.
- `bash -n audit/make-public-export.sh` passes.

## Evidence paths

- `audit/PUBLIC-READINESS.md`
- `audit/REDACTIONS.md`
- `audit/scan.sh`
- `audit/make-public-export.sh`
- `vendor/drive-cu/LICENSE`
- This file

## Not done

- `audit/make-public-export.sh` was not run. Before publication, run it on a clean copy of this branch and make `audit/scan.sh --strict` pass in the new directory.
- Absolute paths under the local root remain in the private tree (should-fix). The export script rewrites them.
- Two GitHub login mentions (`RECOVERY_PLAN.md:231`, `evidence/plan-baseline-20261017.json:5`) are left for the owner to decide.
- The git author email prefix `zzg1` (56 commits on this branch, plus 10 on other branches) and the noreply prefix `8980` (1 commit) are left for the owner to decide. A published history would carry them.
- The unredacted copies on other branches and on `main` were not changed. This worker does not change those branches.

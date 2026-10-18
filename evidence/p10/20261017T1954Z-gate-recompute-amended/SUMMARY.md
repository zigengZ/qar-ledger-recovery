# Amended gate recompute

`goal_complete=true`. This is not a claim list. `publish_claims` is false. `move_collateral` is false.

Two runs of `python3 -m recovery.p10.build_report` wrote `run-1/` and `run-2/`. The replay input is `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`. That file has no last-nonce object. The builder treats it as a finished tail replay because it exited, handler errors are 0, and the assignment count equals the tail nonce minus checkpoint nonce 2074518. It does not invent a last nonce. Agreement inputs are `evidence/repro/20261017T120218Z-w-repro/result-offset-0.json` and `evidence/p10-indep/20261017T104141Z-w-indep/result.json`.

`runs-match.json` records that the two flag objects are equal. Every amended flag is true. Canonical balance SHA-256 is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. Collateral `delta_raw` is null. Legacy `schedule_covered`, `inputs_complete`, `classification_sourced`, `collateral_sourced`, and `collateral_reconciled` stay false. Those legacy flags are not the completion rule.

`goal_complete=true` means the ledger is ready for public audit. It is not an instruction to distribute. P11 starts after the repository is public.

> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P10 gate recompute

`goal_complete=false`. This is not a claim list. `publish_claims` is false. `move_collateral` is false.

The procedure is `python3 -m recovery.p10.build_report`. Supply is the integer string in `evidence/p10/20261017T1047Z-fast-tail-inputs/supply.json`. The ledger sum is subtracted from that supply. The difference is 0. The collateral delta is null.

Two runs on the 1720 inputs, including `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`, match. `pass_all_ten` is false. The crosscheck sha match and zero balance diff are read. That file has no last nonce, so the replay check stays unmet.

Two runs that use `evidence/p7/20261017T1718Z-p7-replay-read/replay.json` also match. The replay check is met. `schedule_covered`, `inputs_complete`, `classification_sourced`, `collateral_sourced`, and `collateral_reconciled` stay false. `pass_all_ten` is false.

Unindexed span: 150000..2074399. Explicit missing nonces: 759. Unknown processes: 369. Wallet rows: 5274. Full safe mode was not run.

Do not open a P4 range at nonce 150000 or later. Do not relabel `unknown_process`. Do not replace the null collateral amount with 0.

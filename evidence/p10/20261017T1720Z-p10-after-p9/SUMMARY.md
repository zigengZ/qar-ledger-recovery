> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

BLOCKED — NOT A CLAIM LIST

The main replay memory sha256 matches `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The tail table has 7615 rows and the raw sum equals Total-Supply `189487568412204611`.

P9 records native AR. There is no single holder. The separable raw amount is null, not 0. `collateral_sourced` is false. `collateral_reconciled` is false. `classification_sourced` is false. `goal_complete` is false. This is not a finished ledger.

# P10 reconciliation

## Conclusion

goal_complete is false. publish_claims is false. move_collateral is false.
Ledger nonce 2075923 has 7615 rows. sum_raw 189487568412204611. total_supply_raw 189487568412204611. sum_equals_total_supply True. ledger_delta_raw 0.
Collateral delta_raw is None (unknown). held raw amount at the tail is unknown.
Checkpoint-to-tail hash chain continuous=True, links 1523/1523.
See REPORT.md for each Done means line.

## Numbers

- rows: 7615
- bad balance values omitted: 0
- classified addresses without a balance row: 0
- explicit missing nonces: 759
- unindexed spans: [[150000, 2074399]]
- class bridge: count 0, raw 0
- class lock: count 2, raw 250346157301342
- class pool: count 74, raw 2330669314779690
- class user: count 5279, raw 186394240884573076
- class process_unknown: count 2260, raw 512312055550503

## Evidence

- `evidence/p10/20261017T1720Z-p10-after-p9/ledger.csv`
- `evidence/p10/20261017T1720Z-p10-after-p9/reconciliation.json`
- `evidence/p10/20261017T1720Z-p10-after-p9/REPORT.md`
- `evidence/p10/20261017T1720Z-p10-after-p9/manifest.json`
- `data/raw/fast/tail/balances.json` sha256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` bytes 402362
- `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json` sha256 `eedd1fbf0b2bb98fbe0cc31516326e68e14826009b84196e1c036359eda5d95b` bytes 7927333
- `evidence/p9/20261017T1720Z-p9-record/collateral-for-report.json` sha256 `4ccceac6aff5c4a6181e3909864b538e882d1d610a0f709a68bd2cb4a4187312` bytes 891
- `evidence/p1-tail.json` sha256 `bafbca307ecf881bc716422bb4fe75506e433b9331c8e2d1e03eb6b0c4babe1f` bytes 2773
- `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json` sha256 `dffec5063b94ce927472a648fedccfe10d7f19ed2a11eb636c9eb94dc98578a3` bytes 1494
- `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json` sha256 `0892943cc64cacae28d2817c31af4f695af16c43c16cb7cd5a33424f30c55eec` bytes 2277
- `evidence/p10/20261017T1047Z-fast-tail-inputs/supply.json` sha256 `0a92e154063267a8ebc1df009864618b19aa3a826f49b6166b7c98ef954416f1` bytes 326
- `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` sha256 `62741c3f5ad08866db3bf1ba9fb7004a3d23036ce13225d717fe0071b23990df` bytes 119958
- `evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json` sha256 `3a8d24dc6e0fd8bd5fd97194b7bbacf0f10c4d0609618c33e522c75c9a32de1a` bytes 1851
- `evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json` sha256 `596b601def373d68172705c49ce911458c409ca5a6dc98ddfa907c1e141cc439` bytes 1356
- `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json` sha256 `dbc3123a5f771431d8209049950d5787447932b2fcf1dc46b25369f117df7ef2` bytes 116357
- `evidence/p6/20261017T052333Z-w-eval/evaluator.json` sha256 `2ea96c6f4d5cf50aa44c5b199531fc080e6f965b9f6726ecc4ff95a48383fe31` bytes 2444
- `evidence/p6/20261017T052333Z-w-eval/semantic.json` sha256 `9a469c29d0c5bd09fba06375bfbec0bc81f046669b07865d65d557f637ddb770` bytes 4812

## Unfinished

- 不满足. Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.
- 不满足. Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.
- 不满足. Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

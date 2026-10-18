> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

精确回放结果，你这条独立回放的最终 sha 交叉核对还没做完

w-fast 从主回放已核对的 next_index 8400 内存继续，以 inplace 跑到 nonce 2075923。handler 错误 0。余额 7615 行。原始合计与单独读出的 Total-Supply 都是 189487568412204611。最终内存 sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。写这份记录时主回放还在运行。后来的主回放内存 sha 与这里一致，见 README。

`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 按 P8 写成 wallet，身份未核实。表内 class `user` 只是 build_report.py 对 P8 wallet 的映射，不是已核实身份。

这不是领取名单。`goal_complete=false`。`classification_sourced` 仍为 false。抵押物差额是 unknown。

# P10 reconciliation

## Conclusion

goal_complete is false. publish_claims is false. move_collateral is false.
Ledger nonce 2075923 has 7615 rows. sum_raw 189487568412204611. total_supply_raw 189487568412204611. sum_equals_total_supply True. ledger_delta_raw 0.
Collateral delta_raw is None (unknown). collateral.json was not provided. The gap is unknown.
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
- class user: count 5278, raw 186393679140702692
- class process_unknown: count 2261, raw 512873799420887

## Evidence

- `evidence/p10/20261017T0954Z-fast-tail/ledger.csv`
- `evidence/p10/20261017T0954Z-fast-tail/reconciliation.json`
- `evidence/p10/20261017T0954Z-fast-tail/REPORT.md`
- `evidence/p10/20261017T0954Z-fast-tail/manifest.json`
- `data/raw/fast/tail/balances.json` sha256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` bytes 402362
- `evidence/p8/20261017T0906Z-w-p8/holders-classified.json` sha256 `a990d811144e5157e308deb33f6b377dcfd14fef554ccd9f358630f4f213f2f6` bytes 6457661
- `evidence/p1-tail.json` sha256 `bafbca307ecf881bc716422bb4fe75506e433b9331c8e2d1e03eb6b0c4babe1f` bytes 2773
- `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json` sha256 `dffec5063b94ce927472a648fedccfe10d7f19ed2a11eb636c9eb94dc98578a3` bytes 1494
- `evidence/p10/20261017T0954Z-fast-tail-inputs/replay.json` sha256 `455da50e72c52ebe752495560d7268438c699212fa39e61dfd07b4a4b0edeb53` bytes 804
- `evidence/p10/20261017T0954Z-fast-tail-inputs/supply.json` sha256 `82ebc440fb8094451bd968a5907f3b9dbb272db1c0f15b363d79402861aceedb` bytes 413
- `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` sha256 `62741c3f5ad08866db3bf1ba9fb7004a3d23036ce13225d717fe0071b23990df` bytes 119958
- `evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json` sha256 `3a8d24dc6e0fd8bd5fd97194b7bbacf0f10c4d0609618c33e522c75c9a32de1a` bytes 1851
- `evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json` sha256 `596b601def373d68172705c49ce911458c409ca5a6dc98ddfa907c1e141cc439` bytes 1356
- `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json` sha256 `dbc3123a5f771431d8209049950d5787447932b2fcf1dc46b25369f117df7ef2` bytes 116357
- `evidence/p6/20261017T052333Z-w-eval/evaluator.json` sha256 `2ea96c6f4d5cf50aa44c5b199531fc080e6f965b9f6726ecc4ff95a48383fe31` bytes 2444
- `evidence/p6/20261017T052333Z-w-eval/semantic.json` sha256 `9a469c29d0c5bd09fba06375bfbec0bc81f046669b07865d65d557f637ddb770` bytes 4812

## Unfinished

- 不满足. Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.
- 不满足. Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.
- 不满足. Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.
- 不满足. Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

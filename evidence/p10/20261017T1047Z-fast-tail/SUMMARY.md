> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

写这份记录时，主回放 sha 复核尚未结束。后来已对照一致，见 README。

w-fast 尾部账本有 7615 行。原始合计与单独读出的 Total-Supply 都是 `189487568412204611`。最终内存 sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。写这份记录时主回放还在运行。后来的主回放内存 sha 与这里一致，见 README。

五笔 Transfer 的 Data 在 `https://arweave.net/raw/{id}` 上是 0 字节，content-digest 是空字节串的 SHA-256。数量在 Quantity tag。活的 Transfer handler 不读 Data，空 Data 不当成数量 0。这五笔的 nonce 是 2074509、2074511、2074513、2074515、2074517，不在尾部区间 2074519..2075923。证据 `evidence/p6/20261017T102111Z-w-eval/`。

`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 按 P8 写成 wallet，身份未核实。表内 class `user` 只是 build_report.py 对 wallet 的映射。

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
- class user: count 5279, raw 186394240884573076
- class process_unknown: count 2260, raw 512312055550503

## Evidence

- `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`
- `evidence/p10/20261017T1047Z-fast-tail/reconciliation.json`
- `evidence/p10/20261017T1047Z-fast-tail/REPORT.md`
- `evidence/p10/20261017T1047Z-fast-tail/manifest.json`
- `data/raw/fast/tail/balances.json` sha256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` bytes 402362
- `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json` sha256 `eedd1fbf0b2bb98fbe0cc31516326e68e14826009b84196e1c036359eda5d95b` bytes 7927333
- `evidence/p1-tail.json` sha256 `bafbca307ecf881bc716422bb4fe75506e433b9331c8e2d1e03eb6b0c4babe1f` bytes 2773
- `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json` sha256 `dffec5063b94ce927472a648fedccfe10d7f19ed2a11eb636c9eb94dc98578a3` bytes 1494
- `evidence/p10/20261017T1047Z-fast-tail-inputs/replay.json` sha256 `cd3a514c73507d78fe1f966c03b0c342d43f6c51bc705c73e3c64e109f0094ff` bytes 676
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

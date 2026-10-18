> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# 试运行，不是最终结果

## Conclusion

goal_complete is false. publish_claims is false. move_collateral is false.
Ledger nonce 2074518 has 7614 rows. sum_raw 189487568412204611. total_supply_raw 189487568412204611. sum_equals_total_supply True. ledger_delta_raw 0.
Collateral delta_raw is None (unknown). collateral.json was not provided. The gap is unknown.
Checkpoint-to-tail hash chain continuous=True, links 1523/1523.
The tail ledger is not in this directory.

## Numbers

- rows: 7614
- bad balance values omitted: 0
- classified addresses without a balance row: 0
- explicit missing nonces: 759
- unindexed spans: [[150000, 2074399]]
- class bridge: count None, raw None
- class lock: count None, raw None
- class pool: count None, raw None
- class user: count None, raw None
- class process_unknown: count 7614, raw 189487568412204611

## Evidence

- `evidence/p10-dryrun/20261017T091010Z-w-report/ledger.csv`
- `evidence/p10-dryrun/20261017T091010Z-w-report/reconciliation.json`
- `evidence/p10-dryrun/20261017T091010Z-w-report/REPORT.md`
- `evidence/p10-dryrun/20261017T091010Z-w-report/manifest.json`
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json` sha256 `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967` bytes 402335
- `evidence/p1-tail.json` sha256 `bafbca307ecf881bc716422bb4fe75506e433b9331c8e2d1e03eb6b0c4babe1f` bytes 2773
- `evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json` sha256 `3f181c88f46549a7a29aa8631cc70aeea05fea4d1131c2e2263513dc0f5bdce3` bytes 1435
- `evidence/p2/20261017T1645Z-p2a/module.json` sha256 `b28ed3aa62560024318ea37f28866c58917f546d82d406b56fec42911e93caea` bytes 1905
- `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json` sha256 `dffec5063b94ce927472a648fedccfe10d7f19ed2a11eb636c9eb94dc98578a3` bytes 1494
- `evidence/p7/20261017T0812Z-p7-tail-progress/cursor.json` sha256 `27fe5be83ac8247ac06ea078eb8a012370dd9754abd53d6000fbad2773b2368e` bytes 1034
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B.json` sha256 `ddaec852665c0764adae71f054674bd80397e196ff4ba8718e416584ef7a2775` bytes 10408
- `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` sha256 `62741c3f5ad08866db3bf1ba9fb7004a3d23036ce13225d717fe0071b23990df` bytes 119958
- `evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json` sha256 `3a8d24dc6e0fd8bd5fd97194b7bbacf0f10c4d0609618c33e522c75c9a32de1a` bytes 1851
- `evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json` sha256 `596b601def373d68172705c49ce911458c409ca5a6dc98ddfa907c1e141cc439` bytes 1356
- `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json` sha256 `dbc3123a5f771431d8209049950d5787447932b2fcf1dc46b25369f117df7ef2` bytes 116357
- `evidence/p6/20261017T052333Z-w-eval/evaluator.json` sha256 `2ea96c6f4d5cf50aa44c5b199531fc080e6f965b9f6726ecc4ff95a48383fe31` bytes 2444
- `evidence/p6/20261017T052333Z-w-eval/semantic.json` sha256 `9a469c29d0c5bd09fba06375bfbec0bc81f046669b07865d65d557f637ddb770` bytes 4812

## Tests

`python3 -m unittest tests.test_build_report -v` result is in `test-result.json` and `test-result.txt`.


## Unfinished

- 不满足. Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.
- 不满足. Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.
- 不满足. Ledger rows: address, raw balance, human balance at 12 decimals.
- 不满足. Sum of raw balances equals the process total supply at that nonce.
- 不满足. Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.
- 不满足. Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

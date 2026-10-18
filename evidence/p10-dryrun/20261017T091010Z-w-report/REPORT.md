# 试运行，不是最终结果

BLOCKED — NOT A CLAIM LIST

This is a dry run of the P10 builder at nonce 2074518. The tail nonce is 2075923. This is not the final ledger.
goal_complete: false
publish_claims: false
move_collateral: false

## Done means

### 1. Tail assignment: process, epoch, nonce, message id, timestamp, and the query that shows no higher pushed nonce.

状态：满足

证据：
- `evidence/p1-tail.json`

process NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8, epoch 0, nonce 2075923, assignment MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs, message wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ, timestamp 2026-07-04T06:19:55.380Z, block 1951869. Query: gateway https://arweave.net/graphql found no assignment at block height >= 1951870; gateway https://arweave-search.goldsky.com/graphql absent nonces [2075924, 2075925, 2075926, 2075927, 2075928, 2075929, 2075930, 2075931, 2075932, 2075933, 2075934, 2075935, 2075936, 2076000, 2077000, 2080000, 2090000, 2200000, 3000000, 4000000]; network height 2022620. Limit recorded by P1: Every nonce above 2075923 was not queried. The next 13 nonces and the listed sentinels are absent, and no assignment for this process is indexed in a block at or above 1951870. A later nonce that the sentinels skipped would still show up as a gap during the continuity sample.

### 2. Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.

状态：不满足

证据：
- `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json`
- `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json`
- `evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json`
- `evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json`

检查点到尾部由哈希链证明：continuous=True, window=[2074400, 2075923], links 1523/1523, failed 0. 检查点之前由 CU 签名的检查点覆盖，不是逐 nonce 索引：signature_valid=True, signer_matches_cu=True, sha256_matches=True, replay_start_accepted=True. 显式缺失列表：50000..99999 missing 132, 100000..149999 missing 627. 未建索引、因此既不是存在也不是缺失列表的区间：150000..2074399. 从第一条已推送 assignment 到尾部还没有被完整点数。

### 3. Module id `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0` bytes hashed, and the evaluator named.

状态：满足

证据：
- `evidence/p2/20261017T1645Z-p2a/module.json`
- `evidence/p6/20261017T052333Z-w-eval`

Module 1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0 sha256 164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8. Evaluator @permaweb/ao-loader 0.0.44.

### 4. Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.

状态：不满足

证据：
- `evidence/p7/20261017T0812Z-p7-tail-progress/cursor.json`
- `evidence/p6/20261017T052333Z-w-eval`

balances_written=False, last saved assignment nonce=2074638, tail=2075923, semantic comparison through nonce 2074518, byte_gate=未通过. Replay has not reached the tail and been checked.

### 5. Ledger rows: address, raw balance, human balance at 12 decimals.

状态：不满足

证据：
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json`

试运行，不是最终结果. This table has 7614 rows at nonce 2074518 with address, raw_balance, and a 12-decimal human_balance. format_ok=True. Bad rows omitted rather than set to 0: 0. Tail nonce is 2075923.

### 6. Sum of raw balances equals the process total supply at that nonce.

状态：不满足

证据：
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json`
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B.json#totalSupply.checkpoint`

At ledger nonce 2074518: sum_raw=189487568412204611, total_supply_raw=189487568412204611, sum_equals_total_supply=True, ledger_delta_raw=0. Supply source: <repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B.json#totalSupply.checkpoint. The sum is not used as the supply. 试运行，不是最终结果. The tail supply is not this number.

### 7. Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.

状态：不满足

证据：没有提供对应文件。

holders-classified.json was not provided. No address is class user, pool, lock, or bridge. Those class totals are unknown, not zero.

### 8. Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

状态：不满足

证据：没有提供对应文件。

asset=None, holder=None, raw_amount=None, source=None, delta_raw=None, status=unknown. collateral.json was not provided. The gap is unknown.

## Numbers

- ledger nonce: 2074518
- rows: 7614
- sum_raw: 189487568412204611
- total_supply_raw: 189487568412204611
- sum_equals_total_supply: True
- ledger_delta_raw: 0
- collateral delta_raw: None
- collateral status: unknown

Class totals are sums of ledger rows only. A missing row is not a zero in these totals.

- bridge: count None, raw None, unclassified
- lock: count None, raw None, unclassified
- pool: count None, raw None, unclassified
- user: count None, raw None, unclassified
- process_unknown: count 7614, raw 189487568412204611, present

Unresolved classified addresses with no balance row: 0.
Bad balance values omitted: 0.

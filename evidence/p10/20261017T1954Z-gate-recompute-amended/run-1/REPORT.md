# P10 reconciliation

goal_complete: true
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
- `evidence/p2/20261017T1645Z-p2a`
- `evidence/p6/20261017T052333Z-w-eval`

Module 1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0 sha256 164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8. Evaluator @permaweb/ao-loader 0.0.44.

### 4. Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.

状态：满足

证据：
- `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`
- `evidence/p6/20261017T052333Z-w-eval`

balances_written=True, last saved assignment nonce=None, tail=2075923, semantic comparison through nonce 2074518, byte_gate=未通过. The crosscheck has no last-nonce object. exited=True, assignments=1405, checkpoint nonce=2074518.

### 5. Ledger rows: address, raw balance, human balance at 12 decimals.

状态：满足

证据：
- `data/raw/fast/tail/balances.json`

This table has 7615 rows at nonce 2075923 with address, raw_balance, and a 12-decimal human_balance. format_ok=True. Bad rows omitted rather than set to 0: 0. Tail nonce is 2075923.

### 6. Sum of raw balances equals the process total supply at that nonce.

状态：满足

证据：
- `data/raw/fast/tail/balances.json`
- `evidence/p10/20261017T1047Z-fast-tail-inputs/supply.json`

At ledger nonce 2075923: sum_raw=189487568412204611, total_supply_raw=189487568412204611, sum_equals_total_supply=True, ledger_delta_raw=0. Supply source: evidence/p10/20261017T1047Z-fast-tail-inputs/supply.json. The sum is not used as the supply.

### 7. Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.

状态：满足

证据：
- `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json`

Classified ledger rows: pool/lock/bridge 76. Balance addresses absent from the holders file: 0. Classified addresses with no balance row, not filled as 0: 0.

### 8. Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

状态：不满足

证据：
- `evidence/p9/20261017T1720Z-p9-record/collateral-for-report.json`

asset=AR, holder=None, raw_amount=None, source=evidence/p9/20261017T090508Z-w-collat/collateral.json, delta_raw=None, status=unknown. held raw amount at the tail is unknown.

## Amended flags

Basis: amendment 2026-10-18. Legacy flags are not the completion rule.

- tail_fixed: true
- checkpoint_verified: true
- tail_inputs_complete: true
- runtime_reproducible: true
- available_checks_match: true
- independent_agreement: true
- ledger_complete: true
- ledger_delta_zero: true
- classification_disclosed: true

## Legacy flags

- tail_fixed: true
- schedule_covered: false
- inputs_complete: false
- runtime_reproducible: true
- available_checks_match: true
- ledger_complete: true
- ledger_delta_zero: true
- classification_sourced: false
- collateral_sourced: false
- collateral_reconciled: false

Collateral is a report field. It is not an amended gate.

## Numbers

- ledger nonce: 2075923
- rows: 7615
- sum_raw: 189487568412204611
- total_supply_raw: 189487568412204611
- sum_equals_total_supply: True
- ledger_delta_raw: 0
- collateral delta_raw: None
- collateral status: unknown

Class totals are sums of ledger rows only. A missing row is not a zero in these totals.

- bridge: count 0, raw 0, present
- lock: count 2, raw 250346157301342, present
- pool: count 74, raw 2330669314779690, present
- user: count 5279, raw 186394240884573076, present
- process_unknown: count 2260, raw 512312055550503, present

Unresolved classified addresses with no balance row: 0.
Bad balance values omitted: 0.

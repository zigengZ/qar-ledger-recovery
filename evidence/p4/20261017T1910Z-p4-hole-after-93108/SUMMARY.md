> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Nonce 93109 exact query

`schedule_covered` stays false. `goal_complete` is false. This is not a claim list.

`load_range_account` on `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` puts nonce 93109 immediately after nonce 93108. One exact Nonce query went to `https://arweave.net/graphql` through `recovery.assignments.fetch_exact_nonces`. HTTP 200. The page closed with `hasNextPage` false and an empty edge list. The assignment id is null. The raw amount is null.

A closed empty page is not proof that nonce 93109 was never published. Nothing was inserted. Earlier exact queries through nonce 93108 also closed empty. No P4 range at nonce 150000 or later was opened. The module was not executed.

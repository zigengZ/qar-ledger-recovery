> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Nonce 88824 exact query

`schedule_covered` stays false. `goal_complete` is false. This is not a claim list.

`load_range_account` on `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` puts nonce 88824 immediately after nonce 87679. One exact Nonce query went to `https://arweave.net/graphql` through `recovery.assignments.fetch_exact_nonces`. HTTP 200. The page closed with `hasNextPage` false and an empty edge list. The assignment id is null. The raw amount is null.

A closed empty page is not proof that nonce 88824 was never published. Nothing was inserted. Nonces 87659, 87662, 87666, 87668, 87670, 87675, 87678, and 87679 stay missing. No P4 range at nonce 150000 or later was opened. The module was not executed.

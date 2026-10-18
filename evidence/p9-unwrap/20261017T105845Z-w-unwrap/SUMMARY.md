> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Unwrap and deposit tables

Run `20261017T105845Z-w-unwrap`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. This is not a claim list. Chain checks and the owed list were not done.

## Answer

The tail memory has no unfinished unwrap. `Unwraps` has 0 rows. `UnwrapsCompleted` has 2234 rows, and every status is `completed`. There is no `burnt_war`, `funds_sent`, `confirmed`, or `cancelled` row.

The tail memory has no unfinished deposit. `Deposits` has 0 rows. `DepositsCompleted` has 4364 rows, and every status is `completed`.

Checkpoint nonce 2074518 has the same row counts, the same statuses, and the same partial quantity sums. `Withdrawals` and `WithdrawalsCompleted` are nil in both memories.

## Totals

Raw sums add every row. Human figures divide by 10^12. Empty tables contribute nothing. Missing quantities were not treated as zero.

| Table | Status | Rows | Raw sum | Human |
| --- | --- | ---: | ---: | ---: |
| Unwraps | — | 0 | 0 | 0 |
| UnwrapsCompleted | completed | 2234 | 272977038419623672 | 272977.038419623672 |
| Deposits | — | 0 | 0 | 0 |
| DepositsCompleted | completed | 4364 | 462464606831828283 | 462464.606831828283 |

The unwrap total has two parts. 2198 string quantities sum to `272924788419623672`. 36 quantities are bint tables. `tostring` on those tables is a decimal integer, and those 36 sum to `52250000000000` (52.25). Of the 36, 21 rows have only `owner`, `quantity`, and `status`. The other 15 also have `request_id` and `transfer_id`. None of the 36 has an `id` field. Their field list is `bint-rows.json`. The checkpoint aggregate matches, including these 36 unexpanded table quantities. `tostring` was run on the tail copy.

## Read

ao-loader 0.0.44 evaluated `require('json').encode(...)` with `Action=Eval` and `From` equal to the process owner. The memory files probed are copies. After the calls, the tail copy still hashes to `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`, and the checkpoint copy still hashes to `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`. A `Balances` read before and after each probe matched. Tail balance bytes hash to `be644d459f76edc2ac325ed65831ef7369fbedc9b85d84cadbfdbe4e36081f91`. Checkpoint balance bytes hash to `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`.

`DEPOSITS_ENABLED` and `WITHDRAWALS_ENABLED` are boolean false. `IS_STOPPED` is boolean false. `TRANSFERS_ENABLED` is boolean true. The encoder writes boolean false as the JSON string `"false"`; the type field is `boolean`.

## Not done

No transfer id was looked up on chain. No `owed.csv`. No per-address debt total.

> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P7 fast replay (w-fast)

Run `20261017T0914Z-w-fast`. Branch `worker/w-fast`. Nice 5. The main tail replay was read only.

## Conclusion

The exact in-place replay and the main tail replay finish on the same memory. Both final memory sha256 values are `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The main cursor is `next_index` 39065, applied 39065, handler errors 0. All 1090 logged step rows match the main `steps.jsonl` on sha256 and nonce. Pending rows are 0. Mismatches are 0. The main `memory.bin` file sha256 is the same value. The record is `main-compare.json`.

Cron in the live 0.16.0 handler does not change `Balances`. Deposits and withdrawals were already closed before checkpoint 2074518. The assignment-only replay of nonces 2074519 through 2075923 and the exact replay, which includes every cron, write byte-identical balance tables. The two memory images differ because the crons update other state. The assignment-only result is labelled 快速估计，非 P7 正式结果. Its memory sha256 is `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7`.

Total-Supply and the sum of Balances are both `189487568412204611`. 7615 addresses. Both runs had 0 handler errors.

## Numbers

| Run | Items | Errors | Addresses | Supply | sum equals supply | Memory sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| Checkpoint 2074518 |  |  | 7614 | 189487568412204611 | yes | `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` |
| Assignments only | 1405 | 0 | 7615 | 189487568412204611 | yes | `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7` |
| Exact inplace replay | 30665 from index 8400, through 39065 | 0 | 7615 | 189487568412204611 | yes | `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` |

Eleven addresses differ from the checkpoint. The list is in `assignment-ledger.json`. One address was added. Supply did not change. The exact and assignment-only balance files are byte-identical, sha256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`.

Exact replay rate from index 8400 was 1069 items per minute. The 480-item check from index 8000 was 366 per minute. The main replay over its first 2.7 hours was about 64 per minute. Both checks were above 1.5x. ao-loader 0.0.44 does not mutate the input buffer, and `HEAPU8.slice()` is stable across the next call. Skipping the two `Buffer.from` copies kept the same sha. Keeping the WASM heap between calls kept the same sha on the 480-item check, on the 171 rows already logged when this run exited, and on all 1090 rows once the main log was complete.

When the exact run exited, the main cursor was still `next_index` 10400. That snapshot was 171 matched rows, 919 rows not yet in the main log, and 0 mismatches. It remains in `exact-ledger.json` under `overlap_with_main_when_recorded`.

## Evidence

- `cron-handler.json` — 0.16.0 Cron source, the three flag Evals, tail action counts, and the one-cron balance diff of 0.
- `loader-probe.json` — input untouched, returned memory stable, first 10 items identical across the copy path and the in-place path, first Transfer/Event balance diff of 0.
- `verify-480.json` — 47 of 47 logged shas match the main steps, including the save whose sha is the main cursor at `next_index` 8400.
- `assignment-ledger.json`, `assignment-balances.json`, `assignment-balances.csv` — fast estimate. Labelled as not the P7 result.
- `exact-ledger.json`, `exact-balances.json`, `exact-balances.csv`, `exact-report.json` — full in-place replay.
- `main-compare.json` — main cursor 39065, 1090 matched rows, file sha256 equal to this run.
- Raw memory and cursors: `data/raw/fast/assignments-only/` and `data/raw/fast/tail/`. Not committed.

## Unfinished

`goal_complete` stays false. The 132 and 627 earlier message holes stay unresolved. This worker does not write the P10 report or the P8 address split. The tail comparison assigned here is complete.

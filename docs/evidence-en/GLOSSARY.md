# Chinese phrases in generated evidence files

Some evidence files were written by scripts, mainly the P10 reports from `recovery/p10/build_report.py`. Their structure and most of their text are English, but the scripts print a few labels and sentences in Chinese. Several of these files are pinned by sha256 elsewhere, and the two amended P10 runs are byte-identical, which is itself part of the evidence. So these files are not rewritten. This page gives the English meaning of every Chinese phrase in them.

P10 reports and summaries covered:

- `evidence/p10/20261017T1954Z-gate-recompute-amended/run-1/REPORT.md` and `run-2/REPORT.md` (the current, amended result)
- `evidence/p10/20261017T1720Z-p10-after-p9/REPORT.md` and `SUMMARY.md`
- `evidence/p10/20261017T1047Z-fast-tail/REPORT.md` and `SUMMARY.md`
- `evidence/p10/20261017T0954Z-fast-tail/REPORT.md` and `SUMMARY.md`
- `evidence/p10-dryrun/20261017T091010Z-w-report/REPORT.md` and `SUMMARY.md`

Machine-readable files covered: every `reconciliation.json` under `evidence/p10/` and `evidence/p10-dryrun/`, `evidence/p10-dryrun/20261017T091010Z-w-report/manifest.json`, the four `gates-*.txt` files in `evidence/p10/20261017T1718Z-gate-recompute/`, `evidence/p6/20261017T052333Z-w-eval/gate.json` and `semantic.json`, and `evidence/p7-fast/20261017T0914Z-w-fast/assignment-report.json` and `loader-probe.json`.

## Labels

| Chinese | English |
| --- | --- |
| 状态：满足 | Status: met |
| 状态：不满足 | Status: not met |
| - 不满足. … | - Not met. … (followed by the English criterion) |
| 证据： | Evidence: |
| 证据：没有提供对应文件。 | Evidence: no corresponding file was provided. |
| 满足 (as a JSON value, or `status=满足`) | met |
| 不满足 (as a JSON value, or `status=不满足`) | not met |
| 未通过 (alone, or `byte_gate=未通过`) | not passed |
| 快速估计，非 P7 正式结果 | Quick estimate, not the formal P7 result |
| 快速估计准备。probe 不是 P7 正式结果。 | Preparation for the quick estimate. The probe is not the formal P7 result. |
| 试运行，不是最终结果 | Dry run, not a final result |
| # 试运行，不是最终结果 | # Dry run, not a final result |

## Sentences

**Nonce continuity (Done means 2).**

> 检查点到尾部由哈希链证明：… 检查点之前由 CU 签名的检查点覆盖，不是逐 nonce 索引：… 显式缺失列表：… 未建索引、因此既不是存在也不是缺失列表的区间：150000..2074399. 从第一条已推送 assignment 到尾部还没有被完整点数。

From the checkpoint to the tail, continuity is proven by the hash chain: continuous=True, window=[2074400, 2075923], links 1523/1523, failed 0. Before the checkpoint, coverage comes from the CU-signed checkpoint, not from a per-nonce index: signature_valid=True, signer_matches_cu=True, sha256_matches=True, replay_start_accepted=True. Explicit missing lists: 50000..99999 missing 132, 100000..149999 missing 627. The range that is not indexed, and is therefore in neither a present list nor a missing list: 150000..2074399. The span from the first pushed assignment to the tail has not been fully counted.

**Not a claim list.**

> 这不是领取名单。`goal_complete=false`。`classification_sourced` 仍为 false。抵押物差额是 unknown。

This is not a claim list. `goal_complete=false`. `classification_sourced` is still false. The collateral delta is unknown.

**The largest holder.**

> `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 按 P8 写成 wallet，身份未核实。表内 class `user` 只是 build_report.py 对 P8 wallet 的映射，不是已核实身份。

`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` is written as wallet per P8; its identity is not verified. The class `user` in the table is only build_report.py's mapping of a P8 wallet, not a verified identity. (One variant ends at "mapping of wallet" without the last clause.)

**The five empty-Data Transfers.**

> 五笔 Transfer 的 Data 在 `https://arweave.net/raw/{id}` 上是 0 字节，…

The Data of the five Transfers is 0 bytes at `https://arweave.net/raw/{id}`, and the content-digest is the SHA-256 of the empty byte string. The amount is in the Quantity tag. The live Transfer handler does not read Data, and empty Data is not treated as a quantity of 0. The nonces of these five are 2074509, 2074511, 2074513, 2074515, 2074517, outside the tail range 2074519..2075923. Evidence `evidence/p6/20261017T102111Z-w-eval/`.

**The fast tail ledger.**

> w-fast 尾部账本有 7615 行。…

The w-fast tail ledger has 7615 rows. The raw total and the separately read Total-Supply are both `189487568412204611`. Final memory sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. When this record was written, the main replay was still running. The later main replay memory sha matches this one; see the README.

> w-fast 从主回放已核对的 next_index 8400 内存继续，以 inplace 跑到 nonce 2075923。…

w-fast continued from the main replay's checked memory at next_index 8400 and ran in place to nonce 2075923. 0 handler errors. 7615 balance rows. The raw total and the separately read Total-Supply are both 189487568412204611. Final memory sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. When this record was written, the main replay was still running. The later main replay memory sha matches this one; see the README.

**Notes added later.**

> 写这份记录时，主回放 sha 复核尚未结束。后来已对照一致，见 README。

When this record was written, the main replay sha check had not finished. It was later compared and matches; see the README.

> 精确回放结果，你这条独立回放的最终 sha 交叉核对还没做完

Exact replay result; the final sha cross-check against "your independent replay" (the worker addressing the main session's slow replay) was not finished yet. This line opens `evidence/p10/20261017T0954Z-fast-tail/REPORT.md` and `SUMMARY.md`. The main replay later matched; see the README.

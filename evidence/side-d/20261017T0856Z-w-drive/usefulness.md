# Drive CU 对 qAR 账本有没有用

公开文件夹是 `1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`。GOAL.md 里的 `1HvWUSVZxHgl6lILpFe9AkODgDxQ6KVdn` 返回 HTTP 404，原文在 `data/raw/drive-cu/http/typo-folder.html`。

这批检查点不是“截止到 7 月 4 日”。归档名是 `state-20260904T155934Z.tar.zst`。`checkpoint_files` 里的状态时间从 2024-06-24 到 2026-08-25。余额交集里最晚一条是 2026-08-25T17:00:47Z。7 月 4 日是其中两个 qAR/wAR 池的状态时间，靠近 qAR 尾部，不是整份盘的终点。

## (a) CU 版本和 9 个 Block-Height

Drive 上没有 `.git`，`package.json` 也没有 commit。能对上的是源码字节：

- `loadMessages.js`、`ao-block.js`、`utils.js` 与 permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461` 逐字节相同。
- lock 里 `@permaweb/ao-loader` 是 `0.0.44`，与 w-eval 的评估器一致。
- 唯一依赖差是 `@permaweb/weavedrive` `0.0.19`，上游 pin 是 `0.0.18`。

`cronMessagesBetweenWith`（`src/domain/lib/loadMessages.js`）里，时间 cron 的 `Block-Height` 写成当前 `curBlock.height`。`curBlock` 从左边界区块开始，当 `toSeconds(curTimestamp) >= toSeconds(nextBlock.timestamp)` 时才推进到下一块。qAR 的 cron 是每 5 分钟，走的是这条时间分支。

`getLatestBlock` 被传进 `reconcileBlocksWith` 并做了 schema 包装，函数体里没有调用它。区块来自 CU 自己的 sqlite 缓存，缺的区间再向 GraphQL 要。

这和 w-eval `recovery/p6/replay.mjs` 的算法是同一套，源码本身不会把高度再加 1 到 3。w-eval 的记录是：9 条 cron 时间戳相同，回放 Block-Height 比检查点高 1 到 3；把那 9 个高度抄回去以后内存 sha 才一致（`evidence/p6/20261017T052333Z-w-eval/SUMMARY.md`）。和这份源码相容的解释是：写出检查点时，CU 手里的区块列表比后来的网关少 1 到 3 块。源码不能证明 CU 故意存了 height-1。

## (b) ao-cache.sqlite

只读打开。表和行数见 `sqlite-index.json`。`blocks`、`processes`、`messages`、`evaluations`、`checkpoints` 都是 0 行。`checkpoint_files` 有 1008 行，是检查点文件名索引，不是进程内存。

qAR `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8` 和 APUS `mqBYxpDsolZmJyBdTK8TJp_ftOuIUXVYcSQ8MYZdJg0` 在这张表里是 0 行。对 sqlite、`-shm`、`-wal` 的字节搜索也没有这两条。w-src 的两个池、桥 `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c`、cron `S_0fyWQknosQ57QWd0iuWl84EYmoi5qCyDai-LYHuhg` 同样是 0 行。

`modules` 有 23 行，其中有 qAR 模块 `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`。有模块 id 不等于有 qAR 进程状态。`modules.owner` 是 JWK，密钥没有写入证据。

四个本地配置池在 `checkpoint_files` 里各有一行，文件名和时间与 Drive 文件名一致。两个 7 月 4 日的 permaswap 池用模块 `Do_Uc2Sju_ffp6Ev0AnLVdPtot15rvMjP-a9VVaA5fM`。Botega 的 `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` 用模块 `G991Xp6Kh28k8_AZcnwaqJ6LZcHlsZcMkrH1mJoAy84`。这是缓存里的 evaluation 字段，不是内存偏移。

## (c) 1012 个检查点里的命名进程

文件名和 `extraction-report.json` 的 996 个 `processId` 里都没有 qAR、APUS、w-src 的两个池、桥、cron。报告的 `missingProcessIds` 有 9817 个，这六个 id 也不在里面，所以它们不在 `war-wusdc-value-holding-process-ids.json` 那次请求里。

Drive 有 1012 个 bin，报告匹配 996 个。16 个 bin 只在 Drive 上。其中 9 个没有保存下来的大小，名单在 `inventory.json` 的 `files_missing_size`。`rKpOUxssKxgfXQOpaCq22npHno6oRw66L3kZeoo_Ndk` 不在报告里；一次 HEAD 的 stdout 给出 `content-length: 481165312`，这次响应没有写入 `http/requests.jsonl`。已记录的 HEAD 与报告大小相比，不一致的条数是 0。

## 本地池清单交集

来源是本地池配置摘录，原文未写入。`id:` 19 行，去重 18 个。和 Drive 文件名相交 4 个。详情在 `overlap.json` 的 `local_config_pools`。

在 Drive 上，字节都没有下载，报告 sha256 都没有用本地文件核对：

| 配置名 | 地址 | 清单 | 状态时间 | 文件名里的高度 | 报告大小 | 报告 sha256 | nonce 2074518 的 qAR 余额 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| redacted | `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` | private parameters redacted | 2026-07-01T01:23:35Z | 1949705 | 158793728 | `e9c7bb1ca888a3f3326c4f917cd2191ee54d519c1cae4ce353ae43fa20aac616` | `320089670049015` |
| redacted | `Eb87m8cazuCnf7BtYk3gQO6kiuhEZwPNL1iTJnR1MdQ` | private parameters redacted | 2026-07-04T06:22:01Z | 1951866 | 206700544 | `26bf2d9396c9852d56f11bdb679a0b370408da044fd352b060692c0dadeb6c8a` | `675157661762225` |
| redacted | `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` | private parameters redacted | 2026-07-04T06:21:56Z | 1951866 | 248053760 | `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a` | `1934348814863` |
| redacted | `fNFUX58BiHeBhB2D4EJsu88IeAHtJhugHSP__U6Y9dk` | private parameters redacted | 2026-02-22T02:45:17Z | 1862495 | 206700544 | `a31704e96b13ebdfafb0d5c670aa8f4013982467d76e90ddb74869f119bb5e6a` | `2000000000000` |

优先文件是 `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4_ts-1783146116188_ord-247049_bh-1951866.bin`，Drive id `18SsJyEnpKkIrjTurvIZei_a-7g8fUJzN`。qAR 尾部是 2026-07-04T06:19:55.380Z，包含区块 1951869，nonce 2075923，消息 `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`。这个池的状态时间比尾部晚约 2 分钟，文件名和 sqlite 里的 `blockHeight` 都是 1951866。sqlite 里的 nonce `247049` 是这个池自己的 evaluation nonce，不是 qAR 的 2075923。

GET 先得到病毒扫描警告页（`http/lama-warn.html`，2534 字节），随后的 uuid 下载得到 `Google Drive - Quota exceeded`（`http/lama-step2.html`，2040 字节）。另一次 `docs.google.com/uc` 返回 303，Location 里没有 uuid。bin 没有保存。报告里的 sha256 因此没有核对。配额期间没有继续拉其余大文件。

另外 14 个去重后的配置池不在 Drive 上。它们在 nonce 2074518 余额表里的原始余额是（缺记录才会是 null，这里都有记录，含三个 0）：

- `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4` botega AO/qAR 0.0025：`381553671374914`
- `WuAkqYvunUtsD8uvpsK9XtR7_5-fbnH3ATD4DJrl-Ac` botega DUMDUM/qAR 0.0025：`371628692276590`
- `lmaw9BhyycEIyxWhr0kF_tTcfoSoduDX8fChpHn2eQM` botega qAR/AGENT 0.0025：`265525803677701`
- `NX9PKbLVIyka3KPZghnEekw9FB2dfzbzVabpY-ZN1Dg` botega qAR/NAB 0.0025：`12500009941418`
- `230cSNf7AWy6VsBTftbTXW76xR5H1Ki42nT2xM2fA6M` permaswap qAR/NAB 0.003：`6312687421159`
- `3biQvRjIp_9Qz1L9D3SJ9laK4akCkP-8bvAo3pQ6jVI` botega AO/qAR 0.0075：`3003053338103`
- `nHWcfNzeqjZ8Bot4R-xs_7Jez7Fl2AeDzKlN7qWmS24` botega qAR/tARIO 0.0025：`812731366345`
- `BeowMvoHuSHbDllewXW6P3QecJDa_059rxqMXQHD3ts` botega TRUNK/qAR 0.0025：`424876313215`
- `ZeSJHyEbZqA3D3h5vMnFPZi3BY4LdgXxL_lZzIUcvPw` botega qAR/BELE 0.0025：`284407499529`
- `usMlh8eWf9wrLR9kSPosW--SrXJGZ40LC5Rekjgywy4` botega PIXL/qAR 0.0025：`178253225566`
- `t3Dxq0oH5gPH38T3uQAek1269tTwMSSZgU6lBFvrNEs` botega LLAMA/qAR 0.0025，清单里出现两次：`127665127065`
- `JmbCVggbs8aID1U2TOleyfGR08BVAQVOmAiYNlRogsE` 注释掉的 permaswap AGENT/qAR 0.0030：`0`
- `DhiYsqOtkd42rSlVyNOyJ8Clxv6HmFbIfi0fSz_PRik` botega qAR/wUSDC 0.0025：`0`
- `8DdYrPbX0XM_3HuOqZN5zMphGFMSDG1pTMkWPyYJ_5k` botega AO/qAR 0.03：`0`

w-src 里低置信度的 Botega 候选 `vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4` 不是这份清单里的 `Bv5mfnx5...`，也不在 Drive 上。

## 余额表交集

余额表是 `data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json`，7614 个地址，nonce 2074518。`data/raw/p7/` 下还没有 `balances.json`，所以没有用尾部回放的余额重算。

相交 54 个进程：41 个余额非 0，13 个是 0。0 是余额表里的值，不是缺记录。这 54 个的 qAR 数是 2074518 那张图，不是 Drive 内存里的余额。

按该余额从大到小，前 20 个文件合计 3739025408 字节，54 个合计 10032578560 字节。前 20 小于 20 GiB，所以下载计划包含全部 54 个。实际保存的交集文件是 0 个。大文件 GET 返回的是病毒扫描警告 HTML，脚本把这些 HTML 删了，没有留在 `checkpoints/`。配额出现之后停止继续下载。

交集里余额最大的是 `Eb87...`（上表，7 月 4 日）。其次是 `Bv5...`（7 月 1 日）。优先池 `_laMMu5...` 在这张 2074518 表上是 `1934348814863`，不是最大的。

报告里最小的检查点是 23003136 字节，没有约 10 MB 的文件。抽到的两个小文件：

- `fzRGvSW2oSop9xGLxs5mcaRtCbrbug8imI_uRZHKdiU_ts-1719201552641_ord-2856_bh-1451201.bin`，23003136 字节，sha256 `19a5f5eff09357078fc5f7c2ce0435b2eda58356971da0222b548539d7c48b13`，与报告一致。它不在 54 个交集里。
- `6eU3_ot8dl0dm9B6pUxZDzl78VKfzgDRSyuRumGbE9E_ts-1744639069181_ord-1412_bh-1649702.bin` 没有保存。报告大小 42991616，报告 sha256 `3e818830e93e0403d8ee6c313665b774c9716909afae335ae7e79599ce90c796`，未核对。

## 只读角色

只读了上面那个 23 MB 样本，方法是正则，没有执行。`roles.json`：

- `Handlers.add` 的名字和第一次出现的偏移：`_eval` 95856，`Info` 5265745，`Credit-Notice` 5266119，`Create-Order` 5268229，`Cancel-Order` 5282473，`Get-Sales-By-Address` 5336636，`Debit-Notice` 5336907。
- 进程标签一组：`App-Name` `aos`，`Name` `ucm-0.3`，`aos-Version` `1.10.21`，旁边有 `Variant` `ao.TN.1`。
- 角色是订单簿（ucm-0.3）。不是 AMM 池、锁仓、桥或质押。字符串 `X-Swap-Token` 出现 750 次，但不是 `Handlers.add` 的名字。
- `"name":"Ticker","value":"AR"` 只有 1 处，偏移 4611268。不把它当作这个进程的 ticker。

`_laMMu5...` 的内存没有读到，没有偏移。清单上的 permaswap qAR/wAR 0.3% 只是配置，不是内存结论。sqlite 只额外给出它的模块 id 和它自己的 nonce。

## 对 P8 / P9

P8 能用的是地址清单，不是已验证的池储备。

Drive 上有状态文件名、报告 sha、以及 sqlite 里的模块和高度的，是 4 个配置池。其中两个 permaswap qAR/wAR 池落在 qAR 尾部之后约两分钟，适合以后对尾部时刻的池储备做检查。字节和 sha 都还没核对，所以现在不能从内存拆出储备或对手方余额。

14 个配置池没有 Drive 状态。其中 `wTIpis...`、`WuAkq...`、`lmaw9...` 在 2074518 的余额表上是最大的几笔 qAR 持仓之一，P8 仍然要单列这些地址，但不能从这份 Drive 读它们的状态。

54 个“qAR 余额地址并且在 Drive 上有检查点”的进程，一个都没有读内存。它们说明哪些 qAR 大户本身是进程、并且这份 wAR/wUSDC 导出里留了状态。除了上面 4 个配置池，其余进程的角色还不知道。

P9 的抵押不能从这里得出。qAR 进程和 APUS 进程的检查点都不在这 1012 个文件里，也不在报告的缺失 id 列表里。sqlite 有 qAR 模块 id，没有 qAR 进程的 checkpoint 行。

## (d) 可转给 fwd 的请求

Please search the archive `minio-rds/rds-backups/cu-state-export/state-20260904T155934Z.tar.zst` for objects named `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8_*` and `mqBYxpDsolZmJyBdTK8TJp_ftOuIUXVYcSQ8MYZdJg0_*`. Those two process ids are not among the 996 matched files in `extraction-report.json`, and they are not in its 9817-id `missingProcessIds` list, so they were not in `war-wusdc-value-holding-process-ids.json`. A state near 2026-07-04T06:19:55.380Z (qAR assignment nonce 2075923, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`, inclusion block 1951869) can check the tail replay.

The public Drive copy also names two pool checkpoints about two minutes after that tail. Google Drive quota blocked the download, so the report sha256 is not checked against local bytes. If the same archive still has these objects, the bytes would close that check:

- `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4_ts-1783146116188_ord-247049_bh-1951866.bin`, 248053760 bytes, sha256 `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a`
- `Eb87m8cazuCnf7BtYk3gQO6kiuhEZwPNL1iTJnR1MdQ_ts-1783146121245_ord-294830_bh-1951866.bin`, 206700544 bytes, sha256 `26bf2d9396c9852d56f11bdb679a0b370408da044fd352b060692c0dadeb6c8a`

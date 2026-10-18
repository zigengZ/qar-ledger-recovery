> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Side D · Drive CU

正确的公开文件夹是 `1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`。GOAL.md 里的 id 多写了一笔，HTTP 404 已保存。盘点用 `embeddedfolderview`，1113 个文件，其中检查点 bin 1012 个，外加 `extraction-report.json`。`node_modules` 只记了 191 个条目，没有逐个下载。

## 结论

这份 CU 源码就是 permaweb/ao `0db88a45` 的 CU，`ao-loader` 锁定 `0.0.44`，依赖差只有 `weavedrive` `0.0.19`。cron 的 Block-Height 算法与 w-eval 相同，不能单独解释那 9 个高度差。qAR 和 APUS 的进程检查点不在这 1012 个文件里。

本地池清单 18 个去重 id 里有 4 个在 Drive 上。优先的 permaswap qAR/wAR 0.3% 池 `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` 的状态时间是 2026-07-04T06:21:56Z，文件名高度 1951866，报告 sha256 `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a`。Drive 配额挡住了下载，sha 没有用本地字节核对。

和 nonce 2074518 的 7614 个 qAR 余额地址相交得到 54 个进程，合计约 9.34 GiB，按规则应全部下载。实际一个都没保存。唯一 sha 核对通过的检查点是一个 23 MB 的 ucm-0.3 订单簿样本，它不在这 54 个里面。

## 数字

- 文件夹文件 1113。检查点 bin 1012。报告匹配 996。只在 Drive 上的 bin 16。没有大小的 bin 9。HEAD 与报告大小不一致 0。
- 余额交集 54。非零 41。零 13。前 20 个 3739025408 字节。全部 10032578560 字节。已下载 0。已核对 sha 0。
- 池清单 id 行 19，去重 18，在 Drive 上 4，不在 Drive 上 14。
- 报告请求 10813 个进程，缺失列表 9817，归档扫描 9723 个条目。来源 `minio-rds/rds-backups/cu-state-export/state-20260904T155934Z.tar.zst`。报告文件 sha256 `10e2e7a0a07b70de3eaddb63ac39c8f5e8d4193857962e45f5b503d6a313414f`。
- sqlite `checkpoint_files` 1008 行。qAR 进程 0 行。qAR 模块 id 在 `modules` 的 23 行里。
- ClamAV 1.5.4，主扫描 101 个文件，0 感染。`npm audit --package-lock-only` 18 条（critical 1，high 15，moderate 2）。没有安装依赖。

## 证据

- `inventory.json`：目录、文件 id、大小来源、命名进程是否出现。
- `overlap.json`：54 个余额交集，以及 19 行池配置。
- `roles.json`：唯一读过的检查点的 handler 偏移。优先池没有内存偏移。
- `sqlite-index.json`：只读 sqlite 的行数和四个池的 evaluation 字段。
- `scan-report.json`：ClamAV 和 npm audit。
- `static-review.md`：脚本、网络地址、子进程搜索、`.env` 变量名。
- `usefulness.md`：(a) 到 (d)、池交集、P8/P9。
- `code-manifest.json`：已保存代码文件的 sha256。`.env` 的哈希没有写入。
- 大文件在 `<repo>/data/raw/drive-cu/`。代码树、两份检查点（报告和 23 MB 样本）、HTTP 记录都在那里。`.env` 模式 0600。

## 未完成

- 54 个交集检查点和 4 个池文件的字节都没有拿到。优先池的 sha256 仍是报告值。
- 第二个小样本 `6eU3_ot8dl0dm9B6pUxZDzl78VKfzgDRSyuRumGbE9E_ts-1744639069181_ord-1412_bh-1649702.bin` 的 sha 未核对。
- 9 个 Drive-only bin 没有大小。
- 尾部回放的 `balances.json` 还不存在，交集没有重算。
- `rKpOUxss...` 的 481165312 来自一次没有写入 `requests.jsonl` 的 HEAD stdout。
- 没有再向 Drive 拉大文件。配额页已经出现，继续下载可能把限制拉长。

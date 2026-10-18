# Evidence index · 证据索引

[English](#english) · [中文](#中文)

## English

This directory is the raw record of the qAR ledger recovery. Each run wrote into its own directory, named `<phase>/<UTC time>-<label>/`. Records are kept as they were written and are not edited afterwards. Several files are pinned by sha256 in other files, so changing them would break those references.

### Language

Records are kept in the language they were written in, English or Chinese. Hashes, numbers, ids, and JSON keys do not depend on language. The conclusions are in the root [README.md](../README.md) and [README.zh.md](../README.zh.md), and the method is in [docs/RECOVERY.md](../docs/RECOVERY.md) and [docs/RECOVERY.zh.md](../docs/RECOVERY.zh.md); all four carry the same facts.

- Many files start with the Chinese line `> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 repro/EXPECTED.json 为准。` It means: "This is a work log. It records progress at the time and is not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`." The line was added before publication.
- Records written mainly in Chinese have English translations in [docs/evidence-en/](../docs/evidence-en/). The original is authoritative.
- Scripts that wrote P10 reports and some JSON print a few Chinese labels, such as 满足 (met), 不满足 (not met), and 未通过 (not passed). [docs/evidence-en/GLOSSARY.md](../docs/evidence-en/GLOSSARY.md) translates every such phrase.

### Start here

To check the ledger, these are the records that matter most.

| What | Where |
| --- | --- |
| Fixed tail: nonce 2075923, and no higher pushed nonce | [p1-tail.json](p1-tail.json) |
| Checkpoint at nonce 2074518 accepted as the replay start | [p5/20261017T053304Z-p5-checkpoints/](p5/20261017T053304Z-p5-checkpoints/), [p6/20261017T052333Z-w-eval/](p6/20261017T052333Z-w-eval/) ([English](../docs/evidence-en/p6/20261017T052333Z-w-eval/SUMMARY.md)), [p6/20261017T0715Z-p6-checkpoint-accepted/](p6/20261017T0715Z-p6-checkpoint-accepted/) |
| All inputs from checkpoint to tail, hash chain 1523/1523 | [p4-tail/20261017T052614Z-w-tail/](p4-tail/20261017T052614Z-w-tail/) |
| Exact replay and assignments-only replay | [p7-fast/20261017T0914Z-w-fast/](p7-fast/20261017T0914Z-w-fast/) |
| Main slow replay, final memory sha cross-check | [p7/20261017T1708Z-p7-main-tail-crosscheck/](p7/20261017T1708Z-p7-main-tail-crosscheck/), [p7/20261017T1718Z-p7-replay-read/](p7/20261017T1718Z-p7-replay-read/) |
| Recompute in Python without running the module, 7615/7615 | [p10-indep/20261017T104141Z-w-indep/](p10-indep/20261017T104141Z-w-indep/) |
| Clean clone from public gateways | [repro/20261017T120218Z-w-repro/](repro/20261017T120218Z-w-repro/) ([English](../docs/evidence-en/repro/20261017T120218Z-w-repro/SUMMARY.md)) |
| Final reconciliation and ledger CSV (current result) | [p10/20261017T1954Z-gate-recompute-amended/](p10/20261017T1954Z-gate-recompute-amended/) |

### By phase

| Directory | What it holds |
| --- | --- |
| [p0-probe.json](p0-probe.json) | First probe of the process, owner, and gateways. |
| [plan-baseline-20261017.json](plan-baseline-20261017.json) | Documentation baseline of the repository, not chain evidence. |
| [p1-tail.json](p1-tail.json) | P1: the tail assignment and the queries showing no higher nonce. |
| [p2/](p2/) | P2: module `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0` bytes and sha256. |
| [p3/](p3/) | P3: small continuity sample and the indexing method, including the hash-chain link function. |
| [p4/](p4/) | P4: indexing of early nonces. Range 0..49999 is complete, 50000..149999 indexed with explicit holes, 150000..2074399 not indexed. The P4 hole walk stopped when the checkpoint superseded it. |
| [p4/…-p4-hole-*](p4/) | 120 directories. Each is one exact query for one missing early nonce that closed empty. They are not missing ledger rows. |
| [p4-tail/](p4-tail/) | All 1524 assignments and messages from nonce 2074400 to the tail, with signatures and the hash chain. |
| [p5/](p5/) | P5: search for CU checkpoints and the selected checkpoint. |
| [p6/](p6/) | P6: evaluator calibration. The byte gate did not pass; the semantic gate passed ([English](../docs/evidence-en/p6/20261017T052333Z-w-eval/SUMMARY.md)). Also the five Transfers with empty Data ([English](../docs/evidence-en/p6/20261017T102111Z-w-eval/SUMMARY.md)). |
| [p7/](p7/) | P7: genesis segment tests, progress of the main slow replay, and its final cross-check. |
| [p7-fast/](p7-fast/) | Fast exact replay and assignments-only replay of the tail. |
| [p8/](p8/) | P8: holder classification (pool, lock, bridge, wallet, unknown process) with the source of each label. |
| [p8-whale/](p8-whale/) | A stopped look at the largest holder; no conclusion ([English](../docs/evidence-en/p8-whale/20261017T094030Z-w-whale/SUMMARY.md)). |
| [p9/](p9/), [p9-prep/](p9-prep/), [p9-unwrap/](p9-unwrap/) | P9: collateral facts (asset, custody wallet, flows), source reading, and unwrap and deposit tables. Collateral is reported as facts only. |
| [p10/](p10/) | P10: reconciliation reports. Earlier drafts kept as written; the current result is `20261017T1954Z-gate-recompute-amended/`. |
| [p10-dryrun/](p10-dryrun/) | A dry run of the P10 report at the checkpoint nonce. |
| [p10-indep/](p10-indep/) | The independent non-WASM recompute. |
| [repro/](repro/) | The clean-clone reproduction ([English](../docs/evidence-en/repro/20261017T120218Z-w-repro/SUMMARY.md)). |
| [side-d/](side-d/) | Review of a public Google Drive CU copy. qAR and APUS are not in it ([English](../docs/evidence-en/side-d/20261017T0856Z-w-drive/SUMMARY.md)). |
| [audit/](audit/) | Pre-publication scans and redaction records ([English](../docs/evidence-en/audit/)). |
| [doc/](doc/) | Notes from writing the public recovery document. |
| [web/](web/) | Notes from building the balance site ([English](../docs/evidence-en/web/20261017T1243Z-w-web2/SUMMARY.md)). |

Large raw downloads and replay memories are not in the repository. Manifests name them under `<repo>/data/raw/...` with their sha256, so they can be fetched again from public gateways and checked. `repro/run.sh` does this.

## 中文

本目录是 qAR 账本恢复的原始记录。每次运行写入自己的目录，命名为 `<阶段>/<UTC 时间>-<标签>/`。记录保持写入时的样子，事后不修改。有些文件被别的文件用 sha256 引用，改动会让引用对不上。

### 语言

记录保留原来的语言，中文或英文。哈希、数字、id 和 JSON 键名与语言无关。结论以根目录 [README.md](../README.md)、[README.zh.md](../README.zh.md) 为准，方法见 [docs/RECOVERY.md](../docs/RECOVERY.md)、[docs/RECOVERY.zh.md](../docs/RECOVERY.zh.md)，四份内容相同。

- 很多文件开头有一行「这是工作日志，记录当时的进度，不是最终结论」。这行是公开前加的。
- 以中文为主的记录，在 [docs/evidence-en/](../docs/evidence-en/) 有英文译本，以原文为准。
- 生成 P10 报告和部分 JSON 的脚本会输出少量中文标签，如「满足」「不满足」「未通过」。[docs/evidence-en/GLOSSARY.md](../docs/evidence-en/GLOSSARY.md) 列出了每一处的英文意思。

### 从这里开始

核对账本，最重要的是这几份。

| 内容 | 位置 |
| --- | --- |
| 固定尾部：nonce 2075923，且没有更高的已推送 nonce | [p1-tail.json](p1-tail.json) |
| nonce 2074518 的检查点被接受为回放起点 | [p5/20261017T053304Z-p5-checkpoints/](p5/20261017T053304Z-p5-checkpoints/)、[p6/20261017T052333Z-w-eval/](p6/20261017T052333Z-w-eval/)、[p6/20261017T0715Z-p6-checkpoint-accepted/](p6/20261017T0715Z-p6-checkpoint-accepted/) |
| 检查点到尾部的全部输入，哈希链 1523/1523 | [p4-tail/20261017T052614Z-w-tail/](p4-tail/20261017T052614Z-w-tail/) |
| 精确回放和只回放 assignment | [p7-fast/20261017T0914Z-w-fast/](p7-fast/20261017T0914Z-w-fast/) |
| 主慢速回放及最终内存 sha 交叉核对 | [p7/20261017T1708Z-p7-main-tail-crosscheck/](p7/20261017T1708Z-p7-main-tail-crosscheck/)、[p7/20261017T1718Z-p7-replay-read/](p7/20261017T1718Z-p7-replay-read/) |
| 不运行模块的 Python 重算，7615/7615 | [p10-indep/20261017T104141Z-w-indep/](p10-indep/20261017T104141Z-w-indep/) |
| 只用公开网关的干净克隆复现 | [repro/20261017T120218Z-w-repro/](repro/20261017T120218Z-w-repro/) |
| 最终对账和账本 CSV（当前结果） | [p10/20261017T1954Z-gate-recompute-amended/](p10/20261017T1954Z-gate-recompute-amended/) |

### 按阶段

| 目录 | 内容 |
| --- | --- |
| [p0-probe.json](p0-probe.json) | 对进程、所有者和网关的第一次探查。 |
| [plan-baseline-20261017.json](plan-baseline-20261017.json) | 仓库的文档基线，不是链上证据。 |
| [p1-tail.json](p1-tail.json) | P1：尾部 assignment，以及证明没有更高 nonce 的查询。 |
| [p2/](p2/) | P2：模块 `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0` 的字节和 sha256。 |
| [p3/](p3/) | P3：连续性小样本和索引方法，包括哈希链的链接函数。 |
| [p4/](p4/) | P4：早期 nonce 索引。0..49999 已完整，50000..149999 已索引并列出空洞，150000..2074399 未索引。检查点取代了这项工作后，逐个查空洞已停止。 |
| [p4/…-p4-hole-*](p4/) | 120 个目录。每个是对一个缺失早期 nonce 的精确查询，结果为空。它们不是缺失的账本行。 |
| [p4-tail/](p4-tail/) | nonce 2074400 到尾部的全部 1524 条 assignment 和消息，含签名和哈希链。 |
| [p5/](p5/) | P5：CU 检查点搜索和选定的检查点。 |
| [p6/](p6/) | P6：执行器校准。字节门未通过，语义门通过。另有五笔 Data 为空的 Transfer。 |
| [p7/](p7/) | P7：创世段测试、主慢速回放的进度和最终交叉核对。 |
| [p7-fast/](p7-fast/) | 尾部的快速精确回放和只回放 assignment。 |
| [p8/](p8/) | P8：持有人分类（池、锁仓、桥、钱包、未知进程），每个标签都有来源。 |
| [p8-whale/](p8-whale/) | 对最大持有人的查看，已停止，没有结论。 |
| [p9/](p9/)、[p9-prep/](p9-prep/)、[p9-unwrap/](p9-unwrap/) | P9：抵押物事实（资产、托管钱包、流水）、源码阅读和 unwrap 与 deposit 表。抵押物只作为事实报告。 |
| [p10/](p10/) | P10：对账报告。早期草稿按原样保留，当前结果是 `20261017T1954Z-gate-recompute-amended/`。 |
| [p10-dryrun/](p10-dryrun/) | 在检查点 nonce 上对 P10 报告的试运行。 |
| [p10-indep/](p10-indep/) | 不运行 WASM 的独立重算。 |
| [repro/](repro/) | 干净克隆复现。 |
| [side-d/](side-d/) | 对 Google Drive 上公开 CU 副本的审查。里面没有 qAR 和 APUS。 |
| [audit/](audit/) | 公开前扫描和脱敏记录。 |
| [doc/](doc/) | 编写公开恢复文档时的记录。 |
| [web/](web/) | 构建余额网站时的记录。 |

大的原始下载和回放内存不在仓库里。清单用 `<repo>/data/raw/...` 指明它们，并附 sha256，可以从公开网关重新下载核对。`repro/run.sh` 就是做这件事。

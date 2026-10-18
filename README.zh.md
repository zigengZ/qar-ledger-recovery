# qAR 余额账本

英文：[README.md](README.md)。

这个仓库是进程 [`NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`](https://arweave.net/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8) 在最后一条已推上 Arweave 的 Assignment 之后的 qAR 余额账本。链上 `Name` 标签是 `local-t-w-001`（`GOAL.md`、`STATE.md`）。尾部是 epoch 0、nonce 2075923，Assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`，消息 `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`，时间 2026-07-04T06:19:55.380Z（`docs/RECOVERY.md`、`repro/EXPECTED.json`）。表内 7615 个地址，其中非零 2239 个。总供应 `189487568412204611` 等于原始余额之和。按 12 位小数，这个供应是 `189487.568412204611`（`repro/EXPECTED.json`、`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`、`docs/RECOVERY.md`）。

按 2026-10-18 的检查点修订，`goal_complete` 为 true（`GOAL.md`、`evidence/p10/20261017T1954Z-gate-recompute-amended/`）。这表示账本可以公开接受审核。它不是领取名单，也不是分配指令。`publish_claims` 为 false。`move_collateral` 为 false。

## 检查点、回放与哈希

回放起点是计算单元检查点 `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`，nonce 2074518，签名者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`。解压后的检查点内存 SHA-256 是 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`（`repro/EXPECTED.json`）。

从该检查点到 nonce 2075923，回放应用 39065 条：1405 条 Assignment 和 37660 条 cron（`repro/EXPECTED.json`、`evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`）。检查点到尾部的哈希链 1523/1523 匹配（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。

最终内存 SHA-256：

`25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`

canonical 余额 SHA-256：

`0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`

两个值都在 `repro/EXPECTED.json`。canonical 文件只保留非零余额，按地址排序，原始数额用字符串，是末尾带一个换行的紧凑 JSON（`repro/README.md`）。`docs/RECOVERY.zh.md` 的「当前结果」一节记下的是同一对哈希。2026-10-18 的修订把这个哈希记成各方一致的尾部哈希（`evidence/p10/20261017T1954Z-gate-recompute-amended/`）。

## 独立核对

| 路线 | 结论 | 证据 |
| --- | --- | --- |
| 精确 WASM 回放 | 到达 nonce 2075923，处理器错误 0，7615 行，原始合计等于单独读出的 Total-Supply `189487568412204611`，最终内存 SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。主会话回放后来对上了这个内存 sha。见下一张表。 | `evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md`、`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md` |
| 只回放 Assignment | 这 1405 条 Assignment 与含 cron 的回放得到同一份余额字节。两份余额 JSON 的 SHA-256 都是 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`，地址和数额差异为 0。只回放 Assignment 的内存 SHA-256 是 `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7`。该次被标成快速估计，不是正式内存结果。 | `STATE.md`、`docs/RECOVERY.md`、`evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json` |
| 不跑 WASM 的 Python 重算 | 703 笔转账入账，0 笔拒绝。7615 个地址和原始余额全部与 fast tail 账本一致。 | `evidence/p10-indep/20261017T104141Z-w-indep/SUMMARY.md` |
| 干净克隆，只访问公开网关 | 内存 SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。canonical 余额 SHA-256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`，非零地址 2239，与 fast tail 的非零行一致。完整 safe 模式没有跑。前 10 条里，未修改的 loader 和原地模式内存 SHA-256 相同：`4e341435f023aa41f27fc2b1dbb764c14c30ca39b13f14a02704bac722562960`。 | `evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`、`repro/EXPECTED.json` |
| cron 区块高度 +3 和 −3 | canonical 余额哈希仍是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。内存 SHA-256 在 +3 时变为 `d0dd22f387150aa3e894106cb5d8dde08783ea30974cfd78ea632e9a1c46bc20`，在 −3 时变为 `6b11be84807469cebb5201867800cdbfcb21266ca14ae65322cff772be126c92`。 | `evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`、`repro/README.md` |

<!-- MAIN_REPLAY_SHA: match -->

| 路线 | 结论 | 证据 |
| --- | --- | --- |
| 主会话慢速重放（逐条复制内存）的最终 sha | 与 fast 回放和干净克隆一致。最终内存 SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。最后一条 Assignment 的 nonce 是 2075923。canonical 余额 SHA-256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。完整 safe 模式没有跑。 | `evidence/p7/20261017T1718Z-p7-replay-read/`、`evidence/p10/20261017T1718Z-gate-recompute/` |

## 自己怎么核对

### 账本哈希

尾部 CSV 是 `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`（7615 行）。回放余额 JSON 是 `data/raw/fast/tail/balances.json`，已被 git 忽略，402362 字节，SHA-256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。那个文件哈希是整张表。canonical 哈希会去掉零余额并按键排序。

在仓库根目录执行：

```python
import csv, json, hashlib
body = dict(sorted((a, r) for a, r, *_ in list(csv.reader(open("evidence/p10/20261017T1047Z-fast-tail/ledger.csv", encoding="utf-8-sig")))[1:] if r != "0"))
print(hashlib.sha256((json.dumps(body, separators=(",", ":")) + "\n").encode()).hexdigest())
```

打印结果是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。

### 从公开网关从零复现

步骤以 `repro/README.md` 为准。在仓库根目录，使用 Node.js v22.22.0：

```sh
./repro/run.sh
```

脚本使用公开网关，默认 `https://arweave.net`，失败后依次试 `ar-io.dev`、`vilenarios.com`、`turbo-gateway.com`。GraphQL 还会试 `arweave-search.goldsky.com`。它从 `/raw/<id>` 下载检查点 `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`，核对 ANS-104 签名和签名者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`，把哈希链核到尾部 `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`，并用 `@permaweb/ao-loader` 0.0.44 回放 nonce 2074519..2075923，包含 cron。输出在 `repro/work/out/`。`out/balances.sha256` 就是 `repro/EXPECTED.json` 里的 `canonical_balances_sha256`。

已发表的那次运行没有执行 `./repro/run.sh --mode safe`。零偏移跑完之后，该 README 里的高度检查是：

```sh
./repro/run.sh --cron-height-offset 3
./repro/run.sh --cron-height-offset -3
```

### 网站

[https://qar-balances.zigza.xyz](https://qar-balances.zigza.xyz) 提供这份尾部账本。地址查询在 [#/lookup](https://qar-balances.zigza.xyz/#/lookup)。验证页 [#/verify](https://qar-balances.zigza.xyz/#/verify) 列出核对时间线，并用浏览器 SubtleCrypto 对已加载的余额现场计算哈希。页脚是同一个 canonical 哈希（`web/SUMMARY.md`）。

## 仓库地图

- [docs/RECOVERY.md](docs/RECOVERY.md) 与 [docs/RECOVERY.zh.md](docs/RECOVERY.zh.md)：全过程方法、未通过的检查、仍然缺失的输入。
- [docs/PUBLICATION.md](docs/PUBLICATION.md)：发布说明。
- [evidence/](evidence/)：各阶段记录。尾部报告在 [evidence/p10/20261017T1047Z-fast-tail/](evidence/p10/20261017T1047Z-fast-tail/)。
- [recovery/](recovery/)：回放和报告脚本。
- [repro/](repro/)：从零复现。预期哈希在 [repro/EXPECTED.json](repro/EXPECTED.json)。
- [web/](web/)：静态账本站。`node_modules/` 和 `dist/` 不提交。
- [audit/REDACTIONS.md](audit/REDACTIONS.md)：公开前从证据正文里改写了什么。
- [GOAL.md](GOAL.md)、[STATE.md](STATE.md)、[RECOVERY_PLAN.md](RECOVERY_PLAN.md)：工作日志。`STATE.md` 是游标。

工作由 Claude 和 Grok 的会话完成。查询使用 `docs/RECOVERY.md` 里写明的公开网关：`https://arweave.net`、`https://turbo-gateway.com`、`https://ar-io.dev`、`https://vilenarios.com`，以及 GraphQL `https://arweave.net/graphql`。`https://arweave-search.goldsky.com/graphql` 返回 HTTP 307，跟随之后落到 `https://arweave.net/graphql`。

## 这些数字是什么意思

**信任假设。** 检查点由 LegacyNet CU 签名者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk` 签发。Arweave 上早期调度有空洞，所以无法从创世独立重算到该检查点。P4 因检查点而关闭，不是因为区间已经补全。这个局限不阻止 `goal_complete`。

**问题反馈。** 本仓库公开之后，任何人都可以提 issue，没有固定审核期。余额一旦改变，canonical 哈希随之改变，并记录在 STATE.md。分配决定由抵押物持有人在本仓库之外作出。

**语言。** 证据记录保留写入时的语言，中文或英文。以中文为主的记录在 [docs/evidence-en/](docs/evidence-en/) 有英文译本，以原文为准。[evidence/README.md](evidence/README.md) 用中英文索引全部证据。

**账本里的零余额。** 表内 7615 个地址。其中 5376 个原始余额为 0，不写入 canonical 文件（`evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`）。这些零是 `evidence/p10/20261017T1047Z-fast-tail/ledger.csv` 里已经在场的键。

**不在账本里的地址。** `GOAL.md` 的原话是："Missing rows are not zero." `docs/RECOVERY.md` 的原话是："A missing row is not written as zero." 同一份说明还写：缺少的余额键用字符串 `0` 回答，这个字符串是处理器回复，不是恢复出来的账本行。`STATE.md` 写明：查询未命中是 `unknown`，不是余额 0。

**抵押物。** 充值和提现消息使用的是原生 AR。没有单一持有人。托管钱包的整笔余额不是可分离抵押，其余已经混同，可分离的原始数量是 null（`evidence/p9/20261017T090508Z-w-collat/SUMMARY.md`、`evidence/p9/20261017T1720Z-p9-record/`）。对账不在这份账本里。`collateral_sourced` 和 `collateral_reconciled` 仍为 false，也不是修订后的门禁（`STATE.md`）。尾部报告里的抵押物差额是 unknown（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。

**Unwraps 与 Deposits。** nonce 2075923 上，`Unwraps` 是 0 行，`Deposits` 是 0 行。`UnwrapsCompleted` 有 2234 行，原始合计 `272977038419623672`。`DepositsCompleted` 有 4364 行，原始合计 `462464606831828283`。这些已完成合计是表的总计，不是持有的抵押物（`evidence/p9-unwrap/20261017T105845Z-w-unwrap/SUMMARY.md`）。

**分类。** 刷新后的尾部报告计数（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）：

| 类别 | 行数 | 原始数量 |
| --- | ---: | --- |
| user | 5279 | `186394240884573076` |
| pool | 74 | `2330669314779690` |
| process_unknown | 2260 | `512312055550503` |
| lock | 2 | `250346157301342` |
| bridge | 0 | `0` |

`classification_sourced` 为 false。`wallet` 标签是一次成功的 id 查询没有返回边，不是已核实的个人身份。报告类别 `user` 是这个 wallet 标签的映射。仅凭 Name 标签分出的锁，置信度是 medium。池余额不是终端用户的领取额（`docs/RECOVERY.md`）。`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 的角色仍是 `wallet`。身份没有核实（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。尾部分类新增 1 个地址，10 个余额有变化，角色变化 0（`STATE.md`）。

**仍然开着的项。** 从第一条已推送 Assignment 起的 nonce 连续性未满足：明确缺失 759 个 nonce，150000..2074399 没有索引（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。`evidence/p4/` 里有 120 个目录，每个目录对应一个尚未解决的 nonce，记录的是一次已关闭且为空的精确查询。这些目录不是缺失的账本行。`docs/RECOVERY.md` 把这些洞分成 50000..99999 里的 132 个和 100000..149999 里的 627 个。独立字节门没有通过。nonce 2074518 的语义余额门通过了（`docs/RECOVERY.md`、`STATE.md`）。检查点之前有五笔 Transfer 的消息体在 `https://arweave.net/raw/{id}` 上是空的，nonce 为 2074509、2074511、2074513、2074515、2074517。数量在 Quantity 标签里。这些 nonce 都不在 2074519..2075923（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。

这个仓库不移动抵押物，也不发布领取名单（`GOAL.md`）。`publish_claims` 和 `move_collateral` 都是 false（`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`）。

## 背景

qAR 是上面这个 AO LegacyNet 代币，12 位小数。LegacyNet 已经停止，也不会恢复。2026-10-12，AOX 把 qAR 排除出清盘，因为当时还没有拿到账本。wUSDC 和 wAR 用检查点数据纳入了清盘。Permaswap 记下了同样的排除。曾索取的这份进程的最终计算单元状态不在已共享的检查点集合里，所以截止点是把公开的 Arweave 记录重放到 nonce 2075923 重建出来的（`docs/RECOVERY.md`）。

## 发现问题怎么报告

开一个 issue。写上地址、你认为正确的余额，以及你用的证据。

## License

本仓库（代码与 evidence 数据）MIT。例外是 `vendor/drive-cu`，它沿用上游 permaweb/ao 的 Business Source License 1.1，见 [vendor/drive-cu/LICENSE](vendor/drive-cu/LICENSE)。

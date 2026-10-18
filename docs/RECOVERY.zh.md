# qAR 余额恢复

这份说明给外部审核者。它写清恢复了什么、哪些检查通过、哪些检查失败、哪些输入仍然缺失。它是研究记录。它不是领取名单，也不包含抵押物分配方案。

按 2026-10-18 的检查点修订，`goal_complete` 为 true。`publish_claims` 为 false。`move_collateral` 为 false。修订后的门禁重算在 [evidence/p10/20261017T1954Z-gate-recompute-amended/](../evidence/p10/20261017T1954Z-gate-recompute-amended/)。较早的草稿 [evidence/p10/20261017T0954Z-fast-tail/REPORT.md](../evidence/p10/20261017T0954Z-fast-tail/REPORT.md) 仍写着 `goal_complete` 为 false；那句话描述的是草稿，不是修订后的规则。不阻塞完成的已知局限：账本无法从创世重算，抵押物只作为事实报告。仓库公开之后，任何人都可以提 issue，没有固定审核期。

英文同一文本是 [RECOVERY.md](RECOVERY.md)。

> 这是工作日志。下面有些句子写于回放完成之前。凡是早先写成「待补」的哈希，当前结果在这一节。

## 当前结果

- 规范余额 SHA-256 是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`（非零地址 2239）。步骤在 `repro/README.md`。该值是 `repro/EXPECTED.json` 的 `canonical_balances_sha256`。
- 主回放已经在 nonce 2075923 结束。内存 SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` 与 fast 回放和干净克隆一致。证据：`evidence/p7/20261017T1718Z-p7-replay-read/replay.json` 和 `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`。完整 safe 模式没有跑。
- 不执行模块的 Python 重算对上了全部 7615 个地址。证据：`evidence/p10-indep/20261017T104141Z-w-indep/SUMMARY.md`。
- 更新后的尾部表是 `evidence/p10/20261017T1047Z-fast-tail/`。第 5 节的类别计数是更早的 0954 快照（user 5278）。更新后的计数是 user 5279、pool 74、process_unknown 2260、lock 2、bridge 0。
- 按 2026-10-18 的检查点修订，`goal_complete` 为 true：账本可以公开接受审核，不是领取名单，也不是分配指令。`publish_claims` 和 `move_collateral` 仍为 false。可分离的抵押物原始数额仍是 null。这个局限不阻止完成。从第一条已推送 Assignment 起的 nonce 覆盖仍不完整：50000..99999 有 132 个洞，100000..149999 有 627 个洞，150000..2074399 没有索引。`evidence/p4/` 另有 120 个按 nonce 分开的记录，每次精确查询都已关闭且为空。这些记录不是缺失的账本行。

## 1. 目标和范围

### 恢复哪本账，恢复到哪一时点

进程是 [`NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`](https://arweave.net/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8)（[ao.link](https://ao.link/#/entity/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8)）。

链上 `Name` 是 `local-t-w-001`。它以 aos 2.0.0、变体 `ao.TN.1`、每 5 分钟一次 cron 创建。创建区块 1505290，时间 2024-09-12T18:00:08Z。所有者 `6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es`。模块 [`1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`](https://arweave.net/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0)。调度器 `_GQ33BkPtZrqxA84vM8Zk-N2aO0toNNu_C-l-rawrBA`。来源：[evidence/p0-probe.json](../evidence/p0-probe.json)。

本地交易配置把同一个进程 id 称为 qAR。恢复固定使用这个 id。来源：[GOAL.md](../GOAL.md) 和 [evidence/p8/20261017T0906Z-w-p8/local-configs.json](../evidence/p8/20261017T0906Z-w-p8/local-configs.json)。

目标状态是：**最后一条实际推上 Arweave 的 Assignment 执行完成之后**的内存。这条 Assignment 是：

| 字段 | 值 |
| --- | --- |
| Epoch / nonce | 0 / 2075923 |
| Assignment | [`MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`](https://arweave.net/MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs) |
| 消息 | [`wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`](https://arweave.net/wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ) |
| Hash-Chain | `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE` |
| 时间 | 2026-07-04T06:19:55.380Z（`1783145995380` 毫秒） |
| 入链区块 | 1951869，时间 2026-07-04T06:20:37Z |

来源：[evidence/p1-tail.json](../evidence/p1-tail.json)。冻结这条边界的方案是 [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) 第 2 节。

### 为什么是这个时点

LegacyNet 已经停止。如果以后要分割抵押物，需要的是每个地址在最后一条已推送 Assignment 上的余额。研究进行的日期不是截止点。nonce 2075923 之后的 cron 也不是截止点。[README.md](../README.md) 记录：曾向持有方索取的这份进程的最终计算单元状态，不在已共享的检查点集合里。这次恢复没有重取那段对话，而是用公开的 Arweave 记录重建截止点。

P1 查找了更高的 nonce。接下来的 13 个 nonce（2075924 到 2075936）不存在。哨兵 2076000、2077000、2080000、2090000、2200000、3000000、4000000 不存在。epoch 1 和 epoch 2 的 Assignment 不存在。区块高度 1951870 及以上没有索引到这个进程的 Assignment。探测时 Arweave 链尖是区块 2022620。P1 没有把 2075923 以上的每一个 nonce 都查一遍。哨兵跳过的 nonce，会在连续性索引里表现为缺口。来源：[evidence/p1-tail.json](../evidence/p1-tail.json)。

这条 Assignment 自己的 `Block-Height` 标签是 `000001951866`。入链高度是 1951869。两个数都保留。执行器使用的是历史计算单元所用的高度，那个字段和入链高度不是同一个。来源：[evidence/p0-probe.json](../evidence/p0-probe.json) 和 [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) 第 2 节。

### 这本账不是什么

这张表不是可以领取的人员名单。它不把池子余额拆成 LP 份额。它不给出抵押物资产、持有人或数量，也不提出分配方案。[GOAL.md](../GOAL.md) 禁止转移抵押物、禁止发布领取名单。尾部报告的标题是 `BLOCKED — NOT A CLAIM LIST`。

Unwrap/Deposit 中可能存在未完成的记录，另行核查，不在本账本范围内。

## 2. 数据来源，以及每类数据如何核对

恢复只用公开节点。

- Arweave 网关：`https://arweave.net`、`https://turbo-gateway.com`、`https://ar-io.dev`、`https://vilenarios.com`，以及 GraphQL `https://arweave.net/graphql`。`https://arweave-search.goldsky.com/graphql` 返回 HTTP 307，跟随之后落到 `https://arweave.net/graphql`，所以它不是第二套索引。来源：[evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md](../evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md)。
- AO 调度器，进程标签给出的 id 是 `_GQ33BkPtZrqxA84vM8Zk-N2aO0toNNu_C-l-rawrBA`。
- LegacyNet 计算单元发布在 Arweave 上、带 `Type=Checkpoint`、且指向本进程的数据项。签名者核对使用 `https://cu.ao-testnet.xyz/` 公布的地址。来源：[evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json)。

一个公开的计算单元文件目录被当作旁路盘点。里面没有 qAR 检查点。见第 3 节。

### Assignment 和哈希链

GraphQL 返回标签。哈希链使用的 id 是内层 ANS-104 数据项。这个 id 是该项签名的 SHA-256。外层 bundle id 是另一个值。用外层 id 时，nonce 5771..5794 的链对不上；改用内层 id 后全部接上。来源：[evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json](../evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json)。

链接函数是 `sha256(上一条 assignment id 的字节 || 上一条 hash-chain 的字节)`，再做 base64url。第一条 nonce 的种子是进程 id，此时不拼 assignment id。函数读自 permaweb/ao 提交 [`7ba5df7b2e3c8f7e891481b4fe1b0489647cf607`](https://github.com/permaweb/ao/blob/7ba5df7b2e3c8f7e891481b4fe1b0489647cf607/servers/su/src/domain/core/scheduler.rs) 的 `gen_hash_chain`。这棵树晚于 2024 年写出早期 Assignment 的调度器。只有重算值等于下一条的 `Hash-Chain` 标签时，才算匹配。实现：[recovery/hashchain.py](../recovery/hashchain.py)。nonce 0 的 `Hash-Chain` 等于进程 id 的 SHA-256。来源：[evidence/p3/20261016T174856Z-p3a/sample.json](../evidence/p3/20261016T174856Z-p3a/sample.json)。

### 检查点

对选中的检查点：ANS-104 签名验证通过，所有者等于 `https://cu.ao-testnet.xyz/` 上的地址，解压后字节的 SHA-256 等于 `SHA-256` 标签。来源：[evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json)。

### 模块字节

`https://arweave.net` 和 `https://turbo-gateway.com` 返回同一份 557297 字节。SHA-256 是 `164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8`。文件以 WASM 魔数开头。RSA 签名已保存，没有验证。来源：[evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json) 和 [fetch-manifest.json](../evidence/p2/20261017T1645Z-p2a/fetch-manifest.json)。

### 检查点到尾部的消息

nonce 2074400..2075923 的 1524 条 Assignment 消息全部存档，签名全部验证通过。GraphQL 没有 nonce 2075899 的消息 [`VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA`](https://arweave.net/VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA)，也没有 nonce 2075900 的消息 [`iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw`](https://arweave.net/iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw)。直接数据 URL 返回 HTTP 404。字节在区块 1924100 的 L1 交易 [`MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA`](https://arweave.net/MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA) 里，通过 chunk offset 接口读出。每条的签名都验证通过。来源：[evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md](../evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md) 和 [message-gap-recovery.json](../evidence/p4-tail/20261017T052614Z-w-tail/message-gap-recovery.json)。

### 没有归档的部分

P0 和 P1 是探测摘要，没有保存每一次 GraphQL 的原始响应。其后各阶段把原始页放在 `data/raw/`。这个目录被 git 忽略。每份已提交的 manifest 写明原始文件路径、字节数和 SHA-256。哈希是内容校验，不是下载地址。没有 `data/raw/` 的机器按 manifest 里的 id 重新下载。来源：[RECOVERY_PLAN.md](../RECOVERY_PLAN.md) 第 2 节和第 4 节。

缺失的行不写成 0。

## 3. 每个阶段做了什么

阶段规则在 [RECOVERY_PLAN.md](../RECOVERY_PLAN.md)。这些阶段写下的游标在 [STATE.md](../STATE.md)。本节按证据写，包括后来放弃的路径。

### P0 和 P1 — 身份和尾部

P0 记录了进程标签，以及按高度降序取到的一条 Assignment。这一条不能证明最大 nonce。P1 是第 1 节的尾部证明。来源：[evidence/p0-probe.json](../evidence/p0-probe.json)、[evidence/p1-tail.json](../evidence/p1-tail.json)。

### P2 — 取模块字节，不执行

模块已下载，没有执行（`executed` 为 false）。存在的标签：`Memory-Limit` `500-mb`，`Compute-Limit` `9000000000000`，`Module-Format` `wasm32-unknown-emscripten`，`Input-Encoding` `JSON-1`，`Output-Encoding` `JSON-1`，`Variant` `ao.TN.1`。`Extensions` 不存在，没有用默认值填上。来源：[evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json)。

### P3 — 三个抽样窗口，不是全覆盖

窗口 0..19、1037960..1037979、2075904..2075923 每个 nonce 都有一条 Assignment。`sample_passed` 为 true。`full_coverage` 为 false。nonce 0 和 nonce 1 都是区块 1505290 里的 `Type=Message`、`Action=Eval`。nonce 0 的消息是 [`GBPuvd6zc47A8PFiD7PGmZXcZPZF-DDWcdEg4tzXC3g`](https://arweave.net/GBPuvd6zc47A8PFiD7PGmZXcZPZF-DDWcdEg4tzXC3g)。nonce 0 的 Assignment 是 [`o6ia7Yi1ijVV0lXM75qK1DM2Alhk4JcdFOd6jnq2pTY`](https://arweave.net/o6ia7Yi1ijVV0lXM75qK1DM2Alhk4JcdFOd6jnq2pTY)。编号从 nonce 0 开始。索引方法是按区块高度遍历，页大小 100，精确 nonce 回退最多 5 个。来源：[evidence/p3/20261016T174856Z-p3a/sample.json](../evidence/p3/20261016T174856Z-p3a/sample.json)、[gaps.json](../evidence/p3/20261016T174856Z-p3a/gaps.json)、[index-method.json](../evidence/p3/20261016T174856Z-p3a/index-method.json)。

### P4 — 索引约两百万个 nonce，以及停在哪里

如果 nonce 0 到 2075923 连续，调度共有 2,075,924 条 Assignment。这个索引没有做完。来源：[RECOVERY_PLAN.md](../RECOVERY_PLAN.md) 第 5 节。

**0..49999 已完成。** 50000 条互不重复的 Assignment，0 个冲突，49999/49999 条哈希链匹配。第一轮 GraphQL 留下 5770..5793 未解决（[evidence/p4/20261016T175757Z-p4-0-49999/](../evidence/p4/20261016T175757Z-p4-0-49999/)）。原始 bundle 里有这 24 个 nonce，但当时用了外层 bundle id，链仍然断开（[evidence/p4/20261016T192515Z-p4-gapfill/](../evidence/p4/20261016T192515Z-p4-gapfill/)）。改用内层 id 后每一条都接上（[evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json](../evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json)）。

**50000..99999 被挡住，没有完成。** 已索引 49868 个互不重复的 nonce。仍缺 132 个。精确 nonce 查询没有返回行。相邻 bundle 补上了一部分洞；另一部分因为包头 chunk 读不出来而停下，那些洞没有插入任何记录。随后对洞旁区块里的非 AO bundle 和非二进制交易的扫描也没有补上洞。所有仍未读到的缺口 chunk 偏移，向 `vilenarios.com` 和 `ar-io.dev` 请求后都是 HTTP 404。404 表示这些字节当时读不到。它不是“这个 nonce 从未上链”的证明。缺失列表在 [evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json](../evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json)。按时间排列的尝试是 [evidence/p4/](../evidence/p4/) 下从 `20261016T193251Z` 到 `20261017T043721Z` 的目录。

**100000..149999 已索引，没有完成。** 49373 个互不重复的 nonce，缺 627 个，0 个冲突。63 批精确 nonce 查询都空关闭（[evidence/p4/20261017T050640Z-p4-100000-exact/finding.json](../evidence/p4/20261017T050640Z-p4-100000-exact/finding.json)）。对这些洞的 AO bundle 扫描在列出的 91 个里停在第 15 个。完整读完的 15 个里面没有目标 nonce。其余没有扫描。这不是缺失证明（[evidence/p4/20261017T052224Z-p4-100000-scan-stopped/finding.json](../evidence/p4/20261017T052224Z-p4-100000-scan-stopped/finding.json)）。洞列表是 [evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json](../evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json)。

nonce 150000 及以后的区间没有打开。150000..2074399 没有索引。它既不是存在列表，也不是缺失列表。

### 为什么放弃全量索引

nonce 2074518 有一份计算单元检查点，距尾部 1405 条 Assignment。[GOAL.md](../GOAL.md) 规定：带内存快照的结果成为回放起点，只重放其后的 nonce。132 个和 627 个洞保留在记录里。它们不被填成 0，也不再挡住尾部账本。方案里的改序说明是 [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) 第 5 节“快照改序”。

### P5 — 搜索检查点

GraphQL 条件为 `Type=Checkpoint` 且 `Process` 为本进程。123 页全部翻完，12267 行。三个签名者：

| 签名者 | 行数 |
| --- | ---: |
| `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`（`https://cu.ao-testnet.xyz/` 上的地址） | 3079 |
| `fcoN_xJeisVsPXA-trzVAuIiqO3ydLQxM-L4XbrQKzY` | 9182 |
| `By2MUXHmmovtHqeQZju4fn8x9a4BjH_msOt_PDjJ2X0` | 6 |

最新一条由计算单元地址签名。它是候选。P5 结束时它还不是已接受的回放起点（`p6_accepted` 为 false）。来源：[evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json) 和 [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json)。

选中的检查点：

| 字段 | 值 |
| --- | --- |
| Id | [`ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`](https://arweave.net/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk) |
| Nonce | 2074518 |
| Assignment | [`yy7ipxqxntq_9yTDaEvEW92CLrUqDssgN-RXYUQAHNA`](https://arweave.net/yy7ipxqxntq_9yTDaEvEW92CLrUqDssgN-RXYUQAHNA) |
| Hash-Chain | `W4h2kwRezDwtQtvxQ9Ssivujj3k2CZolEhKCblKrnTg` |
| 时间 | `1771847683094` 毫秒（2026-02-23T11:54:43.094Z） |
| Block-Height 标签 | 1863436 |
| 入链高度 | 1863456 |
| Gzip | 145634952 字节，SHA-256 `31f5e4811756ff22a98546144075dd238da76eeb05470a126df43eb2fe92e095` |
| 解压后内存 | 428146688 字节，SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` |

解压后的哈希等于标签。ANS-104 签名有效。签名者与计算单元地址一致。gzip 文件只在本地（`data/raw/checkpoints/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.gz`）。

门所用的两份更早内存：nonce 2074510，[`lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg`](https://arweave.net/lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg)；nonce 2074508，[`EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk`](https://arweave.net/EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk)。

### P6 第一次 — 字节门失败，检查点被拒绝

执行器从 nonce 2074508 重放到 2074518。加 300 条合成的 5 分钟 cron，以及完全不加 cron，内存 SHA-256 都既不等于 nonce 2074510，也不等于 nonce 2074518。执行器没有返回错误。只读 `Total-Supply` 在“只重放 Assignment”的结果上和在真实 nonce 2074518 内存上都是 `189487568412204611`。`Info` 一致。两边的 `Balances` 都返回 Output `[]`，这个空 Output 被记成 `Balances_match`。空 Output 不是余额表。aos 的 `Balances` 处理器把回复放在 `Messages[].Data`。这一轮拒绝把 nonce 2074518 当作回放起点。文件保留：[evidence/p6/20261017T054635Z-p6-gate/gate.json](../evidence/p6/20261017T054635Z-p6-gate/gate.json)。

### P7 创世回放 — 试过，保留，然后停止

拒绝检查点之后，回放从进程启动开始。

- nonce 0 的 Eval 在加载 `arweave.types.type` 时失败。内存停在启动哈希。没有写出余额行。失败的 Eval 不是零余额。来源：[evidence/p7/20261017T055800Z-p7-genesis-0-19/](../evidence/p7/20261017T055800Z-p7-genesis-0-19/)。
- 随后应用了 Assignment 1..19 和 226 条 cron。其中一轮用 Arweave 区块时间戳做 cron 边界。nonce 19 之后读到的 `Total-Supply` 是 `10000000000`。这不是停机供应。来源：[evidence/p7/20261017T0605Z-p7-genesis-0-19/](../evidence/p7/20261017T0605Z-p7-genesis-0-19/)。
- 同一段改用 Assignment 的 `Timestamp` 做 cron 边界，nonce 0 仍然没有被应用。nonce 1..19 和 226 条 cron 被应用。内存 SHA-256 `d36a4f98636128efc68f04c92a45e650940e1b77fe3792df2906d58e6eba8538`。供应读数仍是 `10000000000`。来源：[evidence/p7/20261017T0615Z-p7-genesis-0-19/](../evidence/p7/20261017T0615Z-p7-genesis-0-19/)。
- nonce 21..27 的消息体不在 `transactions(ids)` 里，直接取 nonce 21 返回 HTTP 404。这 7 个消息体后来从区块 1505824 的 AO bundle 里读出。Assignment 20..99 和 905 条 cron 被应用，没有处理器错误。内存 SHA-256 `657735b4fec49198f706747c3bce346e20e559ffdbebf6a30503079e9d07e14e`。nonce 99 之后的供应读数是 `1120000000000`。这不是停机供应。来源：[evidence/p7/20261017T0635Z-p7-20-99-inputs/finding.json](../evidence/p7/20261017T0635Z-p7-20-99-inputs/finding.json) 和 [evidence/p7/20261017T0645Z-p7-20-99/](../evidence/p7/20261017T0645Z-p7-20-99/)。
- 下一段 nonce 100..179 在跑完之前被停止。它不是游标。来源：[evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json](../evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json)。

创世回放被停掉，是因为同一个执行器必须在整条调度上都正确，132 个和 627 个洞仍然开着，而且 nonce 0 已经表明这个 loader 复现不了 2024 年的启动环境。计算单元检查点是更强的起始内存。创世文件留在仓库里。

### 语义门 — 余额一致；只有抄入 9 个高度时字节才一致

余额从每份内存的副本上读取 `Messages[].Data`。副本不写回。Output `[]` 被忽略。

使用网关区块高度，不从目标检查点抄高度：

| 门 | 起点 | 终点 | 消息 | 回放内存 SHA-256 | 检查点 SHA-256 | 地址数 | 地址差异 | Total-Supply |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| A | 2074508 | 2074510 | 115（2 条 Assignment，113 条 cron） | `6ea2c0646d295040de6045475faa1b947fa3de09ecf8d6c5a810e038af75a890` | `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1` | 7614 | 0 | `189487568412204611` |
| B | 2074510 | 2074518 | 108（8 条 Assignment，100 条 cron） | `08b33bd914ffd015fff0e0349ab279ed064eaa44dd79a35e3cfb26a7abd32baa` | `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` | 7614 | 0 | `189487568412204611` |

回放和检查点的余额 JSON SHA-256 相同：门 A `24f7b1e2f5a8bb6961c24630bb915cf1cb4804911e5803a8c5459d35b715f400`，门 B `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`。四份内存上，`Balances` 的合计都等于 `Total-Supply`。处理器错误为空。来源：[evidence/p6/20261017T052333Z-w-eval/semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json) 和 [SUMMARY.md](../evidence/p6/20261017T052333Z-w-eval/SUMMARY.md)。

字节差异不是余额变化。门 B 两份内存都是 428146688 字节。精确差异 332736 字节、30004 段，最后一处在偏移 236575800。可读差异是 9 条 cron：时间戳相同，回放的 `Block-Height` 比检查点里留下的高 1 到 3。这些高度出现在 cron 日志和 “Updating latest block height” 里。Anchor 多重集相同。Transfer 数量相同。事件里的 `sender_balance_*` 和 `recipient_balance_*` 多重集相同。供应的十进制串在两边的偏移都是 212117480。堆里没有一条 `"地址":"数额"` 和余额表不一致。其余差异字节是这些字符串挪位周围的 Lua 堆布局。

门 A 有同样的 9 个高度差，另外在 55 个区块的收件箱清理之后，有少量更早的 cron 日志和 anchor 只留在一边。Transfer 数量和事件数额仍然相同。来源：[semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json) 的 `regions` 和 `stringMultisets`。

第 3 次尝试把这 9 个 `Block-Height` 从目标检查点抄进来，并把 32 字节 anchor 解码成检查点里保存的 ASCII 引用。两段内存哈希于是等于检查点标签：A `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1`，B `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`。证据把这次抄录标成不是独立字节门。独立回放是上面的网关高度回放，它的内存哈希不相等。来源：[evidence/p6/20261017T052333Z-w-eval/gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json) 的第 3 次和第 5 次尝试。

随后 nonce 2074518 被接受为回放起点。`independent_byte_gate` 为 false。`semantic_gate` 为 `passed`。先前的拒绝文件没有被覆盖。来源：[evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json](../evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json)。

### 检查点绑定到尾部

nonce 2074400..2075923 共 1524 条 Assignment，缺失 0，冲突 0。哈希链 1523/1523 匹配，并连到 P1 尾部哈希 `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE`。2074508、2074510、2074518 三份检查点的 Assignment 和 Hash-Chain 标签与索引一致。来源：[evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md](../evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md) 和 [range-manifest.json](../evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json)。

### P7 尾部回放 — 其中一条还没走到尾部

主回放从 nonce 2074518 检查点走向 2075923，包含 cron，cron 的 `Block-Height` 取自网关区块时间戳。最后保存的游标是流索引 `next_index` 10400 / 39065，内存 SHA-256 `b3bd4ffd310420c737ee9140a8c265a386629dae1fe041b917cb3dd2db0980af`，处理器错误 0。这次保存里的最后一条 Assignment 是 nonce 2075073，流索引 9834。这次保存不是停机快照。来源：[evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json)。

第 6 节描述的另一次回放已经到达 nonce 2075923。它的最终内存哈希还没有和这条仍在运行的回放比较。

### P8 — 检查点上的持有人，不是尾部

分类用的是 nonce 2074518 的余额表：7614 个地址，原始合计 `189487568412204611`。没有在尾部表上重做。`classification_sourced` 仍为 false。来源：[evidence/p8/20261017T0906Z-w-p8/SUMMARY.md](../evidence/p8/20261017T0906Z-w-p8/SUMMARY.md) 和 [stats.json](../evidence/p8/20261017T0906Z-w-p8/stats.json)。

在 `https://arweave.net/graphql` 上按 100 个一批做 `transactions(ids)`。`Type=Process` 算进程。查询成功且没有边，就标成 `wallet`。这个标签是空的 id 查询，不是已核实的个人身份。五个余额键不是 43 字符的 Arweave id（`AccountCreator`、两个 `0x` 地址、`SwapRequest`、`undefined`），角色是 `invalid_id`。

| nonce 2074518 的角色 | 地址数 | 原始数量 |
| --- | ---: | --- |
| wallet | 5273 | `186296155097251128` |
| pool | 72 | `2427591802661553` |
| unknown_process | 369 | `402625751820531` |
| lock | 2 | `250346157301342` |
| agent | 1889 | `100080610148413` |
| lending | 1 | `7725686192460` |
| token_process | 1 | `1880007389099` |
| pool_candidate | 2 | `862198877788` |
| invalid_id | 5 | `301100562297` |

名称为 Botega 的池：53 个地址，原始量 `1742171823546173`。名称为 Permaswap 的池：19 个地址，原始量 `685419979115380`。没有地址被分成桥。LP 份额和锁仓受益人没有恢复。池余额不是终端用户的领取额。

链上名称，本地配置摘录见 [local-configs.json](../evidence/p8/20261017T0906Z-w-p8/local-configs.json)：

- 借贷：[`fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0`](https://arweave.net/fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0)，名称 `LiquidOps Q Arweave`，检查点原始量 `7725686192460`。
- 池：[`_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4`](https://arweave.net/_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4)，名称 `qAR:wAR:30`，检查点原始量 `1934348814863`。
- 锁，仅凭名称，置信度中等：`KbUW8wkZmiEWeUG0-K8ohSO82TfTUdz6Lqu5nxDoQDc`（名称 `NAB Stake and Mint`，原始量 `250296157301342`）和 `hgj136rPMZOV_ABlXeOpwl91jHGGz1l0ZXwI9Hf2HHk`（名称 `aoVest-Vesting-Process-1732572394108-a120g7`，原始量 `50000000000`）。来源：[pools-locks-bridges.json](../evidence/p8/20261017T0906Z-w-p8/pools-locks-bridges.json)。

检查点上最大的钱包是 `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8`，原始量 `180243716191492791`。身份检查在作出判断之前停止。角色仍是 `wallet`。来源：[evidence/p8-whale/20261017T094030Z-w-whale/SUMMARY.md](../evidence/p8-whale/20261017T094030Z-w-whale/SUMMARY.md)。

尾部报告的类别更粗。[recovery/p10/build_report.py](../recovery/p10/build_report.py) 把 `wallet` 映射为 `user`，把 `pool_candidate` 映射为 `pool`，把 `token_process` 映射为 `process_unknown`。`agent`、`lending`、`invalid_id` 不在这张映射表里。没有映射角色的进程变成 `process_unknown`。`is_process` 为 false 的 `invalid_id` 变成 `user`。因此尾部报告是 5278 行 `user`（5273 个钱包加 5 个无效 id）、74 行 `pool`（72 个池加 2 个候选）、2 个锁、0 个桥、2261 行 `process_unknown`（369 个未知进程、1889 个 agent、借贷那一行、代币进程自己，以及一个不在检查点文件里的尾部地址）。

### P9 — 抵押物未知

现行处理器是 0.16.0，由 Eval nonce 1977055 装入，消息 [`eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA`](https://arweave.net/eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA)（83536 字节，SHA-256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`）。`Denomination` 是 12。供应是全局表 `Balances` 的合计。动作名是 `Total-Supply`。没有单独的 `TotalSupply` 全局变量。缺少的余额键用字符串 `0` 回答。这个字符串是处理器回复，不是恢复出来的账本行。

nonce 1977061 设置 `DEPOSITS_ENABLED = false`（[`xkyG1_Gexl06pnLQ-2j5Du6MC4rAb6CaUrslgs_omVw`](https://arweave.net/xkyG1_Gexl06pnLQ-2j5Du6MC4rAb6CaUrslgs_omVw)）。nonce 1977062 设置 `WITHDRAWALS_ENABLED = false`（[`m1n3dJfy5iZ0ZYO2PWQi9JCuQH_Kr-VXfmR1NmSm69Q`](https://arweave.net/m1n3dJfy5iZ0ZYO2PWQi9JCuQH_Kr-VXfmR1NmSm69Q)）。nonce 1977063 设置 `TRANSFERS_ENABLED = true`（[`gaBFkKOA7cKc5cF3LxoygCkgu90z7tGVAG_nJreDgO8`](https://arweave.net/gaBFkKOA7cKc5cF3LxoygCkgu90z7tGVAG_nJreDgO8)）。这些开关打开之后，充值、铸币、解包和提现会报错。转账仍然允许。这条路径上的 0.16.0 源码没有写出抵押物资产 id，也没有写原生 AR 的持有人。抵押物资产、持有人和原始数量都是未知。未知不是 0。来源：[evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md](../evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md) 和 [handlers.md](../evidence/p9-prep/20261017T051439Z-w-src/handlers.md)。

尾部报告没有收到 `collateral.json`。`delta_raw` 是 null，状态是 `unknown`。来源：[evidence/p10/20261017T0954Z-fast-tail/reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json)。单独的抵押物 worker 没有在这次提交里发表结果。

尾部 Assignment 本身，即 nonce 2075923，把一个地址插入 `ao.authorities`，然后删掉第一项。处理器审阅认为它不改 `Balances`。来源：同一份 P9 摘要。

### 旁路 — 公开的计算单元目录

有响应的目录是 `https://drive.google.com/drive/folders/1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`。[GOAL.md](../GOAL.md) 里写的目录 id 返回 HTTP 404。盘点到 1113 个文件，其中 1012 个是检查点二进制。这 1012 个名字里没有 qAR，也没有单独的 APUS 进程。APUS 没有被重建。目录里的 CU 源码是 permaweb/ao 提交 `0db88a45`，`@permaweb/ao-loader` 锁定在 0.0.44。它的 cron `Block-Height` 算法和执行器所用的是同一套，所以这棵树本身解释不了那 9 个高度差。18 个本地池 id 里有 4 个出现在目录中。优先池 `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` 的文件没有下载，报告里的 SHA-256 没有用本地字节核对。nonce 2074518 持有 qAR 的进程里，有 54 个和这个目录相交。这些检查点文件一个都没有保存。来源：[evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md](../evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md) 和 [inventory.json](../evidence/side-d/20261017T0856Z-w-drive/inventory.json)。

### P10 — 报告生成器、试运行，然后是尾部表

试运行是 nonce 2074518：7614 行，合计 `189487568412204611`，等于那份检查点的供应。抵押物未知。那次试运行把每一行都留成 `process_unknown`。它不是尾部账本。来源：[evidence/p10-dryrun/20261017T091010Z-w-report/SUMMARY.md](../evidence/p10-dryrun/20261017T091010Z-w-report/SUMMARY.md)。

尾部表在第 5 节。

## 4. 执行器

固定在一台 Linux 服务器上。

| 项目 | 值 | 来源 |
| --- | --- | --- |
| 包 | `@permaweb/ao-loader` 0.0.44 | [evidence/p6/20261017T052333Z-w-eval/evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json) |
| Node | v22.22.0 | 同一文件 |
| Node 22 发行包 SHA-256 | `9aa8e9d2298ab68c600bd6fb86a6c13bce11a4eca1ba9b39d79fa021755d7c37` | 同一文件 |
| 锁文件 | [recovery/p6/package-lock.json](../recovery/p6/package-lock.json)，SHA-256 `e5a7d53067caca949e1095dd7f52c81d79c4d30d2ed1746de11cc6c1c352b27f` | 同一文件 |
| CU 语义 | permaweb/ao [`0db88a45aabeb5e88471e5c263790fa51a563461`](https://github.com/permaweb/ao/blob/0db88a45aabeb5e88471e5c263790fa51a563461/servers/cu/src/domain/lib/loadMessages.js)（2026-02-22），`servers/cu/src/domain/lib/loadMessages.js` | 同一文件 |
| 模块 | `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`，SHA-256 `164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8` | [module.json](../evidence/p2/20261017T1645Z-p2a/module.json) |
| 内存上限 | 标签 `500-mb`，524288000 字节 | [evidence/p6/20261017T054635Z-p6-gate/evaluator.json](../evidence/p6/20261017T054635Z-p6-gate/evaluator.json) |
| 计算上限 | `9000000000000` | 同一文件 |
| 进程堆上限 | 8192 MiB，以便 loader 放下 428146688 字节的内存 | w-eval 执行器文件里的 `command` 字段 |
| 检查点内存 | 428146688 字节 | [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json) |

选择提交 `0db88a45`，是因为它是检查点 nonce 2074518 前一天的树。该提交的 CU 锁文件把 `@permaweb/ao-loader` 钉在 0.0.44。在这段历史里，`loadMessages.js` 最后一次修改是 2025-11-13。第 2 节的哈希链函数读自另一个更晚的提交，这个差别写在 [recovery/hashchain.py](../recovery/hashchain.py) 里。

### cron 如何生成

进程标签是 `Cron-Interval=5-minutes` 和 `Cron-Tag-Action=Cron`。基于时间的 cron 在 `(以秒计的时间戳 - 以秒计的起点) % 300 == 0` 时命中。起点那一秒本身不是一次 tick。`cronMessagesBetween` 从左侧 Assignment 的区块时间戳起，按一秒一步走到右侧 Assignment 的区块时间戳，不包含右侧。走到新区块时，该区块的高度成为这条 cron 消息的 `Block-Height`。仓库里的代码是 [vendor/drive-cu/src/domain/lib/loadMessages.js](../vendor/drive-cu/src/domain/lib/loadMessages.js) 的 `isTimestampOnCron` 和 `cronMessagesBetweenWith`，来自同一棵 `0db88a45` 树。

调度器没有返回这个进程的 origin。公开的调度器主机 DNS 失败，后续响应是 HTTP 403。cron 相位取自三份检查点的时间戳，它们都是 `秒 % 300 == 283`。进程区块的秒 1726164008 是相位 8，产生不了这些时间戳。使用的 origin 是 `1726163983000` 毫秒。任何一个与 283 模 300 同余的 origin 秒，都会选出 2026 年的同一组 cron。来源：[evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json) 的 `originMs` 和 `originReason`。

尾部回放把高度来源记为网关区块时间戳。来源：[evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json)。尾部 Assignment 之后的 cron 不生成。

余额和供应的读取在内存副本上进行。历史内存文件不被这次读取替换。来源：[semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json) 的 `readPath`。

## 5. 尾部余额表

表在 [evidence/p10/20261017T0954Z-fast-tail/ledger.csv](../evidence/p10/20261017T0954Z-fast-tail/ledger.csv)。

| 项目 | 值 |
| --- | --- |
| 截止点 | epoch 0，nonce 2075923，该 Assignment 完成之后 |
| 行数 | 7615 |
| 原始合计 | `189487568412204611` |
| 单独读出的 Total-Supply | `189487568412204611` |
| 合计等于供应 | 是 |
| 账本差额 | `0` |
| 12 位小数的人类供应 | `189487.568412204611` |
| 因格式错误而略去的行 | 0 |
| 最终内存 SHA-256 | `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` |
| 内存字节 | 428146688 |
| 已应用的流项目 | 39065 |
| 处理器错误 | 0 |
| 从主回放恢复的位置 | 索引 8400，内存 SHA-256 `78fc3856ea0e4dc6e195463e18a3e6f5810c4c39febcdbc4fc9a0f181a224bfb` |

供应读自回放的 `Total-Supply` 消息数据。它不是用表的合计来定义的。来源：[evidence/p10/20261017T0954Z-fast-tail-inputs/supply.json](../evidence/p10/20261017T0954Z-fast-tail-inputs/supply.json) 和 [replay.json](../evidence/p10/20261017T0954Z-fast-tail-inputs/replay.json)。

文件哈希，来自 [manifest.json](../evidence/p10/20261017T0954Z-fast-tail/manifest.json)：

| 文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| `evidence/p10/20261017T0954Z-fast-tail/ledger.csv` | 3397765 | `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2` |
| `data/raw/fast/tail/balances.json`（git 忽略） | 402362 | `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` |

0954 草稿当时写：另一条回放的最终内存哈希还没有交叉核对。这次核对已经完成。主回放、fast 和干净克隆的内存 SHA-256 都是 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`（`evidence/p7/20261017T1718Z-p7-replay-read/`、`evidence/p10/20261017T1718Z-gate-recompute/`）。nonce 2075923 仍然没有已上链的检查点。草稿自己的 `goal_complete` 仍是 false。修订后的 `goal_complete` 为 true。

### 规范余额哈希

规范余额哈希是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。从零复现的说明是 [repro/README.md](../repro/README.md)。「当前结果」和 `repro/EXPECTED.json` 记下的是同一个值。这一节的表是 0954 快照。早先的“待补”已被替代。

### 尾部表上的类别

这些是报告的类别，不是 P8 的角色。映射见第 3 节。`classification_sourced` 为 false。`user` 是报告对 P8 `wallet` 或 `invalid_id` 的叫法。它不是已核实的身份。

| 类别 | 行数 | 原始数量 |
| --- | ---: | --- |
| user | 5278 | `186393679140702692` |
| pool | 74 | `2330669314779690` |
| process_unknown | 2261 | `512873799420887` |
| lock | 2 | `250346157301342` |
| bridge | 0 | `0` |

来源：[evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md](../evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md)。

有 11 个地址和 nonce 2074518 的表不同。其中 10 个在 `holder_balance_mismatches` 里。有 1 个是新地址。这些原始差额加上新地址，合计为 0，与供应不变相符。这张表本身不能说明是哪些消息搬走了这些单位。来源：[reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json) 和 [evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json)。

| 地址 | 2074518 的原始量 | 2075923 的原始量 |
| --- | --- | --- |
| `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` | `180243716191492791` | `180398401009414645` |
| `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4` | `381553671374914` | `291712135061413` |
| `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` | `320089670049015` | `312546942799043` |
| `wWq05ZZX6Jj2p9wW59oZ6lMF_KdW754zywqLa9n8INA` | `149454420015180` | `0` |
| `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948` | `56636111316938` | `123291631310116` |
| `MmhScGp35v-9veB1ufbXRDoaDleTi_z3V_vZTjA8bnU` | `4725068954918` | `0` |
| `AxpxHZmHQhF25FkVSVX0T877PP2WUi7I46nmQaECUHI` | `0` | `31129166766473` |
| `3biQvRjIp_9Qz1L9D3SJ9laK4akCkP-8bvAo3pQ6jVI` | `3003053338103` | `2602630141925` |
| `F9dWqoqSMzC3oyigfhezyT0fzc5BjhIYVSqcQWOgDq8` | `561743870384` | `0` |
| `yEGUy_Dl229kp8cDtJ8wxekm0cqe2t68PhLrHPoHWQY` | `505328951756` | `0` |
| `wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4` | 不在表中 | `561743870384` |

`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 仍是类别 `user`，因为 P8 把它写成 `wallet`。身份没有核实。

### 为什么 `goal_complete` 是 false

这一节描述的是 2026-10-17 的草稿。2026-10-18 的修订替代了它：`goal_complete` 为 true，下面这些未满足的旧检查不再是完成规则。

[REPORT.md](../evidence/p10/20261017T0954Z-fast-tail/REPORT.md) 把四项标成未满足：

- 从第一条 Assignment 到尾部的 nonce 连续性。检查点到尾部的哈希链是连续的。检查点之前，50000..99999 有 132 个明确的洞，100000..149999 有 627 个明确的洞，150000..2074399 没有索引。
- 把每条存在的 Assignment 重放到尾部，并对照一份带有足够状态的已上链结果。语义核对停在 nonce 2074518。独立字节门没有通过。nonce 2075923 没有已上链内存。
- 把池、锁、桥和终端用户钱包分开，并且每个地址都有满足目标的来源。P8 文件是检查点上的表。有一个尾部地址不在其中。`classification_sourced` 为 false。
- 抵押物的资产、持有人、原始数量，以及相对供应的差额。差额是未知。

对这张表而言，行数、12 位小数格式，以及合计与供应的核对，是满足的。

## 6. 交叉验证

### 进入检查点时的逐地址余额

门 A 和门 B 各比较了 7614 个地址。差异都是 0。供应都是 `189487568412204611`。来源：[semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json)。

### 使用计算单元的 9 个高度之后，内存哈希一致

第 3 次尝试的内存哈希等于检查点标签。那一次从目标检查点抄了这 9 个高度，所以它不是独立字节门。来源：[gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json)。

### 含 cron 的回放和只回放 Assignment

现行 0.16.0 的 cron 处理器不写 `Balances`。充值和提现在检查点内部已经关闭。nonce 2074519..2075923 的 Assignment 动作是 703 次 `Transfer`、701 次 `Event`、1 次 `Eval`。充值、铸币、解包、提现和 `BalanceResponse` 的次数都是 0。在检查点上应用一条 cron，余额变化数是 0。来源：[evidence/doc/20261017T1037Z-w-doc/fast-excerpt/cron-handler.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/cron-handler.json)。

只回放这 1405 条 Assignment，和连 cron 一起回放，得到的余额字节相同。两份余额 JSON 的 SHA-256 都是 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`，也就是 P10 manifest 里的哈希。两份内存不同。只回放 Assignment 的内存 SHA-256 是 `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7`。含 cron 的内存 SHA-256 是 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。只回放 Assignment 被标成快速估计，不是正式的内存结果。来源：[exact-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/exact-ledger.json)、[assignment-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json) 和 [provenance.json](../evidence/doc/20261017T1037Z-w-doc/provenance.json)。

这四份 JSON 是写这份说明时复制的字节。快速回放 worker 当时还没有提交它们。这次提交不是合并那个 worker。[provenance.json](../evidence/doc/20261017T1037Z-w-doc/provenance.json) 记下了副本哈希。

### 两条回放的中间内存哈希

含 cron 的回放有一段 480 个项目，流索引 8000 到 8480，与主回放已经写下的 47 个内存哈希全部一致，包括索引 8399 的保存点。该保存点的 SHA-256 是 `78fc3856ea0e4dc6e195463e18a3e6f5810c4c39febcdbc4fc9a0f181a224bfb`，与主回放在 `next_index` 8400 记下的值相同。来源：[verify-480.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/verify-480.json)。主游标上的同一记录是 [evidence/p7/20261017T0942Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0942Z-p7-tail-progress/cursor.json)。

含 cron 的回放结束时，主游标仍是 `next_index` 10400，内存 `b3bd4ffd310420c737ee9140a8c265a386629dae1fe041b917cb3dd2db0980af`。来源：[evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json)，字段 `fast_tail_sha_crosscheck` 为 `not done`。那是当时的进度记录。已经完成的主回放内存与 fast 回放和干净克隆一致：`25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`（`evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`）。见「当前结果」。

### 独立算法复核，以及从零复现

两项后来都完成了。Python 重算与全部 7615 个地址一致（`evidence/p10-indep/20261017T104141Z-w-indep/result.json`）。干净克隆的 canonical 哈希是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`（`evidence/repro/20261017T120218Z-w-repro/result-offset-0.json` 和 `repro/EXPECTED.json`）。它们不再是进行中。

## 7. 已知问题和假设

**五笔 Transfer 的消息体没有作为数据取回。** 语义门回放期间，五笔 `Transfer` 的 GraphQL `data.size` 是 0。`https://arweave.net` 对每一笔都返回 2285 字节的 HTML 壳，SHA-256 都是 `2abbd9f95f88a91c43ddb5e4f84ff9779adca5ce44c775d684b4729ceca333c7`。回放把 `Data` 当作空字符串。保存的文件列在 [evidence/p6/20261017T052333Z-w-eval/manifest.json](../evidence/p6/20261017T052333Z-w-eval/manifest.json)。说明在 [SUMMARY.md](../evidence/p6/20261017T052333Z-w-eval/SUMMARY.md)。id 是：

- [`0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw`](https://arweave.net/0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw)
- [`4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y`](https://arweave.net/4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y)
- [`OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q`](https://arweave.net/OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q)
- [`iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY`](https://arweave.net/iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY)
- [`ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw`](https://arweave.net/ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw)

这并不是说原始数据项是空的。它是说网关没有返回数据，回放用空字符串继续。这五笔在门的窗口里，位于 nonce 2074518 之前。尾部回放从检查点内存起步，所以它们在快照之内，而不是在走向尾部时被重新执行。

**cron 高度的来源。** 独立回放使用当前网关区块时间戳所暗示的高度。这些高度比检查点里保存的 9 个 cron 高度高 1 到 3。尾部回放使用同一个网关来源。把检查点的 9 个高度抄进来可以使门的内存哈希一致，而这次抄录不是独立核对。

**分类时点。** 角色按 nonce 2074518 的表指定。尾部表有 7615 行。11 个原始数量不同。报告保留尾部数量和检查点角色。

**LegacyNet 已停止。** 这项工作不重启它，不启动调度器，也不发布新的 Assignment。

**抵押物数量是未知。** 它不是 0，也不是代币供应。

**信任了什么。**

- 计算单元签名者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`，因为这是 P5 保存响应时公开 CU 端点返回的地址。响应体哈希是 [search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json) 里的 `cu_body_sha256` `5f42df49481944607d1d1dd8d8198684091975a2f1043b8c8cdcf61911a4d398`。选中检查点的 ANS-104 签名在这个所有者下验证通过。另外两个检查点签名者没有被用作回放起点。
- 网关返回的模块、Assignment、消息，以及用作 cron 高度的区块时间戳。两个网关的模块字节一致。模块的 RSA 签名没有核对。
- 2026 年读到的 `gen_hash_chain` 公式，并在已经在场的链接上做了经验核对。没有通过运行 2024 年的调度器二进制来核对。
- 在语义比较之后，把检查点内存当作 nonce 2074518 的状态。独立的字节比较没有通过。

**没有信任什么。** 模型的一句话、空的 `Balances` Output、把 GraphQL 未命中当成从未上链，或者一份只有哈希、没有字节的本地内存镜像。

## 8. 方法和工具

恢复工作由 AI 编码代理完成。Claude（Anthropic）负责协调、审阅证据和纠偏：全量 nonce 索引改为从检查点继续，失败的字节门改为语义余额比较。多个 Grok（xAI，grok-4.7）命令行 worker 并行执行。每个 worker 在自己的 git 分支上写证据。主会话审阅后再合并。worker 不发布领取名单，也不转移抵押物。

已经进入这棵树的证据分支包括：尾部窗口索引、执行器门、处理器和抵押来源预研、持有人分类、被停止的身份检查、Drive 盘点、报告生成器，以及尾部表。快速回放自己的分支没有合并。第 6 节复制了本说明所引用的四份小 JSON，并写明了这一点。

重要结论由一个以上的 worker 或一种以上的方法核对。这次提交里的例子：

- 检查点的签名、签名者、gzip 哈希和标签哈希（P5），然后是 Assignment 与哈希链绑定（尾部索引），然后是余额比较（执行器）。
- 尾部余额合计由各行算出，再与单独读出的 `Total-Supply` 比较。
- 主回放和第二次回放重叠的内存哈希，到流索引 8480 为止 47/47 一致。
- 含 cron 的回放和只回放 Assignment，余额字节相同。

AI 生成的代码和结论，在哈希、独立回放或逐地址比较对上之后才被接受。不因为模型这么说就接受。最终内存哈希和规范复现哈希后来已经对上。仍然开着、而且不是修订后门禁的，是抵押物数量，以及旧的 `classification_sourced`。未识别进程仍列为 unknown。

## 9. 如何复现

从零复现的指南是 [repro/README.md](../repro/README.md)。在仓库根目录运行。它只访问公开网关。早先的“待补”已被替代。

以后的复现必须钉住的内容已经在树里：

- 模块 id 和 SHA-256，见 [evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json)。
- 执行器版本、锁文件哈希、Node 版本和 CU 提交，见 [evidence/p6/20261017T052333Z-w-eval/evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json)。
- 检查点 id `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`，解压后 SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`。
- 尾部 Assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`。
- 消息窗口 2074400..2075923，见 [evidence/p4-tail/20261017T052614Z-w-tail/](../evidence/p4-tail/20261017T052614Z-w-tail/)。
- cron origin `1726163983000`，高度来源为网关区块时间戳；除非这次复现明确是那次非独立的高度抄录实验。

实现其中片段的脚本在 [recovery/](../recovery/) 下。它们不是单一的复现入口。`data/raw/` 下的大文件不在 git 里。manifest 用哈希标明它们。

## 10. 审核者应先看的几点

1. **检查点字节。** 下载 [`ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`](https://arweave.net/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk)，gunzip，确认 SHA-256 为 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`，长度为 428146688。与 [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json) 比较。
2. **签名者。** 确认所有者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk` 下的 ANS-104 签名，并把这个所有者与 `https://cu.ao-testnet.xyz/` 提供的地址比较。保存的响应体哈希在 [search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json)。
3. **检查点到尾部的哈希链。** 用 [recovery/hashchain.py](../recovery/hashchain.py) 对 [evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json](../evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json) 重算 `gen_hash_chain`。预期 1523 次匹配、0 次失败，终点是 `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE`。
4. **字节门确实失败，以及原因。** 读 [evidence/p6/20261017T052333Z-w-eval/gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json) 的第 3 次和第 5 次尝试，以及 [semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json) 里关于 9 个高度的说明。第 3 次匹配，是因为它抄了检查点高度。
5. **余额门。** 确认 7614 个地址、0 个差异、供应 `189487568412204611`，以及门 B 的余额 JSON SHA-256 `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`。不要使用 Output `[]`。
6. **尾部合计。** 用整数累加 [ledger.csv](../evidence/p10/20261017T0954Z-fast-tail/ledger.csv) 的 `raw_balance` 列。预期 `189487568412204611`、7615 行，文件 SHA-256 `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2`（3397765 字节）。更新后的尾部文件是 [evidence/p10/20261017T1047Z-fast-tail/ledger.csv](../evidence/p10/20261017T1047Z-fast-tail/ledger.csv)，SHA-256 `abaf6d70d279c16b5acee1825c25af70bef018a0b37e3a9c525471074ad2722c`（4212717 字节）。不要用浮点。规范哈希不是这两个文件哈希。
7. **洞没有被填成 0。** 132 个缺失 nonce 在 [evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json](../evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json)。627 个在 [evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json](../evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json)。nonce 150000..2074399 没有索引。
8. **分类不是尾部表。** 把第 5 节的 11 行和 [reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json) 比较。确认 `classification_sourced` 为 false，并且 `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` 没有被识别身份。
9. **抵押物未知。** 确认对账文件里 `collateral.status` 为 `unknown`。不要把供应当成抵押物数量。
10. **这不是领取名单。** `publish_claims` 和 `move_collateral` 仍为 false。0954 草稿的 `goal_complete` 为 false。修订后重算的 `goal_complete` 为 true（[evidence/p10/20261017T1954Z-gate-recompute-amended/](../evidence/p10/20261017T1954Z-gate-recompute-amended/)）。最终内存交叉核对已经一致，规范哈希是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。见「当前结果」。

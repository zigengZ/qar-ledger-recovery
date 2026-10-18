> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# qAR 停机余额恢复：执行与交接规范

日期：2026-10-17。依据：`origin/main@12ccc532ae997d8a87de006542875c54c9fa77ba`。
入口仍为 `STATE.md`；目标与权限边界仍为 `GOAL.md`。本文件细化 P2–P10，不重开 P0/P1。

**最终交付是有证据、可复算的逐地址余额表，不是本方案。当前没有余额表、没有已核实总供应，也没有已核实抵押物数量。本次仅完成方案落库；下一次只做 P2。**

## 1. 现状、已关闭路径与阻塞

已读 `README.md`、`GOAL.md`、`STATE.md`、`AGENTS.md`、`evidence/p0-probe.json`、`evidence/p1-tail.json`。基线文件对象与本轮范围见 `evidence/plan-baseline-20261017.json`。

| 项目 | 已知事实 / 证据 | 对工作的约束 |
| --- | --- | --- |
| 进程 | `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`；链上 Name 为 `local-t-w-001`；本地配置称 qAR。P0、GOAL。 | 固定此 id，不按名字换币。12 位小数是交付口径，执行时仍须核对实际合约语义。 |
| 运行身份 | 模块 `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`；调度器 `_GQ33BkPtZrqxA84vM8Zk-N2aO0toNNu_C-l-rawrBA`；aos 2.0.0，ao.TN.1，5-minutes cron。P0。 | 不能拿最新 aos、HyperBEAM 或通用 ERC-20 逻辑代替历史模块。 |
| 创建 | 2024-09-12T18:00:08Z，区块 1505290；owner `6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es`。P0。 | 创建消息、启动数据、历史代码装载均属于恢复输入。 |
| 最终 CU checkpoint | README/STATE 已记录：qAR 与 APUS 均缺失；2026-10-13 Jonny Ringo 表示没有这两份状态。 | “向该持有方再取最终状态”这条路关闭，不循环询问或重做同一查询。本轮沿用仓库记录，并未独立取得原对话附件。 |
| Drive | README 给出的共享目录尚未在本仓库清点。 | 不写成“已经查过目录且没有”。D 只在 STATE 明确开启、取得目录清单后执行；不阻塞主路，不重建 APUS。 |
| Arweave 重放 | P0/P1 证明存在该进程的调度记录；未取得完整账本。 | 完整调度、消息数据与可复现执行，是目前剩下的主路；可行性仍取决于数据完整和执行验证。 |
| 当前阻塞 | 模块字节及 hash 未入证；0 到尾部的连续性未证；消息正文未收齐；执行器未校准；历史快照未知；分类配置未入库；抵押物未知。 | 下一步只补模块取证。不能从“约 207 万 nonce”推导余额，更不能按 Transfer 文本简单加减。 |

“最终 checkpoint 路径关闭”不等于“任何历史快照都不存在”。P5 单独检查已上链历史计算结果/内存；没有合格快照则从启动状态重放。当前没有任何已验证可缩短重放的快照。

## 2. 固定停机点，不把查询时间当停机时间

目标为**最后一条实际推上 Arweave 的 Assignment 执行完成后的状态**。当前采用 P1 的边界：

| 字段 | 固定值 |
| --- | --- |
| process | `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8` |
| epoch / nonce | `0` / `2075923` |
| assignment | `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs` |
| message | `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ` |
| assignment timestamp | `1783145995380` ms = `2026-07-04T06:19:55.380Z` |
| Arweave inclusion block / timestamp | `1951869` / `2026-07-04T06:20:37Z` |
| Hash-Chain | `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE` |
| boundary evidence | `evidence/p1-tail.json` |

P1 记录链尖约 2022620、1951870 及以后未索引到该进程 Assignment、后续 13 个 nonce 及若干哨兵未找到。**这是当前采纳的尾部证据，不是对所有更大 nonce 的穷举，也不是对前缀连续性的证明。** P1 的 `limit` 不能被解读为“三个抽样窗口一定能发现任意更高 nonce”。本轮不重复这些探测。P0/P1 是既有探测摘要，没有完整保存逐次 GraphQL 请求/响应原文；不能事后编造原文填回旧证据。当前边界仍按这份证据冻结，后续新查询才按第 4 节留存原文。

P0 中 Assignment 的 `Block-Height` tag 为 `000001951866`，与入链高度 1951869 不同。二者分别保存；执行环境采用经历史 CU 语义验证的字段，不能以入链高度代替调度环境高度。所有归档同时保留原始 tag、毫秒时间、入链时间，禁止相互覆盖。

除非出现新查询证据，不延伸到 2026-10-17、链尖、停机公告日或额外 cron。发现更高有效调度或 epoch 异常，暂停并写 `tail_review_required`。如需修订边界，新建 `evidence/p1-tail-<run_id>.json`，保存实际查询、变量、响应、来源和旧新边界；经验证后仅更新 STATE/新报告的引用。**不得覆盖原 `evidence/p1-tail.json`；旧产物标记过期，不删除。**

## 3. 余额怎样得到

### 3.1 原程序执行，而非猜一套转账规则

取得并校验原 WASM，以与其 Module-Format、输入/输出编码、内存/计算限制及扩展兼容的执行器运行。候选为 `@permaweb/ao-loader` 加经过核验的 Legacy CU 消息装配逻辑；**候选尚未选定、安装或执行**。P6 固定具体版本、源码 commit、依赖锁文件及环境，aos 2.0.0 不等于 loader 版本。

概念状态转移是 `handle(previous_memory, normalized_message, historical_environment)`；完整 `Memory` 传到下一步。模块可能是 aos 运行时，业务处理器可能来自后续 Eval/启动数据，因此须执行真实初始化、代码更新、mint/burn、锁仓、费用与错误路径。不能只解析 Transfer，不能把请求数或通知数当成功转账数。外部数据/扩展必须固定历史字节，不能偷用当前网络值。

### 3.2 顺序、身份与 cron

调度主序键为 `(process, epoch, nonce)` 的数值序；当前范围仅 epoch 0。不按 GraphQL 返回顺序、消息 txid、区块时间或字符串 nonce 排序。同一消息可被不同 nonce 引用，不因 message id 重复而跳过调度。重复抓到同一 Assignment 只去掉抓取副本；同一 nonce 指向不同有效 Assignment 则停。

原始 Assignment 和其引用的原始消息分别归档，保留有序 tags、owner、签名/身份材料、target、data、排除字段与 base-layer 等实际存在的标记。按历史 CU 规则生成 From/Owner/Timestamp/Block-Height/环境；不能把 From 一律写成钱包 owner，也不能未经核验要求每条被指派消息的原始 Target 必须等于本进程。签名/数据完整性、调度器身份、Hash-Chain 的核验方法与结果必须落盘。

官方 CU 源码有 cron 生成与旧进程启动消息补入逻辑，因此“依 nonce 顺序执行”还须包含历史语义要求的启动/cron 事件。P6 核定 cron 起点、边界、同时间顺序、恢复游标和必要区块元数据；派生事件记录为 `kind=cron`、锚定 nonce、时间及 cron 标识，不伪造 Assignment nonce。最终只执行到尾部 Assignment 完成，不跑尾部之后的 cron。不能因 Action 看似只读就跳过，也不能自行按本机每五分钟补发。

### 3.3 最终读数

在截止点完整状态的**副本**上导出实际余额映射与独立供应字段/经处理器验证的供应定义。离线读取脚本和 hash 入证；不能向网络发送 Eval/Balances 请求，不能将读数探针修改后的内存继续当成历史状态。

保存全量余额键，不仅是已知交易钱包。原始数量全程十进制整数字符串或任意精度整数，禁止 JS Number/浮点转换；人类余额由整数除法和 12 位补零生成。供应不得直接定义成 `sum(balances)` 来制造对账通过；还须对照独立供应状态或可证明的初始化、增发、销毁/其他供应变更账。

## 4. 每个阶段通用的停机与续跑协议

- 一个会话只做 STATE.Next 指定阶段，或其中一个明确区间/批次。工具/脚本尚不存在时，在该阶段实现并测试；本文件里的未来文件名不是“已有可运行程序”。并行仅限同阶段只读任务；STATE 只有一个写入者。
- 证据使用 `evidence/pN/<run_id>/...`，`run_id` 为唯一 UTC 时间加短标识。已有 evidence 一律不改、不删；重试另开 attempt 并引用旧结果。未发生的查询、校验、余额一律不填写成成功。
- 每个查询批次保存 endpoint、UTC 时间、实际 GraphQL/请求体、变量、分页 cursor、HTTP 状态、原始响应文件及 hash；429/超时/GraphQL errors 不等于空结果。采用有限重试（默认最多 3 次，指数退避）；耗尽就写失败，不无限重试。
- 大文件在 `data/raw/`，SQLite 同样不提交。manifest 至少有文件路径、字节数、SHA-256、来源/下载方法、范围、记录数、前后边界、验证状态和重建方法。哈希是内容校验，不是可下载地址。
- 分页与执行都设置请求数/事件数、内存、磁盘与运行预算；每页/小批原子落盘。`.part` 文件不算完成；先写 bytes、flush/校验，再提交 manifest，最后推进 STATE。预算耗尽是 `paused`，硬失败是 `blocked`，均保留当前阶段。
- STATE 交接最少包含：phase、status、active_range、last_complete_range、next_nonce、last_durable_execution_cursor（含 cron 子游标）、snapshot path/hash、manifest path/hash、query cursor、runtime/config hashes、错误与唯一 Next。尚未知用 `unknown` 或 `null`，不填 0。
- 换模型先读 STATE，再读该阶段要求的证据。换机器先核验原始字节/快照是否可取得。链上字节可以重下载；**本地生成的内存快照不能只凭 hash 重下载**。须有已授权私有持久化位置及可恢复副本；没有时明确写出只能从可取得的较早锚点重算。不额外向公开服务上传数据。
- 恢复前核对进程、尾部、模块 hash、执行器锁文件、前一快照 hash 和输入根。不同配置不得混接快照。仅从最后已持久化且验证通过的游标继续；绝不把“请求已发出”当“处理已完成”。
- 任何必需输入缺失、nonce 冲突/未解决缺口、状态不一致或对账失败，写 `evidence/pN/<run_id>/STOP.md` 和 `failure.json`：最后好点、缺失范围/文件、实际差额、可复现失败、恢复条件。不得推进阶段、补零、发布领取名单或转移抵押物。

## 5. 从当前状态到余额表的阶段

### P2 — 模块取证；下一会话只做此项

**输入：** STATE、GOAL 的 P2、P0 的 module id、本文件第 4 节和本节。无需重查进程身份或 P1 尾部。

**动作：** 获取该 module 的交易/数据项元数据及完整原始字节，保存原始 tags；记录数据项/交易验证材料、data size、实际文件长度、SHA-256，静态检查 WASM 头。核对 Module-Format、Input-Encoding、Output-Encoding、Memory-Limit、Compute-Limit、Extensions 等实际 tags；未出现的字段记 missing，不猜默认值。保留下载响应头与来源；通过链上完整性材料或独立来源一致性核验字节。SHA-256 不得冒充 Arweave txid。

**输出：** `data/raw/modules/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0.wasm`；`data/raw/p2/<run_id>/` 原始响应；`evidence/p2/<run_id>/module.json` 和 `fetch-manifest.json`。如失败，产出 `failure.json`/`STOP.md`。

**完成标准：** 可重新取得同一份完整字节，长度/hash/身份检查一致，tags 有来源；证据写明 `executed=false`。更新 STATE.Next 为 P3 后停止，**不加载执行器、不运行模块、不启动 P3**。

**失败停止：** 拉取失败、HTML 错误页、截断、hash/身份冲突都不能算模块取得；保留可用下载游标和响应，下次仍 P2。运行参数缺少但字节有效时在 manifest 明确列出，P6 解决前不能执行。

### P3 — 小样本连续性与索引方法

**输入：** P0/P1、P2 manifest。复用 P1 已有 nonce 2 及尾部四项记录，不为了重复结论再做原探测。

**动作：** 检查起点，并组合三个 20-nonce 窗口：`0..19`、`1037960..1037979`、`2075904..2075923`。已记录项复用证据，新增查询只补未覆盖项；如为取得原始数据而重新下载，单列用途，不能记成新的尾部证明。判明 0/1、Process 启动项的历史协议含义；不能因为只见到 2 就把起点设为 2。

测试小批 exact Nonce tags 查询或有完整分页的区块窗口方案，记录成本、限制、去重与恢复行为。GraphQL tags 不预设支持数值区间；禁止一次塞入 50,000 个值。可按入链高度抓取，但最后必须按数值 nonce 归并；同一高度的记录必须翻页完毕，不能按最后区块加一跳页。

**输出：** `evidence/p3/<run_id>/sample.json`、`gaps.json`、`index-method.json`；查询及原始页 manifest。方法文件写可复用的真实请求模板、每批大小、分页逻辑、预算、下个 cursor 和第一段逻辑区间。

**完成标准：** 每个样本预期 nonce 都有唯一匹配或明确缺失；启动编号规则有证据；选出的索引方法可恢复且不会漏同块记录。样本通过只叫 `sample_passed`，不能叫全程连续。默认下一逻辑区间 `0..49999`；协议证明有特殊起始项时在 coverage manifest 明确建模，不能默默丢弃 0/1。

**失败停止：** 样本缺口须精确 nonce 查询、替代索引/原始 bundle 取证，记录 `not_indexed`、`temporarily_unavailable`、`unresolved`，不能把网关未找到直接等同从未上链。冲突/必需起点无法证明时 STATE 留 P3。

### P4 — 全量索引；一个会话一个逻辑区间

**输入：** P3 index-method、固定尾部、上段 manifest/cursor。默认每段最多 50,000 nonce，网关限制时减小。

**动作：** 先建 Assignment 清单，再为每项建立 message id 引用；原始消息正文可在本阶段同步归档，或在 P6/P7 对应区间执行前按 manifest 补齐，缺正文不得执行。保存原始 Assignment、签名/身份和 Hash-Chain 字段。账本索引至少为 `epoch,nonce,assignment_id,message_id,timestamp_ms,assignment_block_height,inclusion_height,hash_chain,source_id`。

对每段用预期 nonce 集合减去实际唯一 nonce 集合生成缺口区间；另存重复项、冲突、顺序异常。跨段检查 `previous_end + 1 == next_start` 与前后 Hash-Chain（按核验算法，不只比较字段存在）。先记录缺口再补查，所有尝试另写 evidence；缺口未解决不得把该段标记 complete，也不越过缺口启动后段正式重放。

**输出：** `data/raw/p4/<range>/<run_id>/`（页、Assignment、message manifest、可重建索引）；`evidence/p4/<run_id>/range-manifest.json`、`gaps.json`、`conflicts.json`。最后一段另输出 `coverage.json` 汇总全部段 hash、已验证总数、首尾、未解决项。

**完成标准：** 单段所有预期 nonce 有唯一有效调度、分页闭合、缺口/冲突为零、跨段边界通过；成功只推进到下一 P4 段。没有可用内存快照、只能从创世重放时，全部区间完成才进 P5。若编号从 0 开始，总数应为 **2,075,924**（不是已下载数量）；任何特殊启动编号必须有协议证据和显式覆盖项。

**快照改序（2026-10-17）：** 官方 LegacyNet CU 若在链上发布了该 process 的 Type=Checkpoint 完整内存快照，并且本仓库复现了签名者、签名和 gunzip 后的 SHA-256，则 P5 提前于剩余 P4 区间执行。那条规则只把“没有快照、从创世重放”限制为先做完全部区间。P1 尾部边界不变。已记录的缺口（含 50000..99999 的 132 个和 100000..149999 的 627 个）保留为显式缺失，不删除，也不再为它们打开 150000 及以后的正向区间。P6 未通过快照对快照的内存校验前，该快照还不是生效的回放起点。

**失败停止：** 留在当前区间，从最后已确认页/子批续跑；前段不重抓。不以 `max(nonce)` 或总行数相等替代集合连续性。发现高于当前尾部的有效记录进入第 2 节边界复核，不静默扩表。

### P5 — 一次有范围的历史结果/快照搜索

**输入：** 完整 coverage、模块 manifest、官方 CU 历史 checkpoint/结果格式及实际检索字段。

**动作：** 先用源码及样本确定查询字段，不凭猜测的 `Type=Result` 宣布不存在。检索该 process 的已上链 checkpoint、计算结果、余额/供应输出；保存请求模板、网关、查找范围、分页完成状态。每个会话只做 STATE 指定的一批，预算耗尽继续 P5。预设的搜索范围查完即选择起点，不无限寻找；可选来源不可达时说明局限并走创世重放，不用它伪造“没有任何快照”。

候选分为：①可恢复的完整状态；②Balances/Total-Supply 等校验输出；③不足以校验的普通输出。必须绑定 process、module、执行位置（Assignment/nonce 及 cron 子位置）、字节 hash、格式、发布者/签名与可信来源。任意人上传带 Process tag 的文件不自动可信。尾部之后的状态不可倒推使用。

**仅在完整执行状态、来源与位置验证通过，并有恢复/重叠重放验证方案时，才可将候选送 P6。余额 JSON 不含处理器、闭包、供应等状态，默认只作校验；不能直接把它塞进一个新 token 程序继续算。** 这是 GOAL P5 中“snapshot becomes replay start”的必要安全条件；P6 未验证前起点不生效。

**输出：** `evidence/p5/<run_id>/search-manifest.json`、`candidates.json`、`replay-start.json`，原始对象置 `data/raw/p5/`。无可用快照明确写 `start=genesis`、查询覆盖与局限，而非伪造 memory。

**完成标准：** 起点决策有可审计证据，所有可比较输出有明确对应的历史位置；有快照仍保留完整调度 coverage 与起点前的来源/验证边界。P6 对候选拒绝后回到创世方案，不重开最终 CU checkpoint 路径。

**失败停止：** 搜索必需分页未完成则留 P5；候选缺字节/不可信则拒绝使用。可选快照缺失不阻止完整创世重放；创世必需输入缺失才是硬阻塞。

### P6 — 选定并校准执行器；只做一个短验证区间

**输入：** P2 模块、P4 调度/启动/消息、P5 起点与校验输出；原始 tags、历史环境及依赖字节。

**动作：** 在私有离线沙箱建立执行器，锁定 loader、Legacy CU 消息规范化/启动/cron 相关源码版本、Node/平台、配置与依赖 hash。验证模块支持、历史限制、错误状态提交/回滚语义、boot/Eval 代码与外部数据读取。不装“latest”后直接全跑；不因计算失败自行增加 gas 让失败交易变成功。

STATE 指定一个短前缀或候选快照后缀（首次上限 1,000 个 Assignment，派生事件另计），选择能覆盖真实初始化/状态变更的范围。匹配 P5 中对应的已上链结果，逐字段记录原值/重放值/差异。仅有余额子集的结果只能校验子集，不能声称全状态已匹配。无可比较结果则写 `external_oracle=unavailable` 及检索证据，执行两次独立启动、连续执行与中断恢复等一致性测试；不得写成“已匹配链上结果”。如短区间不足以验证，留 P6 并在 Next 明确下一验证范围。

验证 cron/启动事件插入与暂停恢复不重算或漏算；验证同消息多 Assignment、错误/拒绝消息、整数精度与只读导出。验证候选内存恢复；失败则弃用该加速起点，以创世短前缀重新校准。所有输出 Messages/Spawns/Assignments 只存本地，**禁止签名、广播、提交新调度或启动在线 MU/SU**。

**输出：** 执行代码与依赖锁文件、`evidence/p6/<run_id>/runtime.json`、`input-manifest.json`、`conformance.json`、`benchmark.json`、`state-schema.json`；前缀/后缀快照及其 manifest。代码路径和可实际执行的命令写进 STATE。state-schema 写清余额/供应读取位置及 handler 来源。

**完成标准：** 该区间输入完备、执行可复现、可恢复、所有可用校验一致；无外部 oracle 的限制明确保留。冻结生产重放参数与区间大小，不把短测试当成全账本通过。即使已准备好环境，也不能在同一会话启动 P7。

**失败停止：** 不支持的格式/扩展、缺 boot/外部数据、历史环境不明、cron 或错误语义未定、任何可用结果不一致，都停在 P6；保存第一个失败位置及前一好快照。不得换用近似账本逻辑继续。

### P7 — 分段重放直到固定尾部；逐段持久化

**输入：** 已冻结执行器、起点/上一完整快照、coverage、当前区间全量消息与历史依赖字节。

**动作：** P6 基准决定本段大小，逻辑段不超过 50,000 Assignment；段内至少每 1,000 Assignment 或 60 秒（先到者）持久化一次，资源较紧时缩小。正式边界要记录派生 cron 子游标，不能只记一个 nonce。每个会话只做一个 STATE 指定段；预算用尽允许在段内暂停，不自动启动下一段。

逐项按第 3 节执行；保留输入 hash、结果/错误、账本与供应的状态变更审计信息。输入中的真实 handler 拒绝按历史语义记录；执行器崩溃、无法确定的错误不可当作成功 no-op。读取已有校验点就立即比对，首次不一致即停。

**输出：** `data/raw/p7/<range>/<run_id>/memory.bin` 与结果日志/状态摘要；`evidence/p7/<run_id>/replay-manifest.json`、`checkpoint-manifest.json`、`checks.json`；私有 `reports/partial/<run_id>/balances.csv`。中间 CSV 必须标注其实际 nonce 与 `not_for_claims`，不能命名为最终领取名单。

**完成标准：** 本段全部调度及必要派生事件被精确处理一次，输入完整，输出/快照 hash 验证和恢复测试通过；记录实际事件数、最后持久化位置和下一 nonce。只有最后段到达指定 Assignment 完成时，生成 `evidence/p7/<run_id>/terminal-state.json`（含快照、余额导出与供应来源 hash）。

**失败停止：** 缺消息/环境、OOM、磁盘不足、校验分歧或快照损坏即停；以已验证快照重跑未提交子段。没有可靠持久化就不能声称该段完成。尾部本身不能被执行时，不得退到较早 nonce 冒称停机账本。

### P8 — 完整余额导出与地址分层

**输入：** P7 截止状态、state-schema、完整余额键；GOAL 所指本地 qAR/DEX 配置及其原文件/commit；链上 pool/lock/bridge 身份与关系证据。

**动作：** 导出全部地址，再单独做分类。每行有独立的余额来源和地址/分类来源；类别为 `end_user`、`pool`、`lock`、`bridge`、`treasury`、`burn`、`other_contract`、`unknown`。没有标签不等于最终用户；不能只靠名字或地址外形判断。种子配置在基线树中不存在，应明确记录所缺文件，不假装已经读取。

池、锁仓、桥地址保留其 qAR 余额原行。底层用户/LP 份额另表，需同一适用截止点的 LP 供应、份额、锁仓受益人和嵌套关系证据，未恢复则 `unresolved`；不按今天持仓或交易量分摊。**地址账本中的池余额不能与其底层权益再相加，不能直接作为池用户的领取份额。**

**输出：** `reports/<run_id>/balances-all.csv`、`balances-end-users.csv`、`balances-contracts.csv`、`balances-unclassified.csv`；`evidence/p8/<run_id>/address-registry.csv`、`sources.jsonl`、`unresolved.json`。各分类表互斥，其并集等于总表；总表是唯一供应汇总输入。另建的受益权研究表不计入余额总和。

**完成标准：** 所有余额键恰好一行、原始数量可精确还原，三类余额分表不重不漏；每地址都有可追溯来源。必要分类无法验证时保留候选成果，但阶段为 blocked，不能将 unknown 全归用户以通过验收。

**失败停止：** 缺配置时在 STATE 写明需要的是“曾把该 process id 标成 qAR 的原始交易配置，以及其中引用的池/锁仓/桥映射”；缺份额状态就保持不可分配。缺行/缺来源写 unresolved，不写 0。

### P9 — 抵押物资产、持有人与原始数量

**输入：** 经重放确认的初始化/升级、mint/burn/赎回处理器与相关入出站消息；明确资产网络、资产 id、持有人证据和可验证状态。

**动作：** 从处理器与实际往来确定底层资产及兑换比率，不从 qAR ticker 推断 AR/wAR。对每个持有人记录 network、asset id、decimals、holder、raw amount、观测时点（区块/tx/nonce）、来源及证明。区别托管总余额和确实属于 qAR、未被其他负债占用的可用抵押物。

分别记录尾部适用时点与现在仍持有数量；两者时间不同则给出期间进出账的逐笔 roll-forward，不能将今日钱包余额直接与 7 月供应相减。异步已锁未铸、已烧未兑、待处理/失败赎回分别列示，有来源才能调整，并防止重复计入。历史状态取不到而只有现值时明确 `historical_amount=unknown`，不能补造过去数。

**输出：** `reports/<run_id>/collateral.csv`、`collateral-movements.csv`、`collateral-gaps.csv`；`evidence/p9/<run_id>/backing-rules.json`、`sources.jsonl`、`unresolved.json`，对应原始消息/资产状态 manifest。

**完成标准：** 资产、持有人、原始量、时点、用途归属均有证据；兑换规则能把 qAR 原始供应转换成对应资产的所需原始数量，用精确整数/有理数计算。每资产独立对账，不把不同币原始单位直接相加或用市价掩盖差额。

**失败停止：** 任一数量/归属/比率无法确认时差额为 `unknown` 并写缺失项，而非 0；发现非零差额必须单列真实数字并停，不构造“调整用户”平账，也不转移抵押物。

### P10 — 验收包，而不是领取名单

**输入：** P1 边界、P4 全覆盖、P2/P6 执行身份、P7 最终状态、P8 全表与分类、P9 资产/数量及差额。

**输出：** `reports/<run_id>/RECONCILIATION.md`、`validation.json`、最终 `balances-all.csv` 与分层表、`collateral.csv`、`collateral-gaps.csv`、`manifest.json`（所有交付文件 SHA-256 与来源指针）。失败则报告标题为 `BLOCKED — NOT A CLAIM LIST`；不能制造一个空白或全零 final.csv。

**完成标准：** 第 6 节验收门禁全部符合，验证程序、输入 hash 与运行结果可复算；所有已取得外部校验相符，无外部 oracle 的情况如实披露，不伪造匹配。可被接受的是私有余额研究账本，不是对外领取授权。之后的领取设计/抵押物处置不在本仓库任务内。

**失败停止：** 保存实际总数、原始供应、原始合计、逐资产差额和失败规则；STATE 指回第一个不能满足的阶段/区间。不得只写“基本一致”，不得四舍五入通过，不能在对不上时公布任何领取名单。

## 6. 交付数据契约与必须通过的门禁

### 余额表

`process_id,cutoff_epoch,cutoff_nonce,address,raw_balance,human_balance,address_kind,balance_source_id,address_source_id`

`raw_balance` 是不带指数、逗号或小数点的非负整数字符串；`human_balance` 必须保留恰好 12 位小数，可无损反算 raw。只允许状态确证的 0；对预期但没有证据的行，在 unresolved 单独记录，不给余额字段填 0。`balance_source_id` 指向固定尾部快照 hash、状态键、导出脚本与执行链；`address_source_id` 指向地址出现/分类的具体交易、配置文件 commit/行号或已归档证据。所有 source id 必须在 sources 中可解析。

### 数量检查

- `ledger_delta_raw = sum(all.raw_balance) - independently_established_total_supply_raw`，必须精确为 0。供应未知、为非整数、来源循环或数值不等均失败。
- 分类表地址集合互斥且覆盖总表，分类合计等于全表合计；池/锁/桥余额不能丢掉，也不能展开后双计。
- 每资产在相同时点和明确兑换单位下计算 `collateral_delta_raw = eligible_held_raw - required_backing_raw`，正号表示多余、负号表示短缺。来源未齐时写 unknown，不计算伪精确值；存在非零或未解决差额即停止，不对外分配。

### 完成判定

`tail_fixed && schedule_covered && inputs_complete && runtime_reproducible && available_checks_match && ledger_complete && ledger_delta_zero && classification_sourced && collateral_sourced && collateral_reconciled`

任一为 false/unknown，`goal_complete=false`。研究中间产物可私有提交，但不能标成通过验收的余额表。无论此判定是否为 true，当前任务的 `publish_claims=false`、`move_collateral=false` 始终不变。

上面这一段完成判定 superseded 2026-10-18。它保留作对照，不再决定 `goal_complete`。`collateral_sourced` 和 `collateral_reconciled` 改为报告字段，不进入判定。抵押物仍写入报告：原生 AR、尾部区块上托管钱包的余额、其余已混同、可分离数量为 null。不把 null 写成 0，也不把差额写成 0。

新判定：

`tail_fixed && checkpoint_verified && tail_inputs_complete && runtime_reproducible && available_checks_match && independent_agreement && ledger_complete && ledger_delta_zero && classification_disclosed`

`checkpoint_verified` 替代从第一条已推送 Assignment 起的连续性。`tail_inputs_complete` 只要求检查点 nonce 的下一条到尾部都在，且哈希链 1523/1523。`classification_disclosed` 替代 `classification_sourced`：池、锁、桥写明来源；未识别进程列为 unknown；`wallet` 表示“不是进程”，不是已识别的所有者。`independent_agreement` 要求至少两种独立方法得到同一个 canonical 余额哈希。

新判定全部为真时，`goal_complete=true`，含义是账本可以公开接受审核。它不是领取名单，也不是分配指令。`publish_claims=false` 和 `move_collateral=false` 不变。已知局限（检查点信任假设、抵押物不对账）不阻塞完成。P11 已于 2026-10-18 撤销（见 GOAL.md Amendment 2026-10-18b）：本仓库公开之后，任何人都可以提 issue，没有固定审核期。余额一旦改变，canonical 哈希随之改变，并记录在 STATE.md。分配决定由抵押物持有人在本仓库之外作出。

## 7. Git 提交与持久交接

每次写入前读取最新 main；正常 Git 环境使用 `git fetch origin` 后 `git pull --ff-only origin main`。若 Git 传输不可用，但已授权 GitHub API 可用，则读取 main ref、固定 SHA 下文件和树，以该 SHA 作新提交的唯一父提交，使用非强制 ref 更新并校验 expected head，记录这是 API 同步而非谎称 git pull 成功。

提交前再次确认 repo full_name 为 `zigengZ/qar-ledger-recovery` 且 visibility 为 `private`。审阅只含本阶段的预期改动；旧 evidence 的 blob SHA 必须不变。更新时若 main 已前进，读取新 head、协调 STATE，不覆盖他人进度、不 force-push。权限/保护规则拒绝 main 时，在同一私有仓库建分支并开向 main 的 PR；不创建公开 fork。若分支/PR 也被拒绝，明确报告失败并保留可应用补丁，不能声称已推送。

本轮提交仅新增本方案及基线取证记录、更新 STATE；不改 README/GOAL/AGENTS，不修改 P0/P1，不执行 P2，不生成余额或领取文件。推送后回读 ref/文件列表并确认旧证据仍在，再结束会话。

## 8. 技术参考的范围

仓库事实以基线六文件为准。以下是 2026-10-17 阅读的官方实现参考，**不是已验证适用于本进程的历史 runtime 版本**；P6 必须固定与验证具体 commit，不能随 main 漂移：

- `permaweb/ao`, `loader/README.md`：WASM loader、handle、Memory 与输入环境接口。<https://github.com/permaweb/ao/blob/main/loader/README.md>
- `permaweb/ao`, `servers/cu/src/domain/lib/loadMessages.js`：`parseCrons`、`cronMessagesBetweenWith`、`maybePrependProcessMessage`。<https://github.com/permaweb/ao/blob/main/servers/cu/src/domain/lib/loadMessages.js>

这些参考说明需要验证哪些执行语义，不构成本进程已成功重放、存在历史快照或能够领取的证据。

> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# qAR 账本网站

静态站点，放在本仓库的 `web/`。查询尾部 nonce 2075923 的公开余额。按 2026-10-18 的检查点修订，`goal_complete` 为 true：账本可以公开接受审核。这不是领取名单，也不是分配指令。

## 三页

导航是查询、全部余额、验证与方法。旧路由 `#/overview` 和 `#/lookup` 转到 `#/`，`#/method` 转到 `#/verify`。

- 查询是首页。地址框在最上面，回车即查，结果仍写在 `?a=`。结果是卡片：可读余额去掉末尾的 0，原始整数用等宽字体并可复制，另有排名、占比和分类。账本里没有的地址写「账本里没有这个地址」，不显示成 0。账本里的 0 写「余额为 0」。输入框下是总供应、持有地址、非零地址、账本时点。可信度横条链到验证页。
- 全部余额是一张表，手机上是卡片。可搜索、按钱包 / 池子 / 锁仓 / 进程 / 未知筛选、排序、分页。表头可下载 CSV 和 canonical JSON。第 1 名沿用报告原文：单个地址，分类为钱包，身份没有核实。余额分布图收在折叠里。
- 验证页上方是最终内存 sha256、canonical 余额哈希，以及浏览器 SubtleCrypto 现场重算。五种独立计算各一行，cron 高度 ±3 另起一行。自己验证是 README 里的 3 行 Python，外加 `./repro/run.sh`。已知局限是检查点信任假设、抵押物未对账、钱包标签只表示不是进程。完整方法文档和数据状态表默认折叠。Markdown 仍经 DOMPurify 3.4.17。

页头标题是 qAR Balances。页脚是生成时间、canonical 余额哈希、GitHub「源码与证据」，以及「这不是领取名单」。中英文都有。

## 这次的数据

`npm run build` 重跑了 `scripts/build-data.mjs`。主回放状态改为吻合：`cursor.json` 仍写着 not done，但 `README.md` 的 `MAIN_REPLAY_SHA: match` 与 `evidence/p7/20261017T1718Z-p7-replay-read/replay.json` 的内存 sha256 一致，都是 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。manifest 里的账本路径改记较晚的 `evidence/p10/20261017T1720Z-p10-after-p9/ledger.csv`。`public/data/ledger.json` 的行没有变。canonical 余额哈希仍是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。

## 功能

- 供应量 `189,487.568412204611` qAR。7615 个地址，2239 个非零。分类来自尾部账本，页面上收成钱包、池子、锁仓、进程、未知。借贷并进进程，无效 id 并进未知。
- 地址查询接受逗号、空白和换行。43 位 base64url 以外的输入标成「地址格式无效」。账本里没有的地址不显示成 0。
- 全量 7615 行，每页 50 行。完整 CSV 同时给 raw 和 12 位小数。canonical JSON 只留非零余额。
- 五种计算都是一致：精确 WASM 回放、只回放 assignment、不跑 WASM 的 Python 重算、干净克隆从公开网关从零复现、主会话逐条复制内存的慢速回放。cron 高度 ±3 不改变 canonical 余额哈希。验证页会用浏览器再算一次。
- 已知局限：检查点由 LegacyNet CU 签名，不能从创世独立重算；抵押物只作为事实，可分离数量是 null；`wallet` 表示不是进程，不是已核实身份。公开后欢迎提 issue。

没有钱包页，也没有钱包持仓列表。

中文是默认语言。深色和浅色跟随系统，也可以手动切换。主题脚本是 `theme-init.js`，不是内联脚本。

## 这次用的数据

生成时间 `2026-10-17T19:49:38.681Z`。余额合计等于总供应 `189487568412204611`。按 canonical 规则（地址排序、只留非零、raw 为字符串、紧凑 JSON 加换行）算出的 sha256 是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。

| 用途 | 路径 |
| --- | --- |
| 尾部账本 | `evidence/p10/20261017T1720Z-p10-after-p9/ledger.csv` |
| 尾部分类 | `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json` |
| 独立重算 | `evidence/p10-indep/20261017T104141Z-w-indep/result.json` |
| 从零复现 | `evidence/repro/20261017T120218Z-w-repro/` 与 `repro/EXPECTED.json` |
| 说明 | `docs/RECOVERY.md`、`docs/RECOVERY.zh.md` |

`data/raw` 只做交叉校验，不入库。这次本机的 `balances.json` 和账本逐地址一致。站点页面不写本机路径。

## 构建

```bash
cd web
npm run build
```

需要 Node.js v22.22.0，并且 `node` 在 `PATH` 上。

`npm run build` 会生成 `public/data/*.json`、跑测试、做类型检查，再打 `dist/`。余额合计不等于总供应，或 canonical 哈希对不上，构建失败。发布前还会拒绝本机绝对路径、IP、邮箱和本机主机名。

预览只绑回环地址，不对外：

```bash
npx vite preview --host 127.0.0.1 --port 4789
```

`node_modules/` 和 `dist/` 不提交。`public/data` 要提交。首屏脚本和样式是外部文件。线上 CSP 用 `script-src 'self'`、`style-src 'self' 'unsafe-inline'`、`img-src 'self' data:`、`connect-src 'self'`。站点代码不调用 eval 或 new Function。

## 怎么刷新

证据、`docs/RECOVERY.md`、`docs/RECOVERY.zh.md` 或 `repro/EXPECTED.json` 更新后，在 `web/` 再跑一次 `npm run build`。

## 已知限制

- 哈希链只覆盖检查点到尾部。从第一条已推送 assignment 到尾部的连续性还不满足。
- 两个快照之间逐地址余额差异为 0。字节门没有通过。
- 只回放 assignment 的余额和精确回放一致。两份内存 sha256 不同。
- 主回放的最终内存 sha 已与精确回放和干净克隆一致。完整 safe 模式没有跑。
- 抵押资产是原生 AR。没有单一持有人，可分离的原始数量是 null。原托管钱包在尾部区块的余额是 978114007970 winston（约 0.978 AR），其余已混入其他钱包。未完成的 Unwrap 和 Deposit 都是 0 行，已完成合计不是抵押余额。
- 从零复现没有跑完整 safe 模式。cron 高度 ±3 不改变 canonical 余额哈希。
- 有 5 笔 Transfer 的 Data 是空字节。数量在 Quantity 标签里。它们的 nonce 在检查点之前。
- 钱包角色不是已核实身份。

# w-pubscan

公开导出前审查。先只读对照了已经做好的那份公开副本（1290 个文件，分支 master，作者 Zigza）。修复在 `worker/w-pubscan`。复验用 `audit/make-public-export.sh` 写到一个临时目录，确认后已删除。最终导出 1291 个文件，默认分支 `main`，`audit/scan.sh --strict` 的 must-fix 是 0。导出字节与工作区一致，导出脚本没有再改写路径。

## 1. 身份泄露

私有词表（主机名、ssh 别名、用户名、私有项目名、screen id、IP）逐个不区分大小写查过。这些词在最终导出里是 0。

留下的命中不是主机名：

- `zigza` 出现在 `https://qar-balances.zigza.xyz`。编码名 `zigzag` 含有同样的字母，那是 Avro 整数编码，不是主机名。
- `hyperbeam` 只有 `RECOVERY_PLAN.md` 里的公开协议名 HyperBEAM，句子是不要用它代替历史模块。
- `m8` 落在交易 id 内部（`_m8`、`-M8`），不是主机名。
- `inbox` 作为 AO 进程标签留在 `vendor/drive-cu` 的测试夹具里。私有 inbox 路径已改成 `private-config/`。

正则：没有邮箱，没有本机根目录、主目录或盘符路径，没有 screen、tmux、ssh 目录或 status 完成标记。ssh 别名已从 `STATE.md` 去掉。一处文档化的测试 IP 只在网站清洗夹具里。`scan.sh` 的 17 条 should-fix 都是允许的 GitHub 登录名 `zigengZ`。

## 2. 占位符后面的目录

`<local-root>/`、`<worktrees>/`、`<home>/` 后面没有目录名。gitignored 的原始下载仍写成 `<repo>/data/raw/...`。worker 目录和 inbox 路径改成了仓库相对路径或 `private-config/`。

## 3. 持有人钱包

14 个地址仍作为账本行、转账记录和消息的 `owner_address` 出现。`owner_address` 是 ANS-104 签名者字段，不是「某人自己的钱包」。没有把它们标成个人名单，也没有持仓文件名或间接持仓名单。`STATE.md` 里原先的个人名单说法已改写。

## 4. 凭据

没有 PEM、JWK 私钥、助记词、`ghp_`、`github_pat_`、`AKIA`、`xox`、`sk-`、Bearer、basic auth、`.env` 密钥、Cloudflare 令牌、nginx/systemd 配置、证书、webhook、ssh 公钥或 deploy key。除 `qar-balances.zigza.xyz` 外没有别的 `*.zigza.xyz`。

二进制文件是 `vendor/drive-cu` 的两份测试 wasm（约 291 KB）。大于 5MB 的是持有人分类、抵押物流水、P5 候选检查点 JSON，都小于 100MB。没有超过 100MB 的文件。

## 5. 哈希链

登记在 manifest、reconciliation、SUMMARY、`audit/REDACTIONS.md`、`repro/EXPECTED.json` 和 `web/public/data/manifest.json` 里、并且目标在导出树中的 `(路径, sha256[, 字节数])`，复验一致。最终导出上在树内的核对是 249 条一致、0 条不一致。`data/raw/` 的登记指向 gitignore 的下载，树里没有这些文件，这是预期的。

原先对不上的原因是导出把绝对路径换成占位符。工作区先做了同样的替换，并更新了清单和 `audit/REDACTIONS.md`。0954、1047、1720 三份 `ledger.csv` 仍是 7615 行，原始余额合计仍是 `189487568412204611`。0906 持有人文件仍是 7614 条，1031 仍是 7615 条。

## 6. README

`README.md`、`README.zh.md`、`docs/PUBLICATION.md` 的相对链接都存在。英文 README 没有中文，也没有 “pending” 或 “Another session is writing this file”。已去掉「规范哈希仍待补」和「主回放尚未交叉核对」。中英文都写明主回放已经对上。

在导出根目录跑 README 的 3 行 Python，输出是 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。

## 7. 工作日志

`STATE.md`、`GOAL.md`、`STOP.md`、`RECOVERY_PLAN.md`、`AGENTS.md`、`SUMMARY.md`、`web/SUMMARY.md` 和各 evidence `SUMMARY.md` 开头加了「这是工作日志」。`docs/RECOVERY.md` 与 `docs/RECOVERY.zh.md` 增加了当前结果，不再把规范哈希写成待补，也不再把主回放写成进行中。`STATE.md` 里「the user」作为决定人的说法改成了 later decision。

## 8. 能否运行

在最终导出目录里：

- `python3 -m unittest discover -s tests -t .`：202 项，2 项跳过，通过。跳过的是缺少 gitignore 的 `data/raw/p7/process-tx.json`，以及原有的一项跳过。
- 全部 `.sh` 的 `bash -n` 通过。
- `vendor/` 和 `node_modules/` 以外的 `.mjs` / `.js`，`node --check` 通过。
- `cd web && npm ci --ignore-scripts && npm test && npm run build` 通过。Node 是 v22.22.0。没有 `origin` 时构建会打印 `No such remote 'origin'`，然后使用默认仓库 slug，构建仍然成功。`raw` 交叉校验在没有 `data/raw` 时记为 absent。
- `repro/run.sh` 和 `repro/README.md` 从仓库根目录启动，没有占位符路径。没有真的跑下载。

`recovery/p6/replay.mjs` 只在作为入口运行时才加载 `@permaweb/ao-loader`。cron 单测因此不需要先安装那个包。

## 9. 其他

README 写明主回放、fast 回放和干净克隆的内存 sha256 一致，也写了检查点签名者这一信任假设。`LICENSE` 是 MIT，`vendor/drive-cu` 保持 BUSL-1.1。没有 `.github`。导出脚本改成 `git init -b main`，与文档里的 `blob/main` 链接一致。`evidence/p4/` 的 120 个空洞目录已在中英文 README 各用一句话说明：每个目录是一次已关闭且为空的精确查询，不是缺失的账本行。

`goal_complete` 仍是 false。可分离抵押物原始数额仍是 null。`classification_sourced` 仍是 false。从创世起的 nonce 覆盖仍不完整。这些是账本结论，不是公开阻塞项。

## 修了什么

- 证据和脚本里的本机绝对路径改成导出占位符或仓库相对路径。
- 清单、SUMMARY 和 `audit/REDACTIONS.md` 的 sha256 与字节数改成当前文件。
- README、RECOVERY、网站数据和构建脚本改成主回放已经完成。
- 去掉 ssh 别名、私有主机名和个人钱包名单字样。
- 网站脚本用 `node`，不再写死本机安装路径。

## 剩下什么

- `data/raw/` 不在仓库里，对应的 sha256 要在重新下载后核对。
- 真正公开时设置 `PUBLIC_GIT_NAME` 和 `PUBLIC_GIT_EMAIL`。脚本默认作者是 `qar-ledger`，不是已有公开副本里的 Zigza。
- 不要把私有分支历史直接推出去。公开用压缩导出。

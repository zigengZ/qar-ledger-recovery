> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# w-pub 公开前清理

`bash audit/scan.sh` 退出码 0，must-fix 0，should-fix 69084。完整输出在 `scan.txt`。should-fix 是本机根目录绝对路径和 GitHub 登录名。绝对路径留给导出脚本替换。`RECOVERY_PLAN.md` 和 `web/` 里的登录名没有改。

## 证据脱敏

用和 `evidence/p8/20261017T0906Z-w-p8/` 相同的改法处理尾部副本。来源句子里的私有池键、费率、私有仓库路径和 git 短 sha 换成占位符。地址、原始余额、可读余额、分类和行数没有改。

| 文件 | 结果 |
| --- | --- |
| `holders-classified.json` | 仍是 7615 条。非来源字段无差异。19 处池句子、1 处借贷句子。 |
| `pools-locks-bridges.json` | 仍是 2341 行。非来源字段无差异。同样 19 + 1 处来源句子。 |
| `local-configs.json` | 配置键和费率改为 `redacted`，私有文件行号和 git 短 sha 改为空，路径改为 `private-config`。地址、dex 名称和摘录行号保留。 |
| `ledger.csv` | 数据行仍是 7615，含表头共 7616 行。原始余额合计仍是 `189487568412204611`。19 处池句子、1 处借贷句子。地址、原始余额、可读余额、分类列无差异。 |

`evidence/p8/20261017T1031Z-w-p8-tail/` 里的 `query-manifest.json` 和 `stats.json` 不哈希这四个文件，所以没有改它们的哈希字段。引用了新字节的清单是 `evidence/p10/20261017T1047Z-fast-tail/` 的 `manifest.json`、`reconciliation.json`、`SUMMARY.md`，以及 `web/public/data/manifest.json`。旧值和新值在 `audit/REDACTIONS.md` 的 “w-pub 追加”。

三处邮箱形态：两份 SUMMARY 里的模式文字改成 `local-part [at] domain.tld`。`web/scripts/methodology.test.mjs` 的夹具改成 `["a", "b.co"].join("@")`。

## 公开导出

`audit/make-public-export.sh` 仍默认 squash，仍拒绝写进本仓库和已存在的目录。解包后删除 `web/shots/`、`audit/scan.sh`、`audit/make-public-export.sh`、`audit/PUBLIC-READINESS.md`。`audit/REDACTIONS.md` 保留。strict 扫描改为在目标目录 `git init && git add -A` 之后，用源仓库的 `audit/scan.sh --strict`。不通过则不 commit，退出码 1，目录留着。说明在 `docs/PUBLICATION.md`。

站点 blob 链接不再跟着 git remote。`PUBLIC_REPO_SLUG` 可以覆盖，默认 `zigengZ/qar-ledger-recovery`。`publishNeedles` 仍用真实 remote 和主机名。

## 测试

`cd web && npm test`：25 项通过，含邮箱夹具和公开 slug。

`python3 -m unittest discover tests`：76 项里 74 通过、1 跳过、1 失败。失败的是 `test_p7_nonce0`。它要求启动内存 sha256 等于 `72db7b1e8806d7621fe1d2fe8a3274f0cbef2105da5facb7da94c3141ba2d5ac`。这次运行得到 `9f32451c2dfd87ca547dd92797a280365666a32a49a83cb88ac33fe98d2ccc51`，字节数同为 7602176，nonce 0 的 Eval 仍然是 handler error，内存没有被这次消息改写。两份内存里的脚本路径不同：记录里的那次是主检出目录，这一次是本 worktree 的 `genesis-segment.mjs`。没有改这个测试的期望哈希。

`audit/make-public-export.sh /tmp/qar-pub-test` 退出码 0。目标里没有 `web/shots`、`audit/scan.sh`、`audit/make-public-export.sh`、`audit/PUBLIC-READINESS.md`。`audit/REDACTIONS.md` 和 `docs/PUBLICATION.md` 还在。`git log` 只有 1 个提交，作者是脚本默认值 `qar-ledger`，邮箱 `dev@localhost`。再用源仓库 `audit/scan.sh --strict --lines` 扫这个目录：退出码 0，must-fix 0，should-fix 16，都是 GitHub 登录名。检查后已删除 `/tmp/qar-pub-test`。源仓库没有被导出脚本改动。

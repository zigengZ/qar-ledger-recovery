> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# w-audit 20261017T105101Z

## 结论

本分支工作区的公开前 must-fix 已清掉。`bash audit/scan.sh` 退出码 0：must-fix 0，should-fix 26519（GitHub 登录 2，本机根目录绝对路径 26517）。

现有历史不能公开。提交进入对象库之后再跑 `bash audit/scan.sh --history`：退出码 1，must-fix 901，should-fix 118177。901 全部来自历史 blob。118177 含当前树、本提交新 blob 里留下的绝对路径，以及其他分支旧 blob 的重复计数。这次提交没有增加 must-fix。`main` 的 `953ff3a` 还有一份未脱敏账本 `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`（18 条费率、97 条私有标记）。`75aec06` 的 `evidence/p8/20261017T1031Z-w-p8-tail/` 是另一份完整副本。这两处都不在本分支上。

推荐公开路径是压缩导出，不是 filter-repo，也不是公开其他分支。`audit/make-public-export.sh` 已写好，默认写到新目录，本次没有执行。

## 数字

- 本分支起点 `f90d6f5`，57 个提交。写作时 `git log --all` 为 67 个提交。
- 已跟踪文件约 280。
- 凭据类：PEM、JWK 私钥、AKIA、GitHub token、Slack token、带密码的数据库 URL、助记词，当前树和历史都是 0。`.env.example` 的 `WALLET` 是 5 个星号。
- 证据身份：持有人 7614 条，池 2341 行，账本 7615 行，原始余额合计 `189487568412204611` 未变。
- 许可证：`vendor/drive-cu/LICENSE` 2941 字节，sha256 `2c736f1951109b205d4d394285f46e7ceb4bf8a57149ce08c37452aed6e6775d`。
- 测试：`python3 -m unittest tests.test_p8_classify`，4 项通过。
- `bash -n audit/make-public-export.sh` 通过。

## 证据路径

- `audit/PUBLIC-READINESS.md`
- `audit/REDACTIONS.md`
- `audit/scan.sh`
- `audit/make-public-export.sh`
- `vendor/drive-cu/LICENSE`
- 本文件

## 未完成

- 没有运行 `audit/make-public-export.sh`。公开前在干净的本分支上执行它，并让新目录的 `audit/scan.sh --strict` 通过。
- 本机根目录绝对路径仍留在私有树里（should-fix）。导出脚本负责改写。
- GitHub 登录两处（`RECOVERY_PLAN.md:231`、`evidence/plan-baseline-20261017.json:5`）留给你决定。
- git 作者邮箱前缀 `zzg1`（56 个本分支提交，另有 10 个在其他分支）和 noreply 前缀 `8980`（1 个提交）留给你决定。公开历史会带上它们。
- 其他分支和 `main` 上的未脱敏副本没有改。本 worker 不改那些分支。

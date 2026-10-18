# 公开副本

## 中文

公开仓库是从私有工作仓库压缩出来的一个初始提交。压缩是因为旧提交里还有私有配置摘录和个人邮箱。改写那些提交会改掉证据哈希，也会把作者邮箱留在历史里。公开站点要的是脱敏之后的当前树，一个初始提交就够。

导出时去掉这些路径：

- `web/shots/`：页面截图
- `audit/scan.sh`：私有字符串的 sha256 拒绝表
- `audit/make-public-export.sh`：导出脚本
- `audit/PUBLIC-READINESS.md`：拒绝表和命中前缀

`audit/REDACTIONS.md` 保留。证据文件的字节级脱敏和哈希链都写在那里。

绝对路径在导出时替换成占位符：仓库前缀换成 `<repo>`，worktree 前缀换成 `<worktrees>`，其余本机根目录前缀换成 `<local-root>/`，主目录前缀换成 `<home>/`。

原始下载 `data/raw` 不在仓库里。另一台机器从公开网关重新下载。在仓库根目录执行 `./repro/run.sh`。它只访问公开网关，从 nonce 2074518 的检查点回放到尾部 nonce 2075923，并把结果和 `repro/EXPECTED.json` 对比。网关列表、运行方式和预期字段见 `repro/README.md`。

## English

The public repository is one initial commit, squashed from the private working repository. The history is squashed because older commits still contain private config excerpts and a personal email address. Rewriting those commits would change evidence hashes and would keep the author email in the history. The public site needs the sanitized tree, and one initial commit is enough.

The export omits these paths:

- `web/shots/`: page screenshots
- `audit/scan.sh`: the sha256 rejection table for private strings
- `audit/make-public-export.sh`: the export script
- `audit/PUBLIC-READINESS.md`: the rejection table and match prefixes

`audit/REDACTIONS.md` stays. Byte-level redaction of the evidence files, and the hash chain, are recorded there.

Absolute paths are replaced during export. The repository prefix becomes `<repo>`, the worktree prefix becomes `<worktrees>`, any other local-root prefix becomes `<local-root>/`, and a home-directory prefix becomes `<home>/`.

The raw downloads in `data/raw` are not in the repository. Another machine downloads them again from public gateways. From the repository root, run `./repro/run.sh`. It talks only to public gateways, replays from the nonce 2074518 checkpoint through tail nonce 2075923, and compares the result with `repro/EXPECTED.json`. The gateway list, the run steps, and the expected fields are in `repro/README.md`.

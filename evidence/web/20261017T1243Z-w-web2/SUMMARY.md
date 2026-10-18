> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# w-web2

静态站点收尾。没有部署。`goal_complete` 仍是 false。这不是领取名单。

## 结论

钱包页和钱包路由已去掉。构建不再读取钱包持仓目录。说明页用 DOMPurify 3.4.17，只留常规排版标签，链接仍走原来的白名单。主题初始化是 `theme-init.js`。`dist/index.html` 里的 script 都带 `src`，没有内联脚本。

分类用尾部 `evidence/p8/20261017T1031Z-w-p8-tail`，nonce 2075923。7615 个地址，非零 2239，相对快照有 10 个余额变化。canonical 余额 sha256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。验证时间线是快照、哈希链、引擎校验、精确回放、只回放 assignment、不跑 WASM 的 7615/7615、从零复现、主回放最终 sha（后来已吻合，见 README）。cron 高度 ±3 不改变 canonical 哈希。页脚和浏览器 SubtleCrypto 都显示这个哈希吻合。

`npm test` 24 项通过。`npm run build` 通过。预览只听回环地址。五页在浅色、深色、桌面和 375 宽下截图在 `web/shots/`，控制台没有错误，CSP 没有违规。`dist` 里没有主机名、IP、`<local-root>/`、`<home>/` 或钱包页残留。

## 数字

- 地址 7615，非零 2239，供应 raw `189487568412204611`
- 尾部分类缺失地址 0，相对快照余额变化 10
- 独立重算 7615/7615，Transfer 记入 703，拒绝 0
- 数据生成时间 `2026-10-17T12:42:06.976Z`

## 证据

- `web/public/data/manifest.json`
- `web/public/data/evidence.json`
- `web/public/data/methodology.json`
- `web/shots/`
- 账本 `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`
- 分类 `evidence/p8/20261017T1031Z-w-p8-tail/`
- 独立重算 `evidence/p10-indep/20261017T104141Z-w-indep/result.json`
- 从零复现 `evidence/repro/20261017T120218Z-w-repro/` 与 `repro/EXPECTED.json`

## 未完成

- 写这份记录时主回放最终 sha 还在进行。后来已经吻合，见 README。
- 从零复现没有跑完整 safe 模式。
- 可分离抵押 raw 是 null。
- 没有部署。

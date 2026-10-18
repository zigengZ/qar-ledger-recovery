# 静态审查

审查对象是 `data/raw/drive-cu/tree/`。没有执行 `npm install`，没有构建镜像，没有运行 `deploy.js`，没有启动 `src/app.js`。

## 包脚本

`package.json` 的 `scripts` 只有 `dev`、`lint`、`start`、`test`。没有 `preinstall`、`postinstall`、`prepare`。`start` 是 `node --experimental-wasm-memory64 -r dotenv/config src/app.js`。

与 permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461` 的 `servers/cu/package.json` 相比，唯一依赖差异是 `@permaweb/weavedrive`：上游 `^0.0.18`，Drive 这份 `^0.0.19`。`@permaweb/ao-loader` 两边都是 `^0.0.44`。Drive 的 lockfile 把 `ao-loader` 固定在 `0.0.44`，把 `weavedrive` 固定在 `0.0.19`。和同一 commit 的 lock 相比，版本字段只有 `weavedrive` 从 `0.0.18` 变成 `0.0.19`。

`src/domain/lib/loadMessages.js`、`src/effects/ao-block.js`、`src/domain/utils.js` 与该 commit 的同路径文件逐字节相同。比对用的是 2026-10-17 从 `raw.githubusercontent.com/permaweb/ao/0db88a45aabeb5e88471e5c263790fa51a563461/` 取下的副本。

## deploy.js 和 Dockerfile

`deploy.js` 读取环境变量 `DEPLOY_HOOKS`，对其中每个 URL 发 `POST`。这个文件没有运行。

`Dockerfile` 基于 `node:22`，执行 `npm install --omit=dev`，暴露 6363，入口是 `npm run start`。镜像没有构建。

## 网络地址

`src/config.js` 的默认值：

- `GATEWAY_URL`：`https://arweave.net`（约第 139 行和第 206 行）
- `GRAPHQL_URLS`：`https://arweave.net/graphql` 和 `https://arweave-search.goldsky.com/graphql`（约第 141 行和第 208 行）
- `UPLOADER_URL`：`https://up.arweave.net`（约第 144 行和第 211 行）

同文件里其他 `https://` 命中是 node-config 文档注释。

## 子进程、eval、混淆

在 `src/` 的 `.js` 里搜索：`child_process` 0 次，`eval(` 0 次，`new Function` 0 次。`workerpool` 出现 7 次，调用点是 `workerpool.pool` 和 `workerpool.exec`，用来跑 hash chain 和 evaluate worker，不是 shell。

没有把源码当加密载荷展开的搜索命中。这个结论只覆盖上述字符串计数。

## 密钥和 .env

`.env` 已下载到 `data/raw/drive-cu/tree/.env`，模式 `0600`，1101 字节。变量名 27 个：`PORT`、`NODE_CONFIG_ENV`、`ARWEAVE_URL`、`GRAPHQL_URL`、`GRAPHQL_URLS`、`PROCESS_MEMORY_FILE_CHECKPOINTS_DIR`、`CHECKPOINT_GRAPHQL_URL`、`DB_URL`、`DISABLE_PROCESS_CHECKPOINT_CREATION`、`DISABLE_PROCESS_FILE_CHECKPOINT_CREATION`、`WALLET_FILE`、`PROCESS_MEMORY_CACHE_MAX_SIZE`、`PROCESS_MEMORY_CACHE_CHECKPOINT_INTERVAL`、`ENABLE_METRICS_ENDPOINT`、`WASM_EVALUATION_PRIMARY_WORKERS_PERCENTAGE`、`PROCESS_WASM_MEMORY_MAX_LIMIT`、`PROCESS_WASM_SUPPORTED_EXTENSIONS`、`WASM_INSTANCE_CACHE_MAX_SIZE`、`DEFAULT_LOG_LEVEL`、`PROCESS_CHECKPOINT_TRUSTED_OWNERS`、`EAGER_CHECKPOINT_EVAL_TIME_THRESHOLD`、`IGNORE_LOCAL_CHECKPOINTS`、`CHECKPONT_VALIDATION_STEPS`、`CHECKPONT_VALIDATION_THRESH`、`CHECKPONT_VALIDATION_RETRIES`、`LOAD_MESSAGES_PAGE_SIZE`、`RATE_LIMIT_MAX_REQUESTS`。其中三个 `CHECKPONT_` 是文件里的拼写。值没有打印，文件没有提交。

`.env.example` 45 字节，只有 `NODE_CONFIG_ENV`（值长度 13）和 `WALLET`（值长度 7）。

`ao-cache.sqlite` 的 `modules.owner` 是一个 JWK 形状的对象，全表只有一个不同的值。密钥没有抄进证据。该 sqlite 不进入 `vendor/`。

源码里 `WALLET` 按 README 和 `src/effects/arweave.js` 的用法是一段 JWK 字符串，经 `JSON.parse` 读入。仓库副本里的值只出现在未提交的 `.env`。

## npm audit

命令是 `/opt/node-v22.22.0/bin/npm audit --package-lock-only`，工作目录使用 Drive 的 `package-lock.json`。退出码 1。18 条：critical 1、high 15、moderate 2、low 0、info 0。直接依赖里标出的是 `@fastify/middie`（critical）、`fast-glob`、`fastify`、`nodemon`、`undici`（均为 high）。没有安装任何包。

## 病毒扫描

见 `scan-report.json`。主扫描 101 个文件，0 感染。`.gitkeep` 是扫描之后补下的 0 字节文件，补扫时 clamscan 报告扫描文件数为 0。

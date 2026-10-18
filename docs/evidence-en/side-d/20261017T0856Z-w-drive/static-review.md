> English translation of [`evidence/side-d/20261017T0856Z-w-drive/static-review.md`](../../../../evidence/side-d/20261017T0856Z-w-drive/static-review.md). The original is authoritative.

# Static review

The object of review is `data/raw/drive-cu/tree/`. `npm install` was not run, no image was built, `deploy.js` was not run, and `src/app.js` was not started.

## Package scripts

The `scripts` of `package.json` are only `dev`, `lint`, `start`, `test`. There is no `preinstall`, `postinstall`, or `prepare`. `start` is `node --experimental-wasm-memory64 -r dotenv/config src/app.js`.

Compared with `servers/cu/package.json` of permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461`, the only dependency difference is `@permaweb/weavedrive`: upstream `^0.0.18`, this Drive copy `^0.0.19`. `@permaweb/ao-loader` is `^0.0.44` on both sides. The Drive lockfile pins `ao-loader` at `0.0.44` and `weavedrive` at `0.0.19`. Compared with the lock at the same commit, the only version field change is `weavedrive` from `0.0.18` to `0.0.19`.

`src/domain/lib/loadMessages.js`, `src/effects/ao-block.js`, and `src/domain/utils.js` are byte-identical to the files at the same paths in that commit. The comparison used copies fetched on 2026-10-17 from `raw.githubusercontent.com/permaweb/ao/0db88a45aabeb5e88471e5c263790fa51a563461/`.

## deploy.js and Dockerfile

`deploy.js` reads the environment variable `DEPLOY_HOOKS` and sends a `POST` to each URL in it. This file was not run.

`Dockerfile` is based on `node:22`, runs `npm install --omit=dev`, exposes 6363, and its entry point is `npm run start`. The image was not built.

## Network addresses

Defaults in `src/config.js`:

- `GATEWAY_URL`: `https://arweave.net` (around lines 139 and 206)
- `GRAPHQL_URLS`: `https://arweave.net/graphql` and `https://arweave-search.goldsky.com/graphql` (around lines 141 and 208)
- `UPLOADER_URL`: `https://up.arweave.net` (around lines 144 and 211)

Other `https://` hits in the same file are node-config documentation comments.

## Subprocesses, eval, obfuscation

Search in the `.js` files of `src/`: `child_process` 0 times, `eval(` 0 times, `new Function` 0 times. `workerpool` appears 7 times; the call sites are `workerpool.pool` and `workerpool.exec`, used to run the hash chain and evaluate workers, not a shell.

There were no search hits for unpacking source code as an encrypted payload. This conclusion covers only the string counts above.

## Keys and .env

`.env` was downloaded to `data/raw/drive-cu/tree/.env`, mode `0600`, 1101 bytes. It has 27 variable names: `PORT`, `NODE_CONFIG_ENV`, `ARWEAVE_URL`, `GRAPHQL_URL`, `GRAPHQL_URLS`, `PROCESS_MEMORY_FILE_CHECKPOINTS_DIR`, `CHECKPOINT_GRAPHQL_URL`, `DB_URL`, `DISABLE_PROCESS_CHECKPOINT_CREATION`, `DISABLE_PROCESS_FILE_CHECKPOINT_CREATION`, `WALLET_FILE`, `PROCESS_MEMORY_CACHE_MAX_SIZE`, `PROCESS_MEMORY_CACHE_CHECKPOINT_INTERVAL`, `ENABLE_METRICS_ENDPOINT`, `WASM_EVALUATION_PRIMARY_WORKERS_PERCENTAGE`, `PROCESS_WASM_MEMORY_MAX_LIMIT`, `PROCESS_WASM_SUPPORTED_EXTENSIONS`, `WASM_INSTANCE_CACHE_MAX_SIZE`, `DEFAULT_LOG_LEVEL`, `PROCESS_CHECKPOINT_TRUSTED_OWNERS`, `EAGER_CHECKPOINT_EVAL_TIME_THRESHOLD`, `IGNORE_LOCAL_CHECKPOINTS`, `CHECKPONT_VALIDATION_STEPS`, `CHECKPONT_VALIDATION_THRESH`, `CHECKPONT_VALIDATION_RETRIES`, `LOAD_MESSAGES_PAGE_SIZE`, `RATE_LIMIT_MAX_REQUESTS`. The three `CHECKPONT_` names are spelled that way in the file. The values were not printed, and the file was not committed.

`.env.example` is 45 bytes, with only `NODE_CONFIG_ENV` (value length 13) and `WALLET` (value length 7).

`modules.owner` in `ao-cache.sqlite` is a JWK-shaped object, and the whole table has only one distinct value. The key was not copied into evidence. That sqlite does not go into `vendor/`.

In the source, per the README and the use in `src/effects/arweave.js`, `WALLET` is a JWK string read through `JSON.parse`. In the repository copy, its value appears only in the uncommitted `.env`.

## npm audit

The command is `/opt/node-v22.22.0/bin/npm audit --package-lock-only`, with the working directory using the Drive `package-lock.json`. Exit code 1. 18 items: critical 1, high 15, moderate 2, low 0, info 0. Among direct dependencies, the flagged ones are `@fastify/middie` (critical), `fast-glob`, `fastify`, `nodemon`, `undici` (all high). No package was installed.

## Virus scan

See `scan-report.json`. Main scan 101 files, 0 infected. `.gitkeep` is a 0-byte file fetched after the scan; on the follow-up scan, clamscan reported 0 files scanned.

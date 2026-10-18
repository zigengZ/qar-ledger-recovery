> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# STOP

goal_complete=false

The 0..49999 hash-chain break is resolved. Links 5771..5794 failed because the id taken from the bundle was the outer two-item bundle, not the inner assignment. The inner id is sha256 of the assignment signature. Nonce 5769's inner id is the GraphQL id `JG9L1ph0xWCoW86UhYxzXixV0vTY7RvN96n0FCtxyWI`. With those ids, all 49999 consecutive links in 0..49999 match.

That range is complete. Range 50000..99999 is not complete: 49868 unique nonces are indexed and 132 nonces are still missing. Nonces 99074..99097, 88650..88673, 88596..88621, 88407..88430, and 90879..90909 were recovered from readable bundle items and link to their neighbors. Those bundles still have unread chunk gaps; those bytes were not filled. Exact Nonce queries for the original 261 closed empty. A chunk scan of the largest bundle in each hole-neighbor block did not find this process's missing nonces. Nonce strings in bundles `2G1iolRXciLjzFuG8rOJBtzJW_rSgO4J3Q6AbATXtOI` and `Xhnj-IZ6zyM_6D_a7taxUZ0YcL8zu83jvuxu2bAUO-4` belong to process `1J-YEAF_j0DieqA7Jy_SoH4ZsC2sIF4nxol0YvoPoW0` and were not inserted.

The ledger is not recovered. Do not publish a claim list. The module was not executed. Range 50000..99999 does not have 50000 unique nonces, so it is not complete. It is blocked on unreadable chunk bytes. The next P4 index is 100000..149999. Do not start P5.

Nonce tags 97965 and 97970 were seen in bundle `QCanjfosATSuFwJTEczxk4s_dfyr_xjlaHjv8owoIxM`. A later read could not fetch the bundle header, so those tags were not parsed and not inserted. Hole 97950..97975 stays open. Nonce tags 95463, 95465, 95469, 95473, 95481, and 95485 were seen in bundle `heiqNVDCZihkPzpjdZhru_Cdyl-9hCuE60C2pXpAJ08`. Its header chunk also returned 404, so those tags were not parsed and not inserted. Hole 95460..95486 stays open.

The paired AO bundle queue then finished. Bundle `glr7pOXTBRwk6luSIXPYzoKuKNF3PviP0cBot8P_uQs` was read through the chunks the gateway returned: 2513436672 of 3209925259 bytes, 1213 gaps, 200 process hits, and no wanted missing-nonce tag. Nothing from that bundle was inserted. The unread gaps are not proof that nonces 93058..93110 are absent.

The non-AO binary bundles in those hole-neighbor blocks were then scanned: 1361 bundles, 1355 fully read with no wanted paired nonce, six not closed. Nothing was inserted. A retry of the `QCanjfos` header, the `heiqNVDC` header, and the first gap of `iCo0fdk5` returned HTTP 404 from both arweave.net and turbo-gateway.com. Those tags stay unparsed.

Transactions in the same blocks that are not Bundle-Format=binary were then scanned: 459 transactions, 517774891 bytes, every file fully read, no process hit, nothing inserted. The direct data URL for `QfLTzjBiHDlrM0J7g4Of4ZzCReixsIc5-cue-9NVyCA` also returned HTTP 404.

Every remaining gap chunk offset was then requested from `https://vilenarios.com` and `https://ar-io.dev`: 4079 offsets, 8158 requests. The first pass was 8113 HTTP 404 responses and 45 timeouts. Those 45 timed-out offsets returned HTTP 404 on the retry, and the other host had already returned HTTP 404 for each of them. No chunk body came back. Nothing was inserted and no unread byte was filled. Range 50000..99999 is blocked, not complete. 132 nonces remain missing.

P4 index 100000..149999 then walked inclusion heights 1552710 through 1558269 and stopped because the next window's minimum nonce passed 149999. It seeded the 235 rows already captured above 99999. Result: 49373 unique nonces, 627 missing, 0 conflicts. 49332 present hash-chain links match, and 40 hole boundaries were not crossed. Exact Nonce queries, 63 batches of at most 10, all closed with empty edge lists. Nothing was inserted. The range is not complete.

The follow-up AO bundle scan of those 627 holes was stopped after 15 fully read bundles, none of which held a wanted nonce. The other listed bundles were not scanned. That is not proof the nonces are absent. No P4 range at nonce 150000 or later will be opened.

P5 paged every Type=Checkpoint for this process: 123 pages, 12267 rows, pagination closed. Three signers appear. The CU address from `https://cu.ao-testnet.xyz/` is `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk` and signed 3079 of the rows, including the newest, nonce 2074518, id `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`. Its ANS-104 signature verifies. The gzip is 145634952 bytes and gunzips to 428146688 bytes whose SHA-256 is `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`, the same as the SHA-256 tag. The gzip is local only. P6 then pinned `@permaweb/ao-loader` 0.0.44 and replayed assignments 2074509..2074518 from the nonce 2074508 checkpoint. With 300 synthesized 5-minute crons, and again with none, the memory SHA-256 matched neither nonce 2074510 nor nonce 2074518. No evaluator error was returned. A read-only Total-Supply on the assignments-only result and on the real 2074518 memory both returned `189487568412204611`. Info also matched. Balances returned an empty list on both, so that comparison is not a balance-map proof. Nonce 2074518 is rejected as an effective replay start.

P7 therefore started at genesis. The process boot message ran and its memory is `72db7b1e8806d7621fe1d2fe8a3274f0cbef2105da5facb7da94c3141ba2d5ac` (7602176 bytes, local only). Nonce 0 Eval then failed: `[string ".handlers"]:335: error loading module 'arweave.types.type' from file '/usr/local/share/lua/5.3/arweave/types/type.lua': cannot read ... Function not implemented`. That message was not committed. The cursor remains nonce 0. No balance rows were written. Recovery requires the evaluator to serve that Lua module, then rerun from the boot snapshot.

That recovery note is superseded. `@permaweb/ao-loader` 0.0.44, and the same `wasm32-unknown-emscripten` glue since permaweb/ao `63bbd35` (2024-03-28), returns ENOSYS from `_fd_read`. A host file at the Lua path is not read. The nonce 0 message does not define `arweave.types.type`. The CU worker keeps the previous memory when the result has an Error. Run `20261017T0605Z-p7-genesis-0-19` recorded that error and continued, but its cron boundaries were Arweave block timestamps. The CU uses the assignment Timestamp. That memory `04c4d2c5dbf7f396de286718b565b7a78424e50b53bb363d06806585471eaf01` is not the cursor.

Run `20261017T0615Z-p7-genesis-0-19` uses the assignment Timestamp. Nonce 0 did not apply and memory stayed at the boot hash. Nonce 1 defines the module inside the message and was applied. Assignments 1..19 applied. 226 crons applied, 0 cron handler errors. Memory after nonce 19 is `d36a4f98636128efc68f04c92a45e650940e1b77fe3792df2906d58e6eba8538` (11010048 bytes, local only). A Total-Supply read on that memory returned `10000000000`. That string is not the shutdown supply and no balance rows were written. Resume boundary is block 1505818, timestamp 1726231800507.

The next segment did not start. Of nonces 20..99, 73 message ids resolve through GraphQL `transactions(ids)`. Nonces 21..27 do not, and `GET https://arweave.net/7L4y3VJlF_Y9PskM2RQ-LBlrHCc_L_7BtAp_6PcYy9Q` returned 404. Those seven assignments were included in block 1505824. That block has 49 binary bundles totaling 1688225062 bytes. They were not scanned. A range read of bundle `dc_ROS2cwFwwjxV7cxirpGZ26llD66o2d4tdNdUx7A4` timed out. The missing bodies were not stored as empty. Cursor remains nonce 20. `goal_complete=false`.

Genesis replay is stopped. The 100..179 run was stopped before it finished and is not a cursor. Checkpoint 2074518 is the replay start: semantic gate matched 7614 addresses and Total-Supply `189487568412204611`; the independent byte gate remains failed. `worker/w-tail`, `worker/w-src`, and `worker/w-eval` are merged. Collateral asset, holder, and raw amount stay unknown. Next is replay 2074519..2075923. `goal_complete=false`.

That input gap was then closed by chunk reads. Nonces 21..23 came from bundle `SF7ZadOODqQDheDedChy4dQtgSsrLuP5ei7m9g1hqSE` and nonces 26..27 from `_XHzW6RRXTLRy-kG04xKiUvclruBcxq8vFlE24vD8-c`, both fully read with no chunk gap. Nonces 24..25 came from ranged reads of `dc_ROS2cwFwwjxV7cxirpGZ26llD66o2d4tdNdUx7A4`. Each recovered id matches sha256 of the message signature. Run `20261017T0645Z-p7-20-99` resumed memory `d36a4f98636128efc68f04c92a45e650940e1b77fe3792df2906d58e6eba8538` and applied assignments 20..99 and 905 crons, with no handler error. Memory after nonce 99 is `657735b4fec49198f706747c3bce346e20e559ffdbebf6a30503079e9d07e14e` (172032000 bytes, local only). A Total-Supply read returned `1120000000000`. That is not the shutdown supply. No balance rows were written. Cursor is nonce 100. Resume boundary is block 1507978, timestamp 1726503012144. `goal_complete=false`.

That genesis cursor is superseded. Replay starts at checkpoint nonce 2074518. `goal_complete=false`.

The main tail replay has exited. Stream `next_index` 39065, applied 39065, 0 handler errors. Memory sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`, 428146688 bytes, at `recovery/p7/data/raw/p7/tail-2074518/memory.bin` (gitignored). The file hash matches the fast replay and the clean clone. Do not start another replay. P9 separable collateral raw amount is null, not 0. `collateral_sourced=false`. `collateral_reconciled=false`. `goal_complete=false`. Native AR collateral has no single separable raw amount. If the process dies, resume `recovery/p7/tail-replay.mjs` from that cursor only. w-fast reached nonce 2075923 with memory sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The table is `evidence/p10/20261017T0954Z-fast-tail/`. The fast-tail note written before this exit said the cross-check was unfinished. The match in this paragraph closes it. Five Transfer bodies are empty on arweave.net `/raw`, and their quantities are tags. The handler does not read Data, so empty Data is not a quantity of 0. Those nonces are 2074509, 2074511, 2074513, 2074515, and 2074517. The refreshed table is `evidence/p10/20261017T1047Z-fast-tail/`. An independent non-WASM ledger matches all 7615 addresses in that table. `goal_complete` stays false. `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` keeps the P8 role `wallet`; identity was not checked. The repository stays private. `worker/w-audit` is merged and `audit/make-public-export.sh` was not run. Existing history is not public-ready. Do not execute a historical redaction. Collateral delta is unknown. `goal_complete=false`.

Evidence: `evidence/p4/20261016T193039Z-p4-0-49999-closed/`, `evidence/p4/20261016T193251Z-p4-50000-99999/`, `evidence/p4/20261016T203902Z-p4-50000-largest-false/finding.json`, `evidence/p4/20261016T210139Z-p4-50000-99074/recovered.json`, `evidence/p4/20261016T213620Z-p4-50000-88650/recovered.json`, `evidence/p4/20261016T220113Z-p4-50000-97965-blocked/finding.json`, `evidence/p4/20261016T221334Z-p4-50000-88596/recovered.json`, `evidence/p4/20261016T222554Z-p4-50000-95460-blocked/finding.json`, `evidence/p4/20261016T234433Z-p4-50000-88407/recovered.json`, `evidence/p4/20261017T004251Z-p4-50000-90879/recovered.json`, `evidence/p4/20261017T023731Z-p4-50000-ao-queue/finding.json`, `evidence/p4/20261017T033409Z-p4-50000-non-ao/finding.json`, `evidence/p4/20261017T034025Z-p4-50000-nonbinary/finding.json`, `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json`, `evidence/p4/20261017T043811Z-p4-100000-149999/`, `evidence/p4/20261017T050640Z-p4-100000-exact/finding.json`, `evidence/p4/20261017T052224Z-p4-100000-scan-stopped/finding.json`, `evidence/p5/20261017T053304Z-p5-checkpoints/`, `evidence/p6/20261017T054635Z-p6-gate/`, `evidence/p7/20261017T055800Z-p7-genesis-0-19/`, `evidence/p7/20261017T0605Z-p7-genesis-0-19/`, `evidence/p7/20261017T0615Z-p7-genesis-0-19/`, `evidence/p7/20261017T0635Z-p7-20-99-inputs/finding.json`, `evidence/p7/20261017T0645Z-p7-20-99/`, `evidence/p4-tail/20261017T052614Z-w-tail/`, `evidence/p9-prep/20261017T051439Z-w-src/`, `evidence/p6/20261017T052333Z-w-eval/`, `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/`.

P10 gate recompute `20261017T1718Z` ran `python3 -m recovery.p10.build_report` twice on the 1720 inputs and twice with `evidence/p7/20261017T1718Z-p7-replay-read/replay.json`. The pairs match. `ledger_delta_raw` is 0. Collateral delta is null, not 0. Unindexed span `150000..2074399` and 759 explicit missing nonces keep `schedule_covered` and `inputs_complete` false. 369 `unknown_process` rows and 5274 `wallet` rows keep `classification_sourced` false. `collateral_sourced` and `collateral_reconciled` stay false. The crosscheck file's sha match is read, and that file has no last nonce. The excerpt's last nonce is 2075923. Neither pair makes every section-6 flag true. `goal_complete=false`. Do not publish a claim list. Do not start another replay. Do not open a P4 range at nonce 150000 or later. Recovery still requires sourced classification for the unknown processes, a separable collateral raw amount that is not filled in, and nonce coverage for the unindexed span and the 132 and 627 holes without zero-fill.

The next pre-150000 hole is nonce 87659. Evidence `evidence/p4/20261017T1726Z-p4-hole-87659/` cites the blocked range file. The assignment id is null. The raw amount is null. `schedule_covered=false`. `goal_complete=false`.

Nonce 87662 was then queried once. Evidence `evidence/p4/20261017T1729Z-p4-hole-after-87659/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87666 was then queried once. Evidence `evidence/p4/20261017T1731Z-p4-hole-after-87662/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87668 was then queried once. Evidence `evidence/p4/20261017T1732Z-p4-hole-after-87666/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87670 was then queried once. Evidence `evidence/p4/20261017T1733Z-p4-hole-after-87668/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87675 was then queried once. Evidence `evidence/p4/20261017T1733Z-p4-hole-after-87670/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87678 was then queried once. Evidence `evidence/p4/20261017T1734Z-p4-hole-after-87675/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 87679 was then queried once. Evidence `evidence/p4/20261017T1735Z-p4-hole-after-87678/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88824 was then queried once. Evidence `evidence/p4/20261017T1736Z-p4-hole-after-87679/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88830 was then queried once. Evidence `evidence/p4/20261017T1736Z-p4-hole-after-88824/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88836 was then queried once. Evidence `evidence/p4/20261017T1737Z-p4-hole-after-88830/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88871 was then queried once. Evidence `evidence/p4/20261017T1738Z-p4-hole-after-88836/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88872 was then queried once. Evidence `evidence/p4/20261017T1739Z-p4-hole-after-88871/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88875 was then queried once. Evidence `evidence/p4/20261017T1739Z-p4-hole-after-88872/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88876 was then queried once. Evidence `evidence/p4/20261017T1740Z-p4-hole-after-88875/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88879 was then queried once. Evidence `evidence/p4/20261017T1741Z-p4-hole-after-88876/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88880 was then queried once. Evidence `evidence/p4/20261017T1741Z-p4-hole-after-88879/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88881 was then queried once. Evidence `evidence/p4/20261017T1742Z-p4-hole-after-88880/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88882 was then queried once. Evidence `evidence/p4/20261017T1743Z-p4-hole-after-88881/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88884 was then queried once. Evidence `evidence/p4/20261017T1743Z-p4-hole-after-88882/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88889 was then queried once. Evidence `evidence/p4/20261017T1744Z-p4-hole-after-88884/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88890 was then queried once. Evidence `evidence/p4/20261017T1745Z-p4-hole-after-88889/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88892 was then queried once. Evidence `evidence/p4/20261017T1745Z-p4-hole-after-88890/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88893 was then queried once. Evidence `evidence/p4/20261017T1746Z-p4-hole-after-88892/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88894 was then queried once. Evidence `evidence/p4/20261017T1747Z-p4-hole-after-88893/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 88896 was then queried once. Evidence `evidence/p4/20261017T1748Z-p4-hole-after-88894/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93058 was then queried once. Evidence `evidence/p4/20261017T1749Z-p4-hole-after-88896/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93059 was then queried once. Evidence `evidence/p4/20261017T1749Z-p4-hole-after-93058/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93060 was then queried once. Evidence `evidence/p4/20261017T1750Z-p4-hole-after-93059/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93061 was then queried once. Evidence `evidence/p4/20261017T1751Z-p4-hole-after-93060/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93062 was then queried once. Evidence `evidence/p4/20261017T1752Z-p4-hole-after-93061/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93063 was then queried once. Evidence `evidence/p4/20261017T1753Z-p4-hole-after-93062/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93064 was then queried once. Evidence `evidence/p4/20261017T1755Z-p4-hole-after-93063/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93065 was then queried once. Evidence `evidence/p4/20261017T1756Z-p4-hole-after-93064/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93066 was then queried once. Evidence `evidence/p4/20261017T1758Z-p4-hole-after-93065/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93067 was then queried once. Evidence `evidence/p4/20261017T1759Z-p4-hole-after-93066/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93068 was then queried once. Evidence `evidence/p4/20261017T1802Z-p4-hole-after-93067/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93069 was then queried once. Evidence `evidence/p4/20261017T1809Z-p4-hole-after-93068/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93070 was then queried once. Evidence `evidence/p4/20261017T1812Z-p4-hole-after-93069/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93071 was then queried once. Evidence `evidence/p4/20261017T1812Z-p4-hole-after-93070/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93072 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93071/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93073 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93072/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93074 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93073/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93075 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93074/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93076 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93075/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93077 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93076/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93078 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93077/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93079 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93078/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93080 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93079/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93081 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93080/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93082 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93081/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93083 was then queried once. Evidence `evidence/p4/20261017T1813Z-p4-hole-after-93082/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93084 was then queried once. Evidence `evidence/p4/20261017T1814Z-p4-hole-after-93083/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93085 was then queried once. Evidence `evidence/p4/20261017T1814Z-p4-hole-after-93084/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93086 was then queried once. Evidence `evidence/p4/20261017T1814Z-p4-hole-after-93085/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93087 was then queried once. Evidence `evidence/p4/20261017T1814Z-p4-hole-after-93086/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93088 was then queried once. Evidence `evidence/p4/20261017T1814Z-p4-hole-after-93087/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93089 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93088/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93090 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93089/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93091 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93090/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93092 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93091/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93093 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93092/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93094 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93093/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93095 was then queried once. Evidence `evidence/p4/20261017T1815Z-p4-hole-after-93094/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93096 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93095/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93097 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93096/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93098 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93097/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93099 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93098/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93100 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93099/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93101 was then queried once. Evidence `evidence/p4/20261017T1816Z-p4-hole-after-93100/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93102 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93101/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93103 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93102/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93104 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93103/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93105 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93104/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93106 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93105/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93107 was then queried once. Evidence `evidence/p4/20261017T1817Z-p4-hole-after-93106/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93108 was then queried once. Evidence `evidence/p4/20261017T1909Z-p4-hole-after-93107/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93109 was then queried once. Evidence `evidence/p4/20261017T1910Z-p4-hole-after-93108/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 93110 was then queried once. Evidence `evidence/p4/20261017T1910Z-p4-hole-after-93109/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95460 was then queried once. Evidence `evidence/p4/20261017T1910Z-p4-hole-after-93110/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95461 was then queried once. Evidence `evidence/p4/20261017T1910Z-p4-hole-after-95460/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95462 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95461/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95463 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95462/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95464 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95463/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95465 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95464/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95466 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95465/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95467 was then queried once. Evidence `evidence/p4/20261017T1911Z-p4-hole-after-95466/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95468 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95467/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95469 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95468/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95470 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95469/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95471 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95470/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95472 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95471/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95473 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95472/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95474 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95473/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95475 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95474/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95476 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95475/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95477 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95476/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95478 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95477/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95479 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95478/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95480 was then queried once. Evidence `evidence/p4/20261017T1912Z-p4-hole-after-95479/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95481 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95480/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95482 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95481/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95483 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95482/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95484 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95483/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95485 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95484/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 95486 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95485/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97950 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-95486/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97951 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97950/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97952 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97951/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97953 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97952/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97954 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97953/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97955 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97954/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97956 was then queried once. Evidence `evidence/p4/20261017T1913Z-p4-hole-after-97955/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97957 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97956/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97958 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97957/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97959 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97958/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97960 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97959/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97961 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97960/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97962 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97961/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

Nonce 97963 was then queried once. Evidence `evidence/p4/20261017T1914Z-p4-hole-after-97962/`. The page closed empty. The assignment id is null. The raw amount is null. That empty page is not proof of absence. `schedule_covered=false`. `goal_complete=false`.

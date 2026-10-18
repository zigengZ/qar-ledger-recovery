> English translation of [`evidence/side-d/20261017T0856Z-w-drive/usefulness.md`](../../../../evidence/side-d/20261017T0856Z-w-drive/usefulness.md). The original is authoritative.

# Is the Drive CU useful for the qAR ledger

The public folder is `1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`. `1HvWUSVZxHgl6lILpFe9AkODgDxQ6KVdn` in GOAL.md returns HTTP 404, and the response is in `data/raw/drive-cu/http/typo-folder.html`.

These checkpoints are not "as of July 4". The archive name is `state-20260904T155934Z.tar.zst`. State times in `checkpoint_files` run from 2024-06-24 to 2026-08-25. The latest one in the balance intersection is 2026-08-25T17:00:47Z. July 4 is the state time of two qAR/wAR pools, close to the qAR tail, not the end point of the whole drive.

## (a) CU version and the 9 Block-Heights

There is no `.git` on Drive, and `package.json` has no commit. What can be matched is the source bytes:

- `loadMessages.js`, `ao-block.js`, `utils.js` are byte-identical to permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461`.
- `@permaweb/ao-loader` in the lock is `0.0.44`, the same as the w-eval evaluator.
- The only dependency difference is `@permaweb/weavedrive` `0.0.19`; the upstream pin is `0.0.18`.

In `cronMessagesBetweenWith` (`src/domain/lib/loadMessages.js`), the `Block-Height` of a time cron is written as the current `curBlock.height`. `curBlock` starts from the left boundary block and advances to the next block only when `toSeconds(curTimestamp) >= toSeconds(nextBlock.timestamp)`. The qAR cron is every 5 minutes and takes this time branch.

`getLatestBlock` is passed into `reconcileBlocksWith` and wrapped by a schema, but the function body does not call it. Blocks come from the CU's own sqlite cache, and missing ranges are requested from GraphQL.

This is the same algorithm as w-eval's `recovery/p6/replay.mjs`; the source itself does not add 1 to 3 to the height. The w-eval record is: the 9 cron timestamps are the same, the replay Block-Height is 1 to 3 higher than the checkpoint, and the memory sha matches only after copying those 9 heights back (`evidence/p6/20261017T052333Z-w-eval/SUMMARY.md`). An explanation compatible with this source is that when the checkpoint was written, the CU's block list had 1 to 3 fewer blocks than the gateway did later. The source cannot prove that the CU deliberately stored height-1.

## (b) ao-cache.sqlite

Opened read-only. Tables and row counts are in `sqlite-index.json`. `blocks`, `processes`, `messages`, `evaluations`, `checkpoints` all have 0 rows. `checkpoint_files` has 1008 rows; it is an index of checkpoint file names, not process memory.

qAR `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8` and APUS `mqBYxpDsolZmJyBdTK8TJp_ftOuIUXVYcSQ8MYZdJg0` have 0 rows in this table. A byte search of the sqlite, `-shm`, and `-wal` does not find these two either. The two w-src pools, the bridge `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c`, and the cron `S_0fyWQknosQ57QWd0iuWl84EYmoi5qCyDai-LYHuhg` also have 0 rows.

`modules` has 23 rows, including the qAR module `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`. Having the module id does not mean having qAR process state. `modules.owner` is a JWK, and the key was not written into evidence.

The four locally configured pools each have one row in `checkpoint_files`, with file names and times matching the Drive file names. The two July 4 permaswap pools use module `Do_Uc2Sju_ffp6Ev0AnLVdPtot15rvMjP-a9VVaA5fM`. Botega's `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` uses module `G991Xp6Kh28k8_AZcnwaqJ6LZcHlsZcMkrH1mJoAy84`. These are evaluation fields in the cache, not memory offsets.

## (c) Named processes among the 1012 checkpoints

Neither the file names nor the 996 `processId` values in `extraction-report.json` include qAR, APUS, the two w-src pools, the bridge, or the cron. The report's `missingProcessIds` has 9817 entries, and these six ids are not in it either, so they were not in the `war-wusdc-value-holding-process-ids.json` request.

Drive has 1012 bins, and the report matches 996. 16 bins exist only on Drive. Of these, 9 have no saved size; the list is `files_missing_size` in `inventory.json`. `rKpOUxssKxgfXQOpaCq22npHno6oRw66L3kZeoo_Ndk` is not in the report; the stdout of one HEAD gave `content-length: 481165312`, and that response was not written to `http/requests.jsonl`. Comparing the recorded HEADs with the report sizes, the number of mismatches is 0.

## Intersection with the local pool list

The source is an excerpt of a local pool config; the original is not written. 19 `id:` lines, 18 after deduplication. 4 intersect with the Drive file names. Details are in `local_config_pools` of `overlap.json`.

On Drive, none of the bytes was downloaded, and no report sha256 was checked against a local file:

| Config name | Address | List | State time | Height in file name | Report size | Report sha256 | qAR balance at nonce 2074518 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| redacted | `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` | private parameters redacted | 2026-07-01T01:23:35Z | 1949705 | 158793728 | `e9c7bb1ca888a3f3326c4f917cd2191ee54d519c1cae4ce353ae43fa20aac616` | `320089670049015` |
| redacted | `Eb87m8cazuCnf7BtYk3gQO6kiuhEZwPNL1iTJnR1MdQ` | private parameters redacted | 2026-07-04T06:22:01Z | 1951866 | 206700544 | `26bf2d9396c9852d56f11bdb679a0b370408da044fd352b060692c0dadeb6c8a` | `675157661762225` |
| redacted | `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` | private parameters redacted | 2026-07-04T06:21:56Z | 1951866 | 248053760 | `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a` | `1934348814863` |
| redacted | `fNFUX58BiHeBhB2D4EJsu88IeAHtJhugHSP__U6Y9dk` | private parameters redacted | 2026-02-22T02:45:17Z | 1862495 | 206700544 | `a31704e96b13ebdfafb0d5c670aa8f4013982467d76e90ddb74869f119bb5e6a` | `2000000000000` |

The preferred file is `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4_ts-1783146116188_ord-247049_bh-1951866.bin`, Drive id `18SsJyEnpKkIrjTurvIZei_a-7g8fUJzN`. The qAR tail is 2026-07-04T06:19:55.380Z, inclusion block 1951869, nonce 2075923, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`. This pool's state time is about 2 minutes after the tail, and both the file name and the `blockHeight` in sqlite are 1951866. The nonce `247049` in sqlite is this pool's own evaluation nonce, not qAR's 2075923.

The GET first got a virus scan warning page (`http/lama-warn.html`, 2534 bytes), and the following uuid download got `Google Drive - Quota exceeded` (`http/lama-step2.html`, 2040 bytes). Another `docs.google.com/uc` returned 303, with no uuid in Location. The bin was not saved, so the report sha256 was not checked. The other large files were not pulled during the quota period.

The other 14 deduplicated config pools are not on Drive. Their raw balances in the nonce 2074518 balance table are below (null would mean a missing record; all have records here, including three 0s):

- `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4` botega AO/qAR 0.0025: `381553671374914`
- `WuAkqYvunUtsD8uvpsK9XtR7_5-fbnH3ATD4DJrl-Ac` botega DUMDUM/qAR 0.0025: `371628692276590`
- `lmaw9BhyycEIyxWhr0kF_tTcfoSoduDX8fChpHn2eQM` botega qAR/AGENT 0.0025: `265525803677701`
- `NX9PKbLVIyka3KPZghnEekw9FB2dfzbzVabpY-ZN1Dg` botega qAR/NAB 0.0025: `12500009941418`
- `230cSNf7AWy6VsBTftbTXW76xR5H1Ki42nT2xM2fA6M` permaswap qAR/NAB 0.003: `6312687421159`
- `3biQvRjIp_9Qz1L9D3SJ9laK4akCkP-8bvAo3pQ6jVI` botega AO/qAR 0.0075: `3003053338103`
- `nHWcfNzeqjZ8Bot4R-xs_7Jez7Fl2AeDzKlN7qWmS24` botega qAR/tARIO 0.0025: `812731366345`
- `BeowMvoHuSHbDllewXW6P3QecJDa_059rxqMXQHD3ts` botega TRUNK/qAR 0.0025: `424876313215`
- `ZeSJHyEbZqA3D3h5vMnFPZi3BY4LdgXxL_lZzIUcvPw` botega qAR/BELE 0.0025: `284407499529`
- `usMlh8eWf9wrLR9kSPosW--SrXJGZ40LC5Rekjgywy4` botega PIXL/qAR 0.0025: `178253225566`
- `t3Dxq0oH5gPH38T3uQAek1269tTwMSSZgU6lBFvrNEs` botega LLAMA/qAR 0.0025, listed twice: `127665127065`
- `JmbCVggbs8aID1U2TOleyfGR08BVAQVOmAiYNlRogsE` commented-out permaswap AGENT/qAR 0.0030: `0`
- `DhiYsqOtkd42rSlVyNOyJ8Clxv6HmFbIfi0fSz_PRik` botega qAR/wUSDC 0.0025: `0`
- `8DdYrPbX0XM_3HuOqZN5zMphGFMSDG1pTMkWPyYJ_5k` botega AO/qAR 0.03: `0`

The low-confidence Botega candidate `vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4` from w-src is not the `Bv5mfnx5...` in this list, and it is not on Drive.

## Balance table intersection

The balance table is `data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json`, 7614 addresses, nonce 2074518. There is no `balances.json` under `data/raw/p7/` yet, so the intersection was not recomputed with tail replay balances.

54 processes intersect: 41 have nonzero balances and 13 are 0. The 0 is a value in the balance table, not a missing record. The qAR amounts of these 54 come from the 2074518 snapshot, not from balances in Drive memory.

Sorted by that balance from large to small, the top 20 files total 3739025408 bytes, and all 54 total 10032578560 bytes. The top 20 are under 20 GiB, so the download plan includes all 54. The number of intersection files actually saved is 0. GETs of large files returned the virus scan warning HTML; the script deleted those HTML files and did not leave them in `checkpoints/`. Downloads stopped after the quota appeared.

The largest balance in the intersection is `Eb87...` (table above, July 4). Next is `Bv5...` (July 1). The preferred pool `_laMMu5...` is `1934348814863` in this 2074518 table, not the largest.

The smallest checkpoint in the report is 23003136 bytes; there is no file of about 10 MB. Two small files were sampled:

- `fzRGvSW2oSop9xGLxs5mcaRtCbrbug8imI_uRZHKdiU_ts-1719201552641_ord-2856_bh-1451201.bin`, 23003136 bytes, sha256 `19a5f5eff09357078fc5f7c2ce0435b2eda58356971da0222b548539d7c48b13`, matching the report. It is not among the 54 intersections.
- `6eU3_ot8dl0dm9B6pUxZDzl78VKfzgDRSyuRumGbE9E_ts-1744639069181_ord-1412_bh-1649702.bin` was not saved. Report size 42991616, report sha256 `3e818830e93e0403d8ee6c313665b774c9716909afae335ae7e79599ce90c796`, not checked.

## Read-only roles

Only the 23 MB sample above was read, using regular expressions, without execution. `roles.json`:

- `Handlers.add` names and first offsets: `_eval` 95856, `Info` 5265745, `Credit-Notice` 5266119, `Create-Order` 5268229, `Cancel-Order` 5282473, `Get-Sales-By-Address` 5336636, `Debit-Notice` 5336907.
- One set of process tags: `App-Name` `aos`, `Name` `ucm-0.3`, `aos-Version` `1.10.21`, with `Variant` `ao.TN.1` nearby.
- The role is an order book (ucm-0.3). It is not an AMM pool, lock, bridge, or staking. The string `X-Swap-Token` appears 750 times, but not as a `Handlers.add` name.
- `"name":"Ticker","value":"AR"` appears once, at offset 4611268. It is not taken as this process's ticker.

The memory of `_laMMu5...` was not read, so there are no offsets. The permaswap qAR/wAR 0.3% in the list is only configuration, not a memory conclusion. sqlite additionally gives only its module id and its own nonce.

## For P8 / P9

What P8 can use is the address list, not verified pool reserves.

The 4 config pools have state file names, report sha values, and module and height in sqlite on Drive. Two of them, the permaswap qAR/wAR pools, fall about two minutes after the qAR tail, which makes them suitable later for checking pool reserves at the tail moment. Neither bytes nor sha have been checked, so reserves or counterparty balances cannot be extracted from memory now.

14 config pools have no Drive state. Among them, `wTIpis...`, `WuAkq...`, `lmaw9...` are among the largest qAR holdings in the 2074518 balance table. P8 still has to list these addresses separately, but their state cannot be read from this Drive.

None of the 54 processes that "hold a qAR balance and have a checkpoint on Drive" had its memory read. They show which large qAR holders are themselves processes and have state left in this wAR/wUSDC export. Apart from the 4 config pools above, the roles of the other processes are unknown.

P9 collateral cannot be derived from here. The checkpoints of the qAR process and the APUS process are not among these 1012 files, and not in the report's missing id list. sqlite has the qAR module id, but no checkpoint row for the qAR process.

## (d) Request that can be forwarded to fwd

Please search the archive `minio-rds/rds-backups/cu-state-export/state-20260904T155934Z.tar.zst` for objects named `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8_*` and `mqBYxpDsolZmJyBdTK8TJp_ftOuIUXVYcSQ8MYZdJg0_*`. Those two process ids are not among the 996 matched files in `extraction-report.json`, and they are not in its 9817-id `missingProcessIds` list, so they were not in `war-wusdc-value-holding-process-ids.json`. A state near 2026-07-04T06:19:55.380Z (qAR assignment nonce 2075923, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`, inclusion block 1951869) can check the tail replay.

The public Drive copy also names two pool checkpoints about two minutes after that tail. Google Drive quota blocked the download, so the report sha256 is not checked against local bytes. If the same archive still has these objects, the bytes would close that check:

- `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4_ts-1783146116188_ord-247049_bh-1951866.bin`, 248053760 bytes, sha256 `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a`
- `Eb87m8cazuCnf7BtYk3gQO6kiuhEZwPNL1iTJnR1MdQ_ts-1783146121245_ord-294830_bh-1951866.bin`, 206700544 bytes, sha256 `26bf2d9396c9852d56f11bdb679a0b370408da044fd352b060692c0dadeb6c8a`

# qAR balance recovery

This note is for an external reviewer. It says what was recovered, which checks passed, which checks failed, and which inputs are still missing. It is a research record. It is not a claim list, and it does not allocate collateral.

`goal_complete` is true under the 2026-10-18 checkpoint amendment. `publish_claims` is false. `move_collateral` is false. The amended gate recompute is [evidence/p10/20261017T1954Z-gate-recompute-amended/](../evidence/p10/20261017T1954Z-gate-recompute-amended/). The earlier draft [evidence/p10/20261017T0954Z-fast-tail/REPORT.md](../evidence/p10/20261017T0954Z-fast-tail/REPORT.md) still says `goal_complete` is false; that sentence describes the draft, not the amended rule. Known limits that do not block completion: the ledger cannot be recomputed from genesis, and collateral is reported as facts only. After the repository is public, anyone may open an issue; there is no fixed review period.

The same text in Chinese is [RECOVERY.zh.md](RECOVERY.zh.md).

> 这是工作日志。Sections below were written as the work proceeded. Where an early sentence said a hash was still pending, the current result is in this section.

## Current results

- Canonical balance SHA-256 is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca` (2239 nonzero addresses). The procedure is `repro/README.md`. The value is `canonical_balances_sha256` in `repro/EXPECTED.json`.
- The main replay finished at nonce 2075923. Memory SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` matches the fast replay and the clean clone. Evidence: `evidence/p7/20261017T1718Z-p7-replay-read/replay.json` and `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`. Full safe mode was not run.
- The Python recompute, without executing the module, matched all 7615 addresses. Evidence: `evidence/p10-indep/20261017T104141Z-w-indep/SUMMARY.md`.
- The refreshed tail table is `evidence/p10/20261017T1047Z-fast-tail/`. Section 5's class counts are the earlier 0954 snapshot (user 5278). The refreshed counts are user 5279, pool 74, process_unknown 2260, lock 2, bridge 0.
- `goal_complete` is true under the 2026-10-18 checkpoint amendment: the ledger is ready for public audit, not a claim list and not a distribution instruction. `publish_claims` and `move_collateral` stay false. The separable collateral raw amount is still null. That limit does not block completion. Nonce coverage from the first pushed assignment is still incomplete: 132 holes in 50000..99999, 627 holes in 100000..149999, and 150000..2074399 is unindexed. `evidence/p4/` also holds 120 per-nonce notes for holes whose exact query closed empty. Those notes are not missing ledger rows.

## 1. Goal and scope

### Which ledger, and at which moment

The process is [`NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`](https://arweave.net/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8) ([ao.link](https://ao.link/#/entity/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8)).

Its on-chain `Name` tag is `local-t-w-001`. It was spawned with aos 2.0.0, variant `ao.TN.1`, and a 5-minute cron. The spawn block is 1505290 at 2024-09-12T18:00:08Z. The owner is `6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es`. The module is [`1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`](https://arweave.net/1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0). The scheduler is `_GQ33BkPtZrqxA84vM8Zk-N2aO0toNNu_C-l-rawrBA`. Source: [evidence/p0-probe.json](../evidence/p0-probe.json).

Local trading configs call this same process id qAR. The recovery stays on this id. Source: [GOAL.md](../GOAL.md) and [evidence/p8/20261017T0906Z-w-p8/local-configs.json](../evidence/p8/20261017T0906Z-w-p8/local-configs.json).

The target state is the memory **after the last Assignment that was actually pushed to Arweave has been applied**. That assignment is:

| Field | Value |
| --- | --- |
| Epoch / nonce | 0 / 2075923 |
| Assignment | [`MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`](https://arweave.net/MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs) |
| Message | [`wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`](https://arweave.net/wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ) |
| Hash-Chain | `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE` |
| Timestamp | 2026-07-04T06:19:55.380Z (`1783145995380` ms) |
| Inclusion block | 1951869 at 2026-07-04T06:20:37Z |

Source: [evidence/p1-tail.json](../evidence/p1-tail.json). The plan that freezes this boundary is [RECOVERY_PLAN.md](../RECOVERY_PLAN.md), section 2.

### Why this moment

LegacyNet has stopped. A later collateral split, if one is ever done, needs each address's balance at the last pushed assignment. The research date is not the cutoff. A cron tick after nonce 2075923 is not the cutoff. [README.md](../README.md) records that a requested final compute-unit state for this process was not in the shared checkpoint set. This recovery did not re-fetch that conversation. It rebuilt the cutoff from public Arweave records.

P1 looked for a higher nonce. The next 13 nonces, 2075924 through 2075936, are absent. The sentinels 2076000, 2077000, 2080000, 2090000, 2200000, 3000000, and 4000000 are absent. Epoch 1 and epoch 2 assignments are absent. No assignment for this process is indexed in a block at height 1951870 or above. The Arweave tip at the probe was block 2022620. P1 did not query every nonce above 2075923. A nonce the sentinels skipped would still show up as a gap in a continuity index. Source: [evidence/p1-tail.json](../evidence/p1-tail.json).

The assignment's own `Block-Height` tag is `000001951866`. The inclusion height is 1951869. Both numbers are kept. The evaluator uses the height the historical compute unit used, which is not the same field as the inclusion height. Source: [evidence/p0-probe.json](../evidence/p0-probe.json) and [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) section 2.

### What this ledger is not

The table is not a list of people who may redeem. It does not split pool balances into LP shares. It does not name a collateral asset, a holder, or an amount, and it does not propose a distribution. [GOAL.md](../GOAL.md) forbids moving collateral and publishing a claim list. The tail report is titled `BLOCKED — NOT A CLAIM LIST`.

Unfinished records may exist in Unwrap/Deposit. They are checked separately and are outside the scope of this ledger.

## 2. Data sources, and how each one is checked

The recovery uses public nodes only.

- Arweave gateways: `https://arweave.net`, `https://turbo-gateway.com`, `https://ar-io.dev`, `https://vilenarios.com`, and GraphQL at `https://arweave.net/graphql`. `https://arweave-search.goldsky.com/graphql` answered HTTP 307 and followed to `https://arweave.net/graphql`, so that host is not a second index. Source: [evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md](../evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md).
- The AO scheduler, identified by the process tag `_GQ33BkPtZrqxA84vM8Zk-N2aO0toNNu_C-l-rawrBA`.
- LegacyNet compute-unit data items with `Type=Checkpoint` for this process, published on Arweave. The signer check uses the address published at `https://cu.ao-testnet.xyz/`. Source: [evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json).

A public Drive folder of compute-unit files was inventoried as a side check. It does not contain a qAR checkpoint. See section 3.

### Assignments and the hash chain

GraphQL returns tags. The hash-chain id is the inner ANS-104 data item. That id is the SHA-256 of the item's signature. An outer bundle id is a different value. Using the outer id broke the chain on nonces 5771..5794; the inner id closes it. Source: [evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json](../evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json).

The link function is `sha256(previous assignment id bytes || previous hash-chain bytes)`, encoded base64url. For the first nonce, the seed is the process id and the assignment id is omitted. The function was read from permaweb/ao commit [`7ba5df7b2e3c8f7e891481b4fe1b0489647cf607`](https://github.com/permaweb/ao/blob/7ba5df7b2e3c8f7e891481b4fe1b0489647cf607/servers/su/src/domain/core/scheduler.rs), `gen_hash_chain`. That tree is later than the 2024 scheduler that wrote the early assignments. A link counts as matched only when the recomputed value equals the next item's `Hash-Chain` tag. Implementation: [recovery/hashchain.py](../recovery/hashchain.py). Nonce 0's `Hash-Chain` equals the SHA-256 of the process id. Source: [evidence/p3/20261016T174856Z-p3a/sample.json](../evidence/p3/20261016T174856Z-p3a/sample.json).

### Checkpoints

For the selected checkpoint, the ANS-104 signature verifies, the owner equals the address at `https://cu.ao-testnet.xyz/`, and the SHA-256 of the gunzipped bytes equals the `SHA-256` tag. Source: [evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json).

### Module bytes

`https://arweave.net` and `https://turbo-gateway.com` returned the same 557297 bytes. SHA-256 is `164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8`. The file starts with the WASM magic. The RSA signature was stored and was not verified. Source: [evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json) and [fetch-manifest.json](../evidence/p2/20261017T1645Z-p2a/fetch-manifest.json).

### Messages from the checkpoint to the tail

All 1524 assignment messages in nonces 2074400..2075923 were stored, and each signature verified. GraphQL had no transaction for nonce 2075899, message [`VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA`](https://arweave.net/VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA), or nonce 2075900, message [`iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw`](https://arweave.net/iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw). Direct data URLs returned HTTP 404. The bytes were inside L1 transaction [`MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA`](https://arweave.net/MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA) at block 1924100, read through the chunk offset API. Each item's signature verifies. Source: [evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md](../evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md) and [message-gap-recovery.json](../evidence/p4-tail/20261017T052614Z-w-tail/message-gap-recovery.json).

### What was not archived

P0 and P1 are probe summaries. They do not contain every raw GraphQL body. Later phases store raw pages under `data/raw/`. That directory is gitignored. Each committed manifest names the raw file, its byte size, and its SHA-256. A hash is a content check. It is not a download URL. A machine without `data/raw/` re-downloads from the ids in the manifests. Source: [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) sections 2 and 4.

A missing row is not written as zero.

## 3. What each phase did

The phase rules are [RECOVERY_PLAN.md](../RECOVERY_PLAN.md). The cursor those phases wrote is [STATE.md](../STATE.md). This section follows the evidence, including the paths that were abandoned.

### P0 and P1 — identity and the tail

P0 recorded the process tags and one height-descending assignment. That single row is not proof of the maximum nonce. P1 is the tail proof in section 1. Sources: [evidence/p0-probe.json](../evidence/p0-probe.json), [evidence/p1-tail.json](../evidence/p1-tail.json).

### P2 — module bytes, not executed

The module was fetched and not executed (`executed` is false). Tags that are present: `Memory-Limit` `500-mb`, `Compute-Limit` `9000000000000`, `Module-Format` `wasm32-unknown-emscripten`, `Input-Encoding` `JSON-1`, `Output-Encoding` `JSON-1`, `Variant` `ao.TN.1`. `Extensions` is absent and was not filled in with a default. Source: [evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json).

### P3 — three sample windows, not full coverage

Windows 0..19, 1037960..1037979, and 2075904..2075923 each have one assignment per nonce. `sample_passed` is true. `full_coverage` is false. Nonce 0 and nonce 1 are both `Type=Message` `Action=Eval` assignments in block 1505290. Nonce 0's message is [`GBPuvd6zc47A8PFiD7PGmZXcZPZF-DDWcdEg4tzXC3g`](https://arweave.net/GBPuvd6zc47A8PFiD7PGmZXcZPZF-DDWcdEg4tzXC3g). Nonce 0's assignment is [`o6ia7Yi1ijVV0lXM75qK1DM2Alhk4JcdFOd6jnq2pTY`](https://arweave.net/o6ia7Yi1ijVV0lXM75qK1DM2Alhk4JcdFOd6jnq2pTY). The numeric schedule starts at nonce 0. The index method is a block-height walk, page size 100, with an exact-nonce fallback of at most 5. Source: [evidence/p3/20261016T174856Z-p3a/sample.json](../evidence/p3/20261016T174856Z-p3a/sample.json), [gaps.json](../evidence/p3/20261016T174856Z-p3a/gaps.json), [index-method.json](../evidence/p3/20261016T174856Z-p3a/index-method.json).

### P4 — indexing about two million nonces, and where it stopped

If nonces 0 through 2075923 were contiguous, the schedule would contain 2,075,924 assignments. That index was not finished. Source: [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) section 5.

**0..49999 is complete.** 50000 unique assignments, 0 conflicts, 49999 of 49999 hash-chain links match. The first GraphQL pass left 5770..5793 unresolved ([evidence/p4/20261016T175757Z-p4-0-49999/](../evidence/p4/20261016T175757Z-p4-0-49999/)). The raw bundle contained those 24 nonces, and the chain still failed while the outer bundle id was used ([evidence/p4/20261016T192515Z-p4-gapfill/](../evidence/p4/20261016T192515Z-p4-gapfill/)). The inner id closes every link ([evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json](../evidence/p4/20261016T193039Z-p4-0-49999-closed/range-manifest.json)).

**50000..99999 is blocked, not complete.** 49868 unique nonces are indexed. 132 nonces are still missing. Exact nonce queries returned no rows. Neighbor bundles recovered some holes and left others blocked because the header chunk was unreadable, so nothing was inserted for those. A later scan of non-AO bundles and of non-binary transactions in the hole-neighbor blocks did not fill a hole. Every unread gap chunk offset then returned HTTP 404 from `vilenarios.com` and `ar-io.dev`. A 404 means those bytes were not readable. It is not a proof that the nonce was never published. The missing list is in [evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json](../evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json). The attempts, in order, are the directories under [evidence/p4/](../evidence/p4/) dated from `20261016T193251Z` through `20261017T043721Z`.

**100000..149999 is indexed and not complete.** 49373 unique nonces, 627 missing, 0 conflicts. Sixty-three exact nonce batches closed empty ([evidence/p4/20261017T050640Z-p4-100000-exact/finding.json](../evidence/p4/20261017T050640Z-p4-100000-exact/finding.json)). An AO bundle scan of those holes stopped after 15 of 91 listed bundles. The 15 that were fully read held no wanted nonce. The rest were not scanned. That is not proof of absence ([evidence/p4/20261017T052224Z-p4-100000-scan-stopped/finding.json](../evidence/p4/20261017T052224Z-p4-100000-scan-stopped/finding.json)). The hole list is [evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json](../evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json).

No range at nonce 150000 or later was opened. Nonces 150000..2074399 are unindexed. They are neither a present list nor a missing list.

### Why the full index was abandoned

A compute-unit checkpoint at nonce 2074518 sits 1,405 assignments before the tail. [GOAL.md](../GOAL.md) says a result that carries a memory snapshot becomes the replay start, and only later nonces are replayed. The 132 and 627 holes stay on record. They are not zero-filled, and they no longer block the tail ledger. The plan's reordering note is [RECOVERY_PLAN.md](../RECOVERY_PLAN.md) section 5, "快照改序".

### P5 — checkpoint search

GraphQL `Type=Checkpoint` and `Process=<this process>`, 123 closed pages, 12,267 rows. Three signers:

| Signer | Rows |
| --- | ---: |
| `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk` (the address at `https://cu.ao-testnet.xyz/`) | 3079 |
| `fcoN_xJeisVsPXA-trzVAuIiqO3ydLQxM-L4XbrQKzY` | 9182 |
| `By2MUXHmmovtHqeQZju4fn8x9a4BjH_msOt_PDjJ2X0` | 6 |

The newest row is signed by the compute-unit address. It is the candidate. At the end of P5 it was not yet an accepted replay start (`p6_accepted` false). Source: [evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json) and [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json).

The selected checkpoint:

| Field | Value |
| --- | --- |
| Id | [`ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`](https://arweave.net/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk) |
| Nonce | 2074518 |
| Assignment | [`yy7ipxqxntq_9yTDaEvEW92CLrUqDssgN-RXYUQAHNA`](https://arweave.net/yy7ipxqxntq_9yTDaEvEW92CLrUqDssgN-RXYUQAHNA) |
| Hash-Chain | `W4h2kwRezDwtQtvxQ9Ssivujj3k2CZolEhKCblKrnTg` |
| Timestamp | `1771847683094` ms (2026-02-23T11:54:43.094Z) |
| Block-Height tag | 1863436 |
| Inclusion height | 1863456 |
| Gzip | 145634952 bytes, SHA-256 `31f5e4811756ff22a98546144075dd238da76eeb05470a126df43eb2fe92e095` |
| Uncompressed memory | 428146688 bytes, SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` |

The uncompressed hash equals the tag. The ANS-104 signature is valid. The signer matches the compute-unit address. The gzip file is local only (`data/raw/checkpoints/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.gz`).

Two earlier checkpoints were used as the gate's starting memories: nonce 2074510, [`lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg`](https://arweave.net/lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg), and nonce 2074508, [`EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk`](https://arweave.net/EwP2h48RouEL0WaTT2Auj5w-PBC8TOOr8sBNFSZGtkk).

### P6, first attempt — byte gate failed, checkpoint rejected

The evaluator replayed from nonce 2074508 through 2074518. With 300 synthesized 5-minute crons, and again with no crons, the memory SHA-256 matched neither nonce 2074510 nor nonce 2074518. No evaluator error was returned. A read-only `Total-Supply` on the assignments-only result and on the real nonce 2074518 memory both returned `189487568412204611`. `Info` matched. `Balances` returned Output `[]` on both memories, and that empty Output was recorded as `Balances_match`. An empty Output is not the balance table. The aos `Balances` handler replies in `Messages[].Data`. This run rejected nonce 2074518 as the replay start. The file is kept: [evidence/p6/20261017T054635Z-p6-gate/gate.json](../evidence/p6/20261017T054635Z-p6-gate/gate.json).

### P7 genesis — tried, kept, then stopped

After that rejection, replay started at process boot.

- Nonce 0's Eval failed while loading `arweave.types.type`. Memory stayed at the boot hash. No balance rows were written. A failed Eval is not a zero balance. Source: [evidence/p7/20261017T055800Z-p7-genesis-0-19/](../evidence/p7/20261017T055800Z-p7-genesis-0-19/).
- Assignments 1..19 and 226 crons were then applied. One run used Arweave block timestamps as cron boundaries. A `Total-Supply` read after nonce 19 returned `10000000000`. That is not the shutdown supply. Source: [evidence/p7/20261017T0605Z-p7-genesis-0-19/](../evidence/p7/20261017T0605Z-p7-genesis-0-19/).
- The same segment with the assignment `Timestamp` as the cron boundary still did not apply nonce 0. Nonces 1..19 and 226 crons applied. Memory SHA-256 `d36a4f98636128efc68f04c92a45e650940e1b77fe3792df2906d58e6eba8538`. The supply read was again `10000000000`. Source: [evidence/p7/20261017T0615Z-p7-genesis-0-19/](../evidence/p7/20261017T0615Z-p7-genesis-0-19/).
- Message bodies for nonces 21..27 were absent from `transactions(ids)`, and a direct fetch of nonce 21 returned HTTP 404. The seven bodies were later read from AO bundles in block 1505824. Assignments 20..99 and 905 crons applied, with no handler error. Memory SHA-256 `657735b4fec49198f706747c3bce346e20e559ffdbebf6a30503079e9d07e14e`. A supply read after nonce 99 returned `1120000000000`. That is not the shutdown supply. Sources: [evidence/p7/20261017T0635Z-p7-20-99-inputs/finding.json](../evidence/p7/20261017T0635Z-p7-20-99-inputs/finding.json) and [evidence/p7/20261017T0645Z-p7-20-99/](../evidence/p7/20261017T0645Z-p7-20-99/).
- The next segment, nonces 100..179, was stopped before it finished. It is not a cursor. Source: [evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json](../evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json).

Genesis was stopped because the same evaluator would have to be right across the whole schedule, the 132 and 627 holes are still open, and nonce 0 already shows that this loader does not reproduce the 2024 boot environment. The compute-unit checkpoint is the stronger starting memory. The genesis files stay in the tree.

### Semantic gate — balances match; bytes match only if nine heights are copied

The balance read uses `Messages[].Data` on a copy of each memory. The copy is not written back. `Output` `[]` is ignored.

Gateway block heights, no height copied from the target checkpoint:

| Gate | From | To | Messages | Replay memory SHA-256 | Checkpoint SHA-256 | Addresses | Address diffs | Total-Supply |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| A | 2074508 | 2074510 | 115 (2 assignments, 113 crons) | `6ea2c0646d295040de6045475faa1b947fa3de09ecf8d6c5a810e038af75a890` | `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1` | 7614 | 0 | `189487568412204611` |
| B | 2074510 | 2074518 | 108 (8 assignments, 100 crons) | `08b33bd914ffd015fff0e0349ab279ed064eaa44dd79a35e3cfb26a7abd32baa` | `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` | 7614 | 0 | `189487568412204611` |

The balance JSON SHA-256 is the same on the replay and the checkpoint: gate A `24f7b1e2f5a8bb6961c24630bb915cf1cb4804911e5803a8c5459d35b715f400`, gate B `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`. On all four memories, the sum of `Balances` equals `Total-Supply`. Handler errors are empty. Source: [evidence/p6/20261017T052333Z-w-eval/semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json) and [SUMMARY.md](../evidence/p6/20261017T052333Z-w-eval/SUMMARY.md).

The byte difference is not a balance change. On gate B both memories are 428146688 bytes. The exact difference is 332736 bytes in 30004 runs, last difference at offset 236575800. The readable difference is nine cron messages: the timestamps match, and the replay's `Block-Height` is 1 to 3 above the height stored in the checkpoint. Those heights appear in the cron log and in "Updating latest block height". Anchors match. Transfer quantities match. Event `sender_balance_*` and `recipient_balance_*` multisets match. The decimal supply string is at offset 212117480 on both sides. No stored `"address":"amount"` pair disagrees with the balance table. The other differing bytes are Lua heap layout around the moved strings.

Gate A has the same nine height gaps, plus a few older cron log lines and anchors kept on only one side after the 55-block inbox trim. Transfer quantities and event amounts still match. Source: the `regions` and `stringMultisets` objects in [semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json).

Attempt 3 copied those nine `Block-Height` values from the target checkpoint and decoded 32-byte anchors to the ASCII reference stored on the checkpoint. Both gates then matched the checkpoint memory hash: A `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1`, B `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`. The evidence labels that copy as not an independent byte gate. The independent replay is the gateway-height run above, and its memory hash does not match. Source: [evidence/p6/20261017T052333Z-w-eval/gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json), attempts 3 and 5.

Nonce 2074518 was then accepted as the replay start. `independent_byte_gate` is false. `semantic_gate` is `passed`. The earlier rejection file was not overwritten. Source: [evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json](../evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json).

### Checkpoint bound to the tail

Nonces 2074400..2075923 are 1524 assignments, 0 missing, 0 conflicts. The hash chain matches on 1523 of 1523 links and reaches the P1 tail hash `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE`. The Assignment and Hash-Chain tags on the checkpoints at 2074508, 2074510, and 2074518 match the index. Source: [evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md](../evidence/p4-tail/20261017T052614Z-w-tail/SUMMARY.md) and [range-manifest.json](../evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json).

### P7 tail replay — one run is still short of the tail

The main replay starts at the nonce 2074518 checkpoint and walks toward 2075923, including crons, with gateway block timestamps as the cron `Block-Height` source. Its last saved cursor is stream `next_index` 10400 of 39065, memory SHA-256 `b3bd4ffd310420c737ee9140a8c265a386629dae1fe041b917cb3dd2db0980af`, 0 handler errors. The last assignment inside that save is nonce 2075073 at stream index 9834. This save is not the shutdown snapshot. Source: [evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json).

A second replay, described in section 6, has reached nonce 2075923. Its final memory hash has not been compared with this running replay.

### P8 — holders at the checkpoint, not at the tail

The classification is the nonce 2074518 balance map: 7614 addresses, raw sum `189487568412204611`. It was not repeated on the tail table. `classification_sourced` stays false. Source: [evidence/p8/20261017T0906Z-w-p8/SUMMARY.md](../evidence/p8/20261017T0906Z-w-p8/SUMMARY.md) and [stats.json](../evidence/p8/20261017T0906Z-w-p8/stats.json).

`transactions(ids)` on `https://arweave.net/graphql`, batches of 100. `Type=Process` is a process. A successful query with no edge is labeled `wallet`. That label is an empty id query, not an identified person. Five balance keys are not 43-character Arweave ids (`AccountCreator`, two `0x` addresses, `SwapRequest`, `undefined`) and are `invalid_id`.

| Role at nonce 2074518 | Addresses | Raw amount |
| --- | ---: | --- |
| wallet | 5273 | `186296155097251128` |
| pool | 72 | `2427591802661553` |
| unknown_process | 369 | `402625751820531` |
| lock | 2 | `250346157301342` |
| agent | 1889 | `100080610148413` |
| lending | 1 | `7725686192460` |
| token_process | 1 | `1880007389099` |
| pool_candidate | 2 | `862198877788` |
| invalid_id | 5 | `301100562297` |

Pools named Botega: 53 addresses, raw `1742171823546173`. Pools named Permaswap: 19 addresses, raw `685419979115380`. No holder was classified as a bridge. LP shares and lock beneficiaries were not recovered. A pool balance is not an end-user claim.

Names that are on chain, with the local config excerpt cited from [local-configs.json](../evidence/p8/20261017T0906Z-w-p8/local-configs.json):

- Lending: [`fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0`](https://arweave.net/fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0), Name `LiquidOps Q Arweave`, raw `7725686192460` at the checkpoint.
- Pool: [`_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4`](https://arweave.net/_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4), Name `qAR:wAR:30`, raw `1934348814863` at the checkpoint.
- Locks, from the Name tag, medium confidence: `KbUW8wkZmiEWeUG0-K8ohSO82TfTUdz6Lqu5nxDoQDc` (Name `NAB Stake and Mint`, raw `250296157301342`) and `hgj136rPMZOV_ABlXeOpwl91jHGGz1l0ZXwI9Hf2HHk` (Name `aoVest-Vesting-Process-1732572394108-a120g7`, raw `50000000000`). Source: [pools-locks-bridges.json](../evidence/p8/20261017T0906Z-w-p8/pools-locks-bridges.json).

The largest checkpoint wallet is `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8`, raw `180243716191492791`. An identity check was stopped before any judgment. The role stays `wallet`. Source: [evidence/p8-whale/20261017T094030Z-w-whale/SUMMARY.md](../evidence/p8-whale/20261017T094030Z-w-whale/SUMMARY.md).

The tail report's class map is coarser. [recovery/p10/build_report.py](../recovery/p10/build_report.py) maps `wallet` to `user`, `pool_candidate` to `pool`, and `token_process` to `process_unknown`. `agent`, `lending`, and `invalid_id` are not in that map. A process with no mapped role becomes `process_unknown`. An `invalid_id` row with `is_process` false becomes `user`. That is why the tail report shows 5278 `user` rows (5273 wallets plus 5 invalid ids), 74 `pool` rows (72 pools plus 2 candidates), 2 locks, 0 bridges, and 2261 `process_unknown` rows (369 unknown processes, 1889 agents, the lending row, the token process, and one tail address that is absent from the checkpoint file).

### P9 — collateral is unknown

The live handlers are version 0.16.0, loaded by Eval nonce 1977055, message [`eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA`](https://arweave.net/eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA) (83536 bytes, SHA-256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`). `Denomination` is 12. Supply is the sum of the global `Balances` table. The action name is `Total-Supply`. There is no separate `TotalSupply` global. A missing balance key is answered with the string `0`. That string is a handler response, not a recovered ledger row.

Nonce 1977061 sets `DEPOSITS_ENABLED = false` ([`xkyG1_Gexl06pnLQ-2j5Du6MC4rAb6CaUrslgs_omVw`](https://arweave.net/xkyG1_Gexl06pnLQ-2j5Du6MC4rAb6CaUrslgs_omVw)). Nonce 1977062 sets `WITHDRAWALS_ENABLED = false` ([`m1n3dJfy5iZ0ZYO2PWQi9JCuQH_Kr-VXfmR1NmSm69Q`](https://arweave.net/m1n3dJfy5iZ0ZYO2PWQi9JCuQH_Kr-VXfmR1NmSm69Q)). Nonce 1977063 sets `TRANSFERS_ENABLED = true` ([`gaBFkKOA7cKc5cF3LxoygCkgu90z7tGVAG_nJreDgO8`](https://arweave.net/gaBFkKOA7cKc5cF3LxoygCkgu90z7tGVAG_nJreDgO8)). With those flags, deposit, mint, unwrap, and withdraw error. Transfer stays allowed. The 0.16.0 source on that path does not name a collateral asset id or a native-AR holder. Collateral asset, holder, and raw amount are unknown. Unknown is not zero. Source: [evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md](../evidence/p9-prep/20261017T051439Z-w-src/SUMMARY.md) and [handlers.md](../evidence/p9-prep/20261017T051439Z-w-src/handlers.md).

No `collateral.json` was given to the tail report. `delta_raw` is null and the status is `unknown`. Source: [evidence/p10/20261017T0954Z-fast-tail/reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json). A separate collateral worker has not published a result in this commit.

The tail assignment itself, nonce 2075923, inserts one address into `ao.authorities` and then removes the first entry. The handler review says it does not touch `Balances`. Source: the same P9 summary.

### Side check — public compute-unit folder

The folder that answered is `https://drive.google.com/drive/folders/1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`. The folder id written in [GOAL.md](../GOAL.md) returned HTTP 404. The inventory has 1113 files, of which 1012 are checkpoint binaries. qAR and the separate APUS process are absent from those 1012 names. APUS was not reconstructed. The CU source in the folder is permaweb/ao commit `0db88a45` with `@permaweb/ao-loader` locked at 0.0.44. Its cron `Block-Height` algorithm is the same one the evaluator uses, so that tree does not by itself explain the nine height gaps. Four of 18 local pool ids appear in the folder. The priority pool file for `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` was not downloaded, and its reported SHA-256 was not checked against local bytes. Fifty-four processes that hold qAR at nonce 2074518 intersect the folder. None of those checkpoint files were saved. Source: [evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md](../evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md) and [inventory.json](../evidence/side-d/20261017T0856Z-w-drive/inventory.json).

### P10 — report builder, dry run, then the tail table

The dry run is nonce 2074518: 7614 rows, sum `189487568412204611`, equal to that checkpoint's supply. Collateral is unknown. Every row was left `process_unknown` in that dry run. It is not the tail ledger. Source: [evidence/p10-dryrun/20261017T091010Z-w-report/SUMMARY.md](../evidence/p10-dryrun/20261017T091010Z-w-report/SUMMARY.md).

The tail table is section 5.

## 4. Evaluator

Pinned on one Linux server.

| Item | Value | Source |
| --- | --- | --- |
| Package | `@permaweb/ao-loader` 0.0.44 | [evidence/p6/20261017T052333Z-w-eval/evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json) |
| Node | v22.22.0 | same file |
| Node 22 distribution SHA-256 | `9aa8e9d2298ab68c600bd6fb86a6c13bce11a4eca1ba9b39d79fa021755d7c37` | same file |
| Lockfile | [recovery/p6/package-lock.json](../recovery/p6/package-lock.json), SHA-256 `e5a7d53067caca949e1095dd7f52c81d79c4d30d2ed1746de11cc6c1c352b27f` | same file |
| CU semantics | permaweb/ao [`0db88a45aabeb5e88471e5c263790fa51a563461`](https://github.com/permaweb/ao/blob/0db88a45aabeb5e88471e5c263790fa51a563461/servers/cu/src/domain/lib/loadMessages.js) (2026-02-22), `servers/cu/src/domain/lib/loadMessages.js` | same file |
| Module | `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`, SHA-256 `164c0859e796d30f682944be8bdd544a1292e9140f6f2998ce5ef93e2184a8c8` | [module.json](../evidence/p2/20261017T1645Z-p2a/module.json) |
| Memory limit | tag `500-mb`, 524288000 bytes | [evidence/p6/20261017T054635Z-p6-gate/evaluator.json](../evidence/p6/20261017T054635Z-p6-gate/evaluator.json) |
| Compute limit | `9000000000000` | same file |
| Process heap allowance | 8192 MiB, so the loader can hold the 428146688-byte memory | the `command` field of the w-eval evaluator file |
| Checkpoint memory | 428146688 bytes | [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json) |

Commit `0db88a45` was chosen because it is the tree from the day before checkpoint nonce 2074518. The CU lockfile at that commit pins `@permaweb/ao-loader` 0.0.44. In that history, `loadMessages.js` last changed on 2025-11-13. The hash-chain function in section 2 was read from a different, later commit, and that difference is recorded in [recovery/hashchain.py](../recovery/hashchain.py).

### How crons are built

The process tags are `Cron-Interval=5-minutes` and `Cron-Tag-Action=Cron`. A time-based cron matches when `(timestamp_in_seconds - origin_in_seconds) % 300 == 0`. The origin second itself is not a tick. `cronMessagesBetween` walks one second at a time from the left assignment's block timestamp up to, and not including, the right assignment's block timestamp. When the walk reaches a new block, that block's height becomes the cron message's `Block-Height`. The code in this repository is [vendor/drive-cu/src/domain/lib/loadMessages.js](../vendor/drive-cu/src/domain/lib/loadMessages.js), functions `isTimestampOnCron` and `cronMessagesBetweenWith`, from the same `0db88a45` tree.

The scheduler did not return this process's origin. The public scheduler host failed DNS, and the follow-up response was HTTP 403. The cron phase is taken from the three checkpoint timestamps, which are all `second % 300 == 283`. The process block second 1726164008 is phase 8 and does not emit those timestamps. The origin used is `1726163983000` milliseconds. Any origin second congruent to 283 modulo 300 selects the same crons in 2026. Source: `originMs` and `originReason` in [evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json).

The tail replay records its height source as gateway block timestamps. Source: [evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json). Crons after the tail assignment are not generated.

Balance and supply reads run on a copy of memory. The historical memory file is not replaced by the read. Source: `readPath` in [semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json).

## 5. The tail table

The table is [evidence/p10/20261017T0954Z-fast-tail/ledger.csv](../evidence/p10/20261017T0954Z-fast-tail/ledger.csv).

| Item | Value |
| --- | --- |
| Cutoff | epoch 0, nonce 2075923, after that assignment |
| Rows | 7615 |
| Raw sum | `189487568412204611` |
| Total-Supply, read separately | `189487568412204611` |
| Sum equals supply | true |
| Ledger delta | `0` |
| Human supply at 12 decimals | `189487.568412204611` |
| Bad rows omitted | 0 |
| Final memory SHA-256 | `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` |
| Memory bytes | 428146688 |
| Stream items applied | 39065 |
| Handler errors | 0 |
| Resumed from main-replay index | 8400, memory SHA-256 `78fc3856ea0e4dc6e195463e18a3e6f5810c4c39febcdbc4fc9a0f181a224bfb` |

The supply was read from the replay's `Total-Supply` message data. It was not defined as the sum of the table. Source: [evidence/p10/20261017T0954Z-fast-tail-inputs/supply.json](../evidence/p10/20261017T0954Z-fast-tail-inputs/supply.json) and [replay.json](../evidence/p10/20261017T0954Z-fast-tail-inputs/replay.json).

File hashes, from [manifest.json](../evidence/p10/20261017T0954Z-fast-tail/manifest.json):

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `evidence/p10/20261017T0954Z-fast-tail/ledger.csv` | 3397765 | `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2` |
| `data/raw/fast/tail/balances.json` (gitignored) | 402362 | `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` |

The 0954 draft said the other replay's final memory hash had not been cross-checked. That cross-check is now done. Main, fast, and the clean clone share memory SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` (`evidence/p7/20261017T1718Z-p7-replay-read/`, `evidence/p10/20261017T1718Z-gate-recompute/`). There is still no pushed checkpoint at nonce 2075923. The draft's own `goal_complete` remains false. The amended `goal_complete` is true.

### Canonical balance hash

The canonical balance hash is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. The from-scratch guide is [repro/README.md](../repro/README.md). Current results and `repro/EXPECTED.json` record the same value. The table in this section is the 0954 snapshot. The earlier pending mark is superseded.

### Classes on the tail table

These are the report's classes, not the P8 roles. The mapping is in section 3. `classification_sourced` is false. `user` is the report's name for a P8 `wallet` or `invalid_id`. It is not a checked identity.

| Class | Rows | Raw amount |
| --- | ---: | --- |
| user | 5278 | `186393679140702692` |
| pool | 74 | `2330669314779690` |
| process_unknown | 2261 | `512873799420887` |
| lock | 2 | `250346157301342` |
| bridge | 0 | `0` |

Source: [evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md](../evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md).

Eleven addresses differ from the nonce 2074518 map. Ten are in `holder_balance_mismatches`. One address is new. The raw differences, including the new address, sum to 0, which matches the unchanged supply. The list does not by itself say which messages moved the units. Source: [reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json) and [evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json).

| Address | Raw at 2074518 | Raw at 2075923 |
| --- | --- | --- |
| `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` | `180243716191492791` | `180398401009414645` |
| `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4` | `381553671374914` | `291712135061413` |
| `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` | `320089670049015` | `312546942799043` |
| `wWq05ZZX6Jj2p9wW59oZ6lMF_KdW754zywqLa9n8INA` | `149454420015180` | `0` |
| `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948` | `56636111316938` | `123291631310116` |
| `MmhScGp35v-9veB1ufbXRDoaDleTi_z3V_vZTjA8bnU` | `4725068954918` | `0` |
| `AxpxHZmHQhF25FkVSVX0T877PP2WUi7I46nmQaECUHI` | `0` | `31129166766473` |
| `3biQvRjIp_9Qz1L9D3SJ9laK4akCkP-8bvAo3pQ6jVI` | `3003053338103` | `2602630141925` |
| `F9dWqoqSMzC3oyigfhezyT0fzc5BjhIYVSqcQWOgDq8` | `561743870384` | `0` |
| `yEGUy_Dl229kp8cDtJ8wxekm0cqe2t68PhLrHPoHWQY` | `505328951756` | `0` |
| `wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4` | absent | `561743870384` |

`cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` is still class `user` because P8 called it `wallet`. Its identity was not checked.

### Why `goal_complete` is false

This section describes the 2026-10-17 draft. The 2026-10-18 amendment supersedes it: `goal_complete` is true, and the unmet legacy checks below are no longer the completion rule.

[REPORT.md](../evidence/p10/20261017T0954Z-fast-tail/REPORT.md) marks four checks unmet:

- Nonce continuity from the first assignment through the tail. The checkpoint-to-tail hash chain is continuous. Before the checkpoint, 132 nonces in 50000..99999 and 627 nonces in 100000..149999 are explicit holes, and 150000..2074399 was not indexed.
- Replay of every present assignment up to the tail, checked against a pushed result that carries enough state. The semantic check stops at nonce 2074518. The independent byte gate did not pass. There is no pushed memory at nonce 2075923.
- Pool, lock, and bridge addresses separated from end-user wallets, each with a source that satisfies the goal. The P8 file is the checkpoint map. One tail address is absent from it. `classification_sourced` is false.
- Collateral asset, holder, raw amount, and the gap against supply. The gap is unknown.

The row count, the 12-decimal formatting, and the sum-versus-supply check are met for this table.

## 6. Cross-checks

### Balances, address by address, on the way into the checkpoint

Gates A and B each compared 7614 addresses. Both diffs are 0. Both supplies are `189487568412204611`. Source: [semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json).

### Memory hash, once the nine compute-unit heights are used

Attempt 3's memory hashes equal the checkpoint tags. That run copies the nine heights out of the target checkpoint, so it is not an independent byte gate. Source: [gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json).

### Cron-inclusive replay and assignment-only replay

The live 0.16.0 cron handler does not write `Balances`. Deposits and withdrawals are already closed inside the checkpoint. In nonces 2074519..2075923 the assignment actions are 703 `Transfer`, 701 `Event`, and 1 `Eval`. Deposit, mint, unwrap, withdraw, and `BalanceResponse` counts are 0. One cron applied to the checkpoint changed 0 balances. Source: [evidence/doc/20261017T1037Z-w-doc/fast-excerpt/cron-handler.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/cron-handler.json).

The assignment-only replay of those 1405 assignments and the cron-inclusive replay produced the same balance bytes. SHA-256 of both balance JSON files is `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`, which is the hash in the P10 manifest. The memory images differ. Assignment-only memory SHA-256 is `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7`. Cron-inclusive memory SHA-256 is `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The assignment-only run is marked as a fast estimate, not the formal memory result. Sources: [exact-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/exact-ledger.json), [assignment-ledger.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json), and [provenance.json](../evidence/doc/20261017T1037Z-w-doc/provenance.json).

Those four JSON files are byte copies taken while writing this note. The fast worker had not committed them. This commit is not a merge of that worker. [provenance.json](../evidence/doc/20261017T1037Z-w-doc/provenance.json) records the copy hashes.

### Two replays, intermediate memory hashes

A 480-item stretch of the cron-inclusive replay, stream index 8000 through 8480, matched 47 of 47 memory hashes already logged by the main replay, including the save at index 8399. That save's SHA-256 is `78fc3856ea0e4dc6e195463e18a3e6f5810c4c39febcdbc4fc9a0f181a224bfb`, the same value the main replay recorded at `next_index` 8400. Source: [verify-480.json](../evidence/doc/20261017T1037Z-w-doc/fast-excerpt/verify-480.json). The main cursor note of the same fact is [evidence/p7/20261017T0942Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0942Z-p7-tail-progress/cursor.json).

When the cron-inclusive replay finished, the main cursor was still `next_index` 10400, memory `b3bd4ffd310420c737ee9140a8c265a386629dae1fe041b917cb3dd2db0980af`. Source: [evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json](../evidence/p7/20261017T0954Z-p7-tail-progress/cursor.json), field `fast_tail_sha_crosscheck` = `not done`. That progress note is historical. The finished main replay memory matches the fast replay and the clean clone: `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` (`evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`). See Current results.

### Independent algorithm check, and a from-scratch reproduction

Both later finished. The Python recompute matches all 7615 addresses (`evidence/p10-indep/20261017T104141Z-w-indep/result.json`). The clean-clone canonical hash is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca` (`evidence/repro/20261017T120218Z-w-repro/result-offset-0.json` and `repro/EXPECTED.json`). They are not in progress.

## 7. Known issues and assumptions

**Five Transfer bodies were not recovered as data.** During the semantic-gate replay, five `Transfer` messages have GraphQL `data.size` 0. `https://arweave.net` returned a 2285-byte HTML shell for each, all SHA-256 `2abbd9f95f88a91c43ddb5e4f84ff9779adca5ce44c775d684b4729ceca333c7`. The replay used an empty string as `Data`. The saved files are listed in [evidence/p6/20261017T052333Z-w-eval/manifest.json](../evidence/p6/20261017T052333Z-w-eval/manifest.json). The note is in [SUMMARY.md](../evidence/p6/20261017T052333Z-w-eval/SUMMARY.md). The ids are:

- [`0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw`](https://arweave.net/0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw)
- [`4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y`](https://arweave.net/4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y)
- [`OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q`](https://arweave.net/OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q)
- [`iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY`](https://arweave.net/iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY)
- [`ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw`](https://arweave.net/ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw)

This does not say the original data item was empty. It says the gateway did not return data, and the replay proceeded with an empty string. These five sit in the gate window, before nonce 2074518. The tail replay starts from the checkpoint memory, so they are inside the snapshot rather than re-executed on the way to the tail.

**Cron height source.** The independent replay uses the height implied by current gateway block timestamps. Those heights are 1 to 3 above the nine cron heights stored in the checkpoint. The tail replay uses the same gateway source. Copying the checkpoint's nine heights makes the gate memory hash match, and that copy is not an independent check.

**Classification time.** Roles were assigned from the nonce 2074518 map. The tail map has 7615 rows. Eleven raw amounts differ. The report keeps the tail amount and the checkpoint role.

**LegacyNet has stopped.** This work does not restart it, does not start a scheduler, and does not publish new assignments.

**Collateral quantity is unknown.** It is not zero, and it is not the token supply.

**What was trusted.**

- The compute-unit signer `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`, because it is the address the public CU endpoint returned when P5 saved the body. The body hash is `cu_body_sha256` `5f42df49481944607d1d1dd8d8198684091975a2f1043b8c8cdcf61911a4d398` in [search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json). The selected checkpoint's ANS-104 signature verifies under that owner. The other two checkpoint signers were not used as the replay start.
- Gateway bytes for the module, the assignments, the messages, and the block timestamps used as cron heights. Two gateways agreed on the module bytes. The module RSA signature was not checked.
- The hash-chain formula from a 2026 reading of `gen_hash_chain`, checked empirically on the links that were present. It was not checked by running the 2024 scheduler binary.
- The checkpoint memory as the state at nonce 2074518, after the semantic comparison. The independent byte comparison did not pass.

**What was not trusted.** A model's statement, an empty `Balances` Output, a GraphQL miss as proof of absence, or a local memory image that has only a hash and no bytes.

## 8. How the work was done

The recovery was written with AI coding agents. Claude (Anthropic) coordinated the work, reviewed evidence, and corrected course: the full nonce index gave way to the checkpoint, and the failed byte gate gave way to the semantic balance comparison. Several Grok (xAI, grok-4.7) command-line workers ran at the same time. Each worker wrote evidence on its own git branch. The main session reviewed a branch and merged it. Workers did not publish the claim list and did not move collateral.

Branches whose evidence is in this tree include the tail-window index, the evaluator gate, the handler and collateral-source review, the holder classification, the stopped identity check, the Drive inventory, the report builder, and the tail table. The fast replay's own branch is not merged. Section 6 copies the four small JSON files this note cites and says so.

A conclusion that matters was checked by more than one worker or more than one method. Examples that are in this commit:

- The checkpoint's signature, signer, gzip hash, and tag hash (P5), then the assignment and hash-chain bind (tail index), then the balance comparison (evaluator).
- The tail balance sum, computed from the rows, against a separate `Total-Supply` read.
- Overlapping memory hashes between the main replay and the second replay, 47 of 47 through stream index 8480.
- The same balance bytes from a cron-inclusive replay and an assignment-only replay.

AI-generated code and conclusions were accepted when a hash, an independent replay, or an address-by-address comparison matched. They were not accepted on the model's say-so. The final memory hash and the canonical reproduction hash have since matched. Still open, and not amended gates: the collateral amount, and the legacy `classification_sourced` flag. Unidentified processes stay unknown.

## 9. How to reproduce

The from-scratch reproduction guide is [repro/README.md](../repro/README.md). Run it from the repository root. It talks only to public gateways. The earlier pending mark is superseded.

What a later reproduction has to pin is already in the tree:

- Module id and SHA-256 in [evidence/p2/20261017T1645Z-p2a/module.json](../evidence/p2/20261017T1645Z-p2a/module.json).
- Evaluator version, lockfile hash, Node version, and CU commit in [evidence/p6/20261017T052333Z-w-eval/evaluator.json](../evidence/p6/20261017T052333Z-w-eval/evaluator.json).
- Checkpoint id `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk` and uncompressed SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`.
- Tail assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`.
- The message window 2074400..2075923 in [evidence/p4-tail/20261017T052614Z-w-tail/](../evidence/p4-tail/20261017T052614Z-w-tail/).
- Cron origin `1726163983000` and gateway block timestamps as the height source, unless the reproduction is explicitly the non-independent height-copy experiment.

Scripts that implement pieces of this are under [recovery/](../recovery/). They are not a single reproduction entry point. Bulk bytes under `data/raw/` are not in git. The manifests name them by hash.

## 10. What a reviewer should check first

1. **Checkpoint bytes.** Download [`ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`](https://arweave.net/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk), gunzip, and confirm SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` and length 428146688. Compare with [replay-start.json](../evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json).
2. **Signer.** Confirm the ANS-104 signature under owner `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`, and compare that owner with the address served by `https://cu.ao-testnet.xyz/`. The saved body hash is in [search-manifest.json](../evidence/p5/20261017T053304Z-p5-checkpoints/search-manifest.json).
3. **Hash chain from the checkpoint to the tail.** Recompute `gen_hash_chain` with [recovery/hashchain.py](../recovery/hashchain.py) across [evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json](../evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json). Expect 1523 matches and 0 failures, ending at `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE`.
4. **The byte gate really failed, and why.** Read attempts 3 and 5 in [evidence/p6/20261017T052333Z-w-eval/gate.json](../evidence/p6/20261017T052333Z-w-eval/gate.json) and the nine-height note in [semantic.json](../evidence/p6/20261017T052333Z-w-eval/semantic.json). Attempt 3 matches only because it copies checkpoint heights.
5. **The balance gate.** Confirm 7614 addresses, 0 diffs, supply `189487568412204611`, and balance JSON SHA-256 `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967` for gate B. Ignore Output `[]`.
6. **The tail sum.** Sum the `raw_balance` column of [ledger.csv](../evidence/p10/20261017T0954Z-fast-tail/ledger.csv) with integers. Expect `189487568412204611`, 7615 rows, and file SHA-256 `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2` (3397765 bytes). The refreshed tail file is [evidence/p10/20261017T1047Z-fast-tail/ledger.csv](../evidence/p10/20261017T1047Z-fast-tail/ledger.csv), SHA-256 `abaf6d70d279c16b5acee1825c25af70bef018a0b37e3a9c525471074ad2722c` (4212717 bytes). Do not use floating point. The canonical hash is not either of these file hashes.
7. **The holes were not zero-filled.** The 132 missing nonces are in [evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json](../evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json). The 627 are in [evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json](../evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json). Nonces 150000..2074399 are unindexed.
8. **Classification is not the tail map.** Compare the eleven rows in section 5 with [reconciliation.json](../evidence/p10/20261017T0954Z-fast-tail/reconciliation.json). Confirm `classification_sourced` is false and that `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` was not identified.
9. **Collateral is unknown.** Confirm `collateral.status` is `unknown` in the reconciliation file. Do not treat supply as the collateral amount.
10. **This is not a claim list.** `publish_claims` and `move_collateral` stay false. The 0954 draft's `goal_complete` is false. The amended recompute's `goal_complete` is true ([evidence/p10/20261017T1954Z-gate-recompute-amended/](../evidence/p10/20261017T1954Z-gate-recompute-amended/)). The final memory cross-check matches, and the canonical hash is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. See Current results.

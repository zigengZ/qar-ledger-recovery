# qAR balance ledger

Chinese: [README.zh.md](README.zh.md).

This repository is the qAR balance ledger for process [`NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`](https://arweave.net/NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8) after the last assignment that was pushed to Arweave. The on-chain `Name` tag is `local-t-w-001` (`GOAL.md`, `STATE.md`). The tail is epoch 0, nonce 2075923, assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`, timestamp 2026-07-04T06:19:55.380Z (`docs/RECOVERY.md`, `repro/EXPECTED.json`). The table has 7615 addresses, of which 2239 are nonzero. Total supply `189487568412204611` equals the sum of the raw balances. At 12 decimals that supply is `189487.568412204611` (`repro/EXPECTED.json`, `evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`, `docs/RECOVERY.md`).

`goal_complete` is true under the 2026-10-18 checkpoint amendment (`GOAL.md`, `evidence/p10/20261017T1954Z-gate-recompute-amended/`). That means the ledger is ready for public audit. It is not a claim list and not an instruction to distribute. `publish_claims` is false. `move_collateral` is false.

## Checkpoint, replay, and hashes

The replay starts at the compute-unit checkpoint `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`, nonce 2074518, signer `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`. Uncompressed checkpoint memory SHA-256 is `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` (`repro/EXPECTED.json`).

From that checkpoint through nonce 2075923 the replay applies 39065 items: 1405 assignments and 37660 crons (`repro/EXPECTED.json`, `evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`). The checkpoint-to-tail hash chain matches 1523/1523 links (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`).

Final memory SHA-256:

`25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`

Canonical balance SHA-256:

`0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`

Both values are in `repro/EXPECTED.json`. The canonical file keeps nonzero balances only, sorts addresses, stores each raw amount as a string, and is compact JSON with one trailing newline (`repro/README.md`). `docs/RECOVERY.md` records the same pair in its current-results section. The 2026-10-18 amendment records this hash as the agreed tail hash (`evidence/p10/20261017T1954Z-gate-recompute-amended/`).

## Independent checks

| Route | Result | Evidence |
| --- | --- | --- |
| Precise WASM replay | Nonce 2075923, 0 handler errors, 7615 rows, raw sum equals the separate Total-Supply read `189487568412204611`, final memory SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The main-session replay later matched this memory sha. See the next table. | `evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md`, `evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md` |
| Assignment-only replay | The 1405 assignments produce the same balance bytes as the cron-inclusive replay. Both balance JSON files are SHA-256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`, with 0 address or value differences. Assignment-only memory SHA-256 is `c328ab18354b7325050285a8b09e9de5e83a42d048653670cbc990d80fc7d3a7`. That run is a fast estimate, not the formal memory result. | `STATE.md`, `docs/RECOVERY.md`, `evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json` |
| Python recompute, module not executed | 703 transfers applied, 0 rejected. All 7615 addresses and raw balances match the fast tail ledger. | `evidence/p10-indep/20261017T104141Z-w-indep/SUMMARY.md` |
| Clean clone from public gateways | Memory SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. Canonical balance SHA-256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`, 2239 nonzero addresses, matching the fast tail nonzero rows. Full safe mode was not run. The first 10 items match between the unmodified loader and the in-place mode: memory SHA-256 `4e341435f023aa41f27fc2b1dbb764c14c30ca39b13f14a02704bac722562960`. | `evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`, `repro/EXPECTED.json` |
| Cron block height +3 and −3 | The canonical balance hash stays `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. Memory SHA-256 changes to `d0dd22f387150aa3e894106cb5d8dde08783ea30974cfd78ea632e9a1c46bc20` at +3 and `6b11be84807469cebb5201867800cdbfcb21266ca14ae65322cff772be126c92` at −3. | `evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`, `repro/README.md` |

<!-- MAIN_REPLAY_SHA: match -->

| Route | Result | Evidence |
| --- | --- | --- |
| Main-session slow replay (memory copied on each item), final sha | Matches the fast replay and the clean clone. Final memory SHA-256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. Last assignment nonce 2075923. Canonical balance SHA-256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. Full safe mode was not run. | `evidence/p7/20261017T1718Z-p7-replay-read/`, `evidence/p10/20261017T1718Z-gate-recompute/` |

## Check it yourself

### Ledger hash

The tail CSV is `evidence/p10/20261017T1047Z-fast-tail/ledger.csv` (7615 rows). The replay balance JSON is `data/raw/fast/tail/balances.json`, gitignored, 402362 bytes, SHA-256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15` (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`). That file hash is the full map. The canonical hash drops zeros and sorts keys.

From the repository root:

```python
import csv, json, hashlib
body = dict(sorted((a, r) for a, r, *_ in list(csv.reader(open("evidence/p10/20261017T1047Z-fast-tail/ledger.csv", encoding="utf-8-sig")))[1:] if r != "0"))
print(hashlib.sha256((json.dumps(body, separators=(",", ":")) + "\n").encode()).hexdigest())
```

The print is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`.

### From-scratch replay

`repro/README.md` is the procedure. From the repository root, with Node.js v22.22.0:

```sh
./repro/run.sh
```

The script uses public gateways, default `https://arweave.net`, then `ar-io.dev`, `vilenarios.com`, and `turbo-gateway.com`. GraphQL also tries `arweave-search.goldsky.com`. It downloads checkpoint `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk` from `/raw/<id>`, checks the ANS-104 signature and signer `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`, checks the hash chain through tail `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`, and replays nonces 2074519..2075923, including crons, with `@permaweb/ao-loader` 0.0.44. Output is `repro/work/out/`. `out/balances.sha256` is `canonical_balances_sha256` in `repro/EXPECTED.json`.

The published run did not execute `./repro/run.sh --mode safe`. After the zero-offset run, the height checks in that README are:

```sh
./repro/run.sh --cron-height-offset 3
./repro/run.sh --cron-height-offset -3
```

### Website

[https://qar-balances.zigza.xyz](https://qar-balances.zigza.xyz) serves this tail ledger. Address lookup is [#/lookup](https://qar-balances.zigza.xyz/#/lookup). The verify page [#/verify](https://qar-balances.zigza.xyz/#/verify) shows the check timeline and hashes the loaded balances in the browser with SubtleCrypto. The same canonical hash is in the footer (`web/SUMMARY.md`).

## Repository map

- [docs/RECOVERY.md](docs/RECOVERY.md) and [docs/RECOVERY.zh.md](docs/RECOVERY.zh.md): full method, failed checks, and missing inputs.
- [docs/PUBLICATION.md](docs/PUBLICATION.md): publication note.
- [evidence/](evidence/): phase records. The tail report is [evidence/p10/20261017T1047Z-fast-tail/](evidence/p10/20261017T1047Z-fast-tail/).
- [recovery/](recovery/): replay and report scripts.
- [repro/](repro/): from-scratch replay. Expected hashes are [repro/EXPECTED.json](repro/EXPECTED.json).
- [web/](web/): static ledger site. `node_modules/` and `dist/` are not committed.
- [audit/REDACTIONS.md](audit/REDACTIONS.md): what was removed from evidence text before publication.
- [GOAL.md](GOAL.md), [STATE.md](STATE.md), and [RECOVERY_PLAN.md](RECOVERY_PLAN.md): work logs. `STATE.md` is the cursor.

Work ran in Claude and Grok sessions. Queries used the public gateways named in `docs/RECOVERY.md`: `https://arweave.net`, `https://turbo-gateway.com`, `https://ar-io.dev`, `https://vilenarios.com`, and GraphQL at `https://arweave.net/graphql`. `https://arweave-search.goldsky.com/graphql` returned HTTP 307 and followed to `https://arweave.net/graphql`.

## What the numbers mean

**Trust assumption.** The checkpoint was signed by the LegacyNet CU signer `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`. Early scheduling on Arweave has holes, so the ledger cannot be independently recomputed from genesis to that checkpoint. P4 is closed as superseded by the checkpoint, not as complete. This limitation does not block `goal_complete`.

**Issues.** After this repository is public, anyone may open an issue. There is no fixed review period. If a balance changes, the canonical hash changes and the change is recorded in STATE.md. Any distribution decision is made by the collateral holder, outside this repository.

**Language.** Evidence records are kept in the language they were written in, English or Chinese. Records written mainly in Chinese have English translations in [docs/evidence-en/](docs/evidence-en/), and the originals are authoritative. [evidence/README.md](evidence/README.md) indexes all evidence in both languages.

**Zero rows in the ledger.** The table has 7615 addresses. 5376 of them have raw balance 0 and are omitted from the canonical file (`evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`). Those zeros are keys present in `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`.

**An address that is not in the ledger.** `GOAL.md` says: "Missing rows are not zero." `docs/RECOVERY.md` says: "A missing row is not written as zero." The same note says a missing balance key is answered with the string `0`, and that string is a handler response, not a recovered ledger row. `STATE.md` says a lookup miss is `unknown`, not a balance of 0.

**Collateral.** Deposit and withdraw messages use native AR. There is no single holder. The custody wallet's whole balance is not separable collateral, the rest is commingled, and the separable raw amount is null (`evidence/p9/20261017T090508Z-w-collat/SUMMARY.md`, `evidence/p9/20261017T1720Z-p9-record/`). Reconciliation is outside this ledger. `collateral_sourced` and `collateral_reconciled` stay false and are not amended gates (`STATE.md`). The tail report's collateral gap is unknown (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`).

**Unwraps and deposits.** At nonce 2075923, `Unwraps` has 0 rows and `Deposits` has 0 rows. `UnwrapsCompleted` has 2234 rows, raw sum `272977038419623672`. `DepositsCompleted` has 4364 rows, raw sum `462464606831828283`. Those completed sums are table totals, not collateral held (`evidence/p9-unwrap/20261017T105845Z-w-unwrap/SUMMARY.md`).

**Classes.** The refreshed tail report counts (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`):

| Class | Rows | Raw amount |
| --- | ---: | --- |
| user | 5279 | `186394240884573076` |
| pool | 74 | `2330669314779690` |
| process_unknown | 2260 | `512312055550503` |
| lock | 2 | `250346157301342` |
| bridge | 0 | `0` |

`classification_sourced` is false. A `wallet` label is an empty id query that returned no edge, not an identified person. The report class `user` is the mapping of that wallet label. Locks taken from the Name tag are medium confidence. A pool balance is not an end-user claim (`docs/RECOVERY.md`). `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` stays role `wallet`. Its identity was not checked (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`). The tail classification added 1 address, changed 10 balances, and changed 0 roles (`STATE.md`).

**Still open.** Nonce continuity from the first pushed assignment is unmet: 759 explicit missing nonces, and 150000..2074399 is unindexed (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`). `evidence/p4/` has 120 directories, one per unresolved nonce. Each directory records one exact query that closed empty. Those directories are not missing ledger rows. `docs/RECOVERY.md` splits those holes into 132 nonces in 50000..99999 and 627 nonces in 100000..149999. The independent byte gate did not pass. The semantic balance gate at nonce 2074518 did pass (`docs/RECOVERY.md`, `STATE.md`). Five Transfer bodies before the checkpoint, nonces 2074509, 2074511, 2074513, 2074515, and 2074517, are empty on `https://arweave.net/raw/{id}`. The quantity is the Quantity tag. None of those nonces is in 2074519..2075923 (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`).

This repository does not move collateral and does not publish a claim list (`GOAL.md`). `publish_claims` and `move_collateral` are false (`evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`).

## Background

qAR is the AO LegacyNet token above, with 12 decimals. LegacyNet has stopped and is not coming back. On 2026-10-12, AOX excluded qAR from its wind-down because the ledger had not been obtained. wUSDC and wAR were included from checkpoint data. Permaswap noted the same exclusion. A requested final compute-unit state for this process was not in the shared checkpoint set, so the cutoff is reconstructed by replaying the public Arweave record through nonce 2075923 (`docs/RECOVERY.md`).

## Report a discrepancy

Open an issue. Include the address, the balance you believe is right, and the evidence you used.

## License

This repository (code and the `evidence/` data) is MIT. The exception is `vendor/drive-cu`, which keeps the upstream permaweb/ao Business Source License 1.1. See [vendor/drive-cu/LICENSE](vendor/drive-cu/LICENSE).

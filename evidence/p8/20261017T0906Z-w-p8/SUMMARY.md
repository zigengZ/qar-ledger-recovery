> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P8 holder classification

Run `20261017T0906Z`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. The module was not executed. `goal_complete` is false. Balances are the nonce 2074518 checkpoint map, 7614 addresses, raw supply `189487568412204611` (189487.568412204611 qAR at 12 decimals). The sum of classified raw balances equals that supply. Top 500 holders by raw balance were all queried. No `balances.json` exists under `data/raw/fast/` or `data/raw/p7/`, so this run was not repeated on a tail ledger.

## Conclusion

Ordinary wallets hold 186296.155097251128 qAR, 98.3157663894810268% of supply. One wallet, `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8`, holds 180243.716191492791 qAR, 95.1216576907023958% of supply. `transactions(ids)` returned no edge. `transactions(owners)` returned an ao `Type=Message` it signed, so the wallet label has that positive signature as well as the empty id query.

Pools hold 2427.591802661553 qAR (1.2811351282848566%) across 72 process ids. Botega names account for 1742.171823546173 qAR on 53 addresses. Permaswap names account for 685.419979115380 qAR on 19 addresses. Locks hold 250.346157301342 qAR on 2 addresses. The only lending row is LiquidOps oQAR, 7.725686192460 qAR. No holder was classified as a bridge. Pool balances are not split into LP shares.

## Highlighted addresses

LiquidOps oQAR `fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0` is rank 96, raw `7725686192460`, role `lending`, confidence high. The process tag `Name` is `LiquidOps Q Arweave`, `Type` is `Process`, module `zDRUJPd8JrnpMmsQaD-8tGALUyfNFVUNTUx17mfzFn0`. Source: a local config excerpt. Private repository paths and parameters are not stored. It is recorded as lending, not as an AMM pool.

Permaswap `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` is rank 180, raw `1934348814863`, role `pool`, confidence high. The process tag `Name` is `qAR:wAR:30`, `Type` is `Process`, module `Do_Uc2Sju_ffp6Ev0AnLVdPtot15rvMjP-a9VVaA5fM`. Source: a local config excerpt. Private parameters are not stored. `data/raw/drive-cu/overlap-rows.json` lists checkpoint `checkpoints/_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4_ts-1783146116188_ord-247049_bh-1951866.bin` with the same raw balance. That file is not `w-drive/evidence/side-d/overlap.json`.

## How roles were assigned

`transactions(ids)` in batches of 100 on `https://arweave.net/graphql`. `Type=Process` is a process. A successful query with no edge is a wallet, except five balance keys that are not 43-character Arweave ids (`AccountCreator`, two `0x` addresses, `SwapRequest`, `undefined`). Those are `invalid_id`. A failed query would have stayed `unqueried`; the final table has zero unqueried rows. Raw request and response bodies are under `<repo>/data/raw/p8/20261017T0906Z-w-p8/`.

Local config pools: all 18 distinct ids in the local pool excerpt are `Type=Process` and role `pool`. Commented rows stay pools with `config_status=commented`. Ids past the end of that excerpt were not invented. Further pools come from a process `Name` of `Botega LP ...`, a Permaswap name, or a `token:token:<fee>` name on the same module as an active config-confirmed Permaswap pool. That module is also used by non-pools, so the name shape is required; the module alone does not assign a pool.

`Botega Agent...` (and `Dexi Portfolio Agent`) is role `agent`, from the Name tag. Those 1889 processes hold 100.080610148413 qAR. They are not labeled pools.

Locks, from the Name tag only, confidence medium: `NAB Stake and Mint` (`KbUW8wkZmiEWeUG0-K8ohSO82TfTUdz6Lqu5nxDoQDc`, rank 10, 250.296157301342 qAR) and `aoVest-Vesting-Process-1732572394108-a120g7` (rank 831, 0.050000000000 qAR). No beneficiary list was recovered.

w-src candidates `vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4` (raw 0) and `KQhYTVaQ5tXcOQ3SrJiIt60_mdO0zAGUnT4snNwQs9U` (raw `862198877788`) stay `pool_candidate` at low confidence. The id query did not return `Type=Process` for either. The config pools above are the identified Botega and Permaswap processes. The qAR process itself is rank 183, role `token_process`, Name `local-t-w-001`, raw `1880007389099`.

369 processes stay `unknown_process`. The largest are `data-ownership-protocol-agent Bonding-Curve` (`AnbK4zzN6VE78QogW6OSxfne9DqdqJOXIU5KhMAuuCY`, 234.450881600000 qAR) and `Veritas2701250117` (121.605143413574 qAR). Names such as `qar_war_1_fp` were left unknown. Info queries for the unknown processes inside the top 500 did not supply a pool, lock, bridge, or lending tag. `Data-Protocol=ao` only marks an AO process.

## Numbers

| Role | Addresses | Raw qAR | Human qAR (12 decimals) | Share of supply |
| --- | ---: | ---: | ---: | ---: |
| wallet | 5273 | 186296155097251128 | 186296.155097251128 | 0.983157663894810268 |
| pool | 72 | 2427591802661553 | 2427.591802661553 | 0.012811351282848566 |
| unknown_process | 369 | 402625751820531 | 402.625751820531 | 0.002124813544203982 |
| lock | 2 | 250346157301342 | 250.346157301342 | 0.001321174573082006 |
| agent | 1889 | 100080610148413 | 100.080610148413 | 0.000528164517530253 |
| lending | 1 | 7725686192460 | 7.725686192460 | 0.000040771467264036 |
| token_process | 1 | 1880007389099 | 1.880007389099 | 0.00000992153419273 |
| pool_candidate | 2 | 862198877788 | 0.862198877788 | 0.000004550160651765 |
| invalid_id | 5 | 301100562297 | 0.301100562297 | 0.00000158902541639 |

| Provider | Addresses | Raw qAR | Human qAR | Share of supply |
| --- | ---: | ---: | ---: | ---: |
| botega | 53 | 1742171823546173 | 1742.171823546173 | 0.009194122010982343 |
| permaswap | 19 | 685419979115380 | 685.419979115380 | 0.003617229271866222 |

## Evidence

- `holders-classified.json` — every balance key once: address, raw balance, is_process, role, name, source, confidence
- `pools-locks-bridges.json` — 2341 rows whose role is not `wallet`
- `stats.json`, `local-configs.json`, `query-manifest.json`
- `recovery/p8/classify_holders.py` — rerun with `--balances` when a tail `balances.json` appears
- Raw GraphQL bodies, gitignored: `<repo>/data/raw/p8/20261017T0906Z-w-p8/`

Seven local files that label this process id as qAR are cited in `local-configs.json`. Private paths and parameters are not stored.

## Unfinished

- Tail `balances.json` under `data/raw/fast/` or `data/raw/p7/` is absent. This is not the shutdown ledger.
- `w-drive/evidence/side-d/overlap.json` and `roles.json` are absent.
- LP shares, lock beneficiaries, and nested ownership are unresolved. A pool balance is not an end-user claim.
- A wallet label from an empty `transactions(ids)` result is the prescribed test. It is not a positive identification of a person, except where an owner query is cited.
- 369 processes remain `unknown_process`.
- Collateral asset, holder, and raw amount are unknown. No claim list is published.

> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P8 tail holder classification

Run `20261017T1031Z-w-p8-tail`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. Ledger nonce 2075923. The module was not executed. Prior classification is nonce 2074518 at `evidence/p8/20261017T0906Z-w-p8/holders-classified.json`.

## Conclusion

The tail map has 7615 addresses and raw supply `189487568412204611` (189487.568412204611 qAR). Sum of classified balances equals that supply: True. Against nonce 2074518: 1 added, 0 removed, 10 balance changes, 7604 reused without a new id query. The raw deltas on added, changed, and removed addresses sum to 0.

Balance changes and the new address were queried with `transactions(ids)`. The first page returned 3 process ids. A second read of the other 8 ids returned 0 edges (`<repo>/data/raw/p8/20261017T1031Z-w-p8-tail/gql/ids/delta-absent.body`). Unchanged addresses keep the nonce 2074518 role, name, and sources. Their ranks follow the tail balance order.

## Movement since nonce 2074518

| Address | Change | Old raw | New raw | Delta raw | Old role | New role | Old rank | New rank |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: |
| `wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4` | added | None | 561743870384 | None | None | wallet | None | 350 |
| `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` | balance | 180243716191492791 | 180398401009414645 | 154684817921854 | wallet | wallet | 1 | 1 |
| `wWq05ZZX6Jj2p9wW59oZ6lMF_KdW754zywqLa9n8INA` | balance | 149454420015180 | 0 | -149454420015180 | wallet | wallet | 18 | 7319 |
| `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4` | balance | 381553671374914 | 291712135061413 | -89841536313501 | pool | pool | 6 | 8 |
| `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948` | balance | 56636111316938 | 123291631310116 | 66655519993178 | wallet | wallet | 31 | 18 |
| `AxpxHZmHQhF25FkVSVX0T877PP2WUi7I46nmQaECUHI` | balance | 0 | 31129166766473 | 31129166766473 | wallet | wallet | 3256 | 42 |
| `Bv5mfnx5Ln2BU60inXPnMOGMwecJXadV4oqw7iwjzSk` | balance | 320089670049015 | 312546942799043 | -7542727249972 | pool | pool | 8 | 7 |
| `MmhScGp35v-9veB1ufbXRDoaDleTi_z3V_vZTjA8bnU` | balance | 4725068954918 | 0 | -4725068954918 | wallet | wallet | 126 | 4168 |
| `F9dWqoqSMzC3oyigfhezyT0fzc5BjhIYVSqcQWOgDq8` | balance | 561743870384 | 0 | -561743870384 | wallet | wallet | 351 | 3604 |
| `yEGUy_Dl229kp8cDtJ8wxekm0cqe2t68PhLrHPoHWQY` | balance | 505328951756 | 0 | -505328951756 | wallet | wallet | 362 | 7461 |
| `3biQvRjIp_9Qz1L9D3SJ9laK4akCkP-8bvAo3pQ6jVI` | balance | 3003053338103 | 2602630141925 | -400423196178 | pool | pool | 149 | 159 |

No address changed role.

New address `wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4` is role `wallet` name `absent` is_process `False` confidence `medium` raw `561743870384`.

The new raw balance on `wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4` equals the raw decrease on `F9dWqoqSMzC3oyigfhezyT0fzc5BjhIYVSqcQWOgDq8` (`561743870384`). This comparison is only the two balance amounts. It does not identify a transfer message.

Confidence changes on requeried addresses: `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948` medium -> high.

Unchanged named processes, roles reused from nonce 2074518: `fODpFVOb5weX9Yc-26AA82m2MhmT7N9L0TkynOsruK0` role `lending` name `LiquidOps Q Arweave` raw `7725686192460`; `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` role `pool` name `qAR:wAR:30` raw `1934348814863`.

Tail report `<repo>/data/raw/fast/tail/report.json` records to_nonce 2075923, handler_errors 0, addresses 7615, sum_equals_supply True.

## Numbers at nonce 2075923

| Role | Addresses | Raw qAR | Human qAR (12 decimals) | Share of supply |
| --- | ---: | ---: | ---: | ---: |
| wallet | 5274 | 186393939784010779 | 186393.939784010779 | 0.983673711926768405 |
| pool | 72 | 2329807115901902 | 2329.807115901902 | 0.012295303250890429 |
| unknown_process | 369 | 402625751820531 | 402.625751820531 | 0.002124813544203982 |
| lock | 2 | 250346157301342 | 250.346157301342 | 0.001321174573082006 |
| agent | 1889 | 100080610148413 | 100.080610148413 | 0.000528164517530253 |
| lending | 1 | 7725686192460 | 7.725686192460 | 0.000040771467264036 |
| token_process | 1 | 1880007389099 | 1.880007389099 | 0.00000992153419273 |
| pool_candidate | 2 | 862198877788 | 0.862198877788 | 0.000004550160651765 |
| invalid_id | 5 | 301100562297 | 0.301100562297 | 0.00000158902541639 |

| Role | Old addresses | New addresses | Old raw | New raw | Delta raw |
| --- | ---: | ---: | ---: | ---: | ---: |
| pool | 72 | 72 | 2427591802661553 | 2329807115901902 | -97784686759651 |
| wallet | 5273 | 5274 | 186296155097251128 | 186393939784010779 | 97784686759651 |

## Evidence

- `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json`
- `evidence/p8/20261017T1031Z-w-p8-tail/stats.json`
- `evidence/p8/20261017T1031Z-w-p8-tail/diff-2074518.json`
- `evidence/p8/20261017T1031Z-w-p8-tail/pools-locks-bridges.json`
- `<repo>/data/raw/p8/20261017T1031Z-w-p8-tail`

## Unfinished

- LP shares, lock beneficiaries, and nested pool ownership remain unresolved.
- 369 unknown_process rows were carried forward where the balance did not change. They were not re-queried.
- No requeried address stayed unknown_process.
- Collateral asset, holder, and raw amount remain unknown. This is not a claim list.

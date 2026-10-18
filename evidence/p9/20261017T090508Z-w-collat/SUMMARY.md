> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P9 collateral

Run `20261017T090508Z-w-collat`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. The module was not executed. No funds were moved. `goal_complete` is false. `publish_claims` is false. `move_collateral` is false.

## Conclusion

The layer-1 asset in the deposit and withdraw transactions is native AR, in winston. The handler mints data.quantity one-for-one into qAR and does not name that asset. Every resolved deposit pays `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c`, the original custody wallet. Its ar-io.dev history closes to the gateway balance, so at tail block 1951869 and now it holds 978114007970 winston. Before the tail, untagged transfers moved the bulk from that wallet through 11c550, qmg, uXBW, and cjp59 into AKQc. AKQc received 176000000000000000 winston from cjp59 across heights 1665001–1804219, while it already held 265960818776783497 winston. From that arrival through the tail it paid 803 recipients. A separate 20000 AR branch went from uXBW through miz into 4JOma at height 1729976. miz's tail balance is zero. 4JOma then paid 147 recipients 16369665321330000000 winston before the tail, far more than that inbound transfer. Those wallets are mixed with other AR, so there is no single holder and no single raw collateral amount. The wallet figures are not summed, and none of the gaps below is written back into a balance.

## Numbers

| Item | Value |
| --- | --- |
| Asset | AR |
| Holder | not one wallet |
| Separable raw winston at tail block 1951869 | null |
| Separable raw winston now | null |
| Checkpoint supply raw (nonce 2074518) | 189487568412204611 |
| qAR minted from deposit messages | null |
| qAR minted, partial sum of agreed groups | 461853766879179571 |
| Deposit groups missing an agreed quantity | 15 |
| qAR burned with a withdraw follow-up | null |
| Follow-up burn, partial | 262319318419623672 |
| Linked unwrap groups | 2125 of 2685 |
| (minted − burned) − supply | null |
| Original custody wallet at tail − supply | -189486590298196641 |
| Original custody wallet now − supply | -189486590298196641 |
| Holder-set collateral − supply | null |

Wallet balances below are the whole wallet. They are not a qAR slice. A match means the ar-io.dev owner and recipient pages, with the sender charged quantity plus fee, close to `/wallet/<address>/balance`.

| Wallet | Role | At checkpoint | At tail | Now | Matches gateway |
| --- | --- | --- | --- | --- | --- |
| `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c` | original_custody | 978114007970 | 978114007970 | 978114007970 | True |
| `11c550AqWT74EvGJ6oYBwCYqHDWSZ41tnympN_lYNx0` | untagged_forward | 6000000000000 | 6000000000000 | 6000000000000 | True |
| `qmg-WUYiCHqhnx_kv4zx2zedssosU1is9Td2UWGfI5g` | untagged_forward | 1546659611671199 | 1661515914915635 | 1661515914915635 | True |
| `uXBWmzYSA-yjkGm-cYMN_fl1R__USQLFORskGXGxdW0` | untagged_forward | 33212493375455601 | 33212493375455601 | 33212493375455601 | True |
| `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` | untagged_forward | 99925730950 | 99925730950 | 99925730950 | True |
| `AKQcAkNtnNXmEWBMMxfJ08oeoHP3RLs2jshRGnje1ow` | mixed_after_forward | 138721299168711687 | 123199764772062513 | 123454235289151276 | True |
| `mizBOKEIkpih0qAI-giz_kJrcfcQs5eZvqeUZHUD50E` | side_branch | 0 | 0 | 0 | True |
| `4JOmaT9fFe2ojFJEls3Zow5UKO2CBOk7lOirbPTtX1o` | side_branch | 47717442407 | 147717442407 | 147717442407 | True |

Untagged forwards, quantity in winston. Pair totals count every positive transfer between those two addresses. `qmg_to_uxbw` includes transfers before 11c550 paid qmg. `miz_to_4joma` includes four earlier transfers before the 20000 AR forward at height 1729976. Fees are on each hop in `flows.json` and are not added back.

| Hop | Txs | Quantity | Height |
| --- | --- | --- | --- |
| nLVp9_to_11c550 | 113 | 271377200000000000 | 1551227–1657109 |
| 11c550_to_qmg | 5 | 189488099940292480 | 1657051–1661231 |
| 11c550_back_to_nLVp9 | 43 | 81799999934367810 | 1551409–1649144 |
| 11c550_to_k4op | 1 | 89198858535710 | 1774837–1774837 |
| qmg_to_uxbw | 4 | 219708700000000000 | 1445445–1662584 |
| qmg_back_to_11c550 | 1 | 100000000000 | 1656864–1656864 |
| uxbw_to_cjp59 | 12 | 176000100000000000 | 1664994–1804210 |
| uxbw_to_miz | 1 | 20000000000000000 | 1729945–1729945 |
| miz_to_4joma | 5 | 22058187854906413 | 1418576–1729976 |
| uxbw_to_akqc | 1 | 5000000000000000 | 1607822–1607822 |
| cjp59_to_akqc | 11 | 176000000000000000 | 1665001–1804219 |

## Evidence

- Messages, bodies, GraphQL pages, and transaction lookups: `<repo>/data/raw/collat/20261017T090508Z/`
- arweave.net owner and recipient pages for the custody wallet omit the native transfers. The balances above use `wallet/<address>/ario-owners` and `ario-recipients` from `https://ar-io.dev/graphql`.
- `flows.json` groups one mint per underlying layer-1 transfer, one burn request per `X-Request-Id`, and the untagged forwarding transactions.
- `reconciliation.json` holds the gap arithmetic. Gaps are not written back into any balance.
- `collateral.json` names the asset. `holder`, `raw_amount_at_tail`, and `raw_amount_now` are null because the AR is not one separable pile.
- `manifest.json` lists each raw file under `data/raw/collat/20261017T090508Z/` with its byte size and sha256.

## Unfinished

- Mint-Tokens pagination is unfinished: {"action": "Mint-Tokens", "complete": false, "last_page_has_next": true, "last_page_height_max": 1604637, "last_page_height_min": 1604596, "last_page_tag_names": ["Action", "App-Environment", "App-Name", "App-Version", "Data-Protocol", "From-Module", "From-Process", "Reference", "Type", "Variant", "X-Cron-Request-Id"], "pages_saved": 1323}. Saved pages carry Action and X-Cron-Request-Id and no quantity or transfer id.
- Confirm-Deposits pagination is unfinished: {"action": "Confirm-Deposits", "complete": false, "last_page_has_next": true, "last_page_height_max": 1549269, "last_page_height_min": 1549218, "last_page_tag_names": ["Action", "App-Environment", "App-Name", "App-Version", "Data-Protocol", "From-Module", "From-Process", "Reference", "Type", "Variant", "X-Cron-Request-Id"], "pages_saved": 132}. Saved pages carry Action and X-Cron-Request-Id and no quantity or transfer id.
- 102 Withdraw or Unwrap-Funds-Sent bodies are still missing, so some transfer ids and burn links are unknown.
- Minted qAR is unknown: 15 deposit groups have no single agreed quantity. The partial sum is not the total. Missing message quantities are not replaced with the layer-1 amount.
- Burned qAR is unknown. Unwrap burns only when the caller still has the tokens; a message with no Withdraw or Unwrap-Funds-Sent follow-up is not counted as burned and is not counted as zero.
- Deposit transactions with no block height, excluded from confirmed balances: EoKk_EAcosZnZVicY6Oglmd9RK2bizvnW73nDHSkgtI
- Withdraw transfer ids with no layer-1 transaction in GraphQL or GET /tx: 5UtuLQRACikJvgxeusQheT4NAOkwxcSEDlHKMwthfEM, lPfj3Hx5z0Aw4jQhYgbz5pZqp3XShJsWS8vKvEjrgGk, dLWlR1ENw6GwRCCczkTd0OJrze9jtQ10xDGIHHVA4mw, MsAKJdbKRv7oLaR0MjBUeN275vFlPLF0rX39nrjLbwQ, RoeQ08SSkoYj5L3VvTmJCukH9r92LXOtBkOJKVSGl6k, wjtoB-Sfj_IKUuQq27RtcLLPcCV7U-vNAEYGa3fC3qU. They are not treated as zero.
- K4OPvKxtNUG7tBKXWfDPWSLtvLY1geCXfvfvFUGxvpA received 89198858535710 winston from 11c550 at height 1774837 and its history was not walked.

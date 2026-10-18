> English translation of [`evidence/p6/20261017T102111Z-w-eval/SUMMARY.md`](../../../../evidence/p6/20261017T102111Z-w-eval/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# Data of five Transfers

All 5 are Action=Transfer, and GraphQL `data.size` is `"0"`. The body returned by `https://arweave.net/raw/{id}` is empty. No other gateway on the allow list returned these 5 data items, so this is not a case of two gateways both receiving a body. None of the 5 nonces is in the tail range 2074519..2075923.

| nonce | Message | Quantity tag | arweave.net /raw |
| --- | --- | --- | --- |
| 2074509 | `4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y` | `940193118330` | 200, body 0 bytes |
| 2074511 | `ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw` | `189406046916` | 429 first, 200 on retry, body 0 bytes |
| 2074513 | `iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY` | `822375701087` | 429 first, 200 on retry, body 0 bytes |
| 2074515 | `0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw` | `2009265632204` | 200, body 0 bytes |
| 2074517 | `OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q` | `576448605054` | 200, body 0 bytes |

The sender of all of them is `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948`, and the Recipient of all of them is `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4`. `bundledIn` is an empty string.

Every successful `/raw` has `content-length: 0`, `raw-id` equal to the message id, and `content-digest` equal to `sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:`. That is the SHA-256 of the empty byte string. `data-offset - offset` equals `header-length` (1298 for four of them, 1299 for 2074515), so the data section has length 0.

`/tx/{id}` is 404 on arweave.net, ar-io.dev, turbo-gateway.com, and vilenarios.com. These ids are not L1 transactions, and `/tx` has no `data_size`. ar-io.dev's `/raw` was first 504 `upstream request timeout`, and a later single retry was 404. The `/raw` of turbo and vilenarios is 404 with body `Not found`. Goldsky's `/raw` and `/tx` are 307 for all 5 ids, with Location `https://arweave.net/graphql`; the redirect was not followed. `GET /{id}` on ar-io and turbo is 302 and then 404. On vilenarios, `GET /{id}` was probed only for the first one: 302, then a 40-second timeout with 0 bytes received.

The 2285-byte HTML previously returned by `GET https://arweave.net/{id}` is a gateway page, not Data. The replay treats the Data of these 5 as an empty string, which matches the `/raw` body.

## Empty Data and Balances

The amount is in the Quantity tag, not in Data.

The live handler is the Eval `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA` at nonce 1977055, 83536 bytes, sha256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`. `Transfer` is registered at line 2099 of this file. It first checks that the process is not stopped and that `TRANSFERS_ENABLED` is true, then calls `transfer_tokens`. Lines 1175 to 1176 are:

`payload.Recipient = payload.Message.Tags.Recipient`

`payload.Quantity = bint(payload.Message.Tags.Quantity)`

`instance:transfer` at lines 827 to 851 changes `Balances` with this quantity: the recipient gains the quantity and the sender loses it. The whole `transfer_tokens` function never reads `Data`. `msg_to_payload` does not parse Data either.

The handler that does read Data is `Deposit` (from line 2236), which requires `owner`, `quantity`, and `block_height` in JSON. The Action of these 5 is Transfer, not Deposit.

So empty Data does not change balances, and it is not treated as a quantity of 0. The amount transferred is the Quantity tag.

## Tail range

None of the 5 is in 2074519..2075923. Their nonces are 2074509, 2074511, 2074513, 2074515, 2074517.

## Evidence

- `evidence/p6/20261017T102111Z-w-eval/transfers.json`
- `evidence/p6/20261017T102111Z-w-eval/manifest.json`
- Raw responses are in `<repo>/data/raw/eval/20261017T102111Z-w-eval/http/`
- Fetch script `recovery/p6/fetch_transfer_data.py`

Not done: no second gateway returned these 5 data items. The replay was not changed, and the tail was not replayed.

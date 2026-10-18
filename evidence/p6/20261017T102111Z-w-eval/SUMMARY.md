> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# 五笔 Transfer 的 Data

这 5 笔都是 Action=Transfer，GraphQL `data.size` 为 `"0"`。`https://arweave.net/raw/{id}` 返回的正文是空的。允许列表里的其他网关没有返回这 5 个数据项，所以这不是两家网关都拿到了正文。5 笔的 nonce 都不在尾部区间 2074519..2075923。

| nonce | 消息 | Quantity tag | arweave.net /raw |
| --- | --- | --- | --- |
| 2074509 | `4abmavZXf81Y-UheWFraPxmUubZni_XgdmF_tckrg9Y` | `940193118330` | 200，正文 0 字节 |
| 2074511 | `ziTv11hf6H9_9iiWEeeIGSsGo9iB036CYWT_S5F3jyw` | `189406046916` | 先 429，重试 200，正文 0 字节 |
| 2074513 | `iSSX3aBndOHhOReGvcEY-tU_oDi0BsxgKajE5TwqTmY` | `822375701087` | 先 429，重试 200，正文 0 字节 |
| 2074515 | `0EA0BJGA2eP79w5Zply6VYuEop7SMrYkuzo_tCYdIYw` | `2009265632204` | 200，正文 0 字节 |
| 2074517 | `OZYnrr04Q8WU9Fr-GNDcnm407F-jM0MSC6EdgSgaL8Q` | `576448605054` | 200，正文 0 字节 |

发送者都是 `BzZ5t7E0BxYXzKDJoy8DBUDyseK84ODWgk0z9Ra-948`，Recipient 都是 `wTIpisZKMtG5WsLFqQBdoJEObyyeoJQmwWFm1h462D4`。`bundledIn` 是空字符串。

每一笔成功的 `/raw` 都有 `content-length: 0`，`raw-id` 等于消息 id，`content-digest` 是 `sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:`。这是空字节串的 SHA-256。`data-offset - offset` 等于 `header-length`（四笔 1298，2074515 是 1299），所以数据区长度是 0。

`/tx/{id}` 在 arweave.net、ar-io.dev、turbo-gateway.com、vilenarios.com 都是 404。这些 id 不是 L1 交易，`/tx` 里没有 `data_size`。ar-io.dev 的 `/raw` 先是 504 `upstream request timeout`，稍后单笔重试是 404。turbo 和 vilenarios 的 `/raw` 是 404，正文 `Not found`。Goldsky 的 `/raw` 和 `/tx` 对 5 个 id 都是 307，Location 是 `https://arweave.net/graphql`，没有跟随。ar-io 和 turbo 的 `GET /{id}` 是 302 之后 404。vilenarios 的 `GET /{id}` 只探了第一笔，302 之后 40 秒超时，收到 0 字节。

以前 `GET https://arweave.net/{id}` 得到的 2285 字节 HTML 是网关页面，不是 Data。回放把这 5 笔的 Data 当成空字符串，和 `/raw` 的正文一致。

## 空 Data 对 Balances

数量在 Quantity tag 里，不在 Data 里。

活的 handler 是 nonce 1977055 的 Eval `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA`，83536 字节，sha256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`。`Transfer` 注册在这个文件的 2099 行。它先检查进程没有停止，并且 `TRANSFERS_ENABLED` 为真，然后调用 `transfer_tokens`。1175 到 1176 行是：

`payload.Recipient = payload.Message.Tags.Recipient`

`payload.Quantity = bint(payload.Message.Tags.Quantity)`

827 到 851 行的 `instance:transfer` 用这个 quantity 改 `Balances`：收款地址加上 quantity，付款地址减去 quantity。`transfer_tokens` 整个函数没有读 `Data`。`msg_to_payload` 也不解析 Data。

会读 Data 的是 `Deposit`（2236 行起），它要求 JSON 里有 `owner`、`quantity`、`block_height`。这 5 笔的 Action 是 Transfer，不是 Deposit。

所以空 Data 不改变余额，也不会被当成数量 0。转出的数额就是 Quantity tag。

## 尾部区间

2074519..2075923 里没有这 5 笔。它们的 nonce 是 2074509、2074511、2074513、2074515、2074517。

## 证据

- `evidence/p6/20261017T102111Z-w-eval/transfers.json`
- `evidence/p6/20261017T102111Z-w-eval/manifest.json`
- 原始响应在 `<repo>/data/raw/eval/20261017T102111Z-w-eval/http/`
- 取数脚本 `recovery/p6/fetch_transfer_data.py`

未做：没有第二家网关返回这 5 个数据项。没有改回放，没有回放尾部。

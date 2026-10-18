# qAR ledger and collateral handlers

Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. Module was not executed. The live business source is the last Eval that registers each action name.

## Which source is loaded

GraphQL on `https://arweave.net/graphql` returned 278 `Action=Eval` `Type=Message` transactions whose recipient is this process. All 278 have an assignment nonce. 271 bodies were hashed. Seven bodies, nonces 21–27, are still unread: arweave.net returned HTTP 404, and the alt gateways either returned HTTP 404 or a redirect that timed out with an empty body. Nonces 11087 (`Gb-c1wUm5JMGsrSu6-L0K84e4aQCzE2ID7KHOQTqGI0`) and 11096 (`bwLTiJ4Rjv_vV84MTeLMP97YvR4nntySl8S-3k6cIYU`) were HTTP 404 on arweave.net and HTTP 200 on a later gateway. Both bodies are the 21-byte probe `Unwraps[#Unwraps - 1]`, sha256 `6c710b1617805b84bda99b992a0309205f0541e15d239f2895650a03698ebe0d`, the same bytes as nonce 10955. That expression reads one unwrap row. It does not register a handler. The unread seven sit before the later blueprints.

The spawn data is the four bytes `1984`. It is not Lua. Nonce 0 (`GBPuvd6zc47A8PFiD7PGmZXcZPZF-DDWcdEg4tzXC3g`, 74616 bytes) and nonce 1 (`Jj_HBAJiulZFqAvS-gH66ZsuuBfAhYP6p_SuIWaZmZI`, 88432 bytes) are the boot blueprints, version string absent, ticker `qAR`, name `Q Arweave`, denomination 12. Later Evals replace that blueprint. The version literals in the hashed bodies run 0.3.0 through 0.14.0 and then 0.16.0. There is no 0.15.0 body in this set.

The last blueprint is nonce 1977055, message `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA`, 83536 bytes, sha256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`, assignment `suagX-FKHsuxDHw-YUfzhqF4Rf0VuDgJHrDjP7M-ryU`, hash-chain `XtSnXWNyvT1BMMzemMat05RP7DGLez4abe1of9gEnOg`. Its `APP_VERSION` is `0.16.0` and `APP_ENVIRONMENT` is `MAINNET`. The same message is resident in checkpoint `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk` (memory sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`, 428146688 bytes). The printable message object starts at memory offset 5216352 and carries Nonce 1977055 and that same hash-chain.

aos dispatch, from that same checkpoint memory:

- `hasMatchingTag` at offset 85298 returns the boolean `msg.Tags[name] == value`.
- `handlers.evaluate` at offset 92104 turns boolean `true` into match `-1`, runs that handler, and returns. The first match wins.
- `handlers.add` at offset 87792 updates an existing name in place (`handlers.list[idx].pattern` and `.handle`). A new name is inserted at the front. No fetched Eval calls `Handlers.remove`. The capital-H string `Handlers.remove` occurs 0 times in the 271 bodies and 0 times in the 428146688-byte memory.

Nonce 1977055 is the last Eval that calls `Handlers.add` for these action names. Later Evals are probes, three flag writes, and the tail. They do not register handlers. The 0.16.0 functions are the ones aos will call. The runtime defines `handlers.remove` at offset 91718. None of the 271 fetched bodies contains the call `Handlers.remove`.

## Ledger storage

From `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA`, function `__fns__.configs_production_qar_token` and `__fns__.ap_src_token_mod`:

- Name `Q Arweave`, ticker `qAR`.
- `Denomination = 12`. `instance:info` returns that number as a string. Human balance is raw divided by 10^12.
- `Balances` is a global table, `Balances = Balances or globals.Balances`. Keys are addresses. Values are bint raw units. There is no separate `TotalSupply` global. `instance:total_supply` sums `Balances`.
- `Total-Supply` prints that sum and `ao.send`s it. It errors when `payload.Message.From == ao.id`.
- `Balance` reads one entry and sends `Balance`, `Account`, `Ticker`, and the raw integer as `Data`. A missing key is sent as `'0'` in this 0.16.0 balance handler. That `'0'` is the handler's response for an absent key, not a recovered ledger row.
- `Balances` (plural) sends `json.encode` of every balance converted with `tostring`.

Mint adds to `Balances[target]`. Burn subtracts. Neither updates a second supply counter, so the sum of `Balances` is the supply definition in this source.

## Actions registered by 0.16.0

`actions.add` names, in source order: Rewards-Balance, Rewards-Balances, Total-Rewards, Confirm-Deposits, Confirm-Withdrawals, Balance, Balances, Burn, Info, Mint, Mint-Tokens, Transfer, Unwrap, Output-Configs, Total-Supply, Deposit, Query, Stop-Process, Restart-Process, Cron, Cancel-Withdrawals, Unwrap-Funds-Sent, Withdraw, Get-Unwraps, Get-Unwraps-Completed, Get-Deposits, Get-Deposits-Completed.

`Handlers.add` name outside that list: `BalanceResponse`, matched on `Ticker == AO`.

Direct `Mint` only errors: `Action 'Mint' not allowed. Use 'Mint-Tokens' action.` Direct `Burn` only errors: `Action 'Burn' not allowed. Use 'Unwrap' action.`

`Transfer` errors when `TRANSFERS_ENABLED` is false, when the process is stopped, or when the 0.16.0 review map contains the caller or recipient with a truthy value. The only entry is `["93L5bm5NRSiwkMFbjrn9HkAWblV6__LJoMfiGlgSQU0"] = false`, and `false` does not trip the check. The handler then moves `Quantity` raw units from the caller to `Recipient`.

## Mint and redeem

Deposit and mint, same message:

1. `Deposit` requires the caller to be in `AUTHORIZED_MINTERS`, `DEPOSITS_ENABLED`, and the process not stopped. Tags `X-Request-Id` and `X-Transfer-Id` are required. Data must decode to a table with `owner`, `quantity`, and `block_height`. The handler stores a row in `Deposits` with status `funds_sent`. It does not fetch or verify the transfer.
2. Cron sets `LatestBlockHeight` from the cron message `Block-Height` when that value is greater.
3. `Confirm-Deposits` may be called by `AUTHORIZED_DEPOSIT_CONFIRMERS`. For up to 25 rows still `funds_sent` whose `block_height` is a number and `LatestBlockHeight - block_height >= 30`, status becomes `confirmed` and `events.minted_war.status` becomes `pending`. `CONFIRMATIONS.DEPOSITS` is 30.
4. `Mint-Tokens` may be called by `AUTHORIZED_MINTERS` while deposits are enabled. For up to 25 `confirmed` deposits it sets `Quantity` to `bint(deposit.quantity)` and `Target` to `deposit.owner`, then credits `Balances`. The ratio in code is 1 raw unit on the deposit to 1 raw qAR. Status becomes `minted_war`.

Redeem:

1. `Unwrap` burns the caller's qAR for `Tags.Quantity` and appends an `Unwraps` row with status `burnt_war`. It requires `X-Request-Id`, `WITHDRAWALS_ENABLED`, and no existing `burnt_war` row for that owner. It does not send the underlying asset.
2. `Withdraw` and `Unwrap-Funds-Sent` are minter-only. They record `transfer_id`, `block_height`, `quantity_transferred`, `bridge_fee`, and `network_fee` supplied by the caller. They do not verify those fields against a transaction.
3. `Confirm-Withdrawals` confirms rows already in status `funds_sent` after 30 blocks, same shape as deposits. `Cancel-Withdrawals` is minter-only and marks a row `cancelled`. It does not mint the burned qAR back.

`bridge_fee` and `network_fee` are record fields. They are not addresses. 0.16.0 does not contain the string `X-Bridge-Fee`. Earlier blueprints, from nonce 4142 onward, do.

## Collateral

The handler never names an asset id for the external transfer. It does not call a wAR process, an AR wallet, or a bridge process during `Deposit` or `Mint-Tokens`. The event field is still called `minted_war`. Confirmation uses an Arweave `block_height` and a 30-block gap against cron `Block-Height`, which is the shape of an Arweave L1 transaction id in `X-Transfer-Id`. That shape is not a proof of native AR, and it is not a proof of the wAR process seen in a later swap notice.

The process does not hold the external asset in `Balances`. `AR_WALLETS` is the AO-reward watch list, not an AR custody balance. Cron asks `AO_TOKEN_PROCESS_ID` for each wallet's AO balance and adds positive deltas to `REWARDS`, pro rata to qAR `Balances`. `REWARDS` is not qAR supply.

Who holds the external asset, and the raw amount still held, are not in this source. Missing amounts stay unknown.

Authorized set in `configs_production_qar_token` of the live message:

- `ao.id` (this process): minter, deposit confirmer, withdrawal confirmer, stopper, restarter, starter.
- `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c`: minter, deposit confirmer, withdrawal confirmer, and the only `AR_WALLETS` key, initial bint `0`. The same address is the boot minter in nonce 0.
- `S_0fyWQknosQ57QWd0iuWl84EYmoi5qCyDai-LYHuhg`: minter, deposit confirmer, withdrawal confirmer.
- AO token queried for rewards: `1OEAToQGhSKV76oa1MFIGZ9bYxCJoxpXqtksApDdcu8`. The boot blueprint named `m3PaWzK4PTG9lAaqYQPaPdOcXdO8hYqi5Fe9NWqXd0w` instead. The live handler is the 0.16.0 closure.

`AR_WALLETS = tables.merge_objects(AR_WALLETS, configs.AR_WALLETS)` keeps keys that were already present. This prep did not walk the live Lua table, so extra keys beyond the source literal are unknown.

## Flags and cron

Process tags, from the process transaction: `Cron-Interval` `5-minutes`, `Cron-Tag-Action` `Cron`. The 0.16.0 `Cron` handler, if `IS_STOPPED` is false, updates `LatestBlockHeight`, drops inbox items 55 blocks old or whose action is in its eviction list, moves finished deposits and unwraps into the completed tables, and requests AO balances.

Last flag writes after the 0.16.0 load:

- nonce 1977061 `xkyG1_Gexl06pnLQ-2j5Du6MC4rAb6CaUrslgs_omVw`: `DEPOSITS_ENABLED = false`
- nonce 1977062 `m1n3dJfy5iZ0ZYO2PWQi9JCuQH_Kr-VXfmR1NmSm69Q`: `WITHDRAWALS_ENABLED = false`
- nonce 1977063 `gaBFkKOA7cKc5cF3LxoygCkgu90z7tGVAG_nJreDgO8`: `TRANSFERS_ENABLED = true`

No later Eval assigns these three. With those values, `Deposit`, `Mint-Tokens`, `Unwrap`, `Withdraw`, `Cancel-Withdrawals`, and `Unwrap-Funds-Sent` error. `Transfer` is allowed by its flag. `IS_STOPPED` is not assigned by any short Eval after 0.16.0. `Stop-Process` can set it, and those messages were not part of this Eval scan, so the live stop flag is unknown.

## Tail eval

Nonce 2075923, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`, assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`, hash-chain `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE`, 131 bytes:

`table.insert(ao.authorities, 'CCcVUmUBl6scmH2a8thOqXjW9kmPVtf6bEDeP4Edw9c'); table.remove(ao.authorities, 1); print(ao.authorities)`

It does not read or write `Balances`. It is the only Eval that mentions `ao.authorities`. The process transaction has no `Authority` tag. The runtime at memory offset 280097 seeds `ao.authorities` from `Authority` tags only when the list is empty, and `ao.isTrusted` at offset 283738 returns true for every sender when the list is empty. Insert-then-`remove(1)` on an empty list appends the new address and then deletes that same first element. This prep did not execute the message, and the address is absent from the earlier checkpoint memory.

## Pool, lock, and bridge

The handler source names no pool, no lock contract, and no bridge process id. The bridge role in code is the attestor set above.

Checkpoint memory holds two swap notices spawned by this process. They are observations, not a registry:

- Offset 214475082, `X-Provider` `Botega`. qAR was credited from `vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4`. The notice data shows that address's qAR balance moving from `276820576545058` to `278766297997351`.
- Offset 230180022, `X-Provider` `Permaswap`. qAR was credited from `KQhYTVaQ5tXcOQ3SrJiIt60_mdO0zAGUnT4snNwQs9U`. The paired token metadata names wAR process `xU9zFkq3X2ZQ6olwNVvr1vUWIjc3kXTWr7xKQD6dh10`.

`X-Pool` occurs twice, at offsets 10425472 and 10425633, inside non-contiguous bytes. No pool address was recovered from those hits. No lock address appears in the live source. Local configs that map this process to pools are not in this repository.

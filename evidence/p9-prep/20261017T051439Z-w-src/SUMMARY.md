> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P9 prep: qAR source, ledger, collateral

Run `20261017T051439Z-w-src`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. The module was not executed. `goal_complete` is false. `publish_claims` is false. `move_collateral` is false.

## Conclusion

The live handlers are version 0.16.0, loaded by Eval nonce 1977055, message `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA` (83536 bytes, sha256 `9529bc2252ee45f255c6e286129ab0cbc6e638cb34935bf1e6b702997565a903`). aos `handlers.add` replaces an existing action name in place, and `handlers.evaluate` returns on the first match. This Eval is the last one that registers the action names. Checkpoint memory offset 5216352 holds the same message and hash-chain `XtSnXWNyvT1BMMzemMat05RP7DGLez4abe1of9gEnOg`. Older blueprints do not stay stacked under those names.

Supply is the sum of the global `Balances` table. There is no `TotalSupply` global. The action name is `Total-Supply`. `Denomination` is 12, so a human balance is raw units divided by 10^12. A missing balance key is answered with the string `0`. That string is a handler response, not a recovered ledger row.

After that load, nonce 1977061 sets `DEPOSITS_ENABLED = false`, nonce 1977062 sets `WITHDRAWALS_ENABLED = false`, and nonce 1977063 sets `TRANSFERS_ENABLED = true`. With those flags, Deposit, Mint-Tokens, Unwrap, Withdraw, Cancel-Withdrawals, and Unwrap-Funds-Sent error. Transfer is allowed by its flag. No short Eval after 0.16.0 assigns `IS_STOPPED`. Stop-Process messages were outside this Eval scan, so the live stop flag is unknown.

Mint and redeem attest an external transfer. `Deposit` stores `owner`, `quantity`, and `block_height` from the caller. It does not fetch the transfer. `Confirm-Deposits` requires 30 Arweave blocks against cron `Block-Height`. `Mint-Tokens` credits `bint(deposit.quantity)` to `deposit.owner`, one raw deposit unit to one raw qAR. `Unwrap` burns the caller's qAR. `Withdraw` records a caller-supplied `transfer_id` and fees and does not check them against a transaction. The event name remains `minted_war`. The 0.16.0 source does not name an asset id, a wAR process, or a native-AR holder on that path. Collateral asset, holder, and raw held amount are unknown.

Bridge attestors in `configs_production_qar_token` are this process (`ao.id`), `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c`, and cron process `S_0fyWQknosQ57QWd0iuWl84EYmoi5qCyDai-LYHuhg`. `bridge_fee` is a record field, not an address. AO reward token `1OEAToQGhSKV76oa1MFIGZ9bYxCJoxpXqtksApDdcu8` feeds `REWARDS`, which is separate from qAR supply. Boot AO token `m3PaWzK4PTG9lAaqYQPaPdOcXdO8hYqi5Fe9NWqXd0w` belongs to the nonce 0 blueprint.

Pool candidates are single checkpoint notices, confidence low: Botega `vOYSBRYMv2S5l1Zv50Z3_Yv-zTIaNzZgXx9WkgP-Rh4` at memory offset 214475082, and Permaswap `KQhYTVaQ5tXcOQ3SrJiIt60_mdO0zAGUnT4snNwQs9U` at offset 230180022. No lock address is in the live source. No bridge process id is hardcoded.

The tail Eval, nonce 2075923, message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ`, inserts `CCcVUmUBl6scmH2a8thOqXjW9kmPVtf6bEDeP4Edw9c` into `ao.authorities` and then `table.remove(..., 1)`. It does not touch `Balances`. On an empty authority list that pair appends the address and then deletes it. The message was not executed.

Detail and citations are in `handlers.md` and `addresses.json`.

## Numbers

| Item | Value |
| --- | --- |
| Action=Eval messages | 278, every one assigned, nonce unique |
| Bodies hashed | 271 |
| Unique body sha256 | 79 |
| Still unread | 7 (nonces 21–27) |
| Kinds | blueprint 41, probe 225, unread 7, flag 4, tail 1 |
| Checkpoint gzip | 145634952 bytes, sha256 `31f5e4811756ff22a98546144075dd238da76eeb05470a126df43eb2fe92e095` |
| Checkpoint memory | 428146688 bytes, sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` (matches the tag) |
| Spawn data | 4 bytes `1984`, sha256 `4dea5c7cb70f50322ec9d734aa4aa078be9227c05251e18991c596f387552370` |

Nonce 0 body sha256 `f89002e820e9390cad4f26e2b8a2c0eec1fe02490e0fffc8cf6188f2c06598d5` (74616 bytes). Nonce 1 body sha256 `d3656f037100fe5408f8ae1bfc32c835cb830f9f081a80079c672646e5f5aebd` (88432 bytes). Version literals in the hashed bodies run 0.3.0 through 0.14.0 and then 0.16.0. There is no 0.15.0 body in this set.

Nonces 11087 and 11096 were HTTP 404 on arweave.net. ar-io.dev returned HTTP 200 with content-length 21. The body is `Unwraps[#Unwraps - 1]`, the same sha256 as nonce 10955. A second gateway returned the same 21 bytes for each id. The first fetcher marked them not-ok because it required more than 100 bytes. That filter was wrong for these probes. They do not change the 0.16.0 handler set.

Goldsky `https://arweave-search.goldsky.com/graphql` answered HTTP 307. Following it landed on `https://arweave.net/graphql`. It is not an independent index. The first page ids match.

## Evidence

Worktree, this directory:

- `sources.json` — 278 Eval rows (id, nonce, assignment, sha256, kind, path) plus checkpoint and query notes
- `handlers.md` — handler behavior with message ids and memory offsets
- `addresses.json` — address, role, source, confidence
- `fetch_evals.py` — read-only assignment join and body download

Raw bytes, gitignored, under `<repo>/data/raw/src/20261017T051439Z-w-src/`:

- `checkpoint/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.bin` and `.mem`. `data/raw/checkpoints/` was absent, so the bytes live here.
- `gql/` — Eval pages, assignment pages, Goldsky 307, ids query with empty edges for the missing bodies
- `messages/` — hashed bodies and the arweave.net 404 pages. The two recovered probes replaced the HTML at `<id>.body`; the HTML is `<id>.arweave-net-404.body`.
- `messages/alt-gateway/results.json` — per id and gateway HTTP code, byte count, and curl stderr
- `eval-catalog.json` — 367086 bytes, sha256 `981ca9f869a2c5d34ef36bd25081bac626a2a6cc248b4eb04dbc4282a8d7c32e`

Nonce join used the three read-only sqlite files under `data/raw/p4/` for ranges 0–49999, 50000–99999, and 100000–149999, plus GraphQL Assignment tags for the 88 ids those files do not contain. `assign-eval.rows.json` holds those rows. Duplicate nonces: 0.

## Unfinished

- Nonces 21–27 have no accepted body. Ids: `7L4y3VJlF_Y9PskM2RQ-LBlrHCc_L_7BtAp_6PcYy9Q`, `hDHZZRtMNA3yQ0kI8-4Hkr7kd00nxoEIyDFDCfjCbyE`, `nn-olI2CU_MCFThAPCL7iPkSejie1XN3Fevtj6rAoHI`, `dafRRlq3OIPi3phDPcSzuOFko2FY-KWF78XTixWhvPA`, `c23LXQ_LmRV8ZPlTp10wwBCkPt3xa2-hhEIwqrhMABM`, `JnktbqngSHdRIK-k3_R9FVKLCHYnVlHOTLJsG0Fq_RQ`, `WRQeBShb8KbVxW7ETtef7vmpeMO86ubj3y2AXYKvdLI`. arweave.net and, where the final response arrived, ar-io.dev returned HTTP 404. Some turbo-gateway.com and vilenarios.com attempts stopped on HTTP 302 with curl 28 and an empty body. Their bytes are a gap. Globals they might have set could still persist through `or` or `tables.merge_objects`. They cannot replace the 0.16.0 closures.
- The live Lua heap was not walked. `IS_STOPPED`, extra `AR_WALLETS` keys, the `Balances` table, and `ao.authorities` before the tail are unknown.
- Collateral asset id, holder, and raw amount are unknown. Historical amount is unknown. Unknown is not zero.
- `X-Pool` hits at memory offsets 10425472 and 10425633 are non-contiguous. No address was reconstructed.
- Local DEX config files are not in this repository, so the pool list is the two notices only.
- `data/raw/modules` was empty. The module wasm was not scanned. Handler replacement is taken from the aos Lua in checkpoint memory, not from the wasm.

P4 ranges at nonce 150000 and above were not opened. P5 was not started. `STATE.md` was not modified.

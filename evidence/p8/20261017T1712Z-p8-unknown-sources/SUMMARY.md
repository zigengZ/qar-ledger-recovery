> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Unknown process sources

Run `20261017T1712Z-p8-unknown-sources`. Ledger nonce 2075923. The module was not executed.

## Conclusion

`classification_sourced` stays false. All 369 `unknown_process` rows stay `unknown_process`. None were relabeled `end_user` or `user`.

The local pool and process excerpts contain 0 of these ids. The files searched are `qar-pools.txt`, `qar-local-configs.txt`, and `README-local-configs.md` in the private local-config excerpts, which are not in this repository.

278 of these processes use a module that also hosts a named pool. A shared module is not a pool source. Rows with no Name tag stay unknown. Rows whose Name tag does not match a pool, lock, bridge, or lending rule stay unknown.

Wallet labels were not promoted. 5262 wallets rest on a closed `transactions(ids)` page with no edge. 12 also have a signed message in an owner query. Neither source is an end-user identity.

## Numbers

- unknown_process: 369
- config id hits: 0
- wallets: 5274
- wallet no-edge only: 5262
- wallet with a signed message: 12
- relabeled: 0

`goal_complete` is false. Collateral separable raw amount stays null.

> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# w-doc

Public recovery note for an external reviewer. English and Chinese carry the same facts.

`goal_complete` is false. The note is not a claim list and does not allocate collateral.

Unfinished Unwrap/Deposit records may exist. They are checked separately and are outside this ledger.

## Conclusion

The tail balance table at nonce 2075923 has 7615 rows. The raw sum and the separately read Total-Supply are both `189487568412204611`. Final memory SHA-256 of the cron-inclusive replay is `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The main replay and the clean clone match that memory hash. The canonical balance SHA-256 is `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. The separable collateral raw amount is null.

## Numbers

- Checkpoint replay start: nonce 2074518, id `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`, uncompressed SHA-256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`.
- Semantic gate: 7614 addresses, 0 diffs, supply `189487568412204611`. Independent byte gate failed. Copying 9 cron Block-Heights makes the memory hash match.
- Explicit holes kept: 132 in 50000..99999, 627 in 100000..149999. 150000..2074399 is unindexed.
- Assignment-only and cron-inclusive balance JSON files hash to the same SHA-256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`.
- Overlapping memory hashes: 47 of 47 from stream index 8000 through 8480.

## Evidence

- `docs/RECOVERY.md`
- `docs/RECOVERY.zh.md`
- `evidence/doc/20261017T1037Z-w-doc/provenance.json`
- `evidence/doc/20261017T1037Z-w-doc/fast-excerpt/` — byte copies of four unmerged fast-worker JSON files. Not a merge of that branch.

## Unfinished

- Collateral has no single holder. The separable raw amount is null. `collateral_sourced` and `collateral_reconciled` are false.
- `classification_sourced` is false. Identity of `cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8` was not checked.
- Nonce coverage from genesis is unmet: 132 holes in 50000..99999, 627 holes in 100000..149999, and 150000..2074399 is unindexed.
- `goal_complete` is false.

## Privacy grep

Searched `docs/RECOVERY.md`, `docs/RECOVERY.zh.md`, and `evidence/doc/20261017T1037Z-w-doc`, including the Unwrap/Deposit scope sentence.

| Pattern | Result |
| --- | --- |
| `<local-root>/`, `<home>/`, `/opt/` | no matches |
| email (`local-part [at] domain.tld`) | no matches |
| IPv4 | no matches |
| private host names and person names | no matches |

The note names public data sources used as endpoints (`arweave.net`, `turbo-gateway.com`, `ar-io.dev`, `vilenarios.com`, `cu.ao-testnet.xyz`, `drive.google.com`, `github.com`). It describes the machine only as one Linux server running Node v22.22.0.

Evidence paths in this tree use repository-relative paths, or the `<repo>` placeholder for gitignored `data/raw` bytes. This note does not copy machine paths.

> English translation of [`evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`](../../../../evidence/repro/20261017T120218Z-w-repro/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# w-repro

A clean clone, using only public gateways, replayed qAR from the checkpoint at nonce 2074518 to nonce 2075923. The canonical balances match the published fast-tail nonzero balances address by address. Moving the cron Block-Height by plus or minus 3 does not change this hash.

This is not a claim list. No collateral was moved.

## Conclusion

- Memory sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`.
- Canonical balance sha256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. This value is in `repro/EXPECTED.json`.
- 2239 nonzero addresses. 7615 raw addresses. The 5376 zero balances are not in the canonical file.
- Total supply and the balance sum are both `189487568412204611`.
- 0 handler errors. 39065 items replayed: 37660 crons and 1405 assignments.
- Over the first 10 items, the unpatched loader and the in-place mode give the same memory sha256: `4e341435f023aa41f27fc2b1dbb764c14c30ca39b13f14a02704bac722562960`.
- With cron heights +3, the memory sha256 is `d0dd22f387150aa3e894106cb5d8dde08783ea30974cfd78ea632e9a1c46bc20`. With heights -3, the memory sha256 is `6b11be84807469cebb5201867800cdbfcb21266ca14ae65322cff772be126c92`. Both runs give the same canonical balance hash as offset 0.

## Numbers

- Checkpoint gzip 145634952 bytes, sha256 `31f5e4811756ff22a98546144075dd238da76eeb05470a126df43eb2fe92e095`. gunzip 428146688 bytes, sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`. The ANS-104 signature and signer check passed.
- 1406 assignments. 1405 hash-chain hops, tail `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`.
- 1405 messages. Nonce 2075899 `VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA` and nonce 2075900 `iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw` are not in GraphQL; they were taken from bundle `MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA` in block 1924100.
- 88431 blocks, heights 1863436..1951866. 7 clock regressions, the largest 31 seconds. The replay keeps these published times.
- 2537 HTTP responses, kept in `raw/http/` of the working directory, not committed.
- Block pages took about 25 minutes. With inputs already in the working directory, the in-place replay took 601869 ms, and that process's wall clock was 618282 ms.
- One replay's working directory is about 0.6 GB. After three replays it is 1.4 GB.
- Node v22.22.0, `@permaweb/ao-loader` 0.0.44.

## Evidence

- `manifest.json`
- `result-offset-0.json`
- `result-offset-plus-3.json`
- `result-offset-minus-3.json`
- `probe.json`
- Commands and expected hashes: `repro/README.md`, `repro/EXPECTED.json`

## Not done

The full `--mode safe` was not run. The slow mode can be started with `./repro/run.sh --mode safe`. The comparison done covers the first 10 items.

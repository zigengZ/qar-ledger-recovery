> English translation of [`evidence/web/20261017T1243Z-w-web2/SUMMARY.md`](../../../../evidence/web/20261017T1243Z-w-web2/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# w-web2

Finishing the static site. Not deployed. `goal_complete` is still false. This is not a claim list.

## Conclusion

The wallet page and the wallet route were removed. The build no longer reads the wallet holdings directory. The method page uses DOMPurify 3.4.17, keeps only ordinary typography tags, and links still go through the existing allow list. Theme initialization is `theme-init.js`. Every script in `dist/index.html` has a `src`; there are no inline scripts.

Classification uses the tail `evidence/p8/20261017T1031Z-w-p8-tail`, nonce 2075923. 7615 addresses, 2239 nonzero, 10 balance changes relative to the snapshot. Canonical balance sha256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`. The verification timeline is: snapshot, hash chain, engine check, exact replay, assignments-only replay, the non-WASM 7615/7615, from-scratch reproduction, and the final sha of the main replay (it later matched; see the README). Cron heights ±3 do not change the canonical hash. Both the footer and the browser's SubtleCrypto show that this hash matches.

`npm test`: 24 passed. `npm run build` passes. The preview listens only on the loopback address. Screenshots of five pages in light, dark, desktop, and 375 width are in `web/shots/`; there were no console errors and no CSP violations. `dist` contains no host names, IPs, `<local-root>/`, `<home>/`, or wallet page remnants.

## Numbers

- 7615 addresses, 2239 nonzero, supply raw `189487568412204611`
- Addresses missing from the tail classification 0, balance changes relative to the snapshot 10
- Independent recompute 7615/7615, 703 Transfers applied, 0 rejected
- Data generated at `2026-10-17T12:42:06.976Z`

## Evidence

- `web/public/data/manifest.json`
- `web/public/data/evidence.json`
- `web/public/data/methodology.json`
- `web/shots/`
- Ledger `evidence/p10/20261017T1047Z-fast-tail/ledger.csv`
- Classification `evidence/p8/20261017T1031Z-w-p8-tail/`
- Independent recompute `evidence/p10-indep/20261017T104141Z-w-indep/result.json`
- From-scratch reproduction `evidence/repro/20261017T120218Z-w-repro/` and `repro/EXPECTED.json`

## Not done

- When this record was written, the final sha of the main replay was still in progress. It later matched; see the README.
- The from-scratch reproduction did not run the full safe mode.
- The separable collateral raw amount is null.
- Not deployed.

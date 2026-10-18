> English translation of [`evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md`](../../../../evidence/side-d/20261017T0856Z-w-drive/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# Side D · Drive CU

The correct public folder is `1HvWUSVZxHgI6llLpFe9AkODgDxQ6KVdn`. The id in GOAL.md has one wrong character, and its HTTP 404 is saved. The inventory used `embeddedfolderview`: 1113 files, of which 1012 are checkpoint bins, plus `extraction-report.json`. For `node_modules`, only 191 entries were recorded, and they were not downloaded one by one.

## Conclusion

This CU source is the CU of permaweb/ao `0db88a45`, with `ao-loader` locked at `0.0.44`. The only dependency difference is `weavedrive` `0.0.19`. The cron Block-Height algorithm is the same as in w-eval, so it cannot by itself explain the 9 height differences. The process checkpoints of qAR and APUS are not among these 1012 files.

Of the 18 deduplicated ids in the local pool list, 4 are on Drive. The preferred permaswap qAR/wAR 0.3% pool `_laMMu5weQgrtDhKjd4dIOZDej7XKwXcaHJmgOcPvK4` has state time 2026-07-04T06:21:56Z, file-name height 1951866, and report sha256 `d142fbaf334646dcca6e1818534a0dcbefc9d825e0e0ce61a5b8dc6c73a1f94a`. The Drive quota blocked the download, so the sha was not checked against local bytes.

Intersecting with the 7614 qAR balance addresses at nonce 2074518 gives 54 processes, about 9.34 GiB in total. By the rule, all should be downloaded. In fact none was saved. The only checkpoint whose sha check passed is a 23 MB ucm-0.3 order book sample, and it is not among the 54.

## Numbers

- Folder files 1113. Checkpoint bins 1012. Matched in the report 996. Bins only on Drive 16. Bins without a size 9. HEAD size different from the report 0.
- Balance intersection 54. Nonzero 41. Zero 13. Top 20: 3739025408 bytes. All: 10032578560 bytes. Downloaded 0. sha checked 0.
- Pool list id lines 19, deduplicated 18, on Drive 4, not on Drive 14.
- The report requested 10813 processes, the missing list has 9817, and the archive scan has 9723 entries. Source `minio-rds/rds-backups/cu-state-export/state-20260904T155934Z.tar.zst`. Report file sha256 `10e2e7a0a07b70de3eaddb63ac39c8f5e8d4193857962e45f5b503d6a313414f`.
- sqlite `checkpoint_files` has 1008 rows. qAR process 0 rows. The qAR module id is among the 23 rows of `modules`.
- ClamAV 1.5.4, main scan 101 files, 0 infected. `npm audit --package-lock-only` reports 18 items (critical 1, high 15, moderate 2). No dependencies were installed.

## Evidence

- `inventory.json`: directories, file ids, size sources, and whether named processes appear.
- `overlap.json`: the 54 balance intersections, and the 19 pool config lines.
- `roles.json`: handler offsets in the only checkpoint read. The preferred pool has no memory offsets.
- `sqlite-index.json`: row counts of the read-only sqlite and the evaluation fields of the four pools.
- `scan-report.json`: ClamAV and npm audit.
- `static-review.md`: scripts, network addresses, subprocess search, `.env` variable names.
- `usefulness.md`: (a) to (d), the pool intersection, P8/P9.
- `code-manifest.json`: sha256 of the saved code files. The hash of `.env` is not written.
- Large files are in `<repo>/data/raw/drive-cu/`. The code tree, two checkpoints (the report and the 23 MB sample), and the HTTP records are there. `.env` has mode 0600.

## Not done

- The bytes of the 54 intersecting checkpoints and the 4 pool files were not obtained. The preferred pool's sha256 is still the report value.
- The sha of the second small sample `6eU3_ot8dl0dm9B6pUxZDzl78VKfzgDRSyuRumGbE9E_ts-1744639069181_ord-1412_bh-1649702.bin` is not checked.
- 9 Drive-only bins have no size.
- The tail replay `balances.json` does not exist yet, so the intersection was not recomputed.
- The 481165312 for `rKpOUxss...` comes from the stdout of a HEAD that was not written to `requests.jsonl`.
- No more large files were pulled from Drive. The quota page had already appeared, and continuing could extend the limit.

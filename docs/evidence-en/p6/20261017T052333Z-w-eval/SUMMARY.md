> English translation of [`evidence/p6/20261017T052333Z-w-eval/SUMMARY.md`](../../../../evidence/p6/20261017T052333Z-w-eval/SUMMARY.md). The original is authoritative. It is a work log of progress at the time, not a final conclusion. Current numbers are in the root README and `repro/EXPECTED.json`.

# P6 semantic gate

The byte gate did not pass. The semantic gate passed. Using block heights from the current gateway, we replayed from nonce 2074508 to 2074510, and then from 2074510 to 2074518. Neither final memory sha256 equals the target checkpoint. We then read the full balance table from copies of the replay memory and the checkpoint memory. The two sides are identical address by address. Checkpoint 2074518 can be used as the replay start. The tail was not replayed in this run.

The balance table is taken from `Messages[].Data`. `Output` is `[]`, not the balance table. The main session's `Balances_match` at c058c5c compared this `Output`.

| Gate | Start | End | Messages | Resulting sha256 | Checkpoint sha256 | Addresses | Balance differences | Total-Supply | Sum equals supply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 2074508 | 2074510 | 115 | `6ea2c0646d295040de6045475faa1b947fa3de09ecf8d6c5a810e038af75a890` | `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1` | 7614 | 0 | `189487568412204611` | yes |
| B | 2074510 | 2074518 | 108 | `08b33bd914ffd015fff0e0349ab279ed064eaa44dd79a35e3cfb26a7abd32baa` | `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` | 7614 | 0 | `189487568412204611` | yes |

The balance JSON sha256 is also the same on both sides for each segment. A is `24f7b1e2f5a8bb6961c24630bb915cf1cb4804911e5803a8c5459d35b715f400`. B is `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`. For both the replay and the checkpoint, `sum(Balances)` equals Total-Supply. All four reads returned an empty error.

The evaluator is still Node v22.22.0 with `@permaweb/ao-loader@0.0.44`, permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461`. This replay set `REPLAY_GATEWAY_HEIGHTS=1` and did not use the 9 cron heights recorded in the target checkpoint.

## What the byte difference is

The difference is not a balance change, and it is not unstructured noise either.

At 2074518 (gate B), both memories are 428146688 bytes. The exact difference is 332736 bytes in 30004 runs, spread over 40 buckets of 1 MB. The last difference is at offset 236575800. The readable difference is those 9 crons: the timestamps are the same, and the Block-Height used by the replay is 1 to 3 higher than the one left in the checkpoint. These heights are written in the cron log and in "Updating latest block height". The Anchor multiset is the same. The Transfer count and the multisets of `sender_balance_*` / `recipient_balance_*` in events are the same. The decimal string of Total-Supply sits at offset 212117480 on both sides. No `"address":"amount"` entry in the heap disagrees with the balance table. The remaining differing bytes are Lua heap layout around those shifted strings. Category counts: other-text 107509, cron-log 98164, binary 85835, inbox-or-event 36629, block-height 4599.

At 2074510 (gate A), the exact difference is 1822229 bytes in 174208 runs. The last one is at offset 236624412. The same 9 height differences are all present. Beyond that, inbox cleanup over 55 blocks left a few older cron logs that appear on only one side. The replay has `1862417-1771718983630`, `1862431-1771720483630`, `1862476-1771726483630`. The checkpoint has `1862196-1771690483630`, `1862656-1771748383630`, `1862671-1771749583630`, `1862677-1771750183630`. Anchor also has a few copies on only one side (replay 1890100, 1890101, 1890110, 1890111, 1890150, 1890151; checkpoint 1898910, 1898911). The multisets of event amounts and Transfer counts are still the same.

So for ledger semantics, the byte difference is non-semantic. For the cron logs left in the inbox, gate A is not identical entry by entry, and gate B differs only in those 9 height numbers.

## The run that matched only with checkpoint heights

On the 3rd attempt, the 9 Block-Height values were copied in from the target checkpoint. Only then did both memory sha256 values equal the checkpoint. That is not an independent byte gate. The independent replay is the failed result above. The hashes from the earlier attempts are still recorded in `gate.json`.

## Gaps recorded while fetching

- The first GraphQL query (checkpoint, process, module) returned HTTP 572, and 200 on retry. The saved meta holds only the successful one.
- Checkpoint `lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg` was requested from `https://ar-io.dev/` several times, and every request returned HTTP 404. The bytes reuse the gzip already in `data/raw/checkpoints/`. The unpacked sha256 matches the SHA-256 tag.
- Five Transfers have GraphQL `data.size` 0. `arweave.net` returned a 2285-byte HTML shell. The replay treats Data as an empty string.
- The SU does not serve this process's origin (DNS failed, and su-m1 returned 403 after redirect). The cron phase uses `1726163983000`.

## Evidence

- `evidence/p6/20261017T052333Z-w-eval/semantic.json`
- `evidence/p6/20261017T052333Z-w-eval/gate.json`
- `evidence/p6/20261017T052333Z-w-eval/evaluator.json`
- `evidence/p6/20261017T052333Z-w-eval/manifest.json`
- Read script `recovery/p6/semantic.mjs`, difference classifier `recovery/p6/classify_regions.py`
- The raw tables and difference classes are in `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/`
- The gateway-height replay memories are `replay/gate-A-gateway.memory` and `replay/gate-B-gateway.memory` in the same directory

Not done: no tail replay, no claim published, LegacyNet not resumed, APUS not touched.

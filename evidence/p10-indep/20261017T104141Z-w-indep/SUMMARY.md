> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Independent ledger 20261017T104141Z

Python rules from qAR handler 0.16.0. The module was not executed.

## Checkpoint 2074518

Memory `<repo>/data/raw/src/20261017T051439Z-w-src/checkpoint/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.mem` is 428146688 bytes, sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`. Tag match: True.
Lua reader rows 7614. gate-B rows 7614. Equal: True.
Sum parsed 189487568412204611. Sum gate-B 189487568412204611.
Flags from the same globals table: `{"IS_STOPPED": false, "TRANSFERS_ENABLED": true, "DEPOSITS_ENABLED": false, "WITHDRAWALS_ENABLED": false}`.

## Tail 2074519..2075923

Assignments 1405. Transfer ok 703. Transfer rejected 0. Event ignored 701.
New balance keys: [{"nonce": 2075709, "recipient": "wjoJOfqq-JpsBLU196R4K-Fhj1ZQSnNkBqhTWc4ADl4", "quantity": "561743870384", "from": "F9dWqoqSMzC3oyigfhezyT0fzc5BjhIYVSqcQWOgDq8"}].
Independent rows 7615, sum 189487568412204611. Fast rows 7615, sum 189487568412204611.
Every address and raw balance matches `data/raw/fast/tail/balances.json`: True. The two JSON files hash differently because the key order differs.

## Eval nonce 2075923

Message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ` from `6I6ePxxK19g00lsgihn9T84URrBdNbBaRtSGw_qq9es`, 131 bytes.

```
table.insert(ao.authorities, 'CCcVUmUBl6scmH2a8thOqXjW9kmPVtf6bEDeP4Edw9c'); table.remove(ao.authorities, 1); print(ao.authorities)
```

The Eval inserts one ao.authorities entry and removes index 1. It does not read or write Balances. Mentions Balances: False.

## Rules that can write Balances

Source message `eFbNdlgikglktPipxZy8E6fCujVbtx3sdUHZPTFK_HA` (nonce 1977055).
Transfer debits `msg.From` and credits `Tags.Recipient` by `Tags.Quantity` after the checks in `instance:transfer`.
Mint and Burn handlers only raise. Mint-Tokens and Unwrap return before any balance write because DEPOSITS_ENABLED and WITHDRAWALS_ENABLED are false in this memory.
X- tags are copied onto notices. They are not used in the balance arithmetic. No message in this window has a Cast tag. Duplicate tag names do not occur; `Tab` would keep the first value.
Cron is not one of these 1405 assignments. The Cron handler does not write Balances.

## Evidence

- `evidence/p10-indep/20261017T104141Z-w-indep/start.json`
- `evidence/p10-indep/20261017T104141Z-w-indep/result.json`
- `evidence/p10-indep/20261017T104141Z-w-indep/transfers.jsonl`
- `evidence/p10-indep/20261017T104141Z-w-indep/manifest.json`

Manifest files:

- `evidence/p10-indep/20261017T104141Z-w-indep/start.json` 964 bytes sha256 `70886535848b20247b60154a8a5f70a938a38d66b9d2fb349a5d33d699cd5e50`
- `evidence/p10-indep/20261017T104141Z-w-indep/result.json` 1380 bytes sha256 `ff043fe70a26e3cb6b0aa1ecb790bf83f6b69b8b8b1adfd7edff98da468492a9`
- `evidence/p10-indep/20261017T104141Z-w-indep/transfers.jsonl` 336898 bytes sha256 `df510f45f15158961fe652a0ed7eeb70ac977af62ce28cbe9c3294bf37f68c0d`
- `<repo>/data/raw/indep/20261017T104141Z-w-indep/balances.json` 402362 bytes sha256 `80508d6785a97ef877dc07ad46da63f5cd5625d77456e1f4c4b0e08ccf757c16`
- `<repo>/data/raw/src/20261017T051439Z-w-src/checkpoint/ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk.mem` 428146688 bytes sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`
- `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/gate-B-balances-checkpoint.json` 402335 bytes sha256 `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`
- `<repo>/data/raw/fast/tail/balances.json` 402362 bytes sha256 `c1f5493442ce03708d7e9833940f80bc6274880cf9332f6e7ea4223c4a7f5d15`

`goal_complete` is false. This is a balance check, not a claim list.

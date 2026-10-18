> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Goal

Produce a qAR balance ledger at the last scheduled message that was actually pushed to Arweave, with the checks in README, or a written stop that says which check cannot be met and what evidence is missing.

The process id is `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. Its on-chain `Name` tag is `local-t-w-001`. Local trading configs label this same id as qAR. Do not switch to another process because the name tag differs.

This file is the standing order. `STATE.md` is the cursor. One session completes one phase, or one nonce range inside a phase, then stops.

## Done means

A committed report where all of these are true, each with a file path:

- Tail assignment: process, epoch, nonce, message id, timestamp, and the query that shows no higher pushed nonce.
- Nonce continuity from the first pushed assignment through that tail, or an explicit list of missing nonces.
- Module id `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0` bytes hashed, and the evaluator named.
- Replay of every present assignment up to the tail, checked against any pushed compute result that includes enough state to compare.
- Ledger rows: address, raw balance, human balance at 12 decimals.
- Sum of raw balances equals the process total supply at that nonce.
- Pool, lock, and bridge addresses listed apart from end-user wallets, each with the source the address came from.
- Collateral still held: asset, holder, raw amount, source. Any gap against supply is a number in the report, not a filled-in balance.

If a check cannot be met, the report says so and the goal stays unfinished. Missing rows are not zero.

## Out of scope

Do not move collateral. Do not publish a claim list. Do not resume LegacyNet. Do not reconstruct APUS unless `STATE.md` opens that phase. APUS is only a second process the checkpoint did not contain.

## How to run a session

1. Read `STATE.md`. Read only the files it names.
2. Do the phase in `Next`. If that phase says "one range", do one range.
3. Write evidence before writing the conclusion.
4. Update `STATE.md`: phase result, evidence paths, and the next phase. Append one dated line to the log there.
5. Stop. Do not start the next phase in the same session.

A session that is about to run out of quota still does step 4 with whatever finished, including a failed query. The next model starts from that file.

## Where bytes go

Commit small results: JSON findings, manifests, the ledger CSV once it exists, and this status file.

Put bulk downloads, module bytes, and replay snapshots under `data/raw/`. That directory is gitignored, as are `*.sqlite`. Each committed manifest names the raw files by path, byte size, and hash, plus the nonce range they cover. Another machine that does not have `data/raw/` re-downloads from the cursor in `STATE.md`. It does not invent the missing range.

## Models

Any model that can read these files, query Arweave GraphQL, and run the chosen evaluator can take the next phase. Grok memory and chat history are not inputs.

Inside one phase, read-only queries may run in parallel. Only the session that owns `STATE.md` writes that file. Parallel workers write their own files under `evidence/` and do not edit the cursor.

## Stop without calling it done

- The proven tail has a nonce gap, and the missing assignments are not on Arweave.
- The module cannot be fetched, or the evaluator disagrees with a pushed result.
- Supply, balances, and collateral do not meet the checks. Record the numbers and stop.
- A step needs a credential, a private dump, or a human file that is not in the repo. Name the file and stop.

## Phases

P1. Prove or replace the tail candidate in `evidence/p0-probe.json`. Search for an assignment with a higher block or a higher nonce than `2075923`. Record the method.

P2. Fetch module `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0`. Record tags, byte size, and hash. Do not execute it.

P3. Sample nonce continuity: the first assignment, the tail, and three windows of 20 consecutive nonces. Do not download the full history. Choose the index method in `STATE.md` from that sample.

P4. Index assignments in nonce ranges. One range per session. Default range size is 50,000 nonces unless P3 shows the gateway cannot serve that. Manifest each range.

P5. Search pushed compute results for this process. A result that carries a memory or balance snapshot becomes the replay start, and only later nonces are replayed. A result that is only a message output is a later check, not a snapshot. No snapshot means replay from the first nonce.

P6. Select the evaluator and pass one check: replay a short prefix and match a pushed result, or record why no such result exists.

P7. Replay range by range to the tail. Persist a snapshot after each range. Emit partial balance files. One range per session.

P8. Split pool, lock, and bridge addresses from user wallets. Seed the list from the local configs that already map this process id to qAR, and cite the file for each address.

P9. Identify the collateral from the process handlers and from messages, not from the ticker. Record asset, holder, and amount, with sources.

P10. Write the reconciliation report. The goal is complete only when the checks above pass.

Side phase D, any time a human drops a file listing: inventory `https://drive.google.com/drive/folders/1HvWUSVZxHgl6lILpFe9AkODgDxQ6KVdn?usp=sharing` for these two process ids. Absence confirms the checkpoint path stays closed. Do not block P1 on this folder.

## Amendment 2026-10-18: checkpoint basis

The original goal assumed a replay from the first nonce. P5 found a signed compute-unit checkpoint, `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk`, nonce 2074518, signer `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk` (`evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json`, `evidence/p6/20261017T0715Z-p6-checkpoint-accepted/acceptance.json`). The ledger is replayed from that checkpoint to the tail. Two original checks cannot be met on this path, and they do not bear on the tail balances: continuity from the first nonce (`150000..2074399` is not indexed on Arweave, and 759 explicit holes sit below 150000; `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json`, `evidence/p4/20261017T043811Z-p4-100000-149999/gaps.json`), and collateral reconciliation (native AR was moved out of the custody wallet and commingled; `evidence/p9/20261017T1720Z-p9-record/`).

Done means, each with a file path:

1. Tail fixed, unchanged (`evidence/p1-tail.json`).
2. Checkpoint verified: id, nonce, signer, ANS-104 signature, and SHA-256 tag checked (`evidence/p5/20261017T053304Z-p5-checkpoints/replay-start.json`). This replaces "Nonce continuity from the first pushed assignment."
3. Tail inputs complete: every assignment from the checkpoint nonce + 1 through the tail is present, and the hash chain links, 1523/1523 (`evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json`).
4. Module hashed and the evaluator named, unchanged (`evidence/p2/20261017T1645Z-p2a/module.json`, `evidence/p6/20261017T052333Z-w-eval/evaluator.json`).
5. Replay reproducible and checked against available pushed results, unchanged (`evidence/p7/20261017T1718Z-p7-replay-read/replay.json`, `evidence/p7/20261017T1708Z-p7-main-tail-crosscheck/crosscheck.json`).
6. Independent agreement: at least two independent methods produce the same canonical balance hash (`evidence/repro/20261017T120218Z-w-repro/result-offset-0.json`, `evidence/p10-indep/20261017T104141Z-w-indep/result.json`).
7. Ledger rows complete and the raw sum equals total supply, unchanged (`evidence/p10/20261017T1047Z-fast-tail/ledger.csv`, `evidence/p10/20261017T1047Z-fast-tail-inputs/supply.json`).
8. Classification disclosed: pool, lock, and bridge addresses cite their source; unidentified processes are listed as unknown; a `wallet` label means "not a process", not an identified owner (`evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json`). This replaces `classification_sourced`.

Known limitations. They do not block completion.

1. Trust assumption: the starting state is the checkpoint signed by the LegacyNet CU signer above. It cannot be re-derived from the first nonce because of the unindexed span and the holes. P4 is closed as superseded by the checkpoint, not as complete (`evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json`).
2. Collateral is reported as facts only: native AR, the custody-wallet balance at the tail block, the rest commingled, and the separable amount null (`evidence/p9/20261017T1720Z-p9-record/`). Reconciliation is outside this ledger.

`goal_complete=true` means the ledger is ready for public audit. It is not a claim list and not an instruction to distribute. `publish_claims=false` and `move_collateral=false` stay.

P11, the audit window: after the repository is public, issues stay open for 14 days. Every issue gets a written answer. If a balance changes, the canonical hash changes and the 14 days restart. Any distribution decision is made by the collateral holder after the window, outside this repository.

## Amendment 2026-10-18b

The user withdrew P11. There is no fixed audit window. After the repository is public, anyone may open an issue. If a balance changes, the canonical hash changes and the change is recorded in STATE.md. Any distribution decision is made by the collateral holder outside this repository.

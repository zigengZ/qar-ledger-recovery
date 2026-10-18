> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Checkpoint to tail

Run `20261017T052614Z-w-tail`. Process `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8`. The module was not executed.

Nonce set 2074400..2075923 inclusive is 1524 nonces. Indexed 1524. Missing 0. Conflicts 0. Contiguous: True.

Hash chain: 1523 matched, 0 failed, 1523 checked. Continuous through the tail: True.

Checkpoint Assignment and Hash-Chain tags match the indexed assignment at 2074508, 2074510, and 2074518: True.

P1 tail nonce 2075923 assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs` hash `mfxRfK81zmLlDRBkrXmmHN96hkjcWKNJT82n2pHAsvE` message `wEP24VhCVebi9GrE1bsUn0DCiJ0uKBuju1qBm4VYqNQ` matches this index, including 2075920..2075922: True.

Messages stored 1524 of 1524. Signature verified 1524. Missing 0.

GraphQL had no transaction for two message ids, nonce 2075899 `VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA` and nonce 2075900 `iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw`. Both direct data URLs returned HTTP 404. The bytes were in L1 transaction `MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA` at inclusion block 1924100, read through the chunk offset API. Each item's signature verifies. See `message-gap-recovery.json`.

Bound checkpoint to tail: yes.

## Evidence

- `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json`
- `evidence/p4-tail/20261017T052614Z-w-tail/messages-manifest.json`
- `evidence/p4-tail/20261017T052614Z-w-tail/assignments.json`
- Raw GraphQL bodies and ANS-104 items: `<repo>/data/raw/tail-2074400/20261017T052614Z`

## Unfinished

- This run does not replay the process and does not produce a balance ledger. `goal_complete` stays false.
- Checkpoint bytes were not downloaded. The bind uses the Checkpoint tags and the assignment index.
- A GraphQL miss is not proof a nonce was never published. Missing nonces, if any, are listed in the range manifest.

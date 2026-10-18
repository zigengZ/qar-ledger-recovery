# STOP

goal_complete=false

P4 range 0..49999 is not complete.
Unresolved nonces: 5770..5793 inclusive (24 nonces).
Exact Nonce queries, with and without epoch 0, and epoch 1 for nonce 5770, returned no assignment.
Closed block window 1543160..1543170 contains nonces 5698..5841 except that hole.
Neighbors 5769 (block 1543163) and 5794 (block 1543166) are present.
Nonce 0 matches the P3 assignment. Nonce 2 matches P1. Nonce 49999 was indexed.
The module was not executed.

Last cursor: inclusion height next is the scanned cursor in range-manifest.json.
SQLite is local only: data/raw/p4/0-49999/20261016T175757Z-p4-0-49999/assignments.sqlite

Recovery: bring in those 24 assignments from outside this GraphQL index, then recheck the hash chain from 5769 to 5794.
Do not mark this range complete. Do not replay past the hole. Do not publish a claim list.

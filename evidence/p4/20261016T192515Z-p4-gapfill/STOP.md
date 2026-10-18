# STOP

goal_complete=false

P4 range 0..49999 has every nonce exactly once after the raw bundle search. It is still not complete.

GraphQL had no assignments for nonces 5770..5793. They are inside bundle `jMUfJeklmGk0IUTpsVbqasjfu6F8qoYyFOXBWECQ4P4` in block 1543166. Neighbor controls also matched the raw bytes: nonce 5769 in `NtGZ9VCNR541k8sTJqO8O41axvNbpbwSv4YDwCPMvtE`, nonce 5794 in `iBy0pq7-x5jZLhnt6qqvu_jvzAHJWTF0TIMeiBNde0U`.

Hash chain: 49975 of 49999 consecutive links match `sha256(previous assignment id || previous hash chain)`. The 24 that do not are nonces 5771..5794. The link 5769->5770 does match. Assignment ids are `sha256(signature)` and agree with the bundle header.

Do not start nonce 50000. Do not replay across this break. Do not publish a claim list. The module was not executed.

Recovery: explain the preimage of the Hash-Chain tag on nonce 5771, then recheck 5771..5794. Evidence: `evidence/p4/20261016T192515Z-p4-gapfill/`.

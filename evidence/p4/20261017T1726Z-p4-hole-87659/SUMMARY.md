> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Nonce 87659 stays missing

`schedule_covered` stays false. `goal_complete` is false. This is not a claim list.

The first missing range in `evidence/p4/20261017T043721Z-p4-50000-gaps-blocked/finding.json` is nonce 87659 by itself. Its assignment id is null. Its raw amount is null. The blocked file still lists 132 missing nonces in 50000..99999.

Neighbor blocks 1551411 and 1551416 were already scanned. The 29 non-AO bundles in that window were fully read and held no wanted nonce. The largest bundle in each of those blocks had no process hit. AO bundle `iCo0fdk5dSFNKQzcfDDWmmzV5_Xey19YdpEuM_7x7uA` in block 1551416 is not closed. The later chunk probe got HTTP 404 and no readable chunk. That does not prove nonce 87659 was never published.

No row was inserted. The other 131 holes in this range, and the 627 holes in 100000..149999, stay unresolved. No P4 range at nonce 150000 or later is opened.

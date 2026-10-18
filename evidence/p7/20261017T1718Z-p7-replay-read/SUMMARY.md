> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Replay read

The local tail report records the last item as an assignment at nonce 2075923. Its memory sha256 is `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`. The committed crosscheck already records that this sha matches the fast replay and the clean clone, and that the balance diff against the fast file is 0. This file copies those fields so the P10 reader can see them. It does not add `checked_against_pushed_result`. The reader derives that comparison from the sha match and the zero diff.

The crosscheck file itself still has no last nonce. A read of that file alone does not say the replay reached nonce 2075923.

Full safe mode was not run. `goal_complete` is false. This is not a claim list. The 132 and 627 holes stay unresolved. The separable collateral amount stays null.

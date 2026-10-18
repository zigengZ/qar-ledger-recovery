> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P9 collateral record

Run `20261017T1720Z`. The module was not executed. No funds were moved.

## Conclusion

The asset in the deposit and withdraw messages is native AR, in winston, on Arweave. There is no single holder. The original custody wallet `nLVp9CqNi3JQjtQuZidQdUFd-RGULF8WtI0s50WV94c` holds `978114007970` winston at tail block 1951869. That figure is the whole wallet. It is not eligible qAR collateral.

The separable raw amount at nonce 2075923 and now is null. It is not 0. `collateral_sourced` is false. `collateral_reconciled` is false. `goal_complete` is false.

## Time point

Epoch 0, nonce 2075923, block 1951869, 2026-07-04T06:19:55.380Z, assignment `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`.

## Sources

See `sources.jsonl`. The numbers come from `evidence/p9/20261017T090508Z-w-collat/`.

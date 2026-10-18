> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# P6 语义门

字节门未通过。语义门通过。用当前网关的区块高度，从 nonce 2074508 回放到 2074510，再从 2074510 回放到 2074518，最终内存的 sha256 都不等于目标检查点。在回放内存和检查点内存的副本上读取完整余额表后，两边逐地址相同。检查点 2074518 可以作为回放起点。没有往尾部回放。

余额表取自 `Messages[].Data`。`Output` 是 `[]`，不是余额表。主会话 c058c5c 的 `Balances_match` 比的是这个 `Output`。

| 门 | 起点 | 终点 | 消息 | 得到的 sha256 | 检查点 sha256 | 地址 | 余额差异 | Total-Supply | sum 等于供给 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 2074508 | 2074510 | 115 | `6ea2c0646d295040de6045475faa1b947fa3de09ecf8d6c5a810e038af75a890` | `b4805ec77e3b53d0362a1e3b3932ec86b94a6fdbaacdcccf32b74ab29ff829a1` | 7614 | 0 | `189487568412204611` | 是 |
| B | 2074510 | 2074518 | 108 | `08b33bd914ffd015fff0e0349ab279ed064eaa44dd79a35e3cfb26a7abd32baa` | `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26` | 7614 | 0 | `189487568412204611` | 是 |

两段的余额 JSON sha256 也相同。A 是 `24f7b1e2f5a8bb6961c24630bb915cf1cb4804911e5803a8c5459d35b715f400`。B 是 `e8637b0e4af3fae0837fdde365c17997bbd6a715c76750d31783b201b2bc0967`。回放和检查点各自的 `sum(Balances)` 都等于 Total-Supply。四次读取的错误都是空。

评估器仍是 Node v22.22.0 加 `@permaweb/ao-loader@0.0.44`，permaweb/ao `0db88a45aabeb5e88471e5c263790fa51a563461`。这次回放设置 `REPLAY_GATEWAY_HEIGHTS=1`，没有使用目标检查点里记下的 9 个 cron 高度。

## 字节差异是什么

差异不是余额变化，也不是一整片无结构噪声。

2074518（门 B）两份内存都是 428146688 字节，精确差异 332736 字节、30004 段，分布在 40 个 1MB 桶里，最后一处差异在偏移 236575800。可读差异就是那 9 条 cron：时间戳相同，回放用的 Block-Height 比检查点里留下的高 1 到 3。这些高度写在 cron 日志和 “Updating latest block height” 里。Anchor 多重集相同。Transfer 数量和事件里的 `sender_balance_*` / `recipient_balance_*` 多重集相同。Total-Supply 的十进制串在两边的偏移都是 212117480。堆里没有一条 `"地址":"数额"` 和余额表不一致。其余差异字节是这些字符串挪位周围的 lua 堆布局。分类计数：other-text 107509、cron-log 98164、binary 85835、inbox-or-event 36629、block-height 4599。

2074510（门 A）精确差异 1822229 字节、174208 段，最后一处在偏移 236624412。同样的 9 个高度差都在。除此之外，55 区块的收件箱清理留下了少量更早的 cron 日志，只出现在一边：回放有 `1862417-1771718983630`、`1862431-1771720483630`、`1862476-1771726483630`；检查点有 `1862196-1771690483630`、`1862656-1771748383630`、`1862671-1771749583630`、`1862677-1771750183630`。Anchor 也有少量只在一边的副本（回放 1890100、1890101、1890110、1890111、1890150、1890151；检查点 1898910、1898911）。事件数额和 Transfer 数量的多重集仍然相同。

所以对账本语义，字节差异是非语义的。对收件箱里留下的 cron 日志，门 A 不是逐条相同，门 B 的差别只在那 9 个高度数字。

## 用检查点高度才能对上的那次

第 3 次尝试把那 9 个 Block-Height 从目标检查点抄进来，两段内存 sha256 才与检查点一致。那不是独立字节门。独立回放就是上面的未通过结果。前几次的哈希仍记在 `gate.json`。

## 取数时记下的缺口

- 第一次 GraphQL（检查点、进程、模块）HTTP 572，重试后 200。保存的 meta 只有成功的那次。
- 检查点 `lETwgVJ4Enqa_YdUv2IynHNfl940PTDZ7dLdDUc4Arg` 向 `https://ar-io.dev/` 取了多次，都是 HTTP 404。字节复用 `data/raw/checkpoints/` 里已有的 gzip。解压后 sha256 与 SHA-256 tag 一致。
- 五条 Transfer 的 GraphQL `data.size` 是 0。`arweave.net` 返回 2285 字节的 HTML 壳。回放把 Data 当作空字符串。
- SU 不提供这个进程的 origin（DNS 失败，转到 su-m1 后 403）。cron 相位用 `1726163983000`。

## 证据

- `evidence/p6/20261017T052333Z-w-eval/semantic.json`
- `evidence/p6/20261017T052333Z-w-eval/gate.json`
- `evidence/p6/20261017T052333Z-w-eval/evaluator.json`
- `evidence/p6/20261017T052333Z-w-eval/manifest.json`
- 读取脚本 `recovery/p6/semantic.mjs`，差异分类 `recovery/p6/classify_regions.py`
- 原始表和差异分类在 `<repo>/data/raw/eval/20261017T052333Z-w-eval/semantic/`
- 网关高度回放的内存是同目录 `replay/gate-A-gateway.memory` 和 `replay/gate-B-gateway.memory`

未做：不回放尾部，不发布 claim，不恢复 LegacyNet，不碰 APUS。

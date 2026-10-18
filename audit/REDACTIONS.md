# 证据脱敏记录

sha256 是文件字节的哈希，不是 `git hash-object`。旧值来自 `git show HEAD:path`（审计开始时的 `f90d6f5`）。新值是本工作区写完后的字节。

这些文件里的链上地址、原始余额、行数保持不变。`holders-classified.json` 仍是 7614 条，非来源字段没有差异。`pools-locks-bridges.json` 仍是 2341 行。`ledger.csv` 仍是 7615 行，原始余额合计仍是 `189487568412204611`。`overlap.json` 里的地址保留。

分类器源码、测试、`vendor/drive-cu/LICENSE` 和 `vendor/drive-cu/README.md` 是源码变更，不进这张证据表。说明见 `audit/PUBLIC-READINESS.md`。

## 正文被改写的证据

| 文件 | 旧字节 | 旧 sha256 | 新字节 | 新 sha256 | 原因 |
| --- | ---: | --- | ---: | --- | --- |
| `evidence/p8/20261017T0906Z-w-p8/local-configs.json` | 17779 | `85050f798413a94725b1b8bf6a89d4b8757a0c6dacb3193c28dc3e4be27f5ac8` | 15769 | `e3d5bdaf08b8d1e00e3be4d0541059766223dc370ae59a53e88ba63348661919` | 私有配置摘录。配置键和费率改为 `redacted`，行号与 git 短 sha 改为空，路径改为 `private-config`，原文内容改为 `redacted`。 |
| `evidence/p8/20261017T0906Z-w-p8/holders-classified.json` | 6711012 | `4816b179137f27099dfd7c57f6f62971cc9836d96f592f254fc1350ecac8dc0c` | 6457661 | `a990d811144e5157e308deb33f6b377dcfd14fef554ccd9f358630f4f213f2f6` | 来源句子里的私有池键、费率数字和私有路径。19 处池句子、1 处借贷句子。余额与分类保留。 |
| `evidence/p8/20261017T0906Z-w-p8/pools-locks-bridges.json` | 2938696 | `e718cfa049a990bcf424e3aa80c07c9f448fb3a9cf59e36eea275b20dfadfcc9` | 2817470 | `018c03fe6e26f4bd02291f53761a9c91661cd43d544e40abce1dd5a91f07a7c2` | 同上，来源句子。行数与地址保留。 |
| `evidence/p8/20261017T0906Z-w-p8/SUMMARY.md` | 7393 | `8daf4f104c88d51956f836aceddfa01d465fd72739e83fdd3b6ac53718cb04a1` | 6933 | `72c9f3b0937590aad5dd98259e3e9eafab2b5e8e19c542e99a4856577470a4db` | 散文里的私有仓库路径、git 短 sha 和配置键。公开进程 id、排名、原始余额和 Name 保留。 |
| `evidence/p10/20261017T0954Z-fast-tail/ledger.csv` | 3651091 | `d1b70b19d2951043bd71cf9d1540fde28d9f919c59c31dc87da75abe682cb2dc` | 3397765 | `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2` | 从持有人分类复制来的来源句子。地址、原始余额、可读余额和分类保留。 |
| `evidence/side-d/20261017T0856Z-w-drive/overlap.json` | 72824 | `1a469faf88b9cfb01e748ddd0c9b0051e5231d8017e55a2f6517ff7c80250f11` | 70628 | `34b672a412403b49d8a67ccb33ea8fef562ed060538adad3751e5dc274ff5844` | 池记录上的配置键、费率、来源路径和行号。地址保留。 |
| `evidence/side-d/20261017T0856Z-w-drive/roles.json` | 4705 | `3a01647c1a56eadd3776c6c6cc5229043c734c1a317300e3d1fea5f00542aad3` | 4639 | `a736c4f495c727e6e28c5a4b473546fb32edfccf84c7d143ed5e1f38a3a0d426` | 角色说明里的私有配置名。 |
| `evidence/side-d/20261017T0856Z-w-drive/usefulness.md` | 12628 | `5d3e3a6463598f6155b4495841bd664b834bc2e88aff9de9bdf860f1d38b0612` | 12459 | `87a5782af77ca7a24b88c54725d11cc59375d881dc09fdc47faa4b850b2e6b23` | 池表里的配置名、费率和行号，以及来源句里的本地配置路径。Drive 文件 id、时间、大小和报告 sha256 保留。 |

本机根目录绝对路径还留在上述若干文件里，严重度是 should-fix。公开导出脚本会改写它们。本私有分支不改，方便工具继续按原路径读数据。

## 只更新了引用哈希的证据

持有人文件和账本的字节变了，引用它们的清单必须跟着变。下面三处是等长替换或清单字段更新，JSON 仍然有效。`REPORT.md` 没有改，清单里仍是 5810 字节、`275a03db440b09bf981f416dd625ea9ad43b88a81e466cd7c30b136690cac66f`。

| 文件 | 旧字节 | 旧 sha256 | 新字节 | 新 sha256 | 原因 |
| --- | ---: | --- | ---: | --- | --- |
| `evidence/p10/20261017T0954Z-fast-tail/reconciliation.json` | 45233 | `b60d891a0941426325cb5f8aa90ea942c42578f6360311e88a5ad8162060231e` | 45233 | `94d98261a92b5bc850618849ed205399d8d170a94516665cd50253d7d22b22a7` | 持有人输入从 6711012 / `4816b179…dc0c` 改为 6707236 / `f3db13a4…0060`。 |
| `evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md` | 4297 | `b420080de2791a74d9661231e683023e5a85348744f8b13c6e1efe917554abd5` | 4297 | `53e623f21083041758d16e15f8a43d9e27ca7b376af43ddb94c43ac34b53a112` | 同一处持有人 sha256 与字节数。 |
| `evidence/p10/20261017T0954Z-fast-tail/manifest.json` | 3576 | `7aa5fa87501b496aec9c5142d12c4e2660fcfa886d4aa448b43784075762a310` | 3576 | `c5fe7838a1f8b98fe2c7218c5d9bf58b9e8e88a31ae65c10630ed85ec8182547` | 记录账本、对账、SUMMARY 和持有人输入的新 sha256。 |

仓库里没有其他文件引用旧的持有人 sha256 或旧的账本 sha256。`evidence/side-d/20261017T0856Z-w-drive/code-manifest.json` 哈希的是 CU 源码清单，不哈希这些证据文件，所以没有改它。

## w-pub 追加

旧值来自本次改写前的 `git show HEAD:path`。sha256 仍是文件字节，不是 `git hash-object`。

### 正文被改写

| 文件 | 旧字节 | 旧 sha256 | 新字节 | 新 sha256 | 原因 |
| --- | ---: | --- | ---: | --- | --- |
| `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json` | 8545975 | `5d64b8a1051a41d6e6cbe796b479c428ef427c8d71b330df8788f47ce136bbec` | 7927333 | `eedd1fbf0b2bb98fbe0cc31516326e68e14826009b84196e1c036359eda5d95b` | 来源句子里的私有池键、费率数字、私有仓库路径和 git 短 sha。19 处池句子、1 处借贷句子。地址、原始余额、可读余额、分类和条数保留。 |
| `evidence/p8/20261017T1031Z-w-p8-tail/pools-locks-bridges.json` | 3501671 | `0245d4b1106a642dac99808476cce5967841f64c4b594c961832c78307c11c26` | 3268221 | `785c7a1d8557ca1f9155aebefb1f8e8a32ae22ededf594328592cd485a2f1345` | 同上，来源句子。19 处池句子、1 处借贷句子。行数与地址保留。 |
| `evidence/p8/20261017T1031Z-w-p8-tail/local-configs.json` | 17937 | `97b4ec373313f16afb9806d080a159e0d60af3728492d17b65244a84ace12d11` | 15877 | `11fc43357e83dab4c0b75f5501c34eab677f4b3bd36d01fdece028ee8c15bc22` | 配置键和费率改为 `redacted`，私有文件行号与 git 短 sha 改为空，路径改为 `private-config`，原文内容改为 `redacted`。地址、dex 名称和摘录行号保留。 |
| `evidence/p10/20261017T1047Z-fast-tail/ledger.csv` | 4648789 | `b7d49da76830970a720b3c8996a8f913b4396dd2f19f19bb5d83ee3fadb44f72` | 4212717 | `abaf6d70d279c16b5acee1825c25af70bef018a0b37e3a9c525471074ad2722c` | 从持有人分类复制来的来源句子。19 处池句子、1 处借贷句子。地址、原始余额、可读余额和分类保留。数据行仍是 7615，原始余额合计仍是 `189487568412204611`。 |
| `SUMMARY.md` | 2928 | `c6d84a34facae4d85652fee73c9c47a61f2cace785214204c12fd22187ba9037` | 3149 | `439cf7ac223bc1da534670ba6d6fe682f0e40c746f4bb8563dee64af7691e409` | 邮箱形态的模式文字改为不含 `@` 的写法。 |
| `evidence/doc/20261017T1037Z-w-doc/SUMMARY.md` | 2928 | `c6d84a34facae4d85652fee73c9c47a61f2cace785214204c12fd22187ba9037` | 3039 | `13618e702899e51a6b31f4c0c3073d3ebe72d0d3ebaca35a886a553b1189a30f` | 邮箱形态的模式文字改为不含 `@` 的写法。 |
| `web/scripts/methodology.test.mjs` | 2937 | `34ab1426f9147d48cf2a0516362ead8a55e2120719776416ba707a53fabbd3d5` | 3975 | `9bf1b2259136e1543fc736fd1396ec7cfde5145b7d4a20be554ca1b347eccf23` | 测试夹具改为运行时拼接，断言仍要求清洗结果里没有这个邮箱。另加公开仓库 slug 的测试：blob 链接用 `PUBLIC_REPO_SLUG`，默认 `zigengZ/qar-ledger-recovery`，needles 仍取真实 remote。 |

### 只更新了引用哈希

| 文件 | 旧字节 | 旧 sha256 | 新字节 | 新 sha256 | 原因 |
| --- | ---: | --- | ---: | --- | --- |
| `evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md` | 4438 | `16627339cda90ce09fb58fdc861d49e655d582c873dd1e3a43b2f4894db7b34d` | 4438 | `12d3dd3793a6e4d6bdab9203f2990def3dd882ae157f658a80426502aea3ddbe` | 持有人输入的 sha256 与字节数。 |
| `evidence/p10/20261017T1047Z-fast-tail/reconciliation.json` | 42662 | `59684ee57aff293e5f4028e62e45e4e3df6746f77c6bc8ddffa9b4251e806c41` | 42662 | `a6c79278a979fecf4338dfeb172d0593cf4a951002070f06d7d3d38c4f627da4` | 持有人输入的 sha256 与字节数。 |
| `evidence/p10/20261017T1047Z-fast-tail/manifest.json` | 3533 | `9316f6f72ad04d4e60bdc754d148cfc3dcb3873f2507d6c13bb4b2a097fbae7b` | 3533 | `374d79f26f0592de7ba83c979018b7e5aee207d400cea43ca198816315509244` | 账本、持有人输入、对账和 SUMMARY 的新 sha256 与字节数。 |
| `web/public/data/manifest.json` | 8204 | `f163aacaefac2deaf16e21b1e42ef81902a263b236c94d7bb216111bf392837a` | 8500 | `733d983f73ddbbeda875e1a80dfc86f1c718ff7e10202701267abb5dd9a02847` | 账本、持有人、池文件和对账文件的新 sha256 与字节数。 |

## w-pubscan 路径占位符和公开前修正

旧值是这次修改前的 `HEAD` 字节。新值是当前工作区字节。sha256 仍是文件字节，不是 `git hash-object`。

导出脚本会把绝对路径换成占位符，文件字节因此变化，清单里登记的 sha256 就对不上导出树。这些证据文件先在工作区里做了同样的替换。`<worktrees>/` 后面的 worker 目录改成了仓库相对路径。私有 inbox 路径改成了 `private-config/`。账本和持有人文件的地址、原始余额、可读余额、分类和行数没有改：0954、1047、1720 三份 `ledger.csv` 仍是 7615 行，原始余额合计仍是 `189487568412204611`。0906 持有人文件仍是 7614 条，1031 持有人文件仍是 7615 条，原始余额合计相同。

工作日志文件在开头加了「这是工作日志」。`docs/RECOVERY.md` 和 `docs/RECOVERY.zh.md` 改掉了已经过时的「待补」和「主回放进行中」。引用这些文件的清单改成了下表的新 sha256。旧表里的「新 sha256」列也改成了当前字节；「旧 sha256」列没有改。

| 文件 | 旧字节 | 旧 sha256 | 新字节 | 新 sha256 | 原因 |
| --- | ---: | --- | ---: | --- | --- |
| `SUMMARY.md` | 2933 | `9a3b0739b5bc0d11b00e0899b54f2fe262ccb3fe8fb28a009167e0e210ef9697` | 3149 | `439cf7ac223bc1da534670ba6d6fe682f0e40c746f4bb8563dee64af7691e409` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `docs/RECOVERY.md` | 52001 | `f97bf787849023a99e11ccb854de3ac50523bf0f4a2c2465332a905323b45d06` | 55732 | `fbd4de5028410e9d2c3277b6a6e7e0029b9479299f3a114620cb35d6b8b4c814` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `docs/RECOVERY.zh.md` | 50148 | `c11d5fa45631cdbba4e0840e9cf0e9136b534e37677f29d39c395337ad4442e9` | 53818 | `84743ad0ed08a8eea9c6f262b4c14beabbfd7c996ed5ec49583107283b7d83b3` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/doc/20261017T1037Z-w-doc/SUMMARY.md` | 2933 | `9a3b0739b5bc0d11b00e0899b54f2fe262ccb3fe8fb28a009167e0e210ef9697` | 3039 | `13618e702899e51a6b31f4c0c3073d3ebe72d0d3ebaca35a886a553b1189a30f` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10-dryrun/20261017T091010Z-w-report/REPORT.md` | 5541 | `395b2eafb25a157700189f89ef2ed2401356e9f6aa6823bc847de9dc1706b254` | 5441 | `93f67372c0f15a2c321ff3e4bb7f293a26362acfb526e8747d24e2b7b2911fff` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10-dryrun/20261017T091010Z-w-report/SUMMARY.md` | 3914 | `ce879b550fb762ec9ce8508cb7a0652666c778ebc1f8d241c1c25b8c01b59c65` | 4010 | `ec47617866017493371a3745ab00f616cb5decb5d25579c30a22896797303cb4` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10-dryrun/20261017T091010Z-w-report/reconciliation.json` | 43258 | `43002b6c5839edf7f002a3481b96d8bafde82c79451eb7e97c0370a13e1203b0` | 43108 | `7996d8f6b6b0abb464df8edf8f97243d9cabab92631d03f0b57019599b2625bd` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10-indep/20261017T104141Z-w-indep/start.json` | 1014 | `c8f16bd3c485d7a6bad7f3d5d4197a8eadc6cbd8d37e72010cfa8e59036a56ce` | 964 | `70886535848b20247b60154a8a5f70a938a38d66b9d2fb349a5d33d699cd5e50` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T0954Z-fast-tail/REPORT.md` | 5810 | `275a03db440b09bf981f416dd625ea9ad43b88a81e466cd7c30b136690cac66f` | 5853 | `94058e566781274934687a68089e0d953a6863a3e2e623b6fac35d6009039941` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T0954Z-fast-tail/SUMMARY.md` | 4108 | `6c9278b7d142168162345383d0ba1a28e373fc2c02039de609f0f1aa57eac62c` | 4297 | `53e623f21083041758d16e15f8a43d9e27ca7b376af43ddb94c43ac34b53a112` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T0954Z-fast-tail/ledger.csv` | 3647315 | `751053c0545c07142d3cf8edccf1902214f067a27399e4484fc1badfe0115c52` | 3397765 | `bc30de2388ff9934492b5009956ed79be8d9ad840aa7ad9cafc570a6e90597f2` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T0954Z-fast-tail/manifest.json` | 3576 | `141ca9ff0d5cb171f885a6d2be72d57fddb2c64ab039e6b7efbbf9a307c7a55b` | 3576 | `c5fe7838a1f8b98fe2c7218c5d9bf58b9e8e88a31ae65c10630ed85ec8182547` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T0954Z-fast-tail/reconciliation.json` | 45233 | `a6f1c2ed1897940fdb999906b13ce1532e256b4719fe923f0f8b4c60ac7272bb` | 45233 | `94d98261a92b5bc850618849ed205399d8d170a94516665cd50253d7d22b22a7` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1047Z-fast-tail/REPORT.md` | 6028 | `1f459922fe03190bededde937eb6969a93b107d66b8f1d3411836f4bf857484a` | 6117 | `30529b83165cb696e7b96b6651b7ecb415938ea62c7479a007f6c73dc96eadea` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md` | 4203 | `46848af27f4debae5789a2a01c654a234f6a800189d0a3bcb407d2b47c1e44ea` | 4438 | `12d3dd3793a6e4d6bdab9203f2990def3dd882ae157f658a80426502aea3ddbe` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1047Z-fast-tail/ledger.csv` | 4645013 | `ec3872f66811a4fad5aa6e941a69a596ceee89b97199890b4386a54e6584b2b3` | 4212717 | `abaf6d70d279c16b5acee1825c25af70bef018a0b37e3a9c525471074ad2722c` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1047Z-fast-tail/manifest.json` | 3503 | `022a7e4e21587dac0ba20d27cd72e04bd191cf1dd9cb56c5c261d50aa1882b13` | 3533 | `374d79f26f0592de7ba83c979018b7e5aee207d400cea43ca198816315509244` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1047Z-fast-tail/reconciliation.json` | 42662 | `9befbfed54aeb23d0b46d7dc2400df845c15f4f71aabfd9dabae65e7fe1fc31c` | 42662 | `a6c79278a979fecf4338dfeb172d0593cf4a951002070f06d7d3d38c4f627da4` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1720Z-p10-after-p9/SUMMARY.md` | 3880 | `d5040e8f718a7084edbf510e68e7faedac8467c065cb6b3c0fe3dfdd790ff837` | 4026 | `1a786fbefa1c45bc7003dafe5786499d27f5257feac459bb4677425fce17c72d` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1720Z-p10-after-p9/ledger.csv` | 4645013 | `ec3872f66811a4fad5aa6e941a69a596ceee89b97199890b4386a54e6584b2b3` | 4212717 | `abaf6d70d279c16b5acee1825c25af70bef018a0b37e3a9c525471074ad2722c` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p10/20261017T1720Z-p10-after-p9/reconciliation.json` | 43386 | `bf9366243b4082931fe652777457f8d6891dfe506bb2e3cc5e6d2c5545d404b1` | 43386 | `41ff499e0e96566b3d0b984369df30d6fc2433600fe3850b7fab99f3c35a84cd` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p4-tail/20261017T052614Z-w-tail/range-manifest.json` | 127932 | `c145e6618e0d2c654bc35ec80ce4b7bfbf95405addb1e53d5ad35670143f798f` | 116357 | `dbc3123a5f771431d8209049950d5787447932b2fcf1dc46b25369f117df7ef2` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p6/20261017T052333Z-w-eval/SUMMARY.md` | 4847 | `504e3cc01827284e4ae398944adfe774ba6c075ba191629a4e55c4abeba10dda` | 4968 | `a38081ff4cb0cbc98a1537d66016983eb6aa8c50a456a89df39a07150ee6a1d7` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p6/20261017T052333Z-w-eval/semantic.json` | 4837 | `c81d0154e94e8be21e49e04a720549578f48ce4ba0f8fb7aa279ab69cf1f814b` | 4812 | `9a469c29d0c5bd09fba06375bfbec0bc81f046669b07865d65d557f637ddb770` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p6/20261017T102111Z-w-eval/SUMMARY.md` | 3672 | `0cebce842468dbde069f56d661d201b5fdd04a7b138a2513c86e85d18b5130bb` | 3793 | `0d08dda5b97e2ac3a900281ff222189fafca19563c4bf89d8f40f440dbe7a821` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T0906Z-w-p8/SUMMARY.md` | 6837 | `d36356ada787769fb5af27b92d98bcb7e87ab5be74f6238cf68d44393c191386` | 6933 | `72c9f3b0937590aad5dd98259e3e9eafab2b5e8e19c542e99a4856577470a4db` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T0906Z-w-p8/holders-classified.json` | 6707236 | `f3db13a4a20d520c3805754662f0d7b2e0cc51f0f698eaca0c55cef473950060` | 6457661 | `a990d811144e5157e308deb33f6b377dcfd14fef554ccd9f358630f4f213f2f6` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T0906Z-w-p8/local-configs.json` | 15794 | `d1ebd4efa0d86e333b8de6c80c8431ef42bbfc94cbcb465d70b940010487f646` | 15769 | `e3d5bdaf08b8d1e00e3be4d0541059766223dc370ae59a53e88ba63348661919` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T0906Z-w-p8/pools-locks-bridges.json` | 2934920 | `217763c9880a3c7cd26ba8bea62f73b0fab047d3bf8913eb7c84faf879690cd9` | 2817470 | `018c03fe6e26f4bd02291f53761a9c91661cd43d544e40abce1dd5a91f07a7c2` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T1031Z-w-p8-tail/holders-classified.json` | 8542199 | `17d5cd22c2f1353a3a5b4626c12442ad75b9250a207d269db04d5dd135944ff5` | 7927333 | `eedd1fbf0b2bb98fbe0cc31516326e68e14826009b84196e1c036359eda5d95b` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T1031Z-w-p8-tail/local-configs.json` | 15952 | `30006642e07e56bc06f7a79f8cf035cb63768806f1c4a1e66f1877c55ab78466` | 15877 | `11fc43357e83dab4c0b75f5501c34eab677f4b3bd36d01fdece028ee8c15bc22` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/p8/20261017T1031Z-w-p8-tail/pools-locks-bridges.json` | 3497895 | `6dd7959c908efde9f73f7b1dc1774a00a5f172b36c51fbfe2682df910ab700e8` | 3268221 | `785c7a1d8557ca1f9155aebefb1f8e8a32ae22ededf594328592cd485a2f1345` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/side-d/20261017T0856Z-w-drive/overlap.json` | 72003 | `1bc6453705c6317d343eec1b1986723973e507798f63ca3a14017374d7aa2c37` | 70628 | `34b672a412403b49d8a67ccb33ea8fef562ed060538adad3751e5dc274ff5844` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `evidence/side-d/20261017T0856Z-w-drive/roles.json` | 4664 | `74a0dba42e7ba116ef0486a967c65ce6dbd00c1b3f2e31f34821d8957f6d20a9` | 4639 | `a736c4f495c727e6e28c5a4b473546fb32edfccf84c7d143ed5e1f38a3a0d426` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `recovery/p6/classify_regions.py` | 9456 | `92b4fe21b8eef014bfe675742c067453cd5bebafefc5afb29ad2645a3f250fee` | 9440 | `e594e9ed51c04bfb19ac6d677ea89235b613fac245e36519ca7997dbb88a48ef` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `recovery/p6/fetch_transfer_data.py` | 9362 | `1e72133996dbe8a265479729f0036686c768a2d5c9fe1b0dddcbe526b1031689` | 9388 | `af00b7d926a35f31017904f50b19090c51dfa45304ac75826429b9a6c3a59204` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `recovery/p6/replay.mjs` | 17505 | `f9af10e2c35ddb039823225c36c83ffb95dd966533bc1632a3780cdb56c1c08c` | 17509 | `c74701721089544599419edb8f7cc596ab03510f14c52b0e8cffb176df600be4` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `recovery/p6/semantic.mjs` | 11960 | `063a43f6d93def3ef986062b87c73014df8b08571665fcd56d7582a21bf6a646` | 12062 | `1ba747a2ce4b7e481d42850d0aa5026419f439209d60f60458c2407de0df04fe` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |
| `web/public/data/manifest.json` | 8204 | `2185ec94c261c21dc846ec283b7d978b3d63f15f81bdbcea42b06c00f73e6950` | 8500 | `733d983f73ddbbeda875e1a80dfc86f1c718ff7e10202701267abb5dd9a02847` | 绝对路径换成与导出脚本相同的占位符，worker 目录改为仓库相对路径，或工作日志开头说明，或两者都有。地址、余额和行数未改。 |

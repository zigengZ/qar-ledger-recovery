> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# w-repro

干净克隆只访问公开网关，把 qAR 从 nonce 2074518 的检查点回放到 nonce 2075923。canonical 余额与已发表的 fast tail 非零余额逐地址一致。cron 的 Block-Height 加减 3 不改变这个哈希。

这不是领取名单。没有移动抵押物。

## 结论

- 内存 sha256 `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a`。
- canonical 余额 sha256 `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca`。这个值在 `repro/EXPECTED.json`。
- 非零地址 2239。原始地址 7615。5376 个零余额不在 canonical 文件里。
- 总供应和余额合计都是 `189487568412204611`。
- handler 错误 0。回放 39065 条，其中 cron 37660、assignment 1405。
- 前 10 条里，未打补丁的 loader 和原地模式内存 sha256 相同：`4e341435f023aa41f27fc2b1dbb764c14c30ca39b13f14a02704bac722562960`。
- cron 高度 +3 的内存 sha256 `d0dd22f387150aa3e894106cb5d8dde08783ea30974cfd78ea632e9a1c46bc20`。高度 -3 的内存 sha256 `6b11be84807469cebb5201867800cdbfcb21266ca14ae65322cff772be126c92`。两次的 canonical 余额哈希与偏移 0 相同。

## 数字

- 检查点 gzip 145634952 字节，sha256 `31f5e4811756ff22a98546144075dd238da76eeb05470a126df43eb2fe92e095`。gunzip 428146688 字节，sha256 `fbb8172e8879c5d27b3bc4b00de5a150a027d575a9faf511f3cd0747b949ce26`。ANS-104 签名和签名者核对通过。
- assignment 1406 条。hash-chain 1405 跳，尾部 `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`。
- 消息 1405 条。nonce 2075899 `VsMhQeocKCWuqgZk1DB0gzOaDyqJhQb25ELdJ_NSPwA` 和 nonce 2075900 `iiEldOzPeB91Mvt1H7McJq2yP9z0QDkKVSb_DMQgpgw` 不在 GraphQL，取自区块 1924100 的 bundle `MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA`。
- 区块 88431 个，高度 1863436..1951866。7 处时钟回退，最大 31 秒。回放保留这些已发布的时间。
- HTTP 响应 2537 条，留在工作目录的 `raw/http/`，不入库。
- 区块页大约 25 分钟。输入在工作目录之后，原地回放 601869 ms，该次进程墙钟 618282 ms。
- 一次回放的工作目录大约 0.6 GB。三次回放之后是 1.4 GB。
- Node v22.22.0，`@permaweb/ao-loader` 0.0.44。

## 证据

- `manifest.json`
- `result-offset-0.json`
- `result-offset-plus-3.json`
- `result-offset-minus-3.json`
- `probe.json`
- 命令和预期哈希：`repro/README.md`、`repro/EXPECTED.json`

## 未完成

完整的 `--mode safe` 没有跑。慢速模式可以由 `./repro/run.sh --mode safe` 启动。已做的对照是前 10 条。

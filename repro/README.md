# 从公开网关复现 qAR 尾部余额

这条命令从空的工作目录开始，只访问公开 Arweave 网关，把进程 `NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8` 从 nonce 2074518 的检查点回放到尾部 nonce 2075923。回放包含 cron。预期结果写在 `EXPECTED.json`。

## 环境

- Node.js v22.22.0。其他版本会直接退出。
- npm。`@permaweb/ao-loader` 锁定在 0.0.44，锁文件是 `package-lock.json`。
- 能访问公开网关。默认是 `https://arweave.net`，失败时按顺序试 `ar-io.dev`、`vilenarios.com`、`turbo-gateway.com`。GraphQL 再加 `arweave-search.goldsky.com`。
- 磁盘大约 2 GB。检查点 gzip 约 146 MB，解压后的内存约 408 MB，回放保存再写一份。
- 内存建议不少于 8 GB。启动参数已经把 Node 堆上限设为 8192 MB。

网关可以用环境变量换成自己的列表，逗号分隔，第一个是默认：

- `REPRO_DATA_GATEWAYS`
- `REPRO_GQL_ENDPOINTS`

工作目录默认是 `repro/work`，可以用 `REPRO_WORK` 改到别的相对路径。这个目录不入库。每次 HTTP 的请求体和响应体记在工作目录的 `raw/http/`。

## 一条命令

在仓库根目录执行：

```sh
./repro/run.sh
```

脚本会依次做完这些事，任何一步对不上就退出，不会把缺口当成空数据：

1. 从网关的 `/raw/<id>` 下载检查点 `ffGXsmlki22rK3C5Waxie6Ux3IpVFaxgFYZeuMpjnMk` 的原始字节。普通 `/<id>` 会按 `Content-Encoding: gzip` 先解压，签名对不上。核对 ANS-104 签名、签名者 `WjnS-s03HWsDSdMnyTdzB1eHZB2QheUWP_FVRVYxkXk`，以及 gunzip 后的 sha256 等于 tag `SHA-256`。
2. 取 nonce 2074518..2075923 的 assignment。2074518 的 id 和 Hash-Chain 必须等于检查点上的 tag。之后每一跳都是 `sha256(上一条 assignment id || 上一条 hash-chain)`，一直连到尾部 `MZa2GSyyT6V1i_hIZYDumeJFAYPUdvgzGo19RJCIcWs`。
3. 下载并核对每条消息的 ANS-104 签名。GraphQL 没有的消息，会到它的 inclusion 区块里找 binary bundle。tag 索引区分大小写，`bundle-format` 和 `Bundle-Format` 都查；一个网关的空页不会被当成这个区块没有 bundle。取不到就失败。
4. 下载 module `1PdCJiXhNafpJbvC-sjxWTeNzbf9Q_RfUNs84GYoPm0` 并核对 sha256。
5. 用 ao-loader 0.0.44 回放 2074519..2075923，包括每 5 分钟一次的 cron。
6. 写出最终内存 sha256、canonical 余额、余额 sha256、地址数、总供应，以及余额合计是否等于总供应。

canonical 余额是按地址排序的紧凑 JSON，末尾有一个换行。余额是原始整数字符串。零余额不写入。

已发布的这一次运行，原地模式的测量值会写在文末的“本次运行”。预期哈希以 `EXPECTED.json` 为准。

## 慢速模式

```sh
./repro/run.sh --mode safe
```

慢速模式使用未修改的 ao-loader。它每次把输入拷进 WASM 堆，并返回一块新的内存切片。

默认的原地模式在工作目录里写一份 loader 副本，不改 `node_modules`。ao-loader 0.0.44 用 `HEAPU8.set` 把输入拷进堆，用 `HEAPU8.slice()` 返回结果。它不写回调用者传入的 buffer，返回的切片也不是活的堆，所以下一次调用盖不到上一次的结果。堆里已经是上一次的结果时，下一次传入空 buffer，并跳过这次拷贝和切片。保存点仍会把堆拷出来。handler 出错时，从上一个保存点重放这一小段，保留出错前的内存；出错本身会让脚本退出。

默认运行会先用未打补丁的 loader 和原地模式各算前 10 条。两条的内存 sha256 必须相同，然后才继续完整回放。

## cron 高度

cron 的 `Block-Height` 用的是 CU 的规则：从左侧时间边界每秒走一格，当这一秒到达下一个网关区块的时间时，高度改成那个区块。进程区块时间是 `1726164008`。cron 相位是每 300 秒的余数 283。起点取进程区块时间减 25 秒，正好落在这个相位上。加 275 秒会选出同一组 tick。

敏感性测试把每条 cron 的高度整体加 3 或减 3，assignment 的高度不动：

```sh
./repro/run.sh --cron-height-offset 3
./repro/run.sh --cron-height-offset -3
```

先跑完偏移为 0 的那次。这两次必须得到同一个 canonical 余额哈希。内存 sha256 如果变了，会写在各自的 `result.json` 里。

## 输出

偏移为 0 的结果在工作目录的 `out/`：

- `balances.json`：canonical 余额
- `balances.sha256`
- `memory.sha256`
- `result.json`：地址数、总供应、合计是否相等、耗时

`out/balances.sha256` 的值就是 `EXPECTED.json` 里的 `canonical_balances_sha256`。

## 本次运行

下面的数字来自一次只访问公开网关的干净克隆。工作目录里的输入都是这次下载的，没有读取仓库里的 `data/raw`。

区块页大约用了 25 分钟。输入已经在工作目录里之后，原地回放 39065 条用了 601869 ms，这次进程的墙钟是 618282 ms。前 10 条对照里，未打补丁的 loader 用了 5078 ms，原地模式用了 1774 ms，两边的内存 sha256 都是 `4e341435f023aa41f27fc2b1dbb764c14c30ca39b13f14a02704bac722562960`。完整的 `--mode safe` 没有跑。

一次回放的工作目录大约 0.6 GB。再加上 cron 高度 +3 和 -3 各一份内存之后是 1.4 GB。HTTP 日志有 2537 条响应。

| 项目 | 结果 |
| --- | --- |
| 内存 sha256 | `25e629fd58413416511208b7fd5886b17ab971c705fd4f06430b1745814a018a` |
| canonical 余额 sha256 | `0c9fb668c34002db79e4f8a008bfafb2e34103fa4df34220a51f837c6110acca` |
| 非零地址 | 2239 |
| 原始地址 | 7615 |
| 总供应 | `189487568412204611` |
| 余额合计等于总供应 | 是 |
| handler 错误 | 0 |
| cron 高度 +3 的内存 sha256 | `d0dd22f387150aa3e894106cb5d8dde08783ea30974cfd78ea632e9a1c46bc20` |
| cron 高度 -3 的内存 sha256 | `6b11be84807469cebb5201867800cdbfcb21266ca14ae65322cff772be126c92` |

+3 和 -3 的 canonical 余额哈希与偏移 0 相同。+3 的第一条 cron 高度是 1863439，-3 是 1863433。

区块时间有 7 处回退，最大 31 秒。回放保留这些已发布的时间。两条 GraphQL 里没有的消息，nonce 2075899 和 2075900，取自区块 1924100 的 bundle `MguGot_xwUfDFlazB62Vcq7QRlrR_anfyXK8HeEx3eA`。

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Lang = "zh" | "en";
type Dict = Record<string, string>;

const zh: Dict = {
  nav_lookup: "查询",
  nav_holders: "全部余额",
  nav_verify: "验证与方法",
  lang_toggle: "EN",
  theme_dark: "深色",
  theme_light: "浅色",
  subtitle: "qAR（AO LegacyNet）在 nonce 2075923 的持有人余额",
  not_claim: "这不是领取名单。",
  loading: "正在读取数据…",
  load_error: "数据没有读到。请先在 web 目录运行 npm run build。",
  supply: "总供应",
  holders: "持有地址",
  nonzero: "非零地址",
  as_of: "账本时点",
  rank: "排名",
  address: "地址",
  balance: "余额",
  share: "占比",
  role: "分类",
  copy: "复制",
  copied: "已复制",
  lookup_label: "地址",
  lookup_placeholder: "输入或粘贴 Arweave 地址，可多个",
  missing_plain: "账本里没有这个地址",
  balance_zero: "余额为 0",
  invalid_address: "地址格式无效",
  url_trimmed: "分享链接只放进了前一部分地址，查询本身包含全部。",
  duplicates: "已去掉重复",
  trust_ok: "5 种独立计算结果完全一致",
  trust_review: "独立计算还没有全部吻合",
  trust_more: "查看验证 →",
  rank1_known: "第 1 名 {addr}（约 {share}）是单个地址，分类为{role}。身份没有核实。",
  rank1_generic: "第 1 名 {addr}（约 {share}）是单个地址，分类为{role}。",
  filter_all: "全部",
  search_holder: "搜索地址或名称",
  showing: "显示 {n} / {all}",
  sort_hint: "点击表头排序。",
  empty_filter: "没有匹配的地址。",
  download_csv: "下载 CSV",
  download_json: "下载 canonical JSON",
  page_prev: "上一页",
  page_next: "下一页",
  page_status: "{page} / {pages}",
  histogram: "余额分布",
  histogram_hint: "非零地址按数量级分档。零余额 {zero} 个，不在图里。",
  hist_count: "地址数",
  verify_title: "验证与方法",
  memory: "最终内存 sha256",
  canonical_title: "canonical 余额哈希",
  live_match: "吻合 ✓",
  live_waiting: "正在用浏览器重算 canonical 哈希…",
  live_failed: "现场计算和 canonical 余额哈希不一致。",
  live_pending: "canonical 余额哈希还没有公布。",
  checks_title: "五种独立计算",
  check_wasm: "精确 WASM 回放",
  check_wasm_body: "回放到 nonce 2075923，处理器错误 0，7615 行，原始合计等于单独读出的 Total-Supply。",
  check_assign: "只回放 assignment",
  check_assign_body: "1405 条 assignment 与含 cron 的回放得到同一份余额字节，地址和数额差异为 0。",
  check_python: "不跑 WASM 的 Python 重算",
  check_python_body: "703 笔转账入账，0 笔拒绝，7615 个地址和原始余额与 fast tail 账本一致。",
  check_clone: "干净克隆从公开网关从零复现",
  check_clone_body: "只访问公开网关，从检查点重放到尾部，内存和 canonical 余额哈希与 fast tail 一致。",
  check_slow: "主会话逐条复制内存的慢速回放",
  check_slow_body: "逐条复制内存，回放到 nonce 2075923，最终内存 sha 与 fast 回放和干净克隆一致。",
  check_cron: "cron 高度 ±3",
  check_cron_body: "cron 区块高度 +3 和 −3 不改变 canonical 余额哈希。",
  evidence_link: "证据",
  status_matched: "一致",
  status_in_progress: "进行中",
  status_pending: "待补",
  verify_self_title: "自己验证",
  repro_line: "在仓库根目录运行 ./repro/run.sh，从公开网关下载检查点并回放到 nonce 2075923。",
  limits_title: "已知局限",
  limit_checkpoint: "检查点由 LegacyNet CU 签名者签发。Arweave 上早期调度有空洞，所以无法从创世独立重算到该检查点。",
  limit_collateral: "抵押物未对账。充值和提现用的是原生 AR，没有单一持有人，可分离的原始数量是 null。原托管钱包在尾部区块 1951869 的余额是 978114007970 winston（约 0.978 AR），其后无标签转账把其余 AR 混入了其他钱包。",
  limit_wallet: "wallet 标签是一次成功的 id 查询没有返回边，不是已核实的个人身份。它只表示这个地址不是进程。",
  method_full: "完整方法",
  method_writing: "撰写中",
  method_missing: "docs/RECOVERY.zh.md 还没有写进仓库。文档提交后重新构建，这一段会换成正文。",
  sources: "数据状态",
  generated: "生成时间",
  sha: "sha256",
  bytes: "字节",
  outside_repo: "不在本仓库里",
  gitignored: "gitignore，仅交叉校验",
  source_link: "源码与证据",
  group_wallet: "钱包",
  group_pool: "池子",
  group_lock: "锁仓",
  group_process: "进程",
  group_unknown: "未知",
  tip_wallet: "一次 id 查询没有返回边，不是已核实的个人身份，只表示不是进程。",
  tip_pool: "池余额不是终端用户的领取额。",
  tip_lock: "仅凭 Name 标签分出的锁，置信度是 medium。",
  tip_process: "分类文件标成进程，包括代理、借贷和代币进程。",
  tip_unknown: "不是 43 位 Arweave id，或分类文件没有给出角色。",
};

const en: Dict = {
  nav_lookup: "Lookup",
  nav_holders: "All balances",
  nav_verify: "Verification and method",
  lang_toggle: "中文",
  theme_dark: "Dark",
  theme_light: "Light",
  subtitle: "qAR (AO LegacyNet) holder balances at nonce 2075923",
  not_claim: "This is not a claim list.",
  loading: "Loading data…",
  load_error: "The data files did not load. Run npm run build in web/.",
  supply: "Total supply",
  holders: "Addresses",
  nonzero: "Non-zero",
  as_of: "Ledger time",
  rank: "Rank",
  address: "Address",
  balance: "Balance",
  share: "Share",
  role: "Class",
  copy: "Copy",
  copied: "Copied",
  lookup_label: "Address",
  lookup_placeholder: "Enter or paste Arweave addresses, one or many",
  missing_plain: "This address is not on the ledger",
  balance_zero: "Balance is 0",
  invalid_address: "Invalid address format",
  url_trimmed: "The share link includes only the first addresses that fit. The lookup itself used every address.",
  duplicates: "Duplicates removed",
  trust_ok: "5 independent calculations match exactly",
  trust_review: "The independent calculations do not all match yet",
  trust_more: "View verification →",
  rank1_known: "Rank 1 {addr} (about {share}) is a single address, classed as {role}. Its identity was not checked.",
  rank1_generic: "Rank 1 {addr} (about {share}) is a single address, classed as {role}.",
  filter_all: "All",
  search_holder: "Search address or name",
  showing: "Showing {n} / {all}",
  sort_hint: "Click a column to sort.",
  empty_filter: "No matching addresses.",
  download_csv: "Download CSV",
  download_json: "Download canonical JSON",
  page_prev: "Previous",
  page_next: "Next",
  page_status: "{page} / {pages}",
  histogram: "Balance distribution",
  histogram_hint: "Non-zero addresses by magnitude. {zero} zero balances are left off the chart.",
  hist_count: "Addresses",
  verify_title: "Verification and method",
  memory: "Final memory sha256",
  canonical_title: "Canonical balance hash",
  live_match: "Match ✓",
  live_waiting: "Hashing the loaded balances in the browser…",
  live_failed: "The live hash does not equal the canonical balance hash.",
  live_pending: "The canonical balance hash is not published yet.",
  checks_title: "Five independent calculations",
  check_wasm: "Precise WASM replay",
  check_wasm_body: "Replayed through nonce 2075923, 0 handler errors, 7615 rows, raw sum equal to the separate Total-Supply read.",
  check_assign: "Assignment-only replay",
  check_assign_body: "The 1405 assignments produce the same balance bytes as the cron-inclusive replay, with 0 address or value differences.",
  check_python: "Python recompute without WASM",
  check_python_body: "703 transfers applied, 0 rejected. All 7615 addresses and raw balances match the fast tail ledger.",
  check_clone: "Clean clone from public gateways",
  check_clone_body: "Replayed from the checkpoint to the tail using only public gateways. Memory and canonical balance hashes match the fast tail.",
  check_slow: "Main-session slow replay, memory copied on each item",
  check_slow_body: "Copied memory on each item through nonce 2075923. The final memory sha matches the fast replay and the clean clone.",
  check_cron: "Cron height ±3",
  check_cron_body: "Cron block height +3 and −3 leaves the canonical balance hash unchanged.",
  evidence_link: "Evidence",
  status_matched: "Match",
  status_in_progress: "In progress",
  status_pending: "Not published yet",
  verify_self_title: "Check it yourself",
  repro_line: "From the repository root, ./repro/run.sh downloads the checkpoint from a public gateway and replays through nonce 2075923.",
  limits_title: "Known limits",
  limit_checkpoint: "The checkpoint was signed by the LegacyNet CU signer. Early scheduling on Arweave has holes, so the ledger cannot be independently recomputed from genesis to that checkpoint.",
  limit_collateral: "Collateral is not reconciled. Deposit and withdraw messages use native AR. There is no single holder, and the separable raw amount is null. The original custody wallet holds 978114007970 winston (about 0.978 AR) at tail block 1951869, and later untagged transfers mixed the rest into other wallets.",
  limit_wallet: "A wallet label is an empty id query that returned no edge, not an identified person. It only means the address is not a process.",
  method_full: "Full method",
  method_writing: "Being written.",
  method_missing: "docs/RECOVERY.md is not in the repository yet. Rebuild after it lands and this section will show it.",
  sources: "Data status",
  generated: "Generated",
  sha: "sha256",
  bytes: "Bytes",
  outside_repo: "Not in this repository",
  gitignored: "gitignored, cross-check only",
  source_link: "Source and evidence",
  group_wallet: "Wallet",
  group_pool: "Pool",
  group_lock: "Lock",
  group_process: "Process",
  group_unknown: "Unknown",
  tip_wallet: "An id query returned no edge. The label is not a verified person; it only means this is not a process.",
  tip_pool: "A pool balance is not an end-user claim.",
  tip_lock: "A lock taken from the Name tag. Confidence is medium.",
  tip_process: "Classed as a process, including agents, lending, and the token process.",
  tip_unknown: "Not a 43-character Arweave id, or the classification file has no role.",
};

const dict: Record<Lang, Dict> = { zh, en };

export function translate(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  let text = dict[lang][key] ?? dict.zh[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

interface I18nValue {
  lang: Lang;
  t: (key: string, vars?: Record<string, string | number>) => string;
  toggleLang: () => void;
  theme: "light" | "dark";
  toggleTheme: () => void;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("qar-lang") === "en" ? "en" : "zh"));
  const [theme, setTheme] = useState<"light" | "dark">(() => (document.documentElement.dataset.theme === "light" ? "light" : "dark"));

  useEffect(() => {
    document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
    localStorage.setItem("qar-lang", lang);
    document.title = "qAR Balances";
  }, [lang]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("qar-theme", theme);
  }, [theme]);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      t: (key, vars) => translate(lang, key, vars),
      toggleLang: () => setLang((current) => (current === "zh" ? "en" : "zh")),
      theme,
      toggleTheme: () => setTheme((current) => (current === "dark" ? "light" : "dark")),
    }),
    [lang, theme],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("i18n");
  return value;
}

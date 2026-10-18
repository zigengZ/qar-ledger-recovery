import { useEffect, useMemo, useState } from "react";
import { AddressText } from "../components/Address";
import { Distribution } from "../components/Distribution";
import { RoleBadge } from "../components/RoleBadge";
import { loadLedger } from "../data/load";
import type { Holder, LedgerData, Overview } from "../data/types";
import { useI18n } from "../i18n";
import { canonicalBalanceText } from "../lib/canonical.mjs";
import { downloadCsv, downloadText } from "../lib/csv";
import { cmpRaw, formatCount, formatPercentFixed, formatRawDisplay } from "../lib/format.mjs";
import { fullLedgerCsv, ledgerCsvName } from "../lib/ledgerCsv";
import { DISPLAY_ORDER, displayGroup, type DisplayGroup } from "../lib/roles";

const PAGE = 50;
const KNOWN_TOP = "cjp59bXFj6GL8ja200hnjfkGsXQrSG095SlyFH39-U8";
type SortKey = "rank" | "address" | "raw" | "share" | "role";

function compare(a: Holder, b: Holder, key: SortKey): number {
  if (key === "address") return a.address < b.address ? -1 : a.address > b.address ? 1 : 0;
  if (key === "raw" || key === "share") return cmpRaw(a.raw, b.raw);
  if (key === "role") {
    const role = displayGroup(a.role).localeCompare(displayGroup(b.role));
    return role || a.address.localeCompare(b.address);
  }
  return a.rank - b.rank;
}

export default function HoldersPage({ overview }: { overview: Overview }) {
  const { t } = useI18n();
  const [ledger, setLedger] = useState<LedgerData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<DisplayGroup | "all">("all");
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "rank", desc: false });
  const [page, setPage] = useState(1);

  useEffect(() => {
    void loadLedger().then(setLedger).catch((reason: unknown) => setError(String(reason)));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [query, role, sort.key, sort.desc]);

  const groups = useMemo(() => {
    if (!ledger) return [];
    const present = new Set(ledger.list.map((row) => displayGroup(row.role)));
    return DISPLAY_ORDER.filter((item) => present.has(item));
  }, [ledger]);

  const filtered = useMemo(() => {
    if (!ledger) return [];
    const needle = query.trim().toLowerCase();
    return ledger.list.filter((row) => {
      if (role !== "all" && displayGroup(row.role) !== role) return false;
      if (!needle) return true;
      return row.address.toLowerCase().includes(needle) || row.name.toLowerCase().includes(needle);
    });
  }, [ledger, query, role]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => compare(a, b, sort.key) * (sort.desc ? -1 : 1));
    return copy;
  }, [filtered, sort]);

  const pages = Math.max(1, Math.ceil(sorted.length / PAGE));
  const current = Math.min(page, pages);
  const slice = sorted.slice((current - 1) * PAGE, current * PAGE);

  function toggle(key: SortKey) {
    setSort((prev) => (prev.key === key ? { key, desc: !prev.desc } : { key, desc: key === "raw" || key === "share" }));
  }

  function downloadAll() {
    if (!ledger) return;
    downloadCsv(ledgerCsvName(ledger.nonce), fullLedgerCsv(ledger));
  }

  function downloadCanonical() {
    if (!ledger) return;
    const text = canonicalBalanceText(ledger.list.map((row) => [row.address, row.raw] as [string, string]));
    downloadText(`qar-balances-${ledger.nonce ?? "tail"}.json`, text, "application/json");
  }

  if (error) return <p className="text-copper">{error}</p>;
  if (!ledger) return <p className="text-muted">{t("loading")}</p>;

  const top = ledger.list[0];
  const topShare = top ? formatPercentFixed(top.raw, ledger.supplyRaw, 2) : "";
  const topShort = top ? `${top.address.slice(0, 5)}…` : "";
  const topRole = top ? t(`group_${displayGroup(top.role)}`) : "";
  const topKnown = top?.address === KNOWN_TOP;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-3xl">{t("nav_holders")}</h1>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn" onClick={downloadCanonical}>
            {t("download_json")}
          </button>
          <button type="button" className="btn primary" onClick={downloadAll}>
            {t("download_csv")}
          </button>
        </div>
      </div>
      {top ? (
        <p className="text-sm leading-relaxed">
          {t(topKnown ? "rank1_known" : "rank1_generic", { addr: topShort, share: topShare, role: topRole })}
        </p>
      ) : null}
      <Distribution overview={overview} />
      <div className="sticky z-20 -mx-4 space-y-2 border-b border-line/80 bg-bg/95 px-4 py-2 backdrop-blur" style={{ top: "var(--nav-h, 0px)" }}>
        <input className="field" value={query} placeholder={t("search_holder")} onChange={(event) => setQuery(event.target.value)} />
        <div className="flex flex-wrap gap-2">
          <button type="button" className={`chip ${role === "all" ? "chip-current" : "text-ink"}`} onClick={() => setRole("all")}>
            {t("filter_all")}
          </button>
          {groups.map((item) => (
            <button key={item} type="button" className={`chip ${role === item ? "chip-current" : "text-ink"}`} onClick={() => setRole(item)}>
              {t(`group_${item}`)}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted">
          {t("showing", { n: formatCount(filtered.length), all: formatCount(ledger.list.length) })}
          <span className="hidden md:inline"> · {t("sort_hint")}</span>
        </p>
      </div>
      {slice.length === 0 ? <p className="text-sm text-muted">{t("empty_filter")}</p> : null}
      <div className="space-y-2 md:hidden">
        {slice.map((row) => (
          <article key={row.address} className="card p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="num text-sm text-muted">#{row.rank}</span>
              <RoleBadge role={row.role} />
            </div>
            <div className="mt-2">
              <AddressText value={row.address} lookup />
            </div>
            <p className="mt-2 text-lg font-semibold tabular-nums">{formatRawDisplay(row.raw)}</p>
            <p className="raw-line">{row.raw}</p>
            <p className="num mt-1 text-sm text-muted">{formatPercentFixed(row.raw, ledger.supplyRaw, 4)}</p>
          </article>
        ))}
      </div>
      <div className="card hidden overflow-x-auto md:block">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-muted">
            <tr>
              <SortHeader label={t("rank")} active={sort.key === "rank"} desc={sort.desc} onClick={() => toggle("rank")} />
              <SortHeader label={t("address")} active={sort.key === "address"} desc={sort.desc} onClick={() => toggle("address")} />
              <SortHeader label={t("balance")} active={sort.key === "raw"} desc={sort.desc} onClick={() => toggle("raw")} align="right" />
              <SortHeader label={t("share")} active={sort.key === "share"} desc={sort.desc} onClick={() => toggle("share")} align="right" />
              <SortHeader label={t("role")} active={sort.key === "role"} desc={sort.desc} onClick={() => toggle("role")} />
            </tr>
          </thead>
          <tbody>
            {slice.map((row) => (
              <tr key={row.address} className="border-t border-line">
                <td className="num px-3 py-2">#{row.rank}</td>
                <td className="px-3 py-2">
                  <AddressText value={row.address} lookup truncate />
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="tabular-nums">{formatRawDisplay(row.raw)}</div>
                  <div className="raw-line">{row.raw}</div>
                </td>
                <td className="num px-3 py-2 text-right">{formatPercentFixed(row.raw, ledger.supplyRaw, 4)}</td>
                <td className="px-3 py-2">
                  <RoleBadge role={row.role} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between gap-2 text-sm">
        <button type="button" className="btn" disabled={current <= 1} onClick={() => setPage(current - 1)}>
          {t("page_prev")}
        </button>
        <span className="num text-muted">{t("page_status", { page: current, pages })}</span>
        <button type="button" className="btn" disabled={current >= pages} onClick={() => setPage(current + 1)}>
          {t("page_next")}
        </button>
      </div>
    </div>
  );
}

function SortHeader({
  label,
  active,
  desc,
  onClick,
  align = "left",
}: {
  label: string;
  active: boolean;
  desc: boolean;
  onClick: () => void;
  align?: "left" | "right";
}) {
  return (
    <th className={`px-3 py-2 font-medium ${align === "right" ? "text-right" : "text-left"}`}>
      <button type="button" className={align === "right" ? "ml-auto block" : ""} onClick={onClick}>
        {label}
        {active ? (desc ? " ↓" : " ↑") : ""}
      </button>
    </th>
  );
}

import { useEffect, useMemo, useState } from "react";
import { AddressText } from "../components/Address";
import { RoleBadge } from "../components/RoleBadge";
import { loadEvidence, loadLedger } from "../data/load";
import type { LedgerData, Overview } from "../data/types";
import { useI18n } from "../i18n";
import { allChecksMatch } from "../lib/checks.mjs";
import { copyText } from "../lib/csv";
import { formatCount, formatPercentFixed, formatRawDisplay, shortHash } from "../lib/format.mjs";
import { lookupRawText, presentLookup } from "../lib/lookup.mjs";
import { fitQuery, parseAddressList } from "../router";

function ledgerClock(iso: string | null, nonce: number | null): string {
  const nonceText = nonce != null ? `nonce ${nonce}` : "";
  if (!iso) return nonceText || "—";
  const match = iso.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/);
  const clock = match ? `${match[1]} ${match[2]} UTC` : iso;
  return nonceText ? `${clock} · ${nonceText}` : clock;
}

export function LookupPage({ overview }: { overview: Overview | null }) {
  const { t } = useI18n();
  const [text, setText] = useState(() => (new URLSearchParams(window.location.search).get("a") ?? "").replaceAll(",", "\n"));
  const [submitted, setSubmitted] = useState(() => new URLSearchParams(window.location.search).get("a") ?? "");
  const [duplicates, setDuplicates] = useState(0);
  const [trimmed, setTrimmed] = useState(false);
  const [ledger, setLedger] = useState<LedgerData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadLedger().then(setLedger).catch((reason: unknown) => setError(String(reason)));
  }, []);

  useEffect(() => {
    const onChange = () => {
      const value = new URLSearchParams(window.location.search).get("a") ?? "";
      setSubmitted(value);
      setText(value.replaceAll(",", "\n"));
    };
    window.addEventListener("popstate", onChange);
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("popstate", onChange);
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  const parsed = useMemo(() => parseAddressList(submitted.replaceAll(",", "\n")), [submitted]);
  const hits = useMemo(() => {
    if (!ledger) return [];
    return parsed.addresses.map((address) => ({
      address,
      row: ledger.byAddress.get(address) ?? null,
    }));
  }, [ledger, parsed.addresses]);

  function run(source = text) {
    const next = parseAddressList(source);
    const fitted = fitQuery(next.addresses);
    setDuplicates(next.duplicates);
    setTrimmed(fitted.trimmed);
    setSubmitted(next.addresses.join(","));
    const url = new URL(window.location.href);
    if (fitted.value) url.searchParams.set("a", fitted.value);
    else url.searchParams.delete("a");
    url.hash = "#/";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  return (
    <div className="space-y-3">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          run();
        }}
      >
        <label className="sr-only" htmlFor="lookup">
          {t("lookup_label")}
        </label>
        <textarea
          id="lookup"
          className="field lookup-input"
          value={text}
          placeholder={t("lookup_placeholder")}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              run(event.currentTarget.value);
            }
          }}
        />
      </form>
      <section className="stat-row" aria-label={t("supply")}>
        <Stat label={t("supply")} value={overview ? `${formatRawDisplay(overview.supply_raw)} qAR` : "…"} wide />
        <Stat label={t("holders")} value={overview ? formatCount(overview.addresses) : "…"} />
        <Stat label={t("nonzero")} value={overview ? formatCount(overview.nonzero) : "…"} />
        <Stat label={t("as_of")} value={overview ? ledgerClock(overview.as_of, overview.nonce) : "…"} />
      </section>
      <TrustBar />
      {trimmed ? <p className="text-sm text-copper">{t("url_trimmed")}</p> : null}
      {duplicates ? <p className="text-sm text-muted">{t("duplicates")} {duplicates}</p> : null}
      {error ? <p className="text-sm text-copper">{error}</p> : null}
      {submitted && !ledger && !error ? <p className="text-sm text-muted">{t("loading")}</p> : null}
      {ledger && submitted ? (
        <div className="space-y-3">
          {hits.map((hit, index) => {
            const view = presentLookup(hit.address, hit.row);
            return (
              <article key={`${hit.address}-${index}`} className="card p-4" data-kind={view.kind} data-raw={lookupRawText(view)}>
                <AddressText value={hit.address} />
                {view.kind === "balance" && view.raw ? (
                  <p className="balance-lg">
                    {formatRawDisplay(view.raw)} <span className="balance-unit">qAR</span>
                  </p>
                ) : null}
                {view.kind === "zero" ? <p className="balance-lg">{t("balance_zero")}</p> : null}
                {view.kind === "missing" ? <p className="balance-lg balance-note">{t("missing_plain")}</p> : null}
                {view.kind === "invalid" ? <p className="balance-lg balance-note">{t("invalid_address")}</p> : null}
                {view.raw ? <RawLine raw={view.raw} /> : null}
                {hit.row && (view.kind === "balance" || view.kind === "zero") ? (
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
                    <span>
                      <span className="text-muted">{t("rank")} </span>
                      <span className="num">#{hit.row.rank}</span>
                    </span>
                    <span>
                      <span className="text-muted">{t("share")} </span>
                      <span className="num">{formatPercentFixed(hit.row.raw, ledger.supplyRaw, 4)}</span>
                    </span>
                    <RoleBadge role={hit.row.role} />
                  </div>
                ) : null}
                <p className="mt-3 text-xs text-muted">{t("not_claim")}</p>
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "stat-supply min-w-0" : "min-w-0"}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function RawLine({ raw }: { raw: string }) {
  const { t } = useI18n();
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="raw-line"
      onClick={() => {
        void copyText(raw).then(() => {
          setDone(true);
          window.setTimeout(() => setDone(false), 1200);
        });
      }}
    >
      {done ? t("copied") : raw}
    </button>
  );
}

function TrustBar() {
  const { t } = useI18n();
  const [state, setState] = useState<"loading" | "ok" | "review">("loading");
  const [hash, setHash] = useState<string | null>(null);

  useEffect(() => {
    void loadEvidence()
      .then((evidence) => {
        setHash(evidence.canonical_balances?.sha256 ?? null);
        setState(allChecksMatch(evidence.timeline) ? "ok" : "review");
      })
      .catch(() => setState("review"));
  }, []);

  return (
    <a className="trust no-underline" href="#/verify">
      <span>{state === "ok" ? t("trust_ok") : state === "review" ? t("trust_review") : t("loading")}</span>
      {hash ? <span className="num">{shortHash(hash)}</span> : null}
      <span>{t("trust_more")}</span>
    </a>
  );
}

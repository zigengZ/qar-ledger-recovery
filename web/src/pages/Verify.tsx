import { useEffect, useState } from "react";
import { HashText } from "../components/Address";
import { renderMethodology } from "../components/MethodDoc";
import { loadEvidence, loadLedger, loadMethodology } from "../data/load";
import type { Evidence, Manifest, Methodology, Overview } from "../data/types";
import { useI18n } from "../i18n";
import { canonicalBalanceText } from "../lib/canonical.mjs";

const BLOB = "https://github.com/zigengZ/qar-ledger-recovery/blob/main/";

const CHECKS: { id: string; title: string; body: string; href: string }[] = [
  {
    id: "precise-replay",
    title: "check_wasm",
    body: "check_wasm_body",
    href: `${BLOB}evidence/p10/20261017T1047Z-fast-tail/SUMMARY.md`,
  },
  {
    id: "assignment-only",
    title: "check_assign",
    body: "check_assign_body",
    href: `${BLOB}evidence/doc/20261017T1037Z-w-doc/fast-excerpt/assignment-ledger.json`,
  },
  {
    id: "independent-nowasm",
    title: "check_python",
    body: "check_python_body",
    href: `${BLOB}evidence/p10-indep/20261017T104141Z-w-indep/SUMMARY.md`,
  },
  {
    id: "from-scratch",
    title: "check_clone",
    body: "check_clone_body",
    href: `${BLOB}evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`,
  },
  {
    id: "main-sha",
    title: "check_slow",
    body: "check_slow_body",
    href: `${BLOB}evidence/p7/20261017T1718Z-p7-replay-read/SUMMARY.md`,
  },
];

const PYTHON = `import csv, json, hashlib
body = dict(sorted((a, r) for a, r, *_ in list(csv.reader(open("evidence/p10/20261017T1047Z-fast-tail/ledger.csv", encoding="utf-8-sig")))[1:] if r != "0"))
print(hashlib.sha256((json.dumps(body, separators=(",", ":")) + "\\n").encode()).hexdigest())`;

export default function VerifyPage({ overview, manifest }: { overview: Overview; manifest: Manifest | null }) {
  const { lang, t } = useI18n();
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadEvidence().then(setEvidence).catch((reason: unknown) => setError(String(reason)));
  }, []);

  if (error) return <p className="text-copper">{error}</p>;
  if (!evidence) return <p className="text-muted">{t("loading")}</p>;

  const canonical = evidence.canonical_balances?.sha256 ?? null;
  const statusOf = (id: string) => evidence.timeline.find((step) => step.id === id)?.status;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-3xl">{t("verify_title")}</h1>
      </header>
      <section className="card space-y-3 p-4">
        <HashRow label={t("memory")} value={overview.memory_sha256} />
        <HashRow label={t("canonical_title")} value={canonical} />
        <LiveHash expected={canonical} />
      </section>
      <section className="card p-4">
        <h2 className="text-lg font-semibold">{t("checks_title")}</h2>
        <ul className="mt-3 space-y-4">
          {CHECKS.map((check) => (
            <li key={check.id} className="border-t border-line pt-3 first:border-0 first:pt-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-semibold">{t(check.title)}</h3>
                <Conclusion status={statusOf(check.id)} />
              </div>
              <p className="mt-1 text-sm leading-relaxed">{t(check.body)}</p>
              <a className="mt-1 inline-block text-sm" href={check.href} target="_blank" rel="noreferrer">
                {t("evidence_link")}
              </a>
            </li>
          ))}
          <li className="border-t border-line pt-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold">{t("check_cron")}</h3>
              <Conclusion status={statusOf("from-scratch")} />
            </div>
            <p className="mt-1 text-sm leading-relaxed">{t("check_cron_body")}</p>
            <a className="mt-1 inline-block text-sm" href={`${BLOB}evidence/repro/20261017T120218Z-w-repro/SUMMARY.md`} target="_blank" rel="noreferrer">
              {t("evidence_link")}
            </a>
          </li>
        </ul>
      </section>
      <section className="card space-y-3 p-4">
        <h2 className="text-lg font-semibold">{t("verify_self_title")}</h2>
        <pre className="overflow-x-auto rounded-xl bg-chip p-3 text-xs leading-relaxed">
          <code>{PYTHON}</code>
        </pre>
        <p className="text-sm leading-relaxed">{t("repro_line")}</p>
      </section>
      <section className="card p-4">
        <h2 className="text-lg font-semibold">{t("limits_title")}</h2>
        <ul className="mt-3 space-y-3 text-sm leading-relaxed">
          <li>{t("limit_checkpoint")}</li>
          <li>{t("limit_collateral")}</li>
          <li>{t("limit_wallet")}</li>
        </ul>
      </section>
      <MethodFold lang={lang} />
      <Sources manifest={manifest} />
    </div>
  );
}

function HashRow({ label, value }: { label: string; value: string | null }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted">{label}</span>
      {value ? <HashText value={value} /> : <span>{t("status_pending")}</span>}
    </div>
  );
}

function Conclusion({ status }: { status: string | undefined }) {
  const { t } = useI18n();
  if (status === "matched") return <span className="matched">{t("status_matched")}</span>;
  if (status === "in_progress") return <span className="font-medium text-copper">{t("status_in_progress")}</span>;
  return <span className="text-muted">{t("status_pending")}</span>;
}

function LiveHash({ expected }: { expected: string | null }) {
  const { t } = useI18n();
  const [state, setState] = useState<"loading" | "matched" | "mismatch" | "pending">("loading");

  useEffect(() => {
    let cancel = false;
    void loadLedger()
      .then(async (ledger) => {
        const text = canonicalBalanceText(ledger.list.map((row) => [row.address, row.raw] as [string, string]));
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
        const next = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
        if (cancel) return;
        if (!expected) setState("pending");
        else setState(next === expected ? "matched" : "mismatch");
      })
      .catch(() => {
        if (!cancel) setState("mismatch");
      });
    return () => {
      cancel = true;
    };
  }, [expected]);

  return (
    <div className="text-sm" data-canonical-state={state}>
      {state === "loading" ? <span className="text-muted">{t("live_waiting")}</span> : null}
      {state === "matched" ? <span className="matched">{t("live_match")}</span> : null}
      {state === "mismatch" ? <span className="font-medium text-copper">{t("live_failed")}</span> : null}
      {state === "pending" ? <span className="text-muted">{t("live_pending")}</span> : null}
    </div>
  );
}

function MethodFold({ lang }: { lang: "zh" | "en" }) {
  const { t } = useI18n();
  const [doc, setDoc] = useState<Methodology | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open || doc || error) return;
    void loadMethodology().then(setDoc).catch((reason: unknown) => setError(String(reason)));
  }, [open, doc, error]);

  const entry = doc?.documents[lang];
  const ready = entry?.status === "ready" && Boolean(entry.markdown);

  return (
    <details className="card px-4 py-3" onToggle={(event) => setOpen((event.currentTarget as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer text-lg font-semibold">{t("method_full")}</summary>
      {error ? <p className="mt-3 text-copper">{error}</p> : null}
      {open && !doc && !error ? <p className="mt-3 text-sm text-muted">{t("loading")}</p> : null}
      {ready && entry?.markdown ? (
        <article className="prose mt-3" dangerouslySetInnerHTML={{ __html: renderMethodology(entry.markdown, doc?.repo ?? null) }} />
      ) : null}
      {doc && !ready ? (
        <section className="mt-3">
          <p className="font-display text-2xl text-copper">{t("method_writing")}</p>
          <p className="mt-2 text-sm text-muted">{t("method_missing")}</p>
        </section>
      ) : null}
    </details>
  );
}

function Sources({ manifest }: { manifest: Manifest | null }) {
  const { t } = useI18n();
  return (
    <details className="card px-4 py-3">
      <summary className="cursor-pointer text-lg font-semibold">{t("sources")}</summary>
      {!manifest ? <p className="mt-3 text-sm text-muted">{t("loading")}</p> : null}
      {manifest ? (
        <div className="mt-3 overflow-x-auto">
          <p className="text-sm text-muted">
            {t("generated")} <span className="num">{manifest.generated_at}</span>
          </p>
          <table className="mt-3 w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="py-2 pr-3 font-medium">{t("sources")}</th>
                <th className="py-2 pr-3 font-medium">{t("sha")}</th>
                <th className="py-2 font-medium">{t("bytes")}</th>
              </tr>
            </thead>
            <tbody>
              {manifest.sources.map((source) => (
                <tr key={`${source.role}-${source.path}`} className="border-t border-line align-top">
                  <td className="py-2 pr-3">
                    <div className="addr">{source.path || t("outside_repo")}</div>
                    <div className="text-xs text-muted">
                      {source.role}
                      {source.gitignored ? ` · ${t("gitignored")}` : ""}
                      {source.outside_repo ? ` · ${t("outside_repo")}` : ""}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <HashText value={source.sha256} />
                  </td>
                  <td className="num py-2">{source.bytes.toLocaleString("en-US")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </details>
  );
}

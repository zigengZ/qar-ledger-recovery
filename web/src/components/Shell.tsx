import { useEffect, useRef, useState, type ReactNode } from "react";
import { HashText } from "./Address";
import { loadEvidence } from "../data/load";
import type { Manifest } from "../data/types";
import { useI18n } from "../i18n";
import type { PageId } from "../router";

const NAV: { id: PageId; href: string; key: string }[] = [
  { id: "lookup", href: "#/", key: "nav_lookup" },
  { id: "holders", href: "#/holders", key: "nav_holders" },
  { id: "verify", href: "#/verify", key: "nav_verify" },
];

const SOURCE = "https://github.com/zigengZ/qar-ledger-recovery";

export function Shell({
  page,
  manifest,
  children,
}: {
  page: PageId;
  manifest: Manifest | null;
  children: ReactNode;
}) {
  const { t, toggleLang, theme, toggleTheme } = useI18n();
  const headerRef = useRef<HTMLElement>(null);
  const [canonicalSha, setCanonicalSha] = useState<string | null>(null);
  const [canonicalKnown, setCanonicalKnown] = useState(false);

  useEffect(() => {
    const node = headerRef.current;
    if (!node) return;
    const write = () => {
      document.documentElement.style.setProperty("--nav-h", `${node.getBoundingClientRect().height}px`);
    };
    write();
    const observer = new ResizeObserver(write);
    observer.observe(node);
    return () => observer.disconnect();
  }, [theme]);

  useEffect(() => {
    void loadEvidence()
      .then((evidence) => {
        setCanonicalSha(evidence.canonical_balances?.sha256 ?? null);
        setCanonicalKnown(true);
      })
      .catch(() => setCanonicalKnown(true));
  }, []);

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 pb-16">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-40 focus:rounded focus:bg-card focus:px-3 focus:py-2">
        Skip
      </a>
      <header ref={headerRef} className="sticky top-0 z-30 -mx-4 mb-3 border-b border-line/80 bg-bg/90 px-4 py-3 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <a href="#/" className="min-w-0 no-underline">
            <span className="block font-display text-xl tracking-tight text-ink sm:text-2xl">qAR Balances</span>
            <span className="mt-0.5 block text-xs text-muted sm:text-sm">{t("subtitle")}</span>
          </a>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <button type="button" className="btn" onClick={toggleLang}>
              {t("lang_toggle")}
            </button>
            <button type="button" className="btn" onClick={toggleTheme}>
              {theme === "dark" ? t("theme_light") : t("theme_dark")}
            </button>
          </div>
        </div>
        <nav className="mt-3 flex flex-wrap gap-2" aria-label="pages">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={item.href}
              aria-current={page === item.id ? "page" : undefined}
              className={`chip no-underline ${page === item.id ? "chip-current" : "text-ink"}`}
            >
              {t(item.key)}
            </a>
          ))}
        </nav>
      </header>
      <main id="main">{children}</main>
      <footer className="mt-10 space-y-1.5 border-t border-line pt-4 text-xs leading-relaxed text-muted">
        {manifest ? (
          <div>
            {t("generated")} <span className="num text-ink">{manifest.generated_at}</span>
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <span>{t("canonical_title")}</span>
          {canonicalSha ? <HashText value={canonicalSha} /> : <span>{canonicalKnown ? t("status_pending") : "…"}</span>}
        </div>
        <div>
          <a href={SOURCE} target="_blank" rel="noreferrer">
            {t("source_link")}
          </a>
        </div>
        <div>{t("not_claim")}</div>
      </footer>
    </div>
  );
}

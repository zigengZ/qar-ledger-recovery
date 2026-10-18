import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { Shell } from "./components/Shell";
import { loadManifest, loadOverview } from "./data/load";
import type { Manifest, Overview } from "./data/types";
import { useI18n } from "./i18n";
import { LookupPage } from "./pages/Lookup";
import { usePage } from "./router";

const HoldersPage = lazy(() => import("./pages/Holders"));
const VerifyPage = lazy(() => import("./pages/Verify"));

export default function App() {
  const page = usePage();
  const { t } = useI18n();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([loadOverview(), loadManifest()])
      .then(([nextOverview, nextManifest]) => {
        setOverview(nextOverview);
        setManifest(nextManifest);
      })
      .catch((reason: unknown) => setError(String(reason)));
  }, []);

  let body: ReactNode;
  if (error) body = <p className="text-copper">{t("load_error")}</p>;
  else if (page === "lookup") body = <LookupPage overview={overview} />;
  else if (!overview) body = <p className="text-muted">{t("loading")}</p>;
  else {
    body = (
      <Suspense fallback={<p className="text-muted">{t("loading")}</p>}>
        {page === "holders" ? <HoldersPage overview={overview} /> : null}
        {page === "verify" ? <VerifyPage overview={overview} manifest={manifest} /> : null}
      </Suspense>
    );
  }

  return (
    <Shell page={page} manifest={manifest}>
      {body}
    </Shell>
  );
}

import type { Evidence, LedgerData, Manifest, Methodology, Overview } from "./types";

export function dataUrl(name: string): string {
  return `${import.meta.env.BASE_URL}data/${name}`;
}

async function getJson<T>(name: string): Promise<T> {
  const response = await fetch(dataUrl(name));
  if (!response.ok) throw new Error(`${name} ${response.status}`);
  return response.json() as Promise<T>;
}

export function loadOverview(): Promise<Overview> {
  return getJson("overview.json");
}

let manifestBundle: Promise<{ manifest: Manifest; sha256: string }> | null = null;

function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  return crypto.subtle.digest("SHA-256", bytes).then((digest) =>
    [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join(""),
  );
}

function loadManifestBundle(): Promise<{ manifest: Manifest; sha256: string }> {
  if (!manifestBundle) {
    manifestBundle = fetch(dataUrl("manifest.json")).then(async (response) => {
      if (!response.ok) throw new Error(`manifest.json ${response.status}`);
      const text = await response.text();
      return { manifest: JSON.parse(text) as Manifest, sha256: await sha256Hex(text) };
    });
  }
  return manifestBundle;
}

export function loadManifest(): Promise<Manifest> {
  return loadManifestBundle().then((bundle) => bundle.manifest);
}

export function loadManifestSha(): Promise<string> {
  return loadManifestBundle().then((bundle) => bundle.sha256);
}

let evidenceCache: Promise<Evidence> | null = null;

export function loadEvidence(): Promise<Evidence> {
  if (!evidenceCache) evidenceCache = getJson("evidence.json");
  return evidenceCache;
}

export function loadMethodology(): Promise<Methodology> {
  return getJson("methodology.json");
}

let ledgerCache: Promise<LedgerData> | null = null;

export function loadLedger(): Promise<LedgerData> {
  if (!ledgerCache) {
    ledgerCache = getJson<{
      decimals: number;
      supply_raw: string;
      nonce: number | null;
      rows: [string, string, string, string, string, string, string, number][];
    }>("ledger.json").then((data) => {
      const list = data.rows.map((row, index) => ({
        address: row[0],
        raw: row[1],
        role: row[2],
        p10: row[3],
        name: row[4],
        provider: row[5],
        confidence: row[6],
        changed: row[7],
        rank: index + 1,
      }));
      return {
        list,
        byAddress: new Map(list.map((row) => [row.address, row])),
        supplyRaw: data.supply_raw,
        nonce: data.nonce,
        decimals: data.decimals,
      };
    });
  }
  return ledgerCache;
}

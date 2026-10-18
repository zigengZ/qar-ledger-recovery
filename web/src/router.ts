import { useEffect, useState } from "react";
import { resolvePage } from "./lib/routes.mjs";

export type PageId = "lookup" | "holders" | "verify";

export function pageFromHash(hash: string): PageId {
  return resolvePage(hash).page;
}

function applyHash(): PageId {
  const resolved = resolvePage(window.location.hash);
  if (resolved.redirect) {
    const url = new URL(window.location.href);
    const next = `${url.pathname}${url.search}${resolved.redirect}`;
    const current = `${url.pathname}${url.search}${url.hash}`;
    if (next !== current) history.replaceState(null, "", next);
  }
  return resolved.page;
}

export function usePage(): PageId {
  const [page, setPage] = useState<PageId>(() => resolvePage(window.location.hash).page);
  useEffect(() => {
    const onChange = () => setPage(applyHash());
    onChange();
    window.addEventListener("hashchange", onChange);
    window.addEventListener("popstate", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
      window.removeEventListener("popstate", onChange);
    };
  }, []);
  return page;
}

export function goLookup(address: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("a", address);
  url.hash = "#/";
  history.pushState(null, "", `${url.pathname}${url.search}${url.hash}`);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function parseAddressList(text: string): { addresses: string[]; duplicates: number } {
  const parts = text.split(/[\s,，;；]+/).map((part) => part.trim()).filter(Boolean);
  const seen = new Set<string>();
  const addresses: string[] = [];
  let duplicates = 0;
  for (const part of parts) {
    if (seen.has(part)) {
      duplicates += 1;
      continue;
    }
    seen.add(part);
    if (addresses.length < 5000) addresses.push(part);
  }
  return { addresses, duplicates };
}

export function fitQuery(addresses: string[]): { value: string; trimmed: boolean } {
  const kept: string[] = [];
  let size = 0;
  for (const address of addresses) {
    const next = (kept.length ? 1 : 0) + encodeURIComponent(address).length;
    if (size + next > 6000) return { value: kept.join(","), trimmed: true };
    kept.push(address);
    size += next;
  }
  return { value: kept.join(","), trimmed: false };
}

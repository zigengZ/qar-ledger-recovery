const ADDR_RE = /^[A-Za-z0-9_-]{43}$/;

/**
 * A ledger miss is not a balance of 0. `raw` is null unless the address is on the ledger.
 * kind: "invalid" | "missing" | "zero" | "balance"
 */
export function presentLookup(address, row) {
  if (typeof address !== "string" || !ADDR_RE.test(address)) return { kind: "invalid", raw: null };
  if (!row) return { kind: "missing", raw: null };
  if (typeof row.raw !== "string" || !/^-?\d+$/.test(row.raw)) throw new Error("bad raw");
  if (BigInt(row.raw) === 0n) return { kind: "zero", raw: row.raw };
  return { kind: "balance", raw: row.raw };
}

/** Text of the raw integer. Missing and invalid addresses contribute no digits, including 0. */
export function lookupRawText(view) {
  if (!view || view.kind === "missing" || view.kind === "invalid") return "";
  return view.raw ?? "";
}

import type { LedgerData } from "../data/types";
import { formatFraction, formatRaw } from "./format.mjs";

export function fullLedgerCsv(ledger: LedgerData): string[][] {
  const header = ["address", "raw_balance", "human_balance_12dp", "rank", "supply_share", "role", "p10_class", "name", "provider", "confidence", "balance_changed"];
  const body = ledger.list.map((row) => [
    row.address,
    row.raw,
    formatRaw(row.raw),
    String(row.rank),
    formatFraction(row.raw, ledger.supplyRaw),
    row.role,
    row.p10,
    row.name,
    row.provider,
    row.confidence,
    row.changed ? "1" : "0",
  ]);
  return [header, ...body];
}

export function ledgerCsvName(nonce: number | null): string {
  return `qar-ledger-${nonce ?? "tail"}.csv`;
}

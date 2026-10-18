export function presentLookup(
  address: string,
  row: { raw: string } | null,
): { kind: "invalid" | "missing" | "zero" | "balance"; raw: string | null };

export function lookupRawText(view: { kind: string; raw: string | null }): string;

/**
 * Canonical balance bytes: nonzero raw strings, addresses sorted, compact JSON, trailing newline.
 * This is the same rule as repro/lib/schedule.mjs canonicalBalances.
 */

export function canonicalBalanceText(entries) {
  const rows = [];
  for (const entry of entries) {
    const address = Array.isArray(entry) ? entry[0] : entry.address;
    const raw = Array.isArray(entry) ? entry[1] : entry.raw;
    if (typeof address !== "string" || address === "") throw new Error("bad address");
    if (typeof raw !== "string" || !/^-?\d+$/.test(raw)) throw new Error(`bad raw for ${address}`);
    if (BigInt(raw) === 0n) continue;
    rows.push([address, raw]);
  }
  rows.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const ordered = {};
  for (const [address, raw] of rows) {
    if (Object.prototype.hasOwnProperty.call(ordered, address)) throw new Error(`duplicate ${address}`);
    ordered[address] = raw;
  }
  return `${JSON.stringify(ordered)}\n`;
}

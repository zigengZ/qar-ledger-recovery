/**
 * Raw qAR amounts are integer strings. 12 decimal places.
 * Never coerce through Number: supply does not fit in a JS safe integer.
 */

const RAW_RE = /^-?\d+$/;

export function assertRaw(raw) {
  if (typeof raw !== "string" || !RAW_RE.test(raw)) {
    throw new Error(`raw must be an integer string, got ${JSON.stringify(raw)}`);
  }
}

export function formatRaw(raw, decimals = 12) {
  assertRaw(raw);
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 36) {
    throw new Error("bad decimals");
  }
  const value = BigInt(raw);
  const neg = value < 0n;
  const digits = (neg ? -value : value).toString();
  const padded = digits.padStart(decimals + 1, "0");
  const whole = decimals === 0 ? padded : padded.slice(0, -decimals);
  const frac = decimals === 0 ? "" : padded.slice(-decimals);
  const body = decimals === 0 ? whole : `${whole}.${frac}`;
  return neg ? `-${body}` : body;
}

/** Integer part grouped with commas. Fraction stays exact. */
export function formatGrouped(human) {
  const neg = human.startsWith("-");
  const body = neg ? human.slice(1) : human;
  const [whole, frac] = body.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const out = frac !== undefined ? `${grouped}.${frac}` : grouped;
  return neg ? `-${out}` : out;
}

export function formatRawGrouped(raw, decimals = 12) {
  return formatGrouped(formatRaw(raw, decimals));
}

/**
 * Grouped amount rounded half up to `places` fraction digits.
 * The third digit of 189487.568… rounds the supply card to 189,487.57.
 */
export function formatRawRounded(raw, places = 2, decimals = 12) {
  assertRaw(raw);
  if (!Number.isInteger(places) || places < 0 || places > decimals) {
    throw new Error("bad places");
  }
  const value = BigInt(raw);
  const neg = value < 0n;
  const abs = neg ? -value : value;
  const scale = 10n ** BigInt(decimals - places);
  const base = abs / scale;
  const rem = abs % scale;
  const rounded = rem >= scale / 2n ? base + 1n : base;
  const digits = rounded.toString().padStart(places + 1, "0");
  const whole = digits.slice(0, -places) || "0";
  const frac = places === 0 ? "" : digits.slice(-places);
  const body = places === 0 ? whole : `${whole}.${frac}`;
  return formatGrouped(neg ? `-${body}` : body);
}

/**
 * Share of supply as a decimal string with `places` fraction digits.
 * Truncates toward zero (integer division), same direction as the raw units.
 */
export function formatFraction(raw, supply, places = 18) {
  assertRaw(raw);
  assertRaw(supply);
  const s = BigInt(supply);
  if (s === 0n) return formatRaw("0", places);
  const scale = 10n ** BigInt(places);
  const v = (BigInt(raw) * scale) / s;
  return formatRaw(v.toString(), places);
}

/** Percent text. Tiny non-zero amounts that round to zero say "<0.000001%". */
export function formatPercent(raw, supply) {
  assertRaw(raw);
  assertRaw(supply);
  const r = BigInt(raw);
  const s = BigInt(supply);
  if (r === 0n || s === 0n) return "0%";
  const scaled = (r * 100000000n) / s;
  if (scaled === 0n) return "<0.000001%";
  const neg = scaled < 0n;
  const digits = (neg ? -scaled : scaled).toString().padStart(7, "0");
  const whole = digits.slice(0, -6);
  const frac = digits.slice(-6).replace(/0+$/, "");
  const body = frac ? `${whole}.${frac}` : whole;
  return `${neg ? "-" : ""}${body}%`;
}

/**
 * Display percent. Zero is an em dash. A positive share below 0.0001% is "<0.0001%".
 * Other values truncate toward zero and keep exactly `places` digits.
 * CSV and copy paths keep using formatFraction / formatRaw, not this.
 */
export function formatPercentFixed(raw, supply, places = 2) {
  assertRaw(raw);
  assertRaw(supply);
  if (!Number.isInteger(places) || places < 0 || places > 8) throw new Error("bad places");
  const r = BigInt(raw);
  const s = BigInt(supply);
  if (r === 0n || s === 0n) return "—";
  const neg = (r < 0n) !== (s < 0n);
  const ar = r < 0n ? -r : r;
  const asupply = s < 0n ? -s : s;
  if (ar * 1000000n < asupply) return "<0.0001%";
  const scale = 10n ** BigInt(places);
  const scaled = (ar * 100n * scale) / asupply;
  const digits = scaled.toString().padStart(places + 1, "0");
  const whole = digits.slice(0, -places) || "0";
  const frac = places === 0 ? "" : digits.slice(-places);
  const body = places === 0 ? whole : `${whole}.${frac}`;
  return `${neg ? "-" : ""}${body}%`;
}

/** Chart-safe percent number. `digits` is decimal places of the percent. */
export function sharePercentNumber(raw, supply, digits = 4) {
  assertRaw(raw);
  assertRaw(supply);
  const s = BigInt(supply);
  if (s === 0n) return 0;
  const scale = 10n ** BigInt(digits);
  const v = (BigInt(raw) * (100n * scale)) / s;
  return Number(v) / Number(scale);
}

export function cmpRaw(a, b) {
  assertRaw(a);
  assertRaw(b);
  const d = BigInt(a) - BigInt(b);
  if (d < 0n) return -1;
  if (d > 0n) return 1;
  return 0;
}

/**
 * Human amount for the page: thousands separators, at most 12 fraction digits,
 * trailing zeros removed. `formatRaw` stays exact for CSV and hashes.
 */
export function formatRawDisplay(raw, decimals = 12) {
  const exact = formatRaw(raw, decimals);
  const neg = exact.startsWith("-");
  const body = neg ? exact.slice(1) : exact;
  const [whole, frac = ""] = body.split(".");
  const trimmed = frac.replace(/0+$/, "");
  const human = trimmed ? `${whole}.${trimmed}` : whole;
  return formatGrouped(neg ? `-${human}` : human);
}

export function formatCount(value) {
  if (!Number.isInteger(value)) throw new Error("bad count");
  return formatGrouped(String(value));
}

export function shortHash(hex) {
  if (typeof hex !== "string" || hex.length < 16) return hex || "";
  return `${hex.slice(0, 8)}…${hex.slice(-8)}`;
}

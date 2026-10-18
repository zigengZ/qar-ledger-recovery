export const ROLE_GROUP: Record<string, string> = {
  wallet: "wallet",
  pool: "pool",
  pool_candidate: "pool",
  lock: "lock",
  lending: "lending",
  agent: "process",
  unknown_process: "process",
  token_process: "process",
  invalid_id: "process",
  unclassified: "unclassified",
};

export const GROUP_ORDER = ["wallet", "pool", "lock", "lending", "process", "unclassified"];

export const ROLE_ORDER = [
  "wallet",
  "pool",
  "pool_candidate",
  "lock",
  "lending",
  "agent",
  "unknown_process",
  "token_process",
  "invalid_id",
  "unclassified",
];

export function groupOf(role: string): string {
  return ROLE_GROUP[role] ?? "unclassified";
}

export type DisplayGroup = "wallet" | "pool" | "lock" | "process" | "unknown";

export const DISPLAY_ORDER: DisplayGroup[] = ["wallet", "pool", "lock", "process", "unknown"];

/** Five labels on the page. Lending sits with processes. Invalid ids sit with unknown. */
export function displayGroup(role: string): DisplayGroup {
  if (role === "invalid_id" || role === "unclassified") return "unknown";
  const group = groupOf(role);
  if (group === "wallet" || group === "pool" || group === "lock") return group;
  if (group === "process" || group === "lending") return "process";
  return "unknown";
}

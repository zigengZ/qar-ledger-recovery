export const CHECK_IDS = ["precise-replay", "assignment-only", "independent-nowasm", "from-scratch", "main-sha"];

export function allChecksMatch(steps) {
  if (!Array.isArray(steps)) return false;
  return CHECK_IDS.every((id) => steps.some((step) => step && step.id === id && step.status === "matched"));
}

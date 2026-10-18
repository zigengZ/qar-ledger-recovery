export const CHECK_IDS: readonly string[];

export function allChecksMatch(steps: { id: string; status: string }[] | null | undefined): boolean;

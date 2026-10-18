export function resolvePage(hash: string): {
  page: "lookup" | "holders" | "verify";
  redirect: string | null;
};

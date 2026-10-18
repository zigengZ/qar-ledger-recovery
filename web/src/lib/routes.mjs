/** Three pages. Old hashes redirect so published links keep working. */
export function resolvePage(hash) {
  const name = String(hash || "").replace(/^#\/?/, "").split("?")[0];
  if (name === "") return { page: "lookup", redirect: null };
  if (name === "lookup" || name === "overview") return { page: "lookup", redirect: "#/" };
  if (name === "holders") return { page: "holders", redirect: null };
  if (name === "verify") return { page: "verify", redirect: null };
  if (name === "method") return { page: "verify", redirect: "#/verify" };
  return { page: "lookup", redirect: "#/" };
}

/**
 * Turn the recovery write-up into site text.
 * Relative links become repository-file URLs. Chain ids link to arweave.net.
 * Local paths, addresses, and host names are removed before anything is published.
 */

const SHA256 = /^[a-f0-9]{64}$/;
const GENERIC_HOSTS = new Set(["localhost", "ubuntu", "linux", "debian", "github.com", "gitlab.com"]);

export function repoSlugFromRemote(remote) {
  if (typeof remote !== "string") return null;
  const match = remote.trim().match(/[:/]([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?$/);
  if (!match) return null;
  return `${match[1]}/${match[2]}`;
}

const PUBLIC_SLUG = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

// The private remote is zigengZ/qar-ledger-recovery-private. Published blob
// links stay on the public repository unless PUBLIC_REPO_SLUG overrides this.
export const DEFAULT_PUBLIC_REPO_SLUG = "zigengZ/qar-ledger-recovery";

export function publicRepoSlug(env = process.env) {
  const raw = env && typeof env.PUBLIC_REPO_SLUG === "string" ? env.PUBLIC_REPO_SLUG.trim() : "";
  if (!raw) return DEFAULT_PUBLIC_REPO_SLUG;
  if (!PUBLIC_SLUG.test(raw)) throw new Error("PUBLIC_REPO_SLUG must be owner/repo");
  return raw;
}

export function repoBlobBaseFromSlug(slug) {
  if (typeof slug !== "string" || !PUBLIC_SLUG.test(slug)) return null;
  return `https://github.com/${slug}/blob/main`;
}

export function repoBlobBaseFromRemote(remote) {
  const slug = repoSlugFromRemote(remote);
  return slug ? `https://github.com/${slug}/blob/main` : null;
}

export function publishNeedles({ hostname, remote } = {}) {
  const needles = [];
  if (typeof hostname === "string") {
    const name = hostname.trim();
    if (name.length >= 4 && !GENERIC_HOSTS.has(name.toLowerCase())) needles.push(name);
  }
  if (typeof remote === "string") {
    const ssh = remote.match(/^[\w.+-]+@([^:]+):/);
    if (ssh && ssh[1] && !GENERIC_HOSTS.has(ssh[1].toLowerCase())) needles.push(ssh[1]);
  }
  return [...new Set(needles)];
}

function needlePattern(needle) {
  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![A-Za-z0-9._-])${escaped}(?![A-Za-z0-9._-])`);
}

export function publicViolation(text, needles = []) {
  if (typeof text !== "string") return null;
  if (/\/(?:root|home|Users|opt|tmp)\//.test(text)) return "absolute path";
  if (/\b(?:\d{1,3}\.){3}\d{1,3}\b/.test(text)) return "ip";
  if (/\blocalhost\b/i.test(text)) return "localhost";
  if (/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/.test(text)) return "email";
  for (const needle of needles) {
    if (needle && needlePattern(needle).test(text)) return "local name";
  }
  return null;
}

export function scrubText(value, needles = []) {
  if (typeof value !== "string" || value === "") return value;
  let out = value;
  out = out.replace(/\/(?:root|home|Users|opt|tmp)\/[^\s)'"<>]*/g, "[redacted]");
  out = out.replace(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "[redacted]");
  out = out.replace(/\blocalhost\b/gi, "[redacted]");
  out = out.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "[redacted]");
  out = out.replace(/file:\/\/\S+/gi, "[redacted]");
  for (const needle of needles) {
    if (!needle || needle.length < 4) continue;
    const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    out = out.replace(new RegExp(`(?<![A-Za-z0-9._-])${escaped}(?![A-Za-z0-9._-])`, "g"), "[redacted]");
  }
  return publicViolation(out, needles) ? "[redacted]" : out;
}

function posixNormalize(input) {
  const parts = [];
  for (const part of input.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (!parts.length) return null;
      parts.pop();
    } else parts.push(part);
  }
  return parts.join("/");
}

function isSafeRepoPath(rel) {
  if (!rel || rel.startsWith("/") || rel.includes("\\") || rel.includes("\0")) return false;
  const parts = rel.split("/");
  return parts.every((part) => part && part !== "." && part !== ".." && /^[A-Za-z0-9._@~+-]+$/.test(part));
}

function docDir(docRel) {
  const slash = docRel.lastIndexOf("/");
  return slash === -1 ? "" : docRel.slice(0, slash);
}

function resolveRepoPath(href, fromDoc) {
  const trimmed = href.trim().replace(/^<|>$/g, "");
  const pathPart = trimmed.match(/^([^?#]*)/)?.[1] ?? "";
  const suffix = trimmed.slice(pathPart.length);
  const resolved = pathPart.startsWith("/")
    ? posixNormalize(pathPart.replace(/^\/+/, ""))
    : posixNormalize(`${docDir(fromDoc)}/${pathPart}`.replace(/^\//, ""));
  if (!resolved || !isSafeRepoPath(resolved)) return null;
  return { path: resolved, suffix };
}

export function rewriteHref(href, docRel, blobBase) {
  const trimmed = String(href || "").trim().replace(/^<|>$/g, "");
  if (!trimmed) return null;
  if (/^(?:mailto|javascript|data|file):/i.test(trimmed)) return null;
  if (/^https?:\/\//i.test(trimmed)) return publicViolation(trimmed) ? null : trimmed;
  if (trimmed.startsWith("#")) return trimmed;
  const resolved = resolveRepoPath(trimmed, docRel);
  if (!resolved || !blobBase) return null;
  return `${blobBase}/${resolved.path}${resolved.suffix}`;
}

function restoreToken(token, docRel, blobBase) {
  const autolink = token.match(/^<(https?:\/\/[^>\s]+)>$/i);
  if (autolink) return publicViolation(autolink[1]) ? "[redacted]" : token;
  if (/^https?:\/\//i.test(token)) return publicViolation(token) ? "[redacted]" : token;
  return token.replace(/(!?)\[([^\]]*)\]\(([^)\s]+)(\s+(?:"[^"]*"|'[^']*'))?\)/g, (full, bang, label, href, title = "") => {
    const next = rewriteHref(href, docRel, blobBase);
    if (next) return `${bang}[${label}](${next}${title || ""})`;
    const resolved = resolveRepoPath(href, docRel);
    if (!bang && resolved) return `\`${resolved.path}\``;
    return label;
  });
}

export function prepareRecoveryMarkdown(markdown, docRel, blobBase, needles = []) {
  const clean = scrubText(String(markdown), needles);
  const chunks = clean.split(/(```[\s\S]*?```)/g);
  return chunks
    .map((chunk, index) => {
      if (index % 2 === 1) return chunk;
      let text = chunk.replace(/^\[([^\]]+)\]:[ \t]+(\S+)[ \t]*$/gm, (full, id, href) => {
        const next = rewriteHref(href, docRel, blobBase);
        return next ? `[${id}]: ${next}` : full;
      });
      const saved = [];
      const mask = (match) => {
        const token = `\u0000${saved.length}\u0000`;
        saved.push(match);
        return token;
      };
      text = text.replace(/(!?\[[^\]]*\]\([^)\n]+\))/g, mask);
      text = text.replace(/<https?:\/\/[^>\s]+>/g, mask);
      text = text.replace(/https?:\/\/[^\s)<]+/g, mask);
      text = text.replace(/`([A-Za-z0-9_-]{43})`/g, "$1");
      text = text.replace(/(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])/g, (id) => `[${id}](https://arweave.net/${id})`);
      return text.replace(/\u0000(\d+)\u0000/g, (_, n) => restoreToken(saved[Number(n)], docRel, blobBase));
    })
    .join("");
}

const PREFERRED_FIELDS = [
  "canonical_balances_sha256",
  "canonical_balance_sha256",
  "balances_sha256",
  "canonical_sha256",
  "balance_sha256",
];

function takeSha(value) {
  return typeof value === "string" && SHA256.test(value.toLowerCase()) ? value.toLowerCase() : null;
}

export function canonicalFromExpected(doc) {
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) return null;
  for (const key of PREFERRED_FIELDS) {
    const sha256 = takeSha(doc[key]);
    if (sha256) return { sha256, field: key };
  }
  for (const nest of ["canonical_balances", "canonical", "balances", "expected"]) {
    const child = doc[nest];
    if (!child || typeof child !== "object" || Array.isArray(child)) continue;
    for (const key of ["sha256", "balances_sha256", "hash", "canonical_balances_sha256"]) {
      const sha256 = takeSha(child[key]);
      if (sha256) return { sha256, field: `${nest}.${key}` };
    }
  }
  const found = [];
  collectSha(doc, "", found);
  return found.find((item) => /canonical|balance/i.test(item.field)) || null;
}

function collectSha(node, prefix, found) {
  if (!node || typeof node !== "object") return;
  for (const [key, value] of Object.entries(node)) {
    const field = prefix ? `${prefix}.${key}` : key;
    const sha256 = takeSha(value);
    if (sha256 && /canonical|balance/i.test(field)) found.push({ sha256, field });
    else if (value && typeof value === "object") collectSha(value, field, found);
  }
}

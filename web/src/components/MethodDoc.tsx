import DOMPurify from "dompurify";
import { Marked } from "marked";
import { FORBIDDEN_TAGS, TYPOGRAPHY_TAGS } from "../lib/sanitize-policy.mjs";

const marked = new Marked({ gfm: true });

function allowedHref(href: string, repo: string | null): boolean {
  if (href.startsWith("#") && !href.startsWith("#/") && !href.includes("\\")) return true;
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return false;
  }
  if (url.protocol !== "https:" || url.username || url.password) return false;
  if (url.hostname === "arweave.net" || url.hostname === "www.arweave.net" || url.hostname === "ao.link") return true;
  if (repo && url.hostname === "github.com") {
    return url.pathname === `/${repo}` || url.pathname.startsWith(`/${repo}/`);
  }
  return false;
}

export function renderMethodology(markdown: string, repo: string | null): string {
  const html = marked.parse(markdown, { async: false }) as string;
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [...TYPOGRAPHY_TAGS],
    ALLOWED_ATTR: ["href", "title", "colspan", "rowspan", "align", "start"],
    FORBID_TAGS: [...FORBIDDEN_TAGS],
    FORBID_ATTR: ["style"],
    FORBID_CONTENTS: ["script", "style", "iframe", "object", "embed", "math", "svg", "form"],
    ALLOW_DATA_ATTR: false,
    ALLOW_ARIA_ATTR: false,
  });
  if (typeof clean !== "string") throw new Error("sanitizer");
  const doc = new DOMParser().parseFromString(clean, "text/html");
  doc.body.querySelectorAll("script,iframe,object,embed,link,style,meta,base,form,input,button,svg,math").forEach((node) => node.remove());
  doc.body.querySelectorAll("*").forEach((node) => {
    for (const attr of [...node.attributes]) {
      if (attr.name.startsWith("on") || attr.name === "style") node.removeAttribute(attr.name);
    }
  });
  doc.body.querySelectorAll("a").forEach((anchor) => {
    const href = anchor.getAttribute("href") || "";
    if (!allowedHref(href, repo)) {
      anchor.replaceWith(doc.createTextNode(anchor.textContent || ""));
      return;
    }
    anchor.setAttribute("target", "_blank");
    anchor.setAttribute("rel", "noreferrer");
  });
  doc.body.querySelectorAll("img").forEach((image) => {
    const src = image.getAttribute("src") || "";
    if (!allowedHref(src, repo)) image.remove();
  });
  return doc.body.innerHTML;
}

/**
 * Public-gateway HTTP with a hard cap of 4 in-flight requests.
 * A 429 or 5xx waits and retries. A closed miss is returned to the caller.
 * When REPRO_HTTP_DIR is set, every response body is stored there.
 */
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const DEFAULT_DATA = [
  "https://arweave.net",
  "https://ar-io.dev",
  "https://vilenarios.com",
  "https://turbo-gateway.com",
];
const DEFAULT_GQL = [
  "https://arweave.net/graphql",
  "https://arweave-search.goldsky.com/graphql",
  "https://ar-io.dev/graphql",
  "https://vilenarios.com/graphql",
];

let slots = 4;
const waiters = [];
let resumeAt = 0;
let httpSeq = 0;

function recordHttp(meta, responseBody, requestBody) {
  const dir = process.env.REPRO_HTTP_DIR;
  if (!dir) return;
  const seq = httpSeq;
  httpSeq += 1;
  const id = String(seq).padStart(6, "0");
  mkdirSync(join(dir, "bodies"), { recursive: true });
  writeFileSync(join(dir, "bodies", id), responseBody);
  if (requestBody) writeFileSync(join(dir, "bodies", `${id}.req`), requestBody);
  const line = {
    seq,
    method: meta.method,
    url: meta.url,
    status: meta.status,
    response_bytes: responseBody.length,
    response_sha256: createHash("sha256").update(responseBody).digest("hex"),
    response_file: `bodies/${id}`,
    request_file: requestBody ? `bodies/${id}.req` : null,
  };
  appendFileSync(join(dir, "responses.jsonl"), `${JSON.stringify(line)}\n`);
}

function splitEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback.slice();
  const list = raw.split(",").map((item) => item.trim()).filter(Boolean);
  if (!list.length) throw new Error(`${name} is empty`);
  return list;
}

export function dataGateways() {
  return splitEnv("REPRO_DATA_GATEWAYS", DEFAULT_DATA);
}

export function gqlEndpoints() {
  return splitEnv("REPRO_GQL_ENDPOINTS", DEFAULT_GQL);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pace() {
  const wait = resumeAt - Date.now();
  if (wait > 0) await sleep(wait);
}

function backoff(ms) {
  resumeAt = Math.max(resumeAt, Date.now() + ms);
}

function withSlot(fn) {
  return new Promise((resolve, reject) => {
    const start = () => {
      fn().then(resolve, reject).finally(() => {
        slots += 1;
        if (waiters.length) {
          slots -= 1;
          waiters.shift()();
        }
      });
    };
    if (slots > 0) {
      slots -= 1;
      start();
    } else {
      waiters.push(start);
    }
  });
}

async function once(url, options) {
  await pace();
  const requestBody = options.body ? Buffer.from(options.body) : null;
  const { expectBytes, ...request } = options;
  try {
    const response = await fetch(url, {
      ...request,
      signal: AbortSignal.timeout(600_000),
      headers: {
        "user-agent": "qar-repro",
        "accept-encoding": "identity",
        ...(options.headers || {}),
      },
    });
    if (expectBytes) {
      const advertised = Number(response.headers.get("content-length"));
      if (Number.isInteger(advertised) && advertised !== expectBytes) {
        if (response.body && response.body.cancel) await response.body.cancel();
        const note = Buffer.from(`content-length ${advertised}`);
        recordHttp({ method: options.method || "GET", url, status: response.status }, note, requestBody);
        return { url, status: response.status, buf: note, lengthMismatch: advertised };
      }
    }
    const buf = Buffer.from(await response.arrayBuffer());
    recordHttp({ method: options.method || "GET", url, status: response.status }, buf, requestBody);
    return { url, status: response.status, buf };
  } catch (error) {
    recordHttp(
      { method: options.method || "GET", url, status: 0 },
      Buffer.from(String(error && error.message ? error.message : error)),
      requestBody,
    );
    throw error;
  }
}

export async function getBytes(gateways, txId, accept, expectBytes) {
  const errors = [];
  for (const base of gateways) {
    const root = base.replace(/\/$/, "");
    // /raw/ is the stored bytes. /<id> may gunzip a Content-Encoding tag.
    const urls = [`${root}/raw/${txId}`, `${root}/${txId}`];
    for (const url of urls) {
      for (let attempt = 1; attempt <= 4; attempt += 1) {
        try {
          const got = await withSlot(() => once(url, { method: "GET", expectBytes }));
          if (got.lengthMismatch) {
            errors.push({ url, status: got.status, attempt, bytes: got.lengthMismatch, rejected: true });
            break;
          }
          const html = looksLikeHtml(got.buf);
          const rejected = got.status === 200 && !html && accept && !accept(got.buf);
          if (got.status === 200 && !html && !rejected) return { ...got, attempt };
          errors.push({
            url,
            status: got.status,
            attempt,
            bytes: got.buf.length,
            rejected: Boolean(rejected),
          });
          if (rejected || html || got.status === 404) break;
          if (got.status === 429 || got.status >= 500 || got.status === 0) {
            backoff(Math.min(8000, 500 * 2 ** (attempt - 1)));
            continue;
          }
          break;
        } catch (error) {
          const cause = error.cause ? `${error.cause.code || ""} ${error.cause.message || error.cause}` : "";
          errors.push({ url, attempt, error: `${error.message || error} ${cause}`.trim().slice(0, 300) });
          backoff(Math.min(8000, 500 * 2 ** (attempt - 1)));
        }
      }
    }
  }
  const failure = new Error(`GET ${txId} failed on every gateway`);
  failure.attempts = errors;
  throw failure;
}

export async function getBytesOrMiss(gateways, txId) {
  try {
    return await getBytes(gateways, txId);
  } catch (error) {
    const attempts = error.attempts || [];
    const onlyMiss = attempts.length > 0 && attempts.every((item) => item.status === 404);
    if (onlyMiss) return null;
    throw error;
  }
}

function looksLikeHtml(buf) {
  const head = buf.subarray(0, 24).toString("utf8").toLowerCase();
  return head.startsWith("<!doctype") || head.startsWith("<html");
}

async function postOne(endpoint, body, query, variables) {
  const errors = [];
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const got = await withSlot(() => once(endpoint, {
        method: "POST",
        body,
        headers: {
          "content-type": "application/json",
          accept: "application/json",
        },
      }));
      let parsed = null;
      try {
        parsed = JSON.parse(got.buf.toString("utf8"));
      } catch (error) {
        errors.push({ endpoint, attempt, status: got.status, error: `json: ${error.message}` });
        if (got.status === 429 || got.status >= 500) {
          backoff(Math.min(8000, 500 * 2 ** (attempt - 1)));
          continue;
        }
        break;
      }
      if (got.status === 200 && parsed && !parsed.errors) {
        return { endpoint, status: got.status, attempt, buf: got.buf, parsed, variables, query };
      }
      const message = parsed && parsed.errors ? JSON.stringify(parsed.errors).slice(0, 300) : `http ${got.status}`;
      errors.push({ endpoint, attempt, status: got.status, error: message });
      if (got.status === 429 || got.status >= 500 || got.status === 0) {
        backoff(Math.min(8000, 500 * 2 ** (attempt - 1)));
        continue;
      }
      break;
    } catch (error) {
      const cause = error.cause ? `${error.cause.code || ""} ${error.cause.message || error.cause}` : "";
      errors.push({ endpoint, attempt, error: `${error.message || error} ${cause}`.trim().slice(0, 300) });
      backoff(Math.min(8000, 500 * 2 ** (attempt - 1)));
    }
  }
  const failure = new Error(`graphql failed: ${(errors[errors.length - 1] || {}).error || endpoint}`);
  failure.attempts = errors;
  throw failure;
}

export async function postGraphqlOne(endpoint, query, variables) {
  const body = Buffer.from(JSON.stringify({ query, variables }));
  return postOne(endpoint, body, query, variables);
}

export async function postGraphql(endpoints, query, variables) {
  const body = Buffer.from(JSON.stringify({ query, variables }));
  const errors = [];
  for (const endpoint of endpoints) {
    try {
      return await postOne(endpoint, body, query, variables);
    } catch (error) {
      errors.push(...(error.attempts || [{ endpoint, error: error.message }]));
    }
  }
  const failure = new Error(`graphql failed: ${(errors[errors.length - 1] || {}).error || "no endpoint"}`);
  failure.attempts = errors;
  throw failure;
}

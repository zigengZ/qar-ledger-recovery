/**
 * Download the checkpoint, module, assignments, messages, and block timestamps.
 * A missing object is an error. Gateway fallback is only for transport failure
 * or a closed miss that the next public gateway still has.
 */
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { join } from "node:path";
import { dataGateways, getBytes, gqlEndpoints, postGraphql, postGraphqlOne } from "./net.mjs";
import {
  b64url,
  findBundledItem,
  graphqlAnchor,
  ownerAddress,
  rsaPssVerify,
  sha256,
  verifyRawItem,
  verifyReconstructed,
  dataItemSigningBytes,
  serializeTags,
  b64urlDecode,
} from "./ans104.mjs";
import { genHashChain } from "./schedule.mjs";

const TX_QUERY = `query($id:ID!) {
  transaction(id: $id) {
    id anchor signature recipient
    owner { address key }
    data { size }
    bundledIn { id }
    block { height timestamp }
    tags { name value }
  }
}`;

const ASSIGNMENT_QUERY = `query($nonces:[String!]!, $first:Int!, $after:String) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    tags: [
      { name: "Data-Protocol", values: ["ao"] }
      { name: "Type", values: ["Assignment"] }
      { name: "Process", values: ["NG-0lVX882MG5nhARrSzyprEK6ejonHpdUmaaMPsHE8"] }
      { name: "Epoch", values: ["0"] }
      { name: "Nonce", values: $nonces }
    ]
  ) {
    pageInfo { hasNextPage }
    edges { cursor node {
      id
      bundledIn { id }
      block { height timestamp }
      tags { name value }
    } }
  }
}`;

const MESSAGE_QUERY = `query($ids:[ID!]!, $first:Int!, $after:String) {
  transactions(ids: $ids, first: $first, after: $after) {
    pageInfo { hasNextPage }
    edges { cursor node {
      id anchor signature recipient
      owner { address key }
      data { size }
      bundledIn { id }
      tags { name value }
    } }
  }
}`;

const BLOCK_QUERY = `query($min:Int!, $max:Int!) {
  blocks(first: 100, sort: HEIGHT_ASC, height: { min: $min, max: $max }) {
    pageInfo { hasNextPage }
    edges { node { height timestamp } }
  }
}`;

const BUNDLE_TAG_QUERY = `query($min:Int!, $max:Int!, $first:Int!, $after:String, $name:String!) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    block: { min: $min, max: $max }
    tags: [{ name: $name, values: ["binary"] }]
  ) {
    pageInfo { hasNextPage }
    edges { cursor node { id data { size } tags { name value } } }
  }
}`;

const BLOCK_TX_QUERY = `query($min:Int!, $max:Int!, $first:Int!, $after:String) {
  transactions(
    first: $first
    after: $after
    sort: HEIGHT_ASC
    block: { min: $min, max: $max }
  ) {
    pageInfo { hasNextPage }
    edges { cursor node { id data { size } tags { name value } } }
  }
}`;

function log(event) {
  console.log(JSON.stringify({ t: new Date().toISOString(), ...event }));
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function writeJson(path, value) {
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, `${JSON.stringify(value)}\n`);
}

export function sameTags(actual, expected) {
  if (!actual || actual.length !== expected.length) return false;
  return actual.every((tag, index) => tag.name === expected[index].name && tag.value === expected[index].value);
}

function tagMap(tags) {
  const out = {};
  for (const tag of tags) {
    if (Object.prototype.hasOwnProperty.call(out, tag.name)) {
      throw new Error(`duplicate tag ${tag.name}`);
    }
    out[tag.name] = tag.value;
  }
  return out;
}

function requireTag(map, name) {
  if (!Object.prototype.hasOwnProperty.call(map, name) || map[name] === "") {
    throw new Error(`missing tag ${name}`);
  }
  return map[name];
}

async function mapPool(items, worker) {
  const out = new Array(items.length);
  let cursor = 0;
  async function run() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      out[index] = await worker(items[index], index);
    }
  }
  const width = Math.min(4, items.length || 1);
  await Promise.all(Array.from({ length: width }, () => run()));
  return out;
}

function chunk(list, size) {
  const out = [];
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
  return out;
}

export async function fetchTransaction(id) {
  const got = await postGraphql(gqlEndpoints(), TX_QUERY, { id });
  const node = got.parsed.data && got.parsed.data.transaction;
  if (!node || node.id !== id) throw new Error(`graphql has no transaction ${id}`);
  return node;
}

function verifyCheckpointNode(node, expected) {
  const owner = b64urlDecode(node.owner.key);
  const signature = b64urlDecode(node.signature);
  if (ownerAddress(owner) !== node.owner.address) throw new Error("checkpoint owner address does not match the key");
  if (node.owner.address !== expected.checkpoint_signer) {
    throw new Error(`checkpoint signer ${node.owner.address} != ${expected.checkpoint_signer}`);
  }
  if (b64url(Buffer.from(sha256(signature), "hex")) !== node.id) {
    throw new Error(`checkpoint id ${node.id} does not match sha256(signature)`);
  }
  const tags = node.tags;
  const map = tagMap(tags);
  if (requireTag(map, "Type") !== "Checkpoint") throw new Error("checkpoint Type tag is not Checkpoint");
  if (requireTag(map, "Process") !== expected.process_id) throw new Error("checkpoint Process tag mismatch");
  if (requireTag(map, "Nonce") !== String(expected.checkpoint_nonce)) throw new Error("checkpoint Nonce tag mismatch");
  if (requireTag(map, "Assignment") !== expected.checkpoint_assignment) throw new Error("checkpoint Assignment tag mismatch");
  if (requireTag(map, "Hash-Chain") !== expected.checkpoint_hash_chain) throw new Error("checkpoint Hash-Chain tag mismatch");
  if (requireTag(map, "Timestamp") !== String(expected.checkpoint_timestamp_ms)) throw new Error("checkpoint Timestamp tag mismatch");
  if (requireTag(map, "Block-Height") !== String(expected.checkpoint_block_height)) throw new Error("checkpoint Block-Height tag mismatch");
  if (requireTag(map, "Content-Encoding") !== "gzip") throw new Error("checkpoint is not gzip");
  if (requireTag(map, "SHA-256") !== expected.checkpoint_uncompressed_sha256) {
    throw new Error("checkpoint SHA-256 tag mismatch");
  }
  if (node.recipient) throw new Error("checkpoint target is not empty");
  if (node.anchor) throw new Error("checkpoint anchor is not empty");
  return { owner, signature, tags, map };
}

export async function fetchCheckpoint(work, expected) {
  const gzPath = join(work, "raw/checkpoint.gz");
  const metaPath = join(work, "raw/checkpoint.tx.json");
  let node;
  if (existsSync(metaPath)) node = readJson(metaPath);
  else {
    node = await fetchTransaction(expected.checkpoint_id);
    writeJson(metaPath, node);
  }
  const signed = verifyCheckpointNode(node, expected);
  let gzip = null;
  if (existsSync(gzPath)) {
    const cached = readFileSync(gzPath);
    const cachedSha = sha256(cached);
    if (cached.length === expected.checkpoint_gzip_bytes && cachedSha === expected.checkpoint_gzip_sha256) {
      gzip = cached;
    } else {
      unlinkSync(gzPath);
      log({ step: "checkpoint-cache-rejected", bytes: cached.length, sha256: cachedSha });
    }
  }
  if (!gzip) {
    const got = await getBytes(
      dataGateways(),
      expected.checkpoint_id,
      (buf) => buf.length === expected.checkpoint_gzip_bytes,
      expected.checkpoint_gzip_bytes,
    );
    gzip = got.buf;
    const gzipSha = sha256(gzip);
    if (gzip.length !== expected.checkpoint_gzip_bytes || gzipSha !== expected.checkpoint_gzip_sha256) {
      throw new Error(`checkpoint gzip sha ${gzipSha} bytes ${gzip.length}`);
    }
    writeFileSync(gzPath, gzip);
    log({ step: "checkpoint-download", gateway: got.url.split("/")[2], bytes: gzip.length, sha256: gzipSha });
  }
  const gzipSha = sha256(gzip);
  if (gzipSha !== expected.checkpoint_gzip_sha256) throw new Error(`checkpoint gzip sha ${gzipSha}`);
  const tagBytes = serializeTags(signed.tags);
  const message = dataItemSigningBytes(signed.owner, Buffer.alloc(0), Buffer.alloc(0), tagBytes, gzip);
  if (!rsaPssVerify(signed.owner, signed.signature, message)) {
    throw new Error("checkpoint ANS-104 signature did not verify");
  }
  const memory = gunzipSync(gzip);
  if (memory.length !== expected.checkpoint_uncompressed_bytes) {
    throw new Error(`checkpoint gunzip is ${memory.length} bytes`);
  }
  const memorySha = sha256(memory);
  if (memorySha !== expected.checkpoint_uncompressed_sha256) {
    throw new Error(`checkpoint gunzip sha ${memorySha}`);
  }
  log({ step: "checkpoint-ok", bytes: memory.length, sha256: memorySha });
  return memory;
}

export async function fetchModule(work, expected) {
  const wasmPath = join(work, "raw/module.wasm");
  const metaPath = join(work, "raw/module.tx.json");
  let node;
  if (existsSync(metaPath)) node = readJson(metaPath);
  else {
    node = await fetchTransaction(expected.module_id);
    writeJson(metaPath, node);
  }
  if (node.owner.address !== expected.module_owner) throw new Error("module owner mismatch");
  if (!sameTags(node.tags, expected.module_tags)) throw new Error("module tags mismatch");
  let wasm;
  if (existsSync(wasmPath)) wasm = readFileSync(wasmPath);
  else {
    const got = await getBytes(dataGateways(), expected.module_id);
    wasm = got.buf;
    writeFileSync(wasmPath, wasm);
  }
  if (wasm.length !== expected.module_bytes) throw new Error(`module is ${wasm.length} bytes`);
  const digest = sha256(wasm);
  if (digest !== expected.module_sha256) throw new Error(`module sha ${digest}`);
  if (wasm.subarray(0, 4).toString("hex") !== "0061736d") throw new Error("module does not start with wasm magic");
  log({ step: "module-ok", bytes: wasm.length, sha256: digest });
  return wasm;
}

export async function fetchProcess(work, expected) {
  const metaPath = join(work, "raw/process.tx.json");
  let node;
  if (existsSync(metaPath)) node = readJson(metaPath);
  else {
    node = await fetchTransaction(expected.process_id);
    writeJson(metaPath, node);
  }
  if (node.owner.address !== expected.process_owner) throw new Error("process owner mismatch");
  if (!node.block || node.block.timestamp !== expected.process_block_timestamp) {
    throw new Error("process block timestamp mismatch");
  }
  if (!sameTags(node.tags, expected.process_tags)) throw new Error("process tags mismatch");
  log({ step: "process-ok", owner: node.owner.address });
  return node;
}

function assignmentFromNode(node, expected) {
  const map = tagMap(node.tags);
  if (requireTag(map, "Type") !== "Assignment") throw new Error(`tx ${node.id} is not an assignment`);
  if (requireTag(map, "Process") !== expected.process_id) throw new Error(`assignment ${node.id} process mismatch`);
  const nonce = Number(requireTag(map, "Nonce"));
  if (!Number.isInteger(nonce)) throw new Error(`assignment ${node.id} nonce is not an integer`);
  if (!node.block || !Number.isInteger(node.block.height)) throw new Error(`assignment ${node.id} has no inclusion block`);
  return {
    assignment_id: node.id,
    nonce,
    epoch: requireTag(map, "Epoch"),
    message_id: requireTag(map, "Message"),
    timestamp_ms: requireTag(map, "Timestamp"),
    hash_chain: requireTag(map, "Hash-Chain"),
    assignment_block_height: requireTag(map, "Block-Height"),
    inclusion_height: node.block.height,
    bundled_in: node.bundledIn && node.bundledIn.id ? node.bundledIn.id : null,
  };
}

async function assignmentBatch(endpoint, nonces) {
  const edges = [];
  let after = null;
  for (let page = 0; page < 6; page += 1) {
    const got = await postGraphqlOne(endpoint, ASSIGNMENT_QUERY, {
      nonces: nonces.map(String),
      first: 50,
      after,
    });
    const conn = got.parsed.data.transactions;
    const pageEdges = conn.edges || [];
    edges.push(...pageEdges);
    if (!conn.pageInfo.hasNextPage) return edges;
    if (!pageEdges.length || pageEdges[pageEdges.length - 1].cursor === after) {
      throw new Error("assignment page stalled");
    }
    after = pageEdges[pageEdges.length - 1].cursor;
  }
  throw new Error("assignment page budget exhausted");
}

export async function fetchAssignments(work, expected) {
  const path = join(work, "raw/assignments.json");
  if (existsSync(path)) {
    const cached = readJson(path);
    if (cached.length === expected.nonce_to - expected.checkpoint_nonce + 1) {
      log({ step: "assignments-cache", rows: cached.length });
      return cached;
    }
  }
  const nonces = [];
  for (let nonce = expected.checkpoint_nonce; nonce <= expected.nonce_to; nonce += 1) nonces.push(nonce);
  const byNonce = new Map();
  let pending = nonces.slice();
  for (const endpoint of gqlEndpoints()) {
    if (!pending.length) break;
    const batches = chunk(pending, 20);
    let done = 0;
    let rows;
    try {
      rows = await mapPool(batches, async (batch) => {
        const edges = await assignmentBatch(endpoint, batch);
        done += 1;
        if (done % 10 === 0 || done === batches.length) {
          log({ step: "assignments", endpoint: endpoint.split("/")[2], batches: done, of: batches.length });
        }
        return edges;
      });
    } catch (error) {
      log({
        step: "assignments-endpoint-failed",
        endpoint: endpoint.split("/")[2],
        error: String(error.message || error).slice(0, 300),
      });
      continue;
    }
    for (const edges of rows) {
      for (const edge of edges) {
        const row = assignmentFromNode(edge.node, expected);
        const prev = byNonce.get(row.nonce);
        if (prev && prev.assignment_id !== row.assignment_id) {
          throw new Error(`nonce ${row.nonce} has two assignment ids`);
        }
        byNonce.set(row.nonce, row);
      }
    }
    pending = nonces.filter((nonce) => !byNonce.has(nonce));
  }
  if (pending.length) throw new Error(`missing assignment nonces: ${pending.slice(0, 12).join(",")}`);
  const ordered = nonces.map((nonce) => byNonce.get(nonce));
  writeJson(path, ordered);
  log({ step: "assignments-ok", rows: ordered.length });
  return ordered;
}

export function verifyHashChain(assignments, expected) {
  const start = assignments[0];
  if (start.nonce !== expected.checkpoint_nonce) throw new Error("hash chain does not start at the checkpoint nonce");
  if (start.assignment_id !== expected.checkpoint_assignment) throw new Error("checkpoint assignment id mismatch");
  if (start.hash_chain !== expected.checkpoint_hash_chain) throw new Error("checkpoint hash-chain mismatch");
  let previousId = expected.checkpoint_assignment;
  let previousHash = expected.checkpoint_hash_chain;
  let checked = 0;
  for (let index = 1; index < assignments.length; index += 1) {
    const row = assignments[index];
    if (row.nonce !== assignments[index - 1].nonce + 1) {
      throw new Error(`nonce gap before ${row.nonce}`);
    }
    const want = genHashChain(previousHash, previousId);
    if (row.hash_chain !== want) {
      throw new Error(`hash-chain mismatch at nonce ${row.nonce}`);
    }
    previousId = row.assignment_id;
    previousHash = row.hash_chain;
    checked += 1;
  }
  const tail = assignments[assignments.length - 1];
  if (tail.nonce !== expected.nonce_to) throw new Error("hash chain does not reach the tail nonce");
  if (tail.assignment_id !== expected.tail_assignment) throw new Error("tail assignment id mismatch");
  if (tail.message_id !== expected.tail_message) throw new Error("tail message id mismatch");
  if (Number(tail.timestamp_ms) !== expected.tail_timestamp_ms) throw new Error("tail timestamp mismatch");
  log({ step: "hash-chain-ok", links: checked, tail: tail.assignment_id });
  return { links: checked };
}

function storedFromGraphql(node, data) {
  const tags = node.tags.map((tag) => ({ name: tag.name, value: tag.value }));
  const valid = verifyReconstructed(
    node.owner.key,
    node.signature,
    node.recipient || "",
    node.anchor || "",
    tags,
    data,
  );
  if (!valid) throw new Error(`message ${node.id} signature did not verify`);
  if (ownerAddress(b64urlDecode(node.owner.key)) !== node.owner.address) {
    throw new Error(`message ${node.id} owner address mismatch`);
  }
  return {
    id: node.id,
    owner: node.owner.address,
    signature: node.signature,
    target: node.recipient || "",
    anchor: node.anchor || "",
    tags,
    data_b64: data.toString("base64"),
    source: "graphql",
  };
}

function storedFromRaw(raw, source) {
  const { item, valid } = verifyRawItem(raw);
  if (!valid) throw new Error(`bundled message ${item.id} signature did not verify`);
  return {
    id: item.id,
    owner: ownerAddress(item.owner),
    signature: b64url(item.signature),
    target: item.target.length ? b64url(item.target) : "",
    anchor: graphqlAnchor(item.anchor),
    tags: item.tags,
    data_b64: Buffer.from(item.data).toString("base64"),
    source,
  };
}

async function messageBatch(endpoint, ids) {
  const edges = [];
  let after = null;
  for (let page = 0; page < 6; page += 1) {
    const got = await postGraphqlOne(endpoint, MESSAGE_QUERY, { ids, first: Math.max(ids.length, 1), after });
    const conn = got.parsed.data.transactions;
    const pageEdges = conn.edges || [];
    edges.push(...pageEdges);
    if (!conn.pageInfo.hasNextPage) return edges;
    if (!pageEdges.length || pageEdges[pageEdges.length - 1].cursor === after) {
      throw new Error("message page stalled");
    }
    after = pageEdges[pageEdges.length - 1].cursor;
  }
  throw new Error("message page budget exhausted");
}

function isBinaryBundle(tags) {
  return (tags || []).some((tag) => tag.name.toLowerCase() === "bundle-format" && tag.value === "binary");
}

async function pageBinaryBundles(endpoint, query, variables) {
  const found = [];
  let after = null;
  for (let page = 0; page < 40; page += 1) {
    const got = await postGraphqlOne(endpoint, query, { ...variables, after });
    const conn = got.parsed.data && got.parsed.data.transactions;
    if (!conn) throw new Error("bundle page has no transactions");
    for (const edge of conn.edges || []) {
      const node = edge.node;
      if (!node || !isBinaryBundle(node.tags)) continue;
      found.push({ id: node.id, size: Number((node.data || {}).size || 0) });
    }
    if (!conn.pageInfo.hasNextPage) return found;
    const cursor = (conn.edges || []).at(-1)?.cursor;
    if (!cursor || cursor === after) throw new Error("bundle list stalled");
    after = cursor;
  }
  throw new Error("bundle list page budget exhausted");
}

async function listBundles(height) {
  // The tag index is case-sensitive and sometimes empty. `bundle-format` and
  // `Bundle-Format` are both real tags. An empty closed page is not proof
  // that the block has no bundles, so every endpoint is consulted.
  const byId = new Map();
  const errors = [];
  for (const endpoint of gqlEndpoints()) {
    const host = endpoint.split("/")[2];
    for (const name of ["bundle-format", "Bundle-Format"]) {
      try {
        const rows = await pageBinaryBundles(endpoint, BUNDLE_TAG_QUERY, {
          min: height,
          max: height,
          first: 100,
          name,
        });
        for (const row of rows) byId.set(row.id, row);
      } catch (error) {
        errors.push(`${host} ${name}: ${String(error.message || error).slice(0, 180)}`);
      }
    }
    try {
      const rows = await pageBinaryBundles(endpoint, BLOCK_TX_QUERY, {
        min: height,
        max: height,
        first: 100,
      });
      for (const row of rows) byId.set(row.id, row);
    } catch (error) {
      errors.push(`${host} block: ${String(error.message || error).slice(0, 180)}`);
    }
  }
  if (!byId.size) {
    throw new Error(`bundle list failed at height ${height}: ${errors.join(" | ") || "no rows"}`);
  }
  log({ step: "bundles", height, count: byId.size });
  return [...byId.values()].sort((a, b) => a.size - b.size || (a.id < b.id ? -1 : 1));
}

async function downloadBundleItem(txId, wantId, depth) {
  if (depth > 4) return null;
  let got = null;
  try {
    got = await getBytes(dataGateways(), txId);
  } catch (error) {
    const attempts = error.attempts || [];
    const onlyMiss = attempts.length > 0 && attempts.every((item) => item.status === 404);
    if (!onlyMiss) throw error;
  }
  if (got) {
    const raw = findBundledItem(got.buf, wantId);
    if (raw) return { raw, source: txId };
  }
  const node = await fetchTransaction(txId);
  if (node.bundledIn && node.bundledIn.id) return downloadBundleItem(node.bundledIn.id, wantId, depth + 1);
  return null;
}

async function recoverMessage(assignment, wantId) {
  if (assignment.bundled_in) {
    const direct = await downloadBundleItem(assignment.bundled_in, wantId, 0);
    if (direct) return storedFromRaw(direct.raw, direct.source);
  }
  const bundles = await listBundles(assignment.inclusion_height);
  const misses = [];
  for (const bundle of bundles) {
    if (bundle.size > 80_000_000) {
      misses.push(`${bundle.id}:${bundle.size}`);
      continue;
    }
    let got;
    try {
      got = await getBytes(dataGateways(), bundle.id);
    } catch (error) {
      const attempts = error.attempts || [];
      const onlyMiss = attempts.length > 0 && attempts.every((item) => item.status === 404);
      if (!onlyMiss) throw error;
      misses.push(`${bundle.id}:404`);
      continue;
    }
    if (bundle.size && got.buf.length !== bundle.size) {
      throw new Error(`bundle ${bundle.id} is ${got.buf.length} bytes, graphql says ${bundle.size}`);
    }
    const raw = findBundledItem(got.buf, wantId);
    if (raw) return storedFromRaw(raw, bundle.id);
  }
  throw new Error(
    `message ${wantId} nonce ${assignment.nonce} is not on GraphQL and was not inside ${bundles.length} bundles at height ${assignment.inclusion_height}`
    + (misses.length ? `; unscanned large bundles ${misses.join(",")}` : ""),
  );
}

export async function fetchMessages(work, assignments) {
  const dir = join(work, "raw/messages");
  mkdirSync(dir, { recursive: true });
  const wanted = assignments.filter((row) => row.nonce > assignments[0].nonce);
  const pending = [];
  const stored = new Map();
  for (const row of wanted) {
    const path = join(dir, `${row.message_id}.json`);
    if (existsSync(path)) stored.set(row.message_id, readJson(path));
    else pending.push(row);
  }
  log({ step: "messages", cached: stored.size, pending: pending.length });
  const byId = new Map();
  let left = pending.slice();
  for (const endpoint of gqlEndpoints()) {
    if (!left.length) break;
    const unique = [...new Set(left.map((row) => row.message_id))];
    const batches = chunk(unique, 10);
    let done = 0;
    let pages;
    try {
      pages = await mapPool(batches, async (batch) => {
        const edges = await messageBatch(endpoint, batch);
        done += 1;
        if (done % 20 === 0 || done === batches.length) {
          log({ step: "message-meta", endpoint: endpoint.split("/")[2], batches: done, of: batches.length });
        }
        return edges;
      });
    } catch (error) {
      log({
        step: "message-endpoint-failed",
        endpoint: endpoint.split("/")[2],
        error: String(error.message || error).slice(0, 300),
      });
      continue;
    }
    for (const edges of pages) {
      for (const edge of edges) {
        if (edge.node && edge.node.id) byId.set(edge.node.id, edge.node);
      }
    }
    left = left.filter((row) => !byId.has(row.message_id));
    log({ step: "message-endpoint-ok", endpoint: endpoint.split("/")[2], found: byId.size, left: left.length });
  }
  const downloads = pending.filter((row) => byId.has(row.message_id));
  await mapPool(downloads, async (row) => {
    const node = byId.get(row.message_id);
    const size = Number((node.data || {}).size || 0);
    let data = Buffer.alloc(0);
    if (size !== 0) {
      const got = await getBytes(dataGateways(), row.message_id);
      if (got.buf.length !== size) {
        throw new Error(`message ${row.message_id} is ${got.buf.length} bytes, graphql says ${size}`);
      }
      data = got.buf;
    }
    const record = storedFromGraphql(node, data);
    writeJson(join(dir, `${row.message_id}.json`), record);
    stored.set(row.message_id, record);
  });
  const missing = pending.filter((row) => !stored.has(row.message_id));
  if (missing.length) log({ step: "message-recover", count: missing.length });
  for (const row of missing) {
    const record = await recoverMessage(row, row.message_id);
    if (record.id !== row.message_id) throw new Error(`recovered ${record.id} for ${row.message_id}`);
    writeJson(join(dir, `${row.message_id}.json`), record);
    stored.set(row.message_id, record);
    log({ step: "message-recovered", nonce: row.nonce, source: record.source });
  }
  if (stored.size !== wanted.length) throw new Error(`stored ${stored.size} messages, wanted ${wanted.length}`);
  log({ step: "messages-ok", count: stored.size });
  return stored;
}

export function messageForReplay(record, processId) {
  return {
    id: record.id,
    owner: record.owner,
    signature: record.signature,
    target: record.target || processId,
    anchor: record.anchor || "",
    tags: record.tags,
    data: Buffer.from(record.data_b64, "base64").toString("utf8"),
  };
}

export async function fetchBlocks(work, expected) {
  const path = join(work, "raw/blocks.json");
  const wantCount = expected.block_height_max - expected.block_height_min + 1;
  if (existsSync(path)) {
    const cached = readJson(path);
    if (
      cached.length === wantCount
      && cached[0].height === expected.block_height_min
      && cached.at(-1).height === expected.block_height_max
    ) {
      log({ step: "blocks-cache", blocks: cached.length });
      return cached;
    }
  }
  const spans = [];
  for (let height = expected.block_height_min; height <= expected.block_height_max; height += 100) {
    spans.push([height, Math.min(height + 99, expected.block_height_max)]);
  }
  const pageDir = join(work, "raw/block-pages");
  mkdirSync(pageDir, { recursive: true });
  let done = 0;
  const pages = await mapPool(spans, async ([min, max]) => {
    const pagePath = join(pageDir, `${min}.json`);
    if (existsSync(pagePath)) {
      const cached = readJson(pagePath);
      done += 1;
      return cached;
    }
    const got = await postGraphql(gqlEndpoints(), BLOCK_QUERY, { min, max });
    const conn = got.parsed.data.blocks;
    const nodes = (conn.edges || []).map((edge) => edge.node);
    const heights = nodes.map((node) => node.height);
    const want = [];
    for (let height = min; height <= max; height += 1) want.push(height);
    if (heights.join(",") !== want.join(",")) throw new Error(`block page ${min}..${max} returned ${heights.length}`);
    if (conn.pageInfo.hasNextPage) throw new Error(`block page ${min}..${max} is not closed`);
    const rows = nodes.map((node) => ({ height: node.height, timestamp: node.timestamp }));
    writeJson(pagePath, rows);
    done += 1;
    if (done % 25 === 0 || done === spans.length) log({ step: "blocks", pages: done, of: spans.length });
    return rows;
  });
  const blocks = pages.flat().sort((a, b) => a.height - b.height);
  // Miner clocks step backwards by a few seconds. The cron rule uses those
  // published timestamps, so a small dip stays. A large dip is a bad page.
  const dips = [];
  for (let index = 0; index < blocks.length; index += 1) {
    if (blocks[index].height !== expected.block_height_min + index) {
      throw new Error(`missing block height ${expected.block_height_min + index}`);
    }
    if (index > 0 && blocks[index].timestamp < blocks[index - 1].timestamp) {
      const dip = blocks[index - 1].timestamp - blocks[index].timestamp;
      if (dip > 120) throw new Error(`block timestamp went backwards by ${dip}s at ${blocks[index].height}`);
      dips.push({ height: blocks[index].height, seconds: dip });
    }
  }
  writeJson(path, blocks);
  log({
    step: "blocks-ok",
    blocks: blocks.length,
    first: blocks[0].height,
    last: blocks.at(-1).height,
    timestamp_dips: dips.length,
    largest_dip_seconds: dips.reduce((max, dip) => Math.max(max, dip.seconds), 0),
  });
  return blocks;
}

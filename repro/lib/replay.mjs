/**
 * ao-loader 0.0.44 copies the input into the WASM heap with HEAPU8.set and
 * returns HEAPU8.slice(). It does not write back into the buffer it was
 * given, and the slice is not the live heap, so the next call cannot
 * overwrite it.
 *
 * In-place mode patches a copy of the loader. The heap already holds the
 * previous result, so the next call gets a null buffer and copyMemory:false.
 * The published package in node_modules is not edited. A handler error
 * reloads the last save and replays the open batch, which keeps the previous
 * memory. Slow mode uses the unpatched loader.
 */
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../package.json", import.meta.url));
const REPRO_DIR = dirname(fileURLToPath(new URL("../package.json", import.meta.url)));
const LOADER_SRC = join(REPRO_DIR, "node_modules/@permaweb/ao-loader/dist/index.cjs");

const LOADER_OPTIONS = {
  format: "wasm32-unknown-emscripten",
  inputEncoding: "JSON-1",
  outputEncoding: "JSON-1",
  memoryLimit: "524288000",
  computeLimit: 9000000000000,
  extensions: [],
};

const ORIGINAL_RETURN = "  return async (buffer, msg, env) => {";
const ORIGINAL_MEMORY = `      return {
        Memory: instance.HEAPU8.slice(),`;
const ORIGINAL_TAIL = `      buffer = null;
    }
  };
};
`;
const PATCHED_RETURN = "  const run = async (buffer, msg, env, opts) => {";
const PATCHED_MEMORY = `      const copyOut = !opts || opts.copyMemory !== false;
      return {
        Memory: copyOut ? instance.HEAPU8.slice() : null,`;
const PATCHED_TAIL = `      buffer = null;
    }
  };
  run.exportHeap = () => instance.HEAPU8;
  return run;
};
`;

export function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

export function patchLoader(dest) {
  const src = readFileSync(LOADER_SRC, "utf8");
  if (src.split(ORIGINAL_RETURN).length !== 2) throw new Error("loader return pattern is missing or not unique");
  if (src.split(ORIGINAL_MEMORY).length !== 2) throw new Error("loader memory pattern is missing or not unique");
  if (src.split(ORIGINAL_TAIL).length !== 2) throw new Error("loader tail pattern is missing or not unique");
  let next = src.replace(ORIGINAL_RETURN, PATCHED_RETURN);
  next = next.replace(ORIGINAL_MEMORY, PATCHED_MEMORY);
  next = next.replace(ORIGINAL_TAIL, PATCHED_TAIL);
  if (next === src) throw new Error("loader patch did not change the file");
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, next);
  return {
    bytes: Buffer.byteLength(next),
    sha256: sha256(Buffer.from(next)),
    source_sha256: sha256(Buffer.from(src)),
  };
}

export async function createHandle(mode, patchDest) {
  if (mode !== "inplace" && mode !== "safe") throw new Error(`unknown mode ${mode}`);
  let patch = null;
  const AoLoader = mode === "inplace"
    ? (patch = patchLoader(patchDest), require(patchDest))
    : require("@permaweb/ao-loader");
  return { AoLoader, patch, options: LOADER_OPTIONS };
}

export async function openHandle(AoLoader, wasm) {
  const handle = await AoLoader(wasm, LOADER_OPTIONS);
  return handle;
}

function currentBytes(handle, mode, heapLoaded, memory) {
  if (mode === "inplace" && heapLoaded) return handle.exportHeap();
  return memory;
}

async function applyOne(handle, heapLoaded, memory, item, mode, aoGlobal) {
  if (mode === "safe") {
    let result;
    try {
      result = await handle(memory, item.message, aoGlobal);
    } catch (error) {
      return {
        memory,
        applied: false,
        error: String(error && error.message ? error.message : error).slice(0, 240),
        heapLoaded: false,
      };
    }
    if (result && result.Error) {
      return { memory, applied: false, error: String(result.Error).slice(0, 240), heapLoaded: false };
    }
    return { memory: result.Memory, applied: true, error: null, heapLoaded: false };
  }
  let result;
  try {
    result = await handle(heapLoaded ? null : memory, item.message, aoGlobal, { copyMemory: false });
  } catch (error) {
    return {
      memory,
      applied: false,
      error: String(error && error.message ? error.message : error).slice(0, 240),
      heapLoaded,
    };
  }
  if (result && result.Error) {
    return { memory, applied: false, error: String(result.Error).slice(0, 240), heapLoaded };
  }
  return { memory, applied: true, error: null, heapLoaded: true };
}

export async function replayItems(options) {
  const {
    handle,
    items,
    mode,
    aoGlobal,
    dir,
    initialMemory,
    saveEvery,
    onProgress,
  } = options;
  mkdirSync(dir, { recursive: true });
  const cursorPath = join(dir, "cursor.json");
  let memory = initialMemory;
  let heapLoaded = false;
  let applied = 0;
  let handlerErrors = 0;
  let sinceSave = 0;
  let saveIndex = 0;
  if (existsSync(cursorPath)) {
    const cursor = JSON.parse(readFileSync(cursorPath, "utf8"));
    const saved = readFileSync(join(dir, cursor.memory_file));
    if (sha256(saved) !== cursor.memory_sha256) throw new Error("resume memory hash mismatch");
    memory = saved;
    saveIndex = cursor.next_index;
    applied = cursor.applied;
    handlerErrors = cursor.handler_errors;
    sinceSave = 0;
    heapLoaded = false;
  }
  function persist(nextIndex) {
    const bytes = Buffer.from(currentBytes(handle, mode, heapLoaded, memory));
    writeFileSync(join(dir, "memory.bin"), bytes);
    memory = bytes;
    const row = {
      next_index: nextIndex,
      memory_file: "memory.bin",
      memory_sha256: sha256(bytes),
      memory_bytes: bytes.length,
      applied,
      handler_errors: handlerErrors,
      mode,
    };
    writeFileSync(cursorPath, JSON.stringify(row));
    return row;
  }
  function restoreToSave() {
    const heap = handle.exportHeap();
    if (heap.length !== memory.length) {
      throw new Error(`heap length ${heap.length} != saved memory ${memory.length}`);
    }
    heap.set(memory);
    heapLoaded = true;
  }
  for (let index = saveIndex; index < items.length; index += 1) {
    const item = items[index];
    const outcome = await applyOne(handle, heapLoaded, memory, item, mode, aoGlobal);
    if (!outcome.applied && mode === "inplace") {
      restoreToSave();
      for (let redo = saveIndex; redo < index; redo += 1) {
        const again = await applyOne(handle, heapLoaded, memory, items[redo], mode, aoGlobal);
        if (!again.applied) throw new Error(`replay of saved batch failed at ${redo}: ${again.error}`);
        heapLoaded = true;
      }
      handlerErrors += 1;
    } else if (!outcome.applied) {
      memory = outcome.memory;
      heapLoaded = false;
      handlerErrors += 1;
    } else {
      memory = outcome.memory;
      heapLoaded = outcome.heapLoaded;
      applied += 1;
    }
    sinceSave += 1;
    if (onProgress && (item.kind === "assignment" || index % 400 === 0)) {
      onProgress({ index, item, applied, handlerErrors });
    }
    if (sinceSave >= saveEvery || !outcome.applied) {
      // A failed item stays at next_index so a later resume retries it.
      const nextIndex = outcome.applied ? index + 1 : index;
      const row = persist(nextIndex);
      saveIndex = nextIndex;
      sinceSave = 0;
      heapLoaded = mode === "inplace";
      if (!outcome.applied) {
        throw new Error(`handler error at index ${index} nonce ${item.nonce ?? "cron"}: ${outcome.error}. Saved ${row.memory_sha256}`);
      }
    }
  }
  const finalRow = persist(items.length);
  return { applied, handlerErrors, finalRow };
}

export async function readAction(handle, memory, aoGlobal, owner, processId, action, timestamp, height) {
  const result = await handle(Buffer.from(memory), {
    Owner: owner,
    From: owner,
    Target: processId,
    Tags: [{ name: "Action", value: action }],
    Data: "",
    Timestamp: timestamp,
    "Block-Height": height,
    Cron: false,
    "Read-Only": true,
  }, aoGlobal);
  const data = (result.Messages || []).map((message) => (message.Data == null ? "" : String(message.Data))).join("");
  return {
    error: result.Error ? String(result.Error).slice(0, 400) : null,
    output: typeof result.Output === "string" ? result.Output : JSON.stringify(result.Output ?? null),
    data,
  };
}

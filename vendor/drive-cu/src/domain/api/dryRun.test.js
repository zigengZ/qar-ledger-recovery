import { describe, test } from 'node:test'
import * as assert from 'node:assert'

import { createTestLogger } from '../logger.js'
import { dryRunWith } from './dryRun.js'

const PROCESS = 'process-123'
const MODULE = 'module-123'
const MEMORY = Buffer.from('checkpoint memory')

const processTags = [
  { name: 'Data-Protocol', value: 'ao' },
  { name: 'Type', value: 'Process' },
  { name: 'Module', value: MODULE },
  { name: 'Compute-Limit', value: '10000' },
  { name: 'Memory-Limit', value: '16-kb' }
]

const moduleTags = [
  { name: 'Data-Protocol', value: 'ao' },
  { name: 'Type', value: 'Module' },
  { name: 'Module-Format', value: 'wasm32-unknown-emscripten' },
  { name: 'Input-Encoding', value: 'JSON-1' },
  { name: 'Output-Encoding', value: 'JSON-1' },
  { name: 'Compute-Limit', value: '10000' },
  { name: 'Memory-Limit', value: '16-kb' }
]

const checkpoint = {
  processId: PROCESS,
  moduleId: MODULE,
  assignmentId: 'assignment-123',
  hashChain: 'hash-chain-123',
  timestamp: 1700000000000,
  epoch: 0,
  nonce: 42,
  ordinate: '42',
  blockHeight: 1234,
  cron: undefined,
  file: 'process-123.bin'
}

function createEnv (overrides = {}) {
  const schedulerCall = async () => assert.fail('the scheduler must not be called by dry-run')

  return {
    DRY_RUN_DEFAULT_MAX_PROCESS_AGE: 60_000,
    DRY_RUN_RESULT_MAX_AGE: 60_000,
    DRY_RUN_PROCESS_CACHE_TTL: 60_000,
    setTimeout,
    clearTimeout,
    logger: createTestLogger({ name: 'ao-cu:dryRun' }),
    findFileCheckpointBefore: async ({ processId, before }) => {
      assert.equal(processId, PROCESS)
      assert.equal(before, 'LATEST')
      return checkpoint
    },
    readFileCheckpointMemory: async (file) => {
      assert.equal(file, checkpoint.file)
      return MEMORY
    },
    loadTransactionMeta: async (id) => {
      if (id === PROCESS) {
        return {
          owner: { address: 'process-owner', key: 'process-key' },
          tags: processTags
        }
      }
      if (id === MODULE) {
        return {
          owner: { address: 'module-owner', key: 'module-key' },
          tags: moduleTags
        }
      }
      assert.fail(`unexpected transaction metadata request for ${id}`)
    },
    isProcessOwnerSupported: async () => true,
    findModule: async () => {
      const err = new Error('module not cached')
      err.status = 404
      throw err
    },
    saveModule: async () => MODULE,
    isModuleMemoryLimitSupported: async () => true,
    isModuleComputeLimitSupported: async () => true,
    isModuleFormatSupported: async () => true,
    isModuleExtensionSupported: async () => true,
    evaluationCounter: { inc: () => {} },
    findMessageBefore: async () => assert.fail('no prior-message lookup is needed for a local checkpoint dry-run'),
    saveLatestProcessMemory: async () => assert.fail('a dry-run must not save process memory'),
    loadDryRunEvaluator: async ({ moduleId }) => {
      assert.equal(moduleId, MODULE)
      return async ({ processId, Memory, message }) => {
        assert.equal(processId, PROCESS)
        assert.strictEqual(Memory, MEMORY)
        assert.equal(message.Timestamp, checkpoint.timestamp)
        assert.equal(message['Block-Height'], checkpoint.blockHeight)
        return {
          Memory,
          Messages: [],
          Assignments: [],
          Spawns: [],
          Output: { ok: true },
          GasUsed: 1
        }
      }
    },
    loadMessageMeta: schedulerCall,
    loadProcessLatest: schedulerCall,
    loadMessages: schedulerCall,
    locateProcess: schedulerCall,
    loadProcess: schedulerCall,
    ...overrides
  }
}

const request = {
  processId: PROCESS,
  dryRun: {
    Owner: 'dry-run-owner',
    Data: '',
    Tags: [{ name: 'Action', value: 'Balance' }]
  }
}

describe('dryRun from local checkpoint', () => {
  test('evaluates only the submitted dry-run message on the local checkpoint', async () => {
    const result = await dryRunWith(createEnv())(request).toPromise()

    assert.deepStrictEqual(result, {
      result: {
        Messages: [],
        Assignments: [],
        Spawns: [],
        Output: { ok: true },
        GasUsed: 1
      },
      wasCached: false
    })
  })

  test('returns 400 without a local checkpoint and does not query Arweave', async () => {
    const env = createEnv({
      findFileCheckpointBefore: async () => undefined,
      loadTransactionMeta: async () => assert.fail('process metadata should not be loaded without a checkpoint')
    })

    await dryRunWith(env)(request).toPromise()
      .then(() => assert.fail('expected dry-run to reject'))
      .catch((err) => assert.deepStrictEqual(err, {
        status: 400,
        message: `No local checkpoint is available for process "${PROCESS}"`
      }))
  })

  test('returns 400 when the local checkpoint file cannot be read', async () => {
    const env = createEnv({
      readFileCheckpointMemory: async () => { throw new Error('missing file') },
      loadTransactionMeta: async () => assert.fail('process metadata should not be loaded when the checkpoint is unreadable')
    })

    await dryRunWith(env)(request).toPromise()
      .then(() => assert.fail('expected dry-run to reject'))
      .catch((err) => assert.deepStrictEqual(err, {
        status: 400,
        message: `The local checkpoint for process "${PROCESS}" could not be read`
      }))
  })

  test('returns 400 when a scheduler target is requested', async () => {
    const env = createEnv({
      findFileCheckpointBefore: async () => assert.fail('the checkpoint should not be loaded for an unsupported target')
    })

    await dryRunWith(env)({ ...request, messageTxId: 'message-123' }).toPromise()
      .then(() => assert.fail('expected dry-run to reject'))
      .catch((err) => assert.deepStrictEqual(err, {
        status: 400,
        message: 'The "to" parameter is not supported; dry-runs are evaluated against the latest local checkpoint'
      }))
  })
})

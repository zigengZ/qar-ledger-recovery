import { Readable } from 'node:stream'
import { omit, pick } from 'ramda'
import { Rejected, Resolved, of } from 'hyper-async'

import { evaluateWith } from '../lib/evaluate.js'
import { messageSchema } from '../model.js'
import { loadModuleWith } from '../lib/loadModule.js'
import { loadLocalProcessStateWith } from '../lib/loadLocalProcessState.js'
import { mapFrom } from '../utils.js'

/**
 * TODO: should this be an effect or shared util?
 * just keeping here for sake of locality for now
 */
const TtlCache = ({ setTimeout, clearTimeout }) => {
  const cache = {
    data: new Map(),
    timers: new Map(),
    set: (k, v, ttl) => {
      if (cache.timers.has(k)) clearTimeout(cache.timers.get(k))
      const t = setTimeout(() => cache.delete(k), ttl)
      t.unref()
      cache.timers.set(k, t)
      cache.data.set(k, v)
    },
    get: k => cache.data.get(k),
    has: k => cache.data.has(k),
    delete: k => {
      if (cache.timers.has(k)) clearTimeout(cache.timers.get(k))
      cache.timers.delete(k)
      return cache.data.delete(k)
    },
    clear: () => {
      cache.data.clear()
      for (const v of cache.timers.values()) clearTimeout(v)
      cache.timers.clear()
    }
  }

  return cache
}

const cyrb53 = (str, seed = 0) => {
  let h1 = 0xdeadbeef ^ seed; let h2 = 0x41c6ce57 ^ seed
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507)
  h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507)
  h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909)
  return 4294967296 * (2097151 & h2) + (h1 >>> 0)
}

/**
 * @typedef Env
 *
 * @typedef Result
 *
 * @typedef ReadResultArgs
 * @property {string} messageTxId
 *
 * @callback ReadResult
 * @param {ReadResultArgs} args
 * @returns {Promise<Result>} result
 *
 * @param {Env} - the environment
 * @returns {ReadResult}
 */
export function dryRunWith (env) {
  const DRY_RUN_DEFAULT_MAX_PROCESS_AGE = env.DRY_RUN_DEFAULT_MAX_PROCESS_AGE
  const DRY_RUN_RESULT_MAX_AGE = env.DRY_RUN_RESULT_MAX_AGE
  const DRY_RUN_PROCESS_CACHE_TTL = env.DRY_RUN_PROCESS_CACHE_TTL
  const logger = env.logger
  const loadModule = loadModuleWith(env)
  const loadLocalProcessState = loadLocalProcessStateWith(env)
  /**
   * Evaluate performing the dry-run will utilize a separate
   * evaluator using a separate worker thread pool
   */
  const evaluate = evaluateWith({
    ...env,
    loadEvaluator: env.loadDryRunEvaluator
  })

  const processStateCache = TtlCache(env)
  const dryRunResultCache = TtlCache(env)

  function ensureProcessLoaded ({ maxProcessAge }) {
    return (ctx) => of(ctx)
      .chain((ctx) => {
        /**
         * Check whether a recent local-checkpoint load can be reused for this
         * dry-run.
         */
        const cached = processStateCache.get(ctx.processId)

        if (cached && new Date().getTime() - cached.age <= maxProcessAge) {
          logger.debug(
            'Using recently cached process memory for dry-run to process "%s": "%j"',
            ctx.processId,
            pick(['from', 'ordinate', 'fromBlockHeight', 'fromCron'], cached.ctx)
          )
          return Resolved(cached.ctx)
        }

        return Rejected(ctx)
      })
      .bichain(
        (res) => loadLocalProcessState(res)
          .chain(loadModule)
          .map((res) => {
            const cached = { age: new Date().getTime(), ctx: res }
            processStateCache.set(res.id, cached, DRY_RUN_PROCESS_CACHE_TTL)
            return res
          }),
        Resolved
      )
  }

  return ({ processId, messageTxId, maxProcessAge = DRY_RUN_DEFAULT_MAX_PROCESS_AGE, dryRun }) => {
    if (messageTxId) {
      return Rejected({
        status: 400,
        message: 'The "to" parameter is not supported; dry-runs are evaluated against the latest local checkpoint'
      })
    }

    return of({ processId })
      .chain(ensureProcessLoaded({ maxProcessAge }))
      .chain((ctx) => {
        const dryRunHash = cyrb53(JSON.stringify({
          processId,
          checkpoint: {
            timestamp: ctx.from,
            ordinate: ctx.ordinate,
            cron: ctx.fromCron
          },
          dryRun
        }))
        const cached = dryRunResultCache.get(dryRunHash)
        if (cached && new Date().getTime() - cached.age <= DRY_RUN_RESULT_MAX_AGE) {
          logger.debug(
            'Using recently cached dry-run result for dry-run to process "%s"',
            processId
          )
          return Resolved({ result: cached.ctx, wasCached: true })
        }

        return of({
          ...ctx,
          stats: {
            startTime: new Date(),
            endTime: undefined,
            messages: { scheduled: 0, cron: 0 }
          }
        })
          /**
           * Inject the dry-run message directly on top of the local checkpoint.
           *
           * { id, owner, tags, output: { Memory, Error, Messages, Spawns, Output } }
           */
          .chain((ctx) => {
            async function * dryRunMessage () {
              /**
               * Dry run messages are not signed, and therefore
               * will not have a verifiable Id, Signature, Owner, etc.
               *
               * NOTE:
               * Dry Run messages are not signed, therefore not verifiable.
               *
               * This is generally okay, because dry-run message evaluations
               * are Read-Only and not persisted -- the primary use-case for Dry Run is to enable
               * retrieving a view of a processes state, without having to send a bonafide message.
               *
               * However, we should keep in mind the implications. One implication is that spoofing
               * Owner or other fields on a Dry-Run message (unverifiable context) exposes a way to
               * "poke and prod" a process modules for vulnerabilities.
               */
              yield messageSchema.parse({
                /**
                 * Don't save the dryRun message
                 */
                noSave: true,
                deepHash: undefined,
                cron: undefined,
                ordinate: ctx.ordinate,
                name: 'Dry Run Message',
                message: {
                  /**
                   * We default timestamp and block-height using
                   * the current evaluation.
                   *
                   * The Dry-Run message can overwrite them
                   */
                  Timestamp: ctx.from,
                  'Block-Height': ctx.fromBlockHeight,
                  Cron: false,
                  Target: processId,
                  ...dryRun,
                  From: mapFrom({ tags: dryRun.Tags, owner: dryRun.Owner }),
                  'Read-Only': true
                },
                AoGlobal: {
                  Process: { Id: processId, Owner: ctx.owner, Tags: ctx.tags },
                  Module: { Id: ctx.moduleId, Owner: ctx.moduleOwner, Tags: ctx.moduleTags }
                }
              })
            }

            /**
             * Pass a messages stream to evaluate that only emits the single dry-run
             * message and then completes
             */
            return evaluate({ ...ctx, dryRun: true, messages: Readable.from(dryRunMessage()) })
          })
          .map((res) => {
            const omitted = omit(['Memory'], res.output)
            const cached = { age: new Date().getTime(), ctx: omitted }
            dryRunResultCache.set(dryRunHash, cached, DRY_RUN_RESULT_MAX_AGE)
            return { result: omitted, wasCached: false }
          })
      })
  }
}

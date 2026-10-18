import { Rejected, Resolved, fromPromise, of } from 'hyper-async'

import { isProcessOwnerSupportedSchema, loadTransactionMetaSchema } from '../dal.js'
import { addressFrom, eqOrIncludes, parseTags } from '../utils.js'
import { LATEST } from '../../effects/ao-process.js'

const noLocalCheckpoint = (processId, detail) => ({
  status: 400,
  message: detail || `No local checkpoint is available for process "${processId}"`
})

/**
 * Load the latest state for a process strictly from a local file checkpoint.
 *
 * Process metadata is loaded from Arweave, but this loader deliberately has no
 * scheduler dependencies and performs no evaluation or message catch-up.
 */
export function loadLocalProcessStateWith ({
  findFileCheckpointBefore,
  readFileCheckpointMemory,
  loadTransactionMeta,
  isProcessOwnerSupported,
  logger
}) {
  findFileCheckpointBefore = fromPromise(findFileCheckpointBefore)
  readFileCheckpointMemory = fromPromise(readFileCheckpointMemory)
  loadTransactionMeta = fromPromise(loadTransactionMetaSchema.implement(loadTransactionMeta))
  isProcessOwnerSupported = fromPromise(isProcessOwnerSupportedSchema.implement(isProcessOwnerSupported))

  function loadCheckpoint (processId) {
    return findFileCheckpointBefore({ processId, before: LATEST })
      .chain((checkpoint) => checkpoint
        ? Resolved(checkpoint)
        : Rejected(noLocalCheckpoint(processId))
      )
      .chain((checkpoint) => readFileCheckpointMemory(checkpoint.file)
        .bimap(
          (err) => {
            logger('Unable to read local checkpoint file "%s" for process "%s": %O', checkpoint.file, processId, err)
            return noLocalCheckpoint(
              processId,
              `The local checkpoint for process "${processId}" could not be read`
            )
          },
          (Memory) => ({ checkpoint, Memory })
        )
      )
  }

  function loadProcessMeta (processId) {
    return loadTransactionMeta(processId)
      .chain((meta) => {
        const tags = parseTags(meta.tags)
        if (!eqOrIncludes('ao')(tags['Data-Protocol'])) {
          return Rejected({ status: 422, message: `Transaction "${processId}" is not an ao process` })
        }
        if (!eqOrIncludes('Process')(tags.Type)) {
          return Rejected({ status: 422, message: `Transaction "${processId}" is not a process` })
        }
        if (!tags.Module) {
          return Rejected({ status: 422, message: `Process "${processId}" has no Module tag` })
        }

        const owner = addressFrom(meta.owner)
        return isProcessOwnerSupported(owner)
          .chain((isSupported) => isSupported
            ? Resolved({ owner, tags: meta.tags })
            : Rejected({ status: 403, message: `Access denied for process owner ${owner}` })
          )
      })
  }

  return ({ processId }) => of(processId)
    .chain(loadCheckpoint)
    .chain(({ checkpoint, Memory }) => loadProcessMeta(processId)
      .map((process) => ({
        id: processId,
        owner: process.owner,
        tags: process.tags,
        checkpoint,
        Memory,
        result: { Memory },
        from: checkpoint.timestamp,
        ordinate: checkpoint.ordinate,
        fromBlockHeight: checkpoint.blockHeight,
        fromCron: checkpoint.cron,
        mostRecentAssignmentId: checkpoint.assignmentId,
        mostRecentHashChain: checkpoint.hashChain
      }))
    )
}

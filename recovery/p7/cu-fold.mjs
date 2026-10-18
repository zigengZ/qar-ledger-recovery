/**
 * Fold one ao-loader result the way the Legacy CU worker does.
 *
 * permaweb/ao 0db88a45 servers/cu/src/effects/worker/evaluate.js mergeOutput:
 * if the result has Error, the new heap is ignored and the previous memory
 * is kept. The assignment was still evaluated. A handler error is not a
 * successful apply, and it is not an evaluator crash.
 */
export function foldCuResult(previousMemory, result) {
  if (!result || typeof result !== "object") {
    throw new Error("evaluator returned no result");
  }
  const handlerError = result.Error ? String(result.Error) : null;
  if (handlerError) {
    return {
      memory: previousMemory,
      eval_applied: false,
      handler_error: handlerError,
    };
  }
  if (result.Memory == null) {
    throw new Error("evaluator result has no Memory and no Error");
  }
  return {
    memory: result.Memory,
    eval_applied: true,
    handler_error: null,
  };
}

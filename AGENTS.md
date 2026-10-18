> 这是工作日志，记录当时的进度，不是最终结论。当前数字以仓库根目录的 README 和 `repro/EXPECTED.json` 为准。

# Handoff

The next session can be Grok or another model. Chat history is not required.

1. Read `STATE.md`.
2. Read `GOAL.md` sections "Done means", "How to run a session", and the phase named in `Next`.
3. Do that phase only.
4. Update `STATE.md` before stopping, including when the phase fails or the quota runs out.

Bulk bytes go to `data/raw/` and stay uncommitted. Commit the manifest and `STATE.md`.

Grok may run parallel read-only queries inside the active phase. Those workers must not write `STATE.md`.

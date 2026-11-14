- Cursor (or Hermes) is the orchestrator. Claude is the worker. Never invert that.
- Spawn through `claude-spawn.mjs` using official headless `claude -p`. Never launch the `claude` TUI, and never call `claude -p` directly from the parent.
- Always pass `--model`. There is no harness default.
- Never pass `--prompt-interactive`, `--bg`, `--cloud` task descriptions, `--desktop`, or `--input-format`. Child stdin is ignored.
- Default edit jobs pass `--permission-mode auto`. Scout jobs use `--permission-mode plan`. Never pass `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`.
- Never default `--bare` so project and user config (CLAUDE.md, skills, MCP, hooks) load normally.
- Scope file ops with `--cwd`. Do not add MCP servers or subagents unless the prompt asked for them.
- Do not copy Cursor user rules into the prompt. The wrapper attaches `worker-contract.md` via `--append-system-prompt-file` (or fallback).
- After exit, read `report.json`. Process `lifecycle=completed` is not worker success; require `reportValid` and `workerStatus`.
- Do not install packages, paste API keys, or change auth. If `claude` is not on PATH or unattended auth is missing, stop.
- Never silently drop a caller-supplied tool restriction: if `--allowed-tools` or `--disallowed-tools` is passed and the installed CLI does not support it, the harness exits 2 (`ERR_TOOL_FLAG_UNSUPPORTED`).
- `--permission-mode bypassPermissions` is refused by design; the harness exits 2 with a message pointing at this file. Use `auto`, `acceptEdits`, `plan`, `default`, or `dontAsk`.
- `--max-budget-usd` minimum is 0.05 (the ~$0.05 system-prompt cache minimum); values below this are rejected with exit 2.
- `--fork-session` is only valid together with `--conversation-id`; using it alone exits 2.

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | The child process completed. NOT success — you must still check `reportValid` and `workerStatus`. |
| `1`  | Spawn or runtime failure: probe error, child died, or any error carrying no `exitCode`. |
| `2`  | Caller precondition or capability failure; nothing was spawned. Missing `--model`, invalid flag values, and any requested capability the installed CLI does not advertise (including the worker-contract append flags). |

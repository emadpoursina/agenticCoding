# Research: Claude SDK worker harness

Official docs fetched 2026-10-31 (code.claude.com). No NEEDS CLARIFICATION remains; underspecified Ready file probes are recorded as assumptions below.

Sources: [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview), [headless / programmatic](https://code.claude.com/docs/en/headless), [CLI reference](https://code.claude.com/docs/en/cli-reference), [permission modes](https://code.claude.com/docs/en/permission-modes), [authentication](https://code.claude.com/docs/en/authentication), [environment variables](https://code.claude.com/docs/en/env-vars), [sessions](https://code.claude.com/docs/en/sessions), [settings](https://code.claude.com/docs/en/settings).

## Worker is CLI print mode, not language SDK

- **Decision**: New harness wrapper execs operator-installed `claude` with `-p`/`--print`. Ready and spawn do not import `@anthropic-ai/claude-agent-sdk` or `claude-agent-sdk`. Parent never execs `claude` and never uses Managed Agents / Client SDK tool loops / TUI.
- **Rationale**: Official overview: Python/TS Agent SDK still spawn a `claude` CLI subprocess. “To drive the same agent loop from a language other than Python or TypeScript, run the CLI as a subprocess with `-p`.” Pi (`pi-spawn.mjs`) and Antigravity (`agy-spawn.py`) already use that shape. Spec FR-002, FR-003, FR-017.
- **Alternatives considered**: Parent-imported `query()` — rejected (Ready would then look like a package install; SDK still needs `claude` on PATH for most installs). `ant` Managed Agents — rejected (hosted sessions). Bare `claude` TUI — rejected (FR-004).

## Wrapper language: Node, cloned from Pi monitor

- **Decision**: Add `AiNative/docs/agents/claude-harness/claude-spawn.mjs` (Node, stdlib only). Copy Pi run-dir/heartbeat/STATUS-parse/compact-stdout patterns. Do not share a runtime import with `pi-spawn.mjs` (keep files independent so FR-018 stays true).
- **Rationale**: Pi already owns the parent poll contract (`schemaVersion` 2, compact `RUN_DIR=` lines). Claude CLI is typically a Node binary; requiring `python3` for a third backend is extra. Spec left language as an implement choice.
- **Alternatives considered**: Python like `agy-spawn.py` — works, but duplicates the worse of two trees. Shared Node module extracted from Pi — extra abstraction, not requested.

## Print vs stream-json (both always `-p`)

- **Decision**: Wrapper `--print` → `claude -p` with default `--output-format text` (omit the format flag). Wrapper without `--print` → `claude -p --output-format stream-json --verbose`. Persist every stdout line to `events.jsonl`. Never `--input-format stream-json`. Never `--bg`/`--background`. Never `--cloud` with a new-task description. Never `--desktop`. Never `--bare` by default.
- **Rationale**: Official headless: `-p` is non-interactive; `--bg` and `--cloud`+description conflict with `-p`; stream-json last line is a `result` message; `--verbose` is required for complete stream events. Spec FR-004–FR-007, FR-025. Official note that `--bare` “will become the default for `-p` in a future release” is a **follow-up risk**: as of this snapshot, omitting `--bare` loads project/user config. No official `--no-bare` flag exists; if CLI later defaults to bare, implement must re-check docs for a load-config flag rather than invent one.
- **Alternatives considered**: `--output-format json` for long jobs — no live events. `--include-partial-messages` — optional token streaming; not required to reconstruct final `result` text. `--bare` for CI reproducibility — rejected by clarification (load CLAUDE.md/skills/MCP/hooks).

## Permission modes

- **Decision**: Edit (default): `--permission-mode auto`. Scout (`--scout`): `--permission-mode plan`. Never `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`. Optional `--permission-prompts none` if `claude --help` lists `--permission-prompts` (v2.1.259+); omit if help/child rejects it. If required `--permission-mode auto|plan` is rejected, fail closed (no Manual retry).
- **Rationale**: Official: with Claude Code v2.1.302+, `-p` with no permission mode starts Manual and **denies** prompting tool calls (can still exit 0). Anthropic’s unattended example is `--permission-mode auto` (classifier) plus optional `--permission-prompts none`. `plan` is a documented `--permission-mode` value. Spec FR-008, FR-009, FR-026.
- **Alternatives considered**: `bypassPermissions` / skip-permissions — rejected in clarifications. `dontAsk` / `acceptEdits` — not the selected unattended mode. Always pass `--permission-prompts none` without probing — would fail older CLIs; spec says omit optional rejected flags.

## System prompt / contract

- **Decision**: Pass `worker-contract.md` with `--append-system-prompt-file <path>`. If help/child rejects that flag, fall back to `--append-system-prompt` with the same file text. Never drop the contract. Job text is the `-p` prompt argument, not stdin.
- **Rationale**: Official CLI lists both append flags; append keeps Claude Code’s default identity (spec FR-011). Pi uses `--append-system-prompt` with a path; Claude’s file form is the preferred official equivalent.
- **Alternatives considered**: `--system-prompt-file` replacement — would strip default Claude Code behavior. Prepend contract only in the user prompt — allowed as last-resort if both append flags fail, but implement should treat dual-append-failure as fail-closed because FR-011 says the contract must not be dropped.

## Isolation, resume, effort, model, timeout

- **Decision**:
  - `--model` required on wrapper; forwarded as `claude --model`; missing → exit 2, no child.
  - `--effort` forwarded as `claude --effort` when set; omit if CLI rejects (optional).
  - No `--conversation-id` → pass `--no-session-persistence` when help lists it; never `--continue`; never `--resume` without an id (picker).
  - `--conversation-id <id>` → `claude --resume <id>` (print mode) and **omit** `--no-session-persistence`.
  - Wrapper `--timeout`: wrapper kill timer only. Official CLI reference has **no** print-mode duration flag analogous to `agy --print-timeout`. Do not pass `--max-turns` or `--max-budget-usd`. On expiry: SIGINT, wait `GRACEFUL_KILL_MS` (~2s), SIGTERM, wait again, SIGKILL. Official: SIGINT ends the turn; SIGTERM exits 143.
- **Rationale**: CLI reference (`--effort`, `--resume`, `--no-session-persistence`, `--max-turns`, `--max-budget-usd`); headless signal docs; spec FR-010, FR-012, FR-024.
- **Alternatives considered**: Forward `--max-turns` from wrapper timeout — invents a cap. Pi-style SIGTERM-then-SIGKILL only — weaker than documented SIGINT-first. Interactive `--resume` — would attach a TUI picker.

## Stdin

- **Decision**: Child stdio stdin = ignore / DEVNULL. Prompt is the print argument. Official: piped stdin is allowed (10MB) but unattended parent must not wait on a TTY; unreadable stdin warns and continues with the CLI prompt.
- **Rationale**: FR-007, SC-009.
- **Alternatives considered**: Pipe prompt on stdin — rejected (spec: print argument). `--prompt-interactive` — rejected (FR-004).

## STATUS reconstruction

- **Decision**: Text mode: parse captured CLI stdout with existing `WORKER_STATUS_RE`. Stream-json: walk `events.jsonl`; prefer last object with `type == "result"` and a string `result` (or `result.result` if nested); else join assistant `content[].text`; else `stream_event` `text_delta` as last resort. Parent does not read `events.jsonl`. Non-zero child exit → `lifecycle=failed` even if text has `STATUS: ok`.
- **Rationale**: Official json extracts `.result`; stream last line is a `result` message. Spec FR-021, FR-022. Malformed lines increment parseErrors; do not crash the wrapper.
- **Alternatives considered**: Treat CLI process 0 as job success — rejected. Parent ingesting events — rejected.

## Flag probing (no Ready version floor)

- **Decision**: At spawn, run `claude --help` (or equivalent) once. Optional flags absent from help are omitted (`--no-session-persistence`, `--append-system-prompt-file`, `--permission-prompts none`, `--effort` if wrapper passed it). Required flags missing from help (`-p`/`--print`, `--model`, `--permission-mode auto` on edit, `--permission-mode plan` on scout) fail closed before spawn. Ready does **not** parse `claude --version`.
- **Rationale**: FR-026. Avoids a billed probe and avoids encoding a SemVer floor that the spec forbids.
- **Alternatives considered**: Hard-code a min version — rejected. Spawn and retry stripping flags — allowed only for optional flags after a clear “unknown option” stderr; required-flag rejection must not retry.

## Ready worker-runtime (no model call)

- **Decision**: For `claude|claude-code|anthropic`: `command -v "${SPECKIT_CLAUDE_BIN:-claude}"`. Auth is present if **any** of:
  1. Non-empty env `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, or `ANTHROPIC_AUTH_TOKEN`
  2. `apiKeyHelper` key present in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` or the target repo’s `.claude/settings.json` / `.claude/settings.local.json` (presence only; **do not execute** the helper)
  3. Non-empty file `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.credentials.json` (existence/size only; **do not print contents**)
  Fail if CLI missing or none of the above. FIXES: install Claude Code CLI / put `claude` on PATH; or login via official docs (`claude auth login` / API key). Never `pip install claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk`. Never call the model. Cloud env (`CLAUDE_CODE_USE_BEDROCK` / Vertex / Foundry) is **not** a Ready pass by itself (FR-014).
- **Rationale**: Official auth order and storage: env vars; `apiKeyHelper` in settings; `/login` credentials in Keychain (macOS) or `.credentials.json` (Linux/Windows and macOS Keychain fallback). Spec forbids a billed probe.
- **Assumption (macOS Keychain-only)**: Official macOS primary store is Keychain; `.credentials.json` is the fallback when Keychain writes fail. Ready will **not** query Keychain (service name is not a stable documented Ready probe). Operators with Keychain-only login and no env token / helper / credentials file will get `worker-runtime: fail` until they set an env token or a credentials file exists. Document this in Ready FIXES (“if you already logged in interactively, export `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, or confirm `~/.claude/.credentials.json` exists”).
- **Alternatives considered**: `claude auth status` — may be interactive or network. Keychain `security find-generic-password` — unofficial service name, platform-only. Treat Bedrock env as auth — spec says not required and not sufficient.

## Ready selftests

- **Decision**: Keep cases 16 (missing pi), 17 (missing agy), 18 (unknown worker — **update FIXES to list `pi`, `antigravity`, and `claude`**), 19 (default antigravity). Add Claude cases (same numbers in both ready copies), using `SPECKIT_CLAUDE_BIN` and isolated PATH/HOME:
  - Missing `claude` on PATH → fail, PATH install fix, not pip/npm SDK
  - Stub `claude` on PATH, no env tokens, empty HOME (no credentials/settings) → fail, official login/API-key fix, no model invocation in the check script
  - Stub `claude` + `ANTHROPIC_API_KEY` → worker-runtime pass even without npm/python SDK packages
  - Alias `claude-code` and/or `anthropic` → `WORKER: claude`
- **Rationale**: FR-015. Mirror Antigravity isolation so host `claude` cannot flake CI.
- **Alternatives considered**: Live `claude -p` in selftest — not deterministic; optional quickstart smoke only.

## `backend` JSON field

- **Decision**: `"backend": "claude-cli"` in `status.json` / `report.json`. `schemaVersion`: `2` (match Pi monitor keys the parent already understands).
- **Rationale**: Parallel to `agy-cli`. Parent reads lifecycle/workerStatus, not the backend string, but a truthful label avoids “sdk” confusion.
- **Alternatives considered**: `claude-agent-sdk` — misleading. Reuse Pi schemaVersion 2 without a backend key — worse for debugging.

## Docs + changelog

- **Decision**: New `claude-harness/` (`SKILL.md`, `rule.md`, `AGENTS.md`, `worker-contract.md`, `claude-spawn.mjs`). Update worker-resolution lists in orchestrate (SKILL/AGENTS/rule), both ready SKILL + AGENTS, `docs/agents/README.md`, `docs/systems/feature-loop.md`, `cursor-setup.md` slash list, `hermes-readiness.sh` skill presence list. Add Cursor command `AiNative/.cursor/commands/claude-harness.md` (same stub as pi/agy; `link-host-skills.sh` already auto-writes missing command files for every agent folder). Changelog `AiNative/CHANGELOG.md` next minor **0.6.0** (new worker backend). Do not bump Specify artifacts. Do not rewrite host symlinks by hand.
- **Rationale**: FR-016, FR-020. Current newest changelog is 0.5.0.
- **Alternatives considered**: Docs-only without a spawn script — would leave no legal parent API.

## Pi and Antigravity spawn code

- **Decision**: Do not change child argv of `pi-spawn.mjs` or `agy-spawn.py`. Shared resolution/FIXES strings that currently say only `pi` or `antigravity` must gain `claude`.
- **Rationale**: FR-018.
- **Alternatives considered**: Extract a shared worker-resolver library — extra files, not required.

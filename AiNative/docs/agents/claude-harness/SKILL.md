---
name: claude-harness
description: >-
  Delegates one bounded job to the official Claude Code CLI (claude -p) via
  claude-spawn.mjs and brings the result back. Use when the user asks to implement
  or fix code with Claude, or when SPECKIT_WORKER=claude.
  Cursor writes the job. The claude CLI only executes that job.
disable-model-invocation: true
---

# Claude harness

Delegate one job to the official Claude Code CLI (`claude -p` headless) via
`claude-spawn.mjs`, then take the result back. Cursor is the orchestrator.
Claude is the worker. Never invert that.

The worker sees only the prompt you write plus the wrapper-attached contract.
Put the whole job in that prompt, including any files or paths it should read.

Do not tell the worker who owns planning, tasks, questions, or review. Do not
mention Spec Kit, this skill, or “this stays in Cursor” in the prompt. If the
job is a plan, it writes the plan. If the job is implementation, it implements.
The prompt is the job.

You do not edit the code yourself on a job you hand to Claude. After the
wrapper exits, read `report.json`, check the diff, and either finish or spawn
a tighter follow-up.

Ready checks that `claude` is on PATH and unattended auth evidence exists
(`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`,
`apiKeyHelper` in settings JSON, or non-empty `.credentials.json`).
Do not ask the user to paste keys. Do not import or require `@anthropic-ai/claude-agent-sdk`
or `claude-agent-sdk`. Never launch bare `claude` (TUI steals terminal) and never call
`claude -p` directly from the parent.

## Prompt you hand the worker

One job per spawn. Include:

- Goal: the single change or check
- cwd: project root
- Read: file paths, or a spec/task path, that contain what it needs
- Done: how to tell the job worked
- Do not: commit, push, deploy, SSH, or widen the job, unless the user asked
- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed

You choose the job from what the user asked. Do not narrow it before handing it over.

Long jobs **must** go through `claude-spawn.mjs`. Do not call `claude` directly in the
parent. The wrapper keeps streams on disk and exposes a tiny `status.json`.

## Sub-agent model (required — no harness default)

The parent agent **must** pass `--model`. There is no default. Missing
`--model` → wrapper exits `2` and does not start `claude`.

Resolution order:
1. Stage invocation parameter (`worker: { model: ... }`)
2. `SPECKIT_WORKER_MODEL`
3. Runtime default (e.g. `sonnet`)

```bash
# wrapper resolves to the canonical skill dir;
# AiNative canonical: <AINATIVE>/docs/agents/claude-harness/claude-spawn.mjs
# host symlink: $HOME/.cursor/skills/claude-harness/claude-spawn.mjs
node "$HOME/.cursor/skills/claude-harness/claude-spawn.mjs" \
  --name "<job>" --cwd "$PWD" \
  --model <id> \
  -- "<prompt>"
```

Optional: `--effort <low|medium|high|max>` when the parent has a thinking/effort value
and the CLI accepts it. Do not invent a fallback model inside this skill.

## Worker contract (required)

Do not copy Cursor user rules or this skill into the prompt. The wrapper
attaches the contract from:

`<AINATIVE>/docs/agents/claude-harness/worker-contract.md`
(host symlink: `~/.cursor/skills/claude-harness/worker-contract.md`)

via `--append-system-prompt-file` (or `--append-system-prompt` fallback).
Put the actual job, skill path, and report format in the prompt.

## How to spawn

Always non-interactive headless print mode (`claude -p`). Never launch bare `claude`
(TUI steals the terminal). Never pass `--prompt-interactive`, `--bg`, `--cloud`, `--desktop`,
or `--input-format`. Child stdin is ignored (`DEVNULL` / not a TTY).

Working directory is the job’s project root (`--cwd`). `--name` is the job
label. Each spawn gets a unique run id under:

`.agent/claude/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}`

`.agent/claude/<job-name>/latest.json` points at the newest run. Parallel
jobs need **different** `--name` values.

The wrapper:

- Always executes `claude -p` with child stdin ignored (`DEVNULL` / not a TTY).
- Runs in `--cwd` so file tools stay in the job tree.
- Never defaults `--bare` so project and user configuration (`CLAUDE.md`, skills, MCP, hooks) load normally.
- Attaches `worker-contract.md` via `--append-system-prompt-file` or `--append-system-prompt`.
- Sets `--permission-mode auto` for default (edit) jobs (never `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`).
- Sets `--permission-mode plan` for `--scout`.
- Uses `--resume <id>` when `--conversation-id` is passed (isolated default: `--no-session-persistence` when probed present; never `--continue`).

### Edit jobs (default)

Edit jobs auto-approve tool execution via `--permission-mode auto`
so file editing and commands do not wait for a human.

```bash
node "$HOME/.cursor/skills/claude-harness/claude-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> \
  -- "<prompt>"
```

### Scout (read-only)

```bash
node "$HOME/.cursor/skills/claude-harness/claude-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> --scout \
  -- "<prompt>"
```

`--scout` sets `--permission-mode plan` and omits `auto`.
Do not broaden scout access.

### Short jobs

Same wrapper. `--print` runs `claude -p` in CLI text output mode (omits `--output-format`).
Default long jobs use `--output-format stream-json --verbose` and record raw CLI events to `events.jsonl`.
Always prefer the wrapper when you want `report.json`.

### Optional timeout

Enforced by a wrapper kill timer (SIGINT, then wait ~2s, SIGTERM, wait again, SIGKILL).
No official print duration flag exists in the CLI; the wrapper owns timeout enforcement.
If `--timeout` is omitted, no wrapper kill timer is set (and no invented `--max-turns` or `--max-budget-usd`).

```bash
node "$HOME/.cursor/skills/claude-harness/claude-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> --timeout 600 -- "<prompt>"
```

`--timeout` is seconds (or `Nms`). On expiry the wrapper terminates the child,
sets `lifecycle=timed_out` / `timedOut=true`.

Wrapper stdout is a few lines (`RUN_DIR=`, `STATUS_FILE=`, then `LIFECYCLE=` /
`REPORT_FILE=` on exit). Ignore anything else. Do not read `events.jsonl`
unless status is not enough.

Do not pass MCP servers unless the user asked.


## Opt-in flags

All flags below are **additive and opt-in**. Nothing that works today changes behaviour when these flags are absent. All have fail-closed error handling when requested but the installed CLI does not support them.

### `--allowed-tools <list>` / `--disallowed-tools <list>`

Restrict or deny specific tools by name (comma-separated, e.g. `"Read,Edit"`).

- **Default**: not set (no tool restriction).
- Emitted as `--allowedTools <list>` / `--disallowedTools <list>` to the CLI.
- **Fail-closed**: if the caller passes either flag and the installed CLI does not advertise support, the wrapper throws `ERR_TOOL_FLAG_UNSUPPORTED` and exits 2. The harness never silently drops a caller-supplied restriction.

### `--permission-mode <mode>`

Override the permission mode for this run. Accepted values: `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`.

- **Default**: not set — existing defaults apply (`--scout` → `plan`, edit jobs → `auto`). An explicit `--permission-mode` wins over both.
- `acceptEdits` is the tighter choice for jobs that only edit files and need no shell access; it auto-approves file edits but prompts on shell commands.
- **`bypassPermissions` is explicitly rejected** with exit 2 and a message pointing at rule.md. The harness must never enable full bypass.

### `--max-budget-usd <n>`

Cap the run's spend. Must be a finite number ≥ 0.05 (the ~$0.05 system-prompt cache minimum). Values below 0.05 are rejected with exit 2.

- **Default**: not set (no budget cap).
- Emitted as `--max-budget-usd <n>`.
- Capability flag: `hasMaxBudgetUsd`.

### `--json-schema <file-or-inline-json>`

Pass a JSON schema to the CLI. If the value is the path of an existing readable file, the wrapper reads it and passes its contents; otherwise the value is passed verbatim.

- **Default**: not set.
- Emitted as `--json-schema <value>`.
- **Fail-closed**: exits 2 with `ERR_JSON_SCHEMA_UNSUPPORTED` when requested but unsupported.

### `--fork-session`

Boolean flag. Must be used together with `--conversation-id`; if used alone, the wrapper exits 2 with a clear message. When both are present, emitted as `--resume <id> --fork-session`.

- **Default**: not set.
- **Fail-closed**: exits 2 with `ERR_FORK_SESSION_UNSUPPORTED` when requested but unsupported.
- **Requires `--conversation-id`**: using `--fork-session` without `--conversation-id` exits 2.

### `--fallback-model <id>`

Opt-in fallback model ID. There is no default; the flag is never injected.

- Emitted as `--fallback-model <id>`.
- **Fail-closed**: exits 2 with `ERR_FALLBACK_MODEL_UNSUPPORTED` when requested but unsupported.

### `--add-dir <path>`

Repeatable flag. Each occurrence adds an extra directory. Collected into an array and emitted as one `--add-dir <path>` pair per entry in order.

- **Default**: empty (no extra directories).
- **Fail-closed**: exits 2 with `ERR_ADD_DIR_UNSUPPORTED` when requested but unsupported.

## Report fields (schemaVersion 3)

`report.json` and `status.json` include the following fields added in schema version 3:

| Field | Type | Notes |
|-------|------|-------|
| `schemaVersion` | number | Now `3` (was `2`) |
| `totalCostUsd` | number \| null | Extracted from the `result` stream event's `total_cost_usd`; null when absent |
| `numTurns` | number \| null | Extracted from the `result` stream event's `num_turns`; null when absent |
| `sessionId` | string \| null | Session identifier from the `result` event; null when absent |

The harness never fails because these fields are missing from the stream.

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | The child process completed. NOT success — you must still check `reportValid` and `workerStatus`. |
| `1`  | Spawn or runtime failure: probe error, child died, or any error carrying no `exitCode`. |
| `2`  | Caller precondition or capability failure; nothing was spawned. Missing `--model`, invalid flag values, and any requested capability the installed CLI does not advertise (including the worker-contract append flags). |

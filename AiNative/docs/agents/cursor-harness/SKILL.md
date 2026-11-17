---
name: cursor-harness
description: >-
  Delegates one bounded job to a local Cursor agent via the official
  TypeScript SDK (@cursor/sdk) and cursor-spawn.mjs, then brings the result
  back. Use when the user asks to implement or fix code with the Cursor SDK,
  or when SPECKIT_WORKER=cursor. The parent writes the job. The SDK worker
  only executes that job.
disable-model-invocation: true
---

# Cursor harness

Delegate one job to a local Cursor SDK agent (`@cursor/sdk`) via
`cursor-spawn.mjs`, then take the result back. The parent is the orchestrator.
The SDK agent is the worker. Never invert that.

The worker sees only the prompt you write plus the wrapper-attached contract.
Put the whole job in that prompt, including any files or paths it should read.

Do not tell the worker who owns planning, tasks, questions, or review. Do not
mention Spec Kit, this skill, or “this stays in Cursor” in the prompt. If the
job is a plan, it writes the plan. If the job is implementation, it implements.
The prompt is the job.

You do not edit the code yourself on a job you hand to this worker. After the
wrapper exits, read `report.json`, check the diff, and either finish or spawn
a tighter follow-up.

Runtime is local only: the agent loop runs in this Node process and edits the
`--cwd` tree. Inference stays on Cursor's hosted models. Do not start a cloud
agent, the `agent` TUI, or the SDK bridge from this skill.

Docs used here: [TypeScript SDK](https://cursor.com/docs/sdk/typescript.md).
Cursor's in-product `/sdk` skill is an onboarding aid for people writing SDK
code. It is not this harness.

Ready checks Node >= 22.13, `@cursor/sdk` installed in this skill folder, and
unattended auth (`CURSOR_API_KEY` or a non-empty `~/.cursor/sdk/auth.json`).
Do not ask the user to paste keys. Do not call `Cursor.auth.login()` from a job.

One-time install, from this skill folder:

```bash
cd "$HOME/.cursor/skills/cursor-harness" && npm install
```

`zod` is a peer of `@cursor/sdk` and is listed in `package.json`. Node 22.13 or newer is required.

## Prompt you hand the worker

One job per spawn. Include:

- Goal: the single change or check
- cwd: project root
- Read: file paths, or a spec/task path, that contain what it needs
- Done: how to tell the job worked
- Do not: commit, push, deploy, SSH, or widen the job, unless the user asked
- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed

You choose the job from what the user asked. Do not narrow it before handing it over.

Long jobs **must** go through `cursor-spawn.mjs`. Do not import `@cursor/sdk` in the parent.

## Sub-agent model (required — no harness default)

The parent agent **must** pass `--model`. There is no default. Missing
`--model` → wrapper exits `2` and does not start an agent.

Resolution order:

1. Stage invocation parameter (`worker: { model: ... }`)
2. `SPECKIT_WORKER_MODEL`
3. Runtime default the parent already resolved (pass that id through; do not pin one in this skill)

```bash
# wrapper resolves to the canonical skill dir;
# AiNative canonical: <AINATIVE>/docs/agents/cursor-harness/cursor-spawn.mjs
# host symlink: $HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" \
  --model <id> \
  -- "<prompt>"
```

Model ids come from `Cursor.models.list()` for the account (for example `composer-2.5`). `composer-2` and `composer-2-fast` are retired and rerouted by the SDK to Composer 2.5; pass `composer-2.5` when that is the intended model.

Cursor Router is `auto-smart` plus a required optimize target. The wrapper rejects `auto-smart` without it:

```bash
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" \
  --model auto-smart --model-param optimize_for=balanced \
  -- "<prompt>"
```

`optimize_for` is `cost`, `balanced`, or `intelligence`. Discover allowed values from the catalog before assuming a team has Router enabled. Do not invent a fallback model inside this skill.

## Worker contract (required)

Do not copy Cursor user rules or this skill into the prompt. The wrapper prepends `worker-contract.md` to the user message. The SDK's `systemPrompt` option replaces the coding-agent prompt, so this harness does not set it.

`<AINATIVE>/docs/agents/cursor-harness/worker-contract.md`
(host symlink: `~/.cursor/skills/cursor-harness/worker-contract.md`)

## How to spawn

Always non-interactive. Never launch the `agent` TUI.

Working directory is the job’s project root (`--cwd`). `--name` is the job label. Each spawn gets a unique run id under:

`.agent/cursor/<job-name>/<run-id>/{status.json,report.json,events.jsonl}`

`.agent/cursor/<job-name>/latest.json` points at the newest run. Checkpoints for resume live in `.agent/cursor/_store` (JSONL). Parallel jobs need **different** `--name` values.

The wrapper:

- Creates one local agent with `local.cwd` set to `--cwd`.
- Loads `project`, `user`, and `plugins` settings so skills, rules, and project MCP config apply. It does not pass inline `mcpServers`.
- Leaves sandbox and Auto-review off unless the flags below are set. Headless SDK runs have no human approval prompt, so edit jobs can use tools.
- Prepends the worker contract, sends one prompt, streams SDK events to `events.jsonl`, and writes `report.json`.
- Disposes the agent when the run ends.

### Edit jobs (default)

```bash
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> \
  -- "<prompt>"
```

### Scout (read-only)

```bash
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> --scout \
  -- "<prompt>"
```

`--scout` sets conversation `mode` to `plan` and allowlists `read`, `grep`, `glob`, and `ls`. Do not combine it with `--allowed-tools` or `--disallowed-tools`.

### Resume

```bash
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> \
  --conversation-id "<agent-id>" \
  -- "<prompt>"
```

`--conversation-id` is the previous `sessionId` (`agent-...`). The same `--cwd` is required so the JSONL store matches.

### Optional timeout

```bash
node "$HOME/.cursor/skills/cursor-harness/cursor-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> --timeout 600 -- "<prompt>"
```

`--timeout` is seconds (or `Nms`). On expiry the wrapper cancels the run and sets `lifecycle=timed_out`.

Wrapper stdout is a few lines (`RUN_DIR=`, `STATUS_FILE=`, then `LIFECYCLE=` / `REPORT_FILE=` on exit). Do not read `events.jsonl` unless status is not enough.

## Opt-in flags

### `--allowed-tools <list>` / `--disallowed-tools <list>`

Comma-separated public tool names or groups (`read`, `edit`, `shell`, `mcp`, ...). Passed through as SDK `tools` / `disallowedTools`. Unknown names fail at `Agent.create()` and the wrapper exits `1`.

### `--model-param <id=value>`

Repeatable. Passed as `model.params`. Required for `auto-smart` (`optimize_for`).

### `--sandbox`

Sets `local.sandboxOptions.enabled`. Shell writes stay in the workspace and outbound network is denied unless `.cursor/sandbox.json` allows hosts. If the host cannot sandbox, the SDK throws and the wrapper exits `1`.

### `--auto-review`

Sets `local.autoReview`. Tool calls go through the Auto-review classifier. A blocked call is denied, not escalated, because there is no human in the loop.

## Report fields (schemaVersion 1)

| Field | Type | Notes |
|-------|------|-------|
| `schemaVersion` | number | `1` |
| `backend` | string | `cursor-sdk` |
| `workerStatus` | string \| null | Parsed from `STATUS: ok\|stuck\|blocked` |
| `reportValid` | boolean | True only when `workerStatus` parsed |
| `totalCostUsd` | number \| null | From `agent.getUsage()` `chargedCents / 100` when the account allows it; otherwise null |
| `numTurns` | number \| null | Count of `usage` stream events |
| `sessionId` | string \| null | Local agent id (`agent-...`) |
| `requestId` | string \| null | Run request id |
| `tokenUsage` | object \| null | Cumulative `result.usage` when the runtime reported it |

`lifecycle=completed` means the SDK run finished. It does not mean the worker succeeded.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | The run finished. Check `reportValid` and `workerStatus`. |
| `1` | Spawn or runtime failure: SDK error, cancelled run, timeout, or dispose failure. |
| `2` | Caller precondition. Nothing was started. Missing `--model`, bad Router params, Node older than 22.13, SDK not installed, or no unattended auth. |

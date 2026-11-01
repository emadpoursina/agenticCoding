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

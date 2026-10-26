---
name: antigravity-harness
description: >-
  Delegates one bounded job to the official Antigravity CLI (agy -p) via
  agy-spawn.py and brings the result back. Use when the user asks to implement
  or fix code with Antigravity, or when SPECKIT_WORKER=antigravity.
  Cursor writes the job. The agy CLI only executes that job.
disable-model-invocation: true
---

# Antigravity harness

Delegate one job to the official Antigravity CLI (`agy -p` headless) via
`agy-spawn.py`, then take the result back. Cursor is the orchestrator.
Antigravity is the worker. Never invert that.

The worker sees only the prompt you write plus the wrapper-prepended contract.
Put the whole job in that prompt, including any files or paths it should read.

Do not tell the worker who owns planning, tasks, questions, or review. Do not
mention Spec Kit, this skill, or “this stays in Cursor” in the prompt. If the
job is a plan, it writes the plan. If the job is implementation, it implements.
The prompt is the job.

You do not edit the code yourself on a job you hand to Antigravity. After the
wrapper exits, read `report.json`, check the diff, and either finish or spawn
a tighter follow-up.

Ready checks that `agy` is on PATH and authenticated via `agy models`. Auth is
already the operator’s (`agy` CLI login). Do not ask the user to paste keys.
Do not use the community npm `antigravity-sdk` (VS Code extensions) or the
`agy` TUI from this harness. Never launch bare `agy` and never mix `-p` with
`--input-format stream-json`.

## Prompt you hand the worker

One job per spawn. Include:

- Goal: the single change or check
- cwd: project root
- Read: file paths, or a spec/task path, that contain what it needs
- Done: how to tell the job worked
- Do not: commit, push, deploy, SSH, or widen the job, unless the user asked
- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed

You choose the job from what the user asked. Do not narrow it before handing it over.

Long jobs **must** go through `agy-spawn.py`. Do not call `agy` directly in the
parent. The wrapper keeps streams on disk and exposes a tiny `status.json`.

## Sub-agent model (required — no harness default)

The parent agent **must** pass `--model`. There is no default. Missing
`--model` → wrapper exits `2` and does not start `agy`.

```bash
# wrapper resolves to the canonical skill dir;
# AiNative canonical: <AINATIVE>/docs/agents/antigravity-harness/agy-spawn.py
# host symlink: $HOME/.cursor/skills/antigravity-harness/agy-spawn.py
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" \
  --model <id> \
  -- "<prompt>"
```

Optional: `--effort <low|medium|high|xhigh|max>` when the parent has a thinking/effort value
and the CLI accepts it. Do not invent a fallback model inside this skill.

## Worker contract (required)

Do not copy Cursor user rules or this skill into the prompt. The wrapper
always prepends the contract from:

`<AINATIVE>/docs/agents/antigravity-harness/worker-contract.md`
(host symlink: `~/.cursor/skills/antigravity-harness/worker-contract.md`;
Hermes mount: `/opt/data/mnt/AiNative/docs/agents/antigravity-harness/worker-contract.md`)

Put the actual job, skill path, and report format in the prompt.

## How to spawn

Always non-interactive headless print mode (`agy -p`). Never launch bare `agy`
(TUI steals the terminal). Never pass `--prompt-interactive` or `-i`.
Never attach `ask_user` policies — the parent is unattended and child stdin is ignored.

Working directory is the job’s project root (`--cwd`). `--name` is the job
label. Each spawn gets a unique run id under:

`.agent/antigravity/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}`

`.agent/antigravity/<job-name>/latest.json` points at the newest run. Parallel
jobs need **different** `--name` values.

The wrapper:

- Always executes `agy -p` with child stdin ignored (`DEVNULL` / not a TTY).
- Runs in `--cwd` so file tools stay in the job tree.
- Prepends `worker-contract.md` plus a blank line to the job prompt as the single `-p` argument.
- Always passes `--disable-slash-commands`.
- Sets `--mode accept-edits --dangerously-skip-permissions` for default (edit) jobs.
- Sets `--mode plan` for `--scout` (no skip-permissions).
- Uses `--conversation <id>` when `--conversation-id` is passed (isolated default; no `--continue`).

### Edit jobs (default)

Edit jobs auto-approve tool execution via `--mode accept-edits --dangerously-skip-permissions`
so `edit_file` / `run_command` do not wait for a human.

```bash
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" --model <id> \
  -- "<prompt>"
```

### Scout (read-only)

```bash
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" --model <id> --scout \
  -- "<prompt>"
```

`--scout` sets `--mode plan` and omits `--dangerously-skip-permissions`.
Do not broaden scout access.

### Short jobs

Same wrapper. `--print` runs `agy -p` in CLI text output mode (no `--output-format stream-json`).
Default long jobs use `--output-format stream-json` and record raw CLI events to `events.jsonl`.
Always prefer the wrapper when you want `report.json`.

### Optional timeout

Dual timeout enforcement when wrapper `--timeout` is set: forwarded as `agy --print-timeout {n}s`
and enforced by a wrapper kill timer (SIGTERM then SIGKILL with ~2s grace).
If `--timeout` is omitted, neither `--print-timeout` nor a wrapper kill timer is set (CLI default applies).

```bash
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" --model <id> --timeout 600 -- "<prompt>"
```

`--timeout` is seconds (or `Nms`). On expiry the wrapper terminates the child,
sets `lifecycle=timed_out` / `timedOut=true`.

Wrapper stdout is a few lines (`RUN_DIR=`, `STATUS_FILE=`, then `LIFECYCLE=` /
`REPORT_FILE=` on exit). Ignore anything else. Do not read `events.jsonl`
unless status is not enough.

Do not pass MCP servers unless the user asked.

## agy CLI vs Pi (do not copy Pi flags)

| Pi | Antigravity CLI |
| --- | --- |
| `pi` CLI + `--mode json` | `agy` CLI + `-p` + `--output-format stream-json` |
| `--provider` / `--thinking` | `--model` (and optional `--effort` if the CLI accepts it) |
| `--tools read,grep,find,ls` | `--scout` → `--mode plan` |
| `--no-session` | fresh conversation (default; `--conversation <id>` when passed) |
| `--append-system-prompt` | contract prepended to prompt before job text |
| default tools include writes | edit jobs pass `--mode accept-edits --dangerously-skip-permissions` |

Pass `--vertex` only if needed for enterprise routing; authenticate via `agy models`.
Do not put keys on the command line.

## Lifecycle vs worker STATUS

Two layers — do not conflate them:

| Layer | Where | Values | Meaning |
| --- | --- | --- | --- |
| **Process lifecycle** | `status.json` / `report.json` → `lifecycle` | `starting`, `running`, `completed`, `failed`, `terminated`, `timed_out` | Wrapper-verified process outcome |
| **Worker STATUS** | `report.json` → `workerStatus` | `ok`, `stuck`, `blocked`, or `null` | Claim parsed from assistant text |

Also in `report.json`: `reportValid`, `timedOut`, `timeoutMs`, `exitCode`,
`errorMessage`, `summary`.

Exit code 0 / `lifecycle=completed` means the `agy` process exited 0 — **not** that
the job succeeded. Always read `reportValid` and `workerStatus`.

## Monitor

1. Poll `status.json` (via `latest.json` or `STATUS_FILE=`). Default. Do not ingest `events.jsonl`.
2. `processAlive=true` and `watcherUpdatedAt` fresh (~2s) → wrapper is alive.
3. `current.kind=tool` → that built-in (`edit_file`, `run_command`, …) is in flight.
4. After exit, read `report.json`. Check `lifecycle`, then `reportValid` / `workerStatus`.
5. Never dump raw logs unless asked.

Do not kill a live worker only because events went quiet. Abort when the named
tool is far past what it should take, the user wants a stop, spawn never
started, or `--timeout` elapsed.

User-facing pulse: one sentence from status, e.g. “Antigravity is running;
current operation is run_command (12s).”

## Sub-agents

A sub-agent is another wrapper process you start. Wait for the result (poll
`status.json`). Do not let the CLI spawn nested agents.

**Parallel:** distinct `--name`. **Serial:** wait for report A, then spawn B.

## Control rules

- You decide what to spawn, the prompt, cwd, **model**, and when to stop.
- Parent only spawns via `agy-spawn.py`; never call `agy -p` directly.
- Summarize from `report.json`. Do not paste raw dumps unless asked.
- Do not SSH, deploy, commit, or push from a worker job unless the user asked.
- Do not install packages or change operator auth.
- If `agy` is not on PATH or `agy models` fails, stop and report the issue.

## Report back

1. What you asked Antigravity to do
2. What it did (from `report.json`: lifecycle + workerStatus/reportValid)
3. What you will do next

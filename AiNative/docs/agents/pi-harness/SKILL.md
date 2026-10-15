---
name: pi-harness
description: >-
  Delegates one bounded job to Pi and brings the result back. Use when the
  user asks to implement or fix code, to use Pi, or to offload a task to Pi.
  Cursor writes the job. Pi only executes that job.
disable-model-invocation: true
---

# Pi harness

Delegate one job to Pi, then take the result back. Cursor is the orchestrator. Pi is the worker. Never invert that.

Pi sees only the prompt you write. Put the whole job in that prompt, including any files or paths it should read. Do not assume it will look up the rest.

Do not tell Pi who owns planning, tasks, questions, or review. Do not mention Spec Kit, this skill, or “this stays in Cursor” in the prompt. If the job is a plan, Pi writes the plan. If the job is implementation, Pi implements. The prompt is the job.

You do not edit the code yourself on a job you hand to Pi. After Pi exits, read `report.json`, check the diff, and either finish or spawn a tighter follow-up.

Pi is already installed (`pi` on PATH; verified **1.2.0**). Auth and model keys are already configured. Do not ask the user to log in or paste keys.

## Prompt you hand Pi

One job per spawn. Include:

- Goal: the single change or check
- cwd: project root
- Read: file paths, or a spec/task path, that contain what Pi needs
- Done: how to tell the job worked
- Do not: commit, push, deploy, SSH, or widen the job, unless the user asked for that action
- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed

You choose the job from what the user asked. Do not narrow it before handing it over.

Long jobs **must** go through `pi-spawn.mjs`. Do not run `pi --mode json` yourself. That stream is huge; the wrapper keeps it on disk and exposes a tiny `status.json`.

## Sub-agent model (required — no harness default)

The parent agent **must** pass `--model`. There is no default. Missing `--model` → wrapper exits `2` and does not spawn Pi.

Pass model on the wrapper (before `--`) or as a Pi flag (after `--`):

```bash
# preferred: wrapper flags (wrapper resolves to the canonical skill dir;
# AiNative canonical: <AINATIVE>/docs/agents/pi-harness/pi-spawn.mjs,
# host symlink: $HOME/.cursor/skills/pi-harness/pi-spawn.mjs)
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" \
  --provider <name> --model <id> [--thinking <level>] \
  -- "<prompt>"

# also valid: Pi flags after --
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" -- \
  --provider <name> --model <id> --thinking <level> "<prompt>"
```

`--provider` / `--thinking` are optional when the parent includes them (Pi accepts `provider/id` and `id:thinking` in `--model`). The spawning agent chooses the model (user request, runtime default, etc. — never a skill-pinned value). Do not invent a fallback inside this skill.

## Worker contract (required)

Do not copy Cursor user rules or this skill into the prompt. The wrapper always appends the canonical worker contract:

`<AINATIVE>/docs/agents/pi-harness/worker-contract.md`
(host symlink: `~/.cursor/skills/pi-harness/worker-contract.md`;
Hermes mount: `/opt/data/mnt/AiNative/docs/agents/pi-harness/worker-contract.md`)

Put the actual job, skill path, and report format in the prompt.

## How to spawn

Always non-interactive. Never launch bare `pi` (TUI steals the terminal).

Working directory is the job’s project root (`--cwd`). `--name` is the job label. Each spawn gets a unique run id under:

`.agent/pi/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}`

`.agent/pi/<job-name>/latest.json` points at the newest run. Parallel jobs need **different** `--name` values.

### Short jobs (about a minute or less)

Block until exit. `--print` uses `pi -p` (final text only; no JSON pulse):

```bash
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --print \
  --model <id> [--provider <name>] [--thinking <level>] \
  -- "<prompt>"
```

You may still call `pi -p` with the same model flags + worker contract if the task is tiny and you do not need `status.json`. Prefer the wrapper when you want a report file.

### Longer jobs

Background the wrapper (do not use silent `pi -p`; do not attach to JSON stdout). Prompt and extra Pi flags go after `--`:

```bash
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" \
  --model <id> [--provider <name>] [--thinking <level>] \
  -- "<prompt>"
```

Scout (read-only allowlist; Pi 1.2.0 still keeps MCP tools unless an entry starts with `mcp__` — add `--no-mcp` after `--` when MCP must stay off):

```bash
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> -- \
  --tools read,grep,find,ls "<prompt>"
```

(`grep`, `find`, `ls` are off unless listed. Edit workers: omit `--tools`.) Optional denylist: `--exclude-tools <names>` after `--`. Do not broaden scout access.

Wrapper stdout is a few lines (`RUN_DIR=`, `STATUS_FILE=`, then `LIFECYCLE=` / `REPORT_FILE=` on exit). Ignore anything else. Do not read `events.jsonl` unless status is not enough.

Do not use `--mode rpc`.

### Optional timeout

No default timeout. To bound a job, pass wrapper flag **before** `--`:

```bash
node "$HOME/.cursor/skills/pi-harness/pi-spawn.mjs" \
  --name "<job>" --cwd "$PWD" --model <id> --timeout 600 -- "<prompt>"
```

`--timeout` is seconds (or `Nms` for milliseconds). On expiry the wrapper SIGTERMs Pi, escalates to SIGKILL after 2s, sets `lifecycle=timed_out` / `timedOut=true` in status and report.

### Shared spawn notes (Pi 1.2.0 flags after `--`)

Isolated / ephemeral is the default preference: add `--no-session` after `--` when the job must not leave a session file.

Recovery only when you already know the target (never auto-resume or share across concurrent jobs):

- `--session <path|id>` — specific session file or partial UUID
- `--session-id <id>` — exact project session id (creates if missing)
- `--session-dir <dir>` — session storage/lookup directory
- `--continue` / `-c` — continue previous session
- `--fork <path|id>` — fork into a new session

`--resume` / `-r` is interactive session picking — do not use it from this harness.

Project-local Pi/skills files: `--approve` after `--` only when that project should be trusted for this run.

Prompt every child with: goal, cwd, files/paths, done criteria, and what **not** to do. Children have no chat history unless you explicitly pass a session flag.

## Lifecycle vs worker STATUS

Two layers — do not conflate them:

| Layer | Where | Values | Meaning |
| --- | --- | --- | --- |
| **Process lifecycle** | `status.json` / `report.json` → `lifecycle` | `starting`, `running`, `completed`, `failed`, `terminated`, `timed_out` | Wrapper-verified process outcome |
| **Worker STATUS** | `report.json` → `workerStatus` | `ok`, `stuck`, `blocked`, or `null` | Claim parsed from assistant text |

Also in `report.json`:

- `reportValid` — `true` only when a `STATUS: ok|stuck|blocked` token was found in the summary
- `timedOut`, `timeoutMs`, `exitCode`, `signal`, `errorMessage`, `summary`

**Rules:**

- Exit code 0 / `lifecycle=completed` means the process finished cleanly — **not** that the job succeeded. Always read `reportValid` and `workerStatus`.
- Quiet event streams are **not** stuck by themselves (see monitor table).
- `lifecycle=failed` covers spawn failure and non-zero exit; `terminated` is signal kill without timeout; `timed_out` is wrapper timeout.

## Monitor (progressive disclosure)

1. Poll `status.json` (via `latest.json` or `STATUS_FILE=`). Default. Do not ingest `events.jsonl`.
2. Diagnose quiet/stalled workers from status fields (below).
3. If status is insufficient, `tail` **at most ~30 lines** of `events.jsonl`, or grep one event type. Never `cat` the whole file.
4. After the wrapper exits, read `report.json` (not the last activity string in status). Check `lifecycle`, then `reportValid` / `workerStatus`.
5. Never dump raw logs to the user unless they asked.

Heartbeat vs silence (do **not** treat 3 minutes without JSON as “stuck”):

| Observation | Meaning |
| --- | --- |
| `lifecycle=starting` and no `pid` | spawn not finished; if `lastError` appears, spawn failed |
| `processAlive=true`, `watcherUpdatedAt` fresh (~2s) | wrapper is alive |
| `processAlive=true`, `quietMs` large, `current.kind=tool` | **that tool** has been running; may be healthy |
| `processAlive=true`, `quietMs` large, `current.kind` thinking/writing/model | model/stream quiet; still not proof of death |
| `watcherUpdatedAt` stale (>15s) | wrapper stopped updating; `kill -0 <pid>` if you need to know whether Pi is still up |
| `lifecycle=completed\|failed\|terminated\|timed_out` | process exited; read `report.json` |
| `timedOut=true` | wrapper timeout fired |
| `current.kind=emitting_tool_call` | model is streaming a tool call; the tool is **not** running yet |
| `current.kind=tool` | `tool_execution_start` seen; this is the only “operation is executing X” claim you may make |

Do not kill a live worker only because events went quiet. Abort (SIGTERM the wrapper, which forwards to Pi, then SIGKILL after 2s) when the **named tool** is far past what that tool should take, the user wants a stop, spawn never produced a pid, or an optional `--timeout` elapsed.

User-facing pulse: one sentence from status, e.g. “Pi is running; current operation is bash (12s)” or “Pi’s process is alive; last event was thinking 40s ago.” If `current` is null, do not invent an operation.

## Sub-agents

A sub-agent is another wrapper process you start. Wait for the result (blocking on short `--print`; poll `status.json` on longer ones). Pi does not call you back.

**Parallel:** distinct `--name`, separate wrapper processes.

**Serial:** wait for report A, then spawn B.

## Control rules

- You decide what to spawn, the prompt, cwd, **model**, and when to stop. Always pass `--model`; never rely on a harness default.
- Summarize from `report.json`. Do not paste raw Pi dumps unless asked.
- Do not SSH, deploy, commit, or push from a Pi job unless the user asked for that specific action.
- Do not install Pi packages or change Pi auth.
- If a job is actually stuck (see table), abort and rerun tighter. Use `--print` only if the retry is a short job.
- If `pi` is missing, stop and say it is not on PATH. Do not install it.

## Report back

1. What you asked Pi to do
2. What Pi did (from `report.json`: lifecycle + workerStatus/reportValid), or one status line if still running
3. What you will do next

## Future opportunities (not implemented)

- Optional stricter scout: pair `--tools read,grep,find,ls` with `--no-mcp` by default only if callers opt in (MCP-off changes scout behavior).
- Consume richer JSON progress fields only if `status.json` proves insufficient for a real orchestration case — do not replace status polling casually.
- Pi has no CLI job-timeout flag in 1.2.0; wrapper `--timeout` is the supported bound.

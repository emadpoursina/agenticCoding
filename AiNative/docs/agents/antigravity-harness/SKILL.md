---
name: antigravity-harness
description: >-
  Delegates one bounded job to the Google Antigravity Python SDK and brings
  the result back. Use when the user asks to implement or fix code with
  Antigravity, to use the Antigravity SDK, or when SPECKIT_WORKER=antigravity.
  Cursor writes the job. The SDK Agent only executes that job.
disable-model-invocation: true
---

# Antigravity harness

Delegate one job to the Google Antigravity SDK (`google.antigravity.Agent`),
then take the result back. Cursor is the orchestrator. Antigravity is the
worker. Never invert that.

The worker sees only the prompt you write plus the wrapper-appended contract.
Put the whole job in that prompt, including any files or paths it should read.

Do not tell the worker who owns planning, tasks, questions, or review. Do not
mention Spec Kit, this skill, or “this stays in Cursor” in the prompt. If the
job is a plan, it writes the plan. If the job is implementation, it implements.
The prompt is the job.

You do not edit the code yourself on a job you hand to Antigravity. After the
wrapper exits, read `report.json`, check the diff, and either finish or spawn
a tighter follow-up.

Install is `pip install google-antigravity` (the PyPI wheel ships the compiled
`localharness` binary; cloning the GitHub repo is not enough). Auth is already
the operator’s: `GEMINI_API_KEY` / `GOOGLE_API_KEY`, or Vertex
(`GOOGLE_GENAI_USE_VERTEXAI` + project/ADC). Do not ask the user to paste keys.
Do not use the community npm `antigravity-sdk` (VS Code extensions) or the
`agy` TUI from this harness.

## Prompt you hand the worker

One job per spawn. Include:

- Goal: the single change or check
- cwd: project root
- Read: file paths, or a spec/task path, that contain what it needs
- Done: how to tell the job worked
- Do not: commit, push, deploy, SSH, or widen the job, unless the user asked
- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed

You choose the job from what the user asked. Do not narrow it before handing it over.

Long jobs **must** go through `agy-spawn.py`. Do not write ad-hoc
`Agent.chat()` scripts in the parent. The wrapper keeps streams on disk and
exposes a tiny `status.json`.

## Sub-agent model (required — no harness default)

The parent agent **must** pass `--model`. There is no default. Missing
`--model` → wrapper exits `2` and does not start the SDK.

```bash
# wrapper resolves to the canonical skill dir;
# AiNative canonical: <AINATIVE>/docs/agents/antigravity-harness/agy-spawn.py
# host symlink: $HOME/.cursor/skills/antigravity-harness/agy-spawn.py
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" \
  --model <id> \
  -- "<prompt>"
```

Optional: `--effort <low|max|…>` when the parent has a thinking/effort value
and `LocalAgentConfig` accepts it. Do not invent a fallback model inside this
skill.

## Worker contract (required)

Do not copy Cursor user rules or this skill into the prompt. The wrapper
always sets `system_instructions` from:

`<AINATIVE>/docs/agents/antigravity-harness/worker-contract.md`
(host symlink: `~/.cursor/skills/antigravity-harness/worker-contract.md`;
Hermes mount: `/opt/data/mnt/AiNative/docs/agents/antigravity-harness/worker-contract.md`)

Put the actual job, skill path, and report format in the prompt.

## How to spawn

Always non-interactive. Never launch bare `agy` (TUI steals the terminal).
Never call `run_interactive_loop`. Never attach `ask_user` policies — the
parent is unattended and would hang on `run_command`.

Working directory is the job’s project root (`--cwd`). `--name` is the job
label. Each spawn gets a unique run id under:

`.agent/antigravity/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}`

`.agent/antigravity/<job-name>/latest.json` points at the newest run. Parallel
jobs need **different** `--name` values.

The wrapper:

- Starts `async with Agent(LocalAgentConfig(...))` (binary discovery + lifecycle).
- Sets `workspaces=[cwd]` so file tools stay in the job tree.
- Uses a fresh `conversation_id` and `save_dir` under the run dir (isolated;
  no `--continue` unless you pass `--conversation-id`).
- Turns off SDK subagents. The parent orchestrates; the worker does one job.

### Edit jobs (default)

SDK agents are **read-only unless** `CapabilitiesConfig()` is set. The wrapper
enables write tools and `policy.allow_all()` so `run_command` / `edit_file` /
`create_file` do not wait for a human.

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

`--scout` sets `CapabilitiesConfig(enabled_tools=BuiltinTools.read_only())`.
Do not broaden scout access.

### Short jobs

Same wrapper. `--print` still runs the SDK (there is no `agy -p` in this
skill); it just skips extra event chatter in stdout. Always prefer the
wrapper when you want `report.json`.

### Optional timeout

No default timeout. Wrapper flag **before** `--`:

```bash
python3 "$HOME/.cursor/skills/antigravity-harness/agy-spawn.py" \
  --name "<job>" --cwd "$PWD" --model <id> --timeout 600 -- "<prompt>"
```

`--timeout` is seconds (or `Nms`). On expiry the wrapper cancels the agent,
sets `lifecycle=timed_out` / `timedOut=true`.

Wrapper stdout is a few lines (`RUN_DIR=`, `STATUS_FILE=`, then `LIFECYCLE=` /
`REPORT_FILE=` on exit). Ignore anything else. Do not read `events.jsonl`
unless status is not enough.

Do not pass MCP servers unless the user asked. Do not enable
`START_SUBAGENT`.

## SDK vs Pi (do not copy Pi flags)

| Pi | Antigravity SDK |
| --- | --- |
| `pi` CLI + `--mode json` | `Agent` / `LocalAgentConfig` in Python |
| `--provider` / `--thinking` | `--model` (and optional `--effort` if the config accepts it) |
| `--tools read,grep,find,ls` | `--scout` → `BuiltinTools.read_only()` |
| `--no-session` | fresh `conversation_id` + run-local `save_dir` (default) |
| `--append-system-prompt` | `system_instructions=` worker contract |
| default tools include writes | default SDK is read-only; wrapper enables writes unless `--scout` |

Vertex: leave config alone when `GOOGLE_GENAI_USE_VERTEXAI` / project env
are already set. Pass `--vertex` only when the parent must force Enterprise
routing. Do not put keys on the command line.

## Lifecycle vs worker STATUS

Two layers — do not conflate them:

| Layer | Where | Values | Meaning |
| --- | --- | --- | --- |
| **Process lifecycle** | `status.json` / `report.json` → `lifecycle` | `starting`, `running`, `completed`, `failed`, `terminated`, `timed_out` | Wrapper-verified process outcome |
| **Worker STATUS** | `report.json` → `workerStatus` | `ok`, `stuck`, `blocked`, or `null` | Claim parsed from assistant text |

Also in `report.json`: `reportValid`, `timedOut`, `timeoutMs`, `exitCode`,
`errorMessage`, `summary`.

Exit code 0 / `lifecycle=completed` means the SDK turn finished — **not** that
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
`status.json`). Do not let the SDK spawn nested agents.

**Parallel:** distinct `--name`. **Serial:** wait for report A, then spawn B.

## Control rules

- You decide what to spawn, the prompt, cwd, **model**, and when to stop.
- Summarize from `report.json`. Do not paste raw dumps unless asked.
- Do not SSH, deploy, commit, or push from a worker job unless the user asked.
- Do not `pip install google-antigravity` or change Gemini/Vertex auth.
- If `google.antigravity` cannot be imported, stop and say to install the
  PyPI package. Do not install it.

## Report back

1. What you asked Antigravity to do
2. What it did (from `report.json`: lifecycle + workerStatus/reportValid)
3. What you will do next

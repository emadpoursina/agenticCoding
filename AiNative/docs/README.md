# Documentation

How this repo is organized. Full spec: [ENGINEERING-OS.md](../ENGINEERING-OS.md).

Four layers, one decision each: **systems** (how you work), **agents** (AI partners), **knowledge** (evergreen reference), **records** (what happened).

## Retrieval by mental path

| When you need... | Go to... |
|------------------|----------|
| A specific command | [knowledge/commands/](./knowledge/commands/) |
| Project or server setup | [knowledge/setup/](./knowledge/setup/) |
| Architecture patterns | [knowledge/architecture/](./knowledge/architecture/) |
| A working config or script | [knowledge/snippets/](./knowledge/snippets/) |
| How to run a release | [systems/release-management-system.md](./systems/release-management-system.md) |
| Client/server compatibility | [systems/client-compatibility-system.md](./systems/client-compatibility-system.md) |
| A per-task AI agent | [agents/](./agents/) — start with `AGENTS.md` |
| Agentic system (Harness, Model, Context, Tools, Agents) | [systems/agentic-system.md](./systems/agentic-system.md) |
| Harness setup (Tmux + Cursor CLI) | [knowledge/setup/harness.md](./knowledge/setup/harness.md) |
| Live feature loop (Hermes / Cursor) | [systems/feature-loop.md](./systems/feature-loop.md) |
| Historical PIV (not the live stage list) | [systems/agentic-coding.md](./systems/agentic-coding.md) |
| Validation layer architecture | [systems/validation-layer.md](./systems/validation-layer.md) |
| PIV Validation — adversarial review | [agents/critic/](./agents/critic/) |
| PIV Validation — prove the code works | [agents/tester/](./agents/tester/) |
| PR review prompts | [agents/pr-reviewer/](./agents/pr-reviewer/) |
| Task grooming / meeting prep | [agents/task-groomer/](./agents/task-groomer/) |
| New-project scaffolding | [agents/project-bootstrapper/](./agents/project-bootstrapper/) |
| Legacy assessment (strategies, estimates) | [agents/legacy-system-assessment-agent/](./agents/legacy-system-assessment-agent/) |
| Reusable agent skills | [agents/_skills/](./agents/_skills/) |
| Agent handoff between AI passes | [systems/agent-handoff-template.md](./systems/agent-handoff-template.md) |
| How to run planning / board setup | [systems/task-management-system.md](./systems/task-management-system.md) |
| A bug you have seen before | [records/debugging/\<domain\>/](./records/debugging/) |
| Why a decision was made | [records/decisions/](./records/decisions/) |
| What broke and why | [records/postmortems/](./records/postmortems/) |
| Something new to test (model, tool, workflow) | [records/evaluations/](./records/evaluations/) |

## `systems/`

Operational workflows and AI methodology — stable, rarely changes. See [systems/README.md](./systems/README.md).

## `agents/`

Per-task AI agents — see [agents/README.md](./agents/README.md).

## `knowledge/`

Evergreen technical knowledge, updated in place — commands, setup, architecture, and copy-paste [snippets/](./knowledge/snippets/). See [knowledge/README.md](./knowledge/README.md).

## `records/`

Dated, append-only memory — [debugging/](./records/debugging/), [decisions/](./records/decisions/), [postmortems/](./records/postmortems/), [evaluations/](./records/evaluations/). See [records/README.md](./records/README.md).

## Three rituals

1. **Capture during work** — write raw notes in `scratch/` (gitignored except `scratch/README.md`)
2. **Friday review (15 min)** — promote scratch → right layer (including `records/evaluations/` for test candidates), update stale knowledge, delete junk
3. **After significant events** — debug note (hard bug), ADR (architecture decision), postmortem (incident)

See [ENGINEERING-OS.md](../ENGINEERING-OS.md) for layer contracts and migration notes.

# Systems

How you work — the operational workflows and AI methodology you repeat on every team. Stable, rarely changes.

## Workflows

| File | Topic |
|------|-------|
| [task-management-system.md](./task-management-system.md) | Board, tasks, WIP, meetings |
| [pr-review-system.md](./pr-review-system.md) | Staged PR review and human decision |
| [release-management-system.md](./release-management-system.md) | Branching, release flow, backward compatibility, deploy checklists |
| [client-compatibility-system.md](./client-compatibility-system.md) | Server tags vs client adoption |

## AI methodology

Generic AI templates shared across agents — not task-specific.

| File | Purpose |
|------|---------|
| [agentic-system.md](./agentic-system.md) | Five-part model — Harness, Model, Context, Tools, Agents |
| [feature-loop.md](./feature-loop.md) | Live feature loop — Hermes graph, Pi per state, Spec Kit + AiNative gates |
| [agentic-coding.md](./agentic-coding.md) | Historical PIV — not the live Hermes stage list |
| [validation-layer.md](./validation-layer.md) | Validation phase architecture — multi-agent workflow, quality gates, diamond testing model |
| [agent-handoff-template.md](./agent-handoff-template.md) | Structured handoff between planner, plan-reviewer, implementer, critic, tester, and groomer agents |
| [system-understanding-brief-template.md](./system-understanding-brief-template.md) | Brief the scout agent produces before PIV Plan interrogation |
| [ai-rules-template.md](./ai-rules-template.md) | Project-specific `AGENTS.md` rules template used by bootstrapper |

**Per-task agents** (scout, plan-reviewer, critic, tester, pr-reviewer, task-groomer, project-bootstrapper): [agents/](../agents/).

Project-specific rules live in the managed project's `AGENTS.md`.

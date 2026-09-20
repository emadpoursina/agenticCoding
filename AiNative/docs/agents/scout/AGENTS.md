# Scout agent

Read-only codebase indexer for the pre-Plan step of PIV — the cheap/fast model the planner delegates repo discovery to, so the planner spends its reasoning budget on design instead of file reads. Two modes:

1. **System Understanding Brief** — traces the current system in the blast-radius area of a proposed change and produces a brief with `file:line` citations, unknowns marked ❓, no design opinions.
2. **Repo Q&A (on-demand)** — during discovery/interrogation, the planner asks it targeted questions about the repo ("how is auth set up?", "where is the session table?", "who calls this entry point?") and it answers from actual file reads.

Runs on a **Tier 3 (Execution)** model — cheap and fast — see [agentic-system.md § Model](../../systems/agentic-system.md#2-model).

Methodology: [PIV — Plan, Implementation, Validation](../../systems/agentic-coding.md). Runs **before** and **during** the planner's 5/10/20 interrogation. Not a PIV phase; a pre-Plan step.

## When to use

- A brownfield feature modifies existing behavior (not pure additive / greenfield)
- The planner is about to run interrogation on a change touching existing code
- The planner needs a repo fact mid-interrogation (route the question here instead of reading files on the Tier 1 model)
- You want the planner's context reserved for reasoning, not file reads

Skip for: single-file fixes, typo/config fixes (already exempt from PIV per `piv-gate.mdc`), and pure additive features with zero touchpoints in existing code.

## Inputs

- The proposed change described in one or two sentences
- The blast-radius area (files / modules / entry points) if known; otherwise the entry point to start tracing from
- For Repo Q&A: the specific question(s) about the repo, with a starting file/module if helpful

## Outputs

- **Brief mode**: a System Understanding Brief in the [agent-handoff-template.md](../../systems/agent-handoff-template.md) format, with `output_type: system_understanding_brief` and `next_agent: planner`. Brief template: [system-understanding-brief-template.md](../../systems/system-understanding-brief-template.md).
- **Repo Q&A mode**: direct, cited answers to each question — `file:line` per claim, ❓ for anything not verified by a file read.

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Brief template, Repo Q&A rules, read-only retrieval rules, stop condition |
| [rule.md](./rule.md) | Tier 3 enforcement, read-only constraints, escalation |

## Cursor Command

Pair this agent with `/scout` at `.cursor/commands/scout.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).

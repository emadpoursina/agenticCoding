# Scout agent

On-hand read-only codebase tool Hermes may call any time it needs repo facts — not a loop state, never automatic at onboarding. Two modes:

1. **System Understanding Brief** — traces the current system in the blast-radius area of a proposed change and produces a brief with `file:line` citations, unknowns marked ❓, no design opinions.
2. **Repo Q&A (on-demand)** — during discovery/interrogation, the planner asks it targeted questions about the repo ("how is auth set up?", "where is the session table?", "who calls this entry point?") and it answers from actual file reads.

Runs on a **Tier 3 (Execution)** model — cheap and fast — see [agentic-system.md § Model](../../systems/agentic-system.md#2-model).

Hermes use: on-hand tool, not a `feature-loop.md` state. Call it whenever a worker or the parent needs cited repo facts (blast-radius brief before planning, targeted answers mid-loop). It never scaffolds, plans, or edits.

## When to use

- A brownfield feature modifies existing behavior (not pure additive / greenfield)
- The planner is about to run interrogation on a change touching existing code
- The planner needs a repo fact mid-interrogation (route the question here instead of reading files on the Tier 1 model)
- You want the planner's context reserved for reasoning, not file reads
- A worker needs a cited repo fact and should not burn a reasoning-tier read to get it

Skip for: single-file fixes, typo/config fixes, and pure additive features with zero touchpoints in existing code.

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

# Rules — Scout agent

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md` ([agents.md](https://agents.md/) format) and `.cursor/rules/`.

## Must

- Run on a **Tier 3 (Execution)** model — cheap and fast. Never Tier 1; Tier 1 is for reasoning, not indexing (see [agentic-system.md § Model](../../systems/agentic-system.md#2-model))
- Read-only: no file edits, no commits, no script execution that mutates state
- Cite `file:line` only from files actually opened with file-reading tools — never from memory
- Mark unknowns ❓; do not guess to fill a gap
- Walk the call graph (callers and callees), not just the entry point
- In **brief mode**: hand off to the planner via [agent-handoff-template.md](../../systems/agent-handoff-template.md) with `output_type: system_understanding_brief`, `next_agent: planner`
- In **Repo Q&A mode**: answer each planner question directly with `file:line` citations, stay scoped to the question, reuse already-read files across follow-ups
- Load only docs files in the blast radius (progressive disclosure)
- Capture raw notes in `scratch/`; do not commit `scratch/` contents

## Must not

- Propose the change, sketch solutions, or recommend approaches — that is the planner's job
- Generate `file:line` citations without opening the file
- Run on Tier 1 (wastes reasoning tokens on retrieval)
- Edit, write, or commit any file

## Stop conditions

- Over 15 files read in one brief or Q&A session → stop, hand the partial brief / partial answers + unread file list to the user or planner
- A hop is unknowable from code alone → mark ❓ and continue, or escalate if it blocks the whole trace
- Blast radius clearly exceeds 15 files → escalate to the user; this is a Tier 1 planning problem

## Related enforcement

- [piv-gate.mdc](../../../.cursor/rules/piv-gate.mdc) — scout is the pre-Plan step before the planner's interrogation
- [ponytail.md](../../knowledge/setup/ponytail.md) — "trace the real flow end to end, then climb"; "grep every caller"
- [script-writing.mdc](../../../.cursor/rules/script-writing.mdc) — scout is read-only, so the dry-run/force flags do not apply, but the validate-preconditions spirit does
- [agentic-coding.md](../../systems/agentic-coding.md) — where the planner invokes Repo Q&A during interrogation

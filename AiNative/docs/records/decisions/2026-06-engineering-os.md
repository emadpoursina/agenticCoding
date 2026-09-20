# ADR-001: Adopt Engineering Operating System structure

**Date:** 2026-06-06
**Status:** Accepted

## Context

AiNative started as a flat repo with three system docs and one large `programming-documentation.md` file. Prompts were embedded in workflow docs. There was no structured place for bug patterns, ADRs, postmortems, or raw capture — knowledge evaporated after incidents and decisions.

The Engineering Operating System (`ENGINEERING-OS.md`) defines layered folders with clear contracts: systems for workflows, ai-workflows for prompts, reference for evergreen knowledge, debugging/decisions/postmortems for append-only operational records, snippets for copy-paste code, and scratch for zero-friction capture.

## Decision

Adopt the full Engineering OS folder structure in this repo:

- `docs/systems/` — universal workflows (unchanged role)
- `docs/ai-workflows/` — extracted, versioned prompts
- `docs/reference/` — split by setup, commands, architecture
- `docs/debugging/`, `docs/decisions/`, `docs/postmortems/` — append-only layers with templates
- `docs/snippets/` — working code only
- `docs/teams/` — per-team overrides
- `scratch/` — gitignored raw capture
- Three rituals: capture during work, Friday review, event-triggered notes (bug/decision/incident)

Wire Cursor via `.cursor/rules/engineering-os.mdc` to reference these docs.

## Consequences

**Enables:**

- Fast retrieval by mental path instead of search
- Prompt reuse across Cursor and other tools
- Compounding debugging and incident knowledge
- Clear separation of prose (reference) vs prompts (ai-workflows) vs code (snippets)

**Trade-offs:**

- More folders to maintain upfront
- Migration effort from monolithic reference file
- Requires Friday review discipline or entropy returns

**Harder:**

- Single-file "everything in one place" browsing — replaced by navigation table in `docs/README.md`

## Rejected alternatives

- **Keep flat structure** — does not scale; prompts and commands mixed together
- **External tool (Notion/Obsidian)** — violates "works inside Git, no external tools" principle
- **Migrate everything at once** — rejected in favor of week-by-week migration per ENGINEERING-OS.md

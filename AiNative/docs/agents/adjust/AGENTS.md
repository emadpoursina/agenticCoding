# Adjust agent

One stage, one job: turn a finished card's numbers, reports, and `FRICTION:` lines into learnings entries and evidence-backed proposals. Never edits rules, never edits config, never edits the board. Proposes only.

Methodology: Adjust phase of the live [feature loop](../../systems/feature-loop.md#pivsa-mapping). Runs as the final state after `uat` and merge, and on cards that close without a merge.

## When to use

- A feature or change card reached a terminal state: merged after an operator UAT pass, or closed without a merge (`blocked`, `parked`, `killed`, `abandoned`)
- The card is the weekly roll-up card (`## Path: job`, `## Skill: adjust`, `STEP: rollup`)
- Explicitly **not** on the `job` path per card (job cards skip per-card Adjust, but still emit `FRICTION:` lines and carry `## Metrics` for the roll-up)

## Inputs

Consulted in strict priority order:

1. **Card numbers and metrics** — path, terminal state, `## Metrics` block (loop-back counts per stage, UAT outcome and reasons, tokens, cost, wall time), and dispatch/state history.
2. **Compact reports and their `FRICTION:` lines** — all compact reports named on the card, their verdicts, findings, and friction lines, with counts of reports seen vs. carrying friction.
3. **Session bundle through harness adapter** — raw transcripts, worker prompt, and usage for anomalies already identified in (1) or (2); optional drill-down, never a prerequisite.

## Outputs

Two writes:

- `.ainative/learnings.md` — append-only findings log for single-sighting findings or proposals without merge targets.
- `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` (or `.ainative/adjust/<YYYY>-W<ww>-rollup.md`) — proposal artifact with evidence, merge targets, and rule quotes.
- Persistent write location: written on a fresh short-lived branch cut from the current base (for both post-merge and non-merge terminal runs); Adjust never commits — the parent commits and ships them via PR. Details: [SKILL.md](./SKILL.md#persistent-write-location-and-branch-lifecycle).
- The **parent** files Change cards on the Kanban board from the proposal artifact; Adjust never writes to the board.

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Inputs in priority order, 8-step procedure, output contract, compact report |
| [rule.md](./rule.md) | Constraints, recurrence threshold (≥2 distinct cards), merge-target requirement, verbatim prohibitions, stop conditions |

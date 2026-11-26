# Contract: weekly Adjust roll-up card

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-030–FR-032 | **Plan**: [../plan.md](../plan.md) (W7) | **Research**: [../research.md](../research.md) (D2)

The cross-card aggregation. It is **a card**, not an in-process step: visible on
the board, skippable, and run by the same `adjust` skill in `STEP: rollup` mode.

---

## Scheduling

| Aspect | Rule |
|---|---|
| Cadence | One card per **ISO-8601 week** (Mon 00:00 → Sun 23:59 **UTC**), filed no later than the first business day after the week closes |
| Week key | `YYYY-Www` (e.g. `2026-W48`) |
| Owner | The **control plane** (Hermes parent) files the card. AiNative defines the cadence and the shape; the scheduler is the harness's business |
| Routing | Card carries `## Path: job`, `## Skill: adjust`, `STEP: rollup`, `week: <YYYY-Www>` |
| Skip | The operator may skip or delete the card. Nothing else in the loop changes; dependent cards are unaffected |
| Missing week | The next roll-up reports the skipped week in `gaps:`. No back-fill, no catch-up run |

**Week membership**: a card belongs to the week its `## Metrics` `closed_at`
falls in (see `contracts/metrics-block.md`) — not the week Adjust ran, not the
week the PR opened. A late or resumed Adjust run never moves a card between
weeks, and no card is counted twice.

---

## Card body

```markdown
## Path
job

## Skill
adjust

## Step
rollup

## Week
2026-W48

## Inputs
- per-card Adjust artifacts: .ainative/adjust/2026-11-2*-<card>.md
- card metrics: ## Metrics blocks with closed_at in 2026-11-23T00:00Z .. 2026-11-29T23:59:59Z
- learnings log: .ainative/learnings.md

## Output
- artifact: .ainative/adjust/2026-W48-rollup.md
- proposals: as per-card runs (same shape, same rules)

## Done
- ranking printed with counts; recurring-unaccepted listed; gaps listed
```

---

## Artifact

```markdown
# Adjust roll-up — 2026-W48

- inputs: <n> Adjust runs, <m> cards with metrics (paths: feature <a>, change <b>, job <c>)
- week: 2026-W48 (2026-11-23T00:00Z .. 2026-11-29T23:59:59Z)

## Friction by target

| # | target class | target ref | observations | cards | proposals |
|---|---|---|---|---|---|
| 1 | ainative | skill:tester | 7 | 5 | P1 |
| 2 | harness | harness:claude-harness | 3 | 2 | — |

## Recurring, not accepted

| finding key | first week | weeks seen | change card | state |
|---|---|---|---|---|
| ainative/skill:critic/proof-type-gap | 2026-W45 | W45, W46, W47, W48 | 0437 | pending |

## Stage numbers

| path | converge | critic | tester | pr_review | uat fail share |
|---|---|---|---|---|---|
| feature | 1.4 (n=7) | 0.9 (n=7) | 1.1 (n=7) | 0.3 (n=7) | 2/7 |
| change | n/a | n/a | 0.6 (n=5) | 0.2 (n=5) | 1/5 |

## Gaps

- 2026-W46 had no roll-up card (skipped)
- 3 cards predate FRICTION lines: absence treated as unknown, not as clean
- cost_usd unknown on 4 of 12 cards (provider does not report it)

## P1 — <short title>
<same proposal block as a per-card run>
```

### Rules

| Rule | Detail |
|---|---|
| Ranking counts visible | Every ranking line prints the observation count and the distinct-card count behind it (FR-031) |
| Recurring proposals | A proposal seen in an earlier week whose Change card is not approved is listed once in `Recurring, not accepted` — the roll-up never files a second identical card |
| Sample sizes | Every stage number carries `n=`; `n/a` stages are excluded from the sample, not averaged as zero |
| Empty week | If the week produced no Adjust runs, the ranking is empty and `Gaps` says so explicitly. No findings are invented (FR-032) |
| Evidence gap ≠ clean | Missing `FRICTION` lines, `unknown` metrics, and skipped weeks are all reported under `Gaps` |
| Proposals | Same shape and same rejection rules as per-card proposals (`contracts/proposal-artifact.md`); the ≥2-distinct-cards threshold still applies, and cross-week recurrence counts as distinct cards |
| Never gating | The roll-up cannot block, delay, or reorder any other card, and has no state that any card depends on |

---

## Failure and stop conditions

| Condition | Behaviour |
|---|---|
| No inputs at all | `ADJUST: no-findings` with an evidence-gap `SUMMARY`; no artifact proposals |
| Only one card in the week | Roll-up still runs; ranking has one line; `Gaps` notes the small sample |
| Metrics missing on most cards | Run on the Adjust artifacts that exist; state the coverage in `Gaps` |
| Card not routed `job`/`STEP: rollup` | Not a roll-up; the per-card procedure applies instead |

---

## Acceptance (checked by TF-8)

- Cadence, week boundary (ISO, UTC), anchor (`closed_at`), and scheduling owner
  are stated in `feature-loop.md` § Weekly Adjust roll-up.
- The roll-up shape has **one home**: `feature-loop.md` § Weekly Adjust roll-up
  (plan W7). This file is the wire-format reference for that statement, exactly
  as `contracts/metrics-block.md` is for the `## Metrics` block — the loop
  document states the shape and **links** here rather than restating it, so the
  shape never lives in two places. If an implementer needs the artifact template
  in the skill folder instead, the loop doc links there and this file keeps only
  the rules (counts visible, recurring-unaccepted, gaps).
- Skipping and empty weeks have stated behaviours that never touch other cards.

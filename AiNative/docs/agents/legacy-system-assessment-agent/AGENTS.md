# Legacy system assessment agent

Evidence-backed assessment of a legacy system before significant engineering investment — structure, condition, risks, modernization strategies, work packages, and effort/time/AI-cost estimates with explicit uncertainty. Compiles evidence into decision support; never a universal quality score.

This file is the agent's instruction surface in the open [AGENTS.md](https://agents.md/) format — standard Markdown, no required fields. Coding agents load the nearest `AGENTS.md`; keep this file the place for role, triggers, and I/O.

## When to use

- Deciding whether to refactor, incrementally replace, rewrite, replatform, or retain a legacy system
- Taking ownership of an unfamiliar/undocumented codebase and needing structure, risks, and changeability
- Scoping modernization work — what each viable strategy requires, what it costs, how long it takes
- Needing AI-execution suitability and token/cost estimates for a migration before committing budget
- Any "should we rewrite this?" discussion that currently runs on opinion instead of evidence

## Inputs

- Path to the system under assessment (repo root; multi-repo roots if applicable)
- What decision the assessment supports (e.g. "refactor vs rewrite billing service in Q4")
- Available evidence sources (or lack thereof): Git history, runtime/prod access, DB/migrations, docs, observability, owners
- Optional: known constraints (deadlines, vendor options, no-rewrite policy, compliance)

## Outputs

- `legacy-system-assessment.md` — 19-section final report (see [workflow.md](./workflow.md#final-report))
- Durable artifacts per DAG stage: `assessment-boundary`, `repo-profile`, evidence analyses, `contradictions`, `changeability`, `risk-register`, `change-scenarios`, `investigation-gate`, strategies, `work-packages`, `estimates`
- Every major conclusion traceable as conclusion → finding → evidence → source; every estimate as estimate → work package → finding → evidence → assumptions

## Stages

| Stage | DAG id | Workers | Produces |
|-------|--------|---------|----------|
| 0 — Boundary | `boundary` | orchestrator | `assessment-boundary` |
| 1 — Reconnaissance | `recon` | `repo-scout` | `repo-profile` |
| 2 — Evidence (parallel) | `evidence` | `static-analyst`, `architecture-analyst`, `history-analyst`, `system-understanding-analyst`, `behavior-test-analyst` | 5 analysis artifacts |
| 3 — Reconciliation | `reconcile` | `contradiction-reconciler` | `contradictions` |
| 4 — System (parallel) | `system` | `changeability-analyst`, `risk-analyst` | `changeability`, `risk-register` |
| 5 — Scenarios | `scenarios` | `change-scenario-selector` | `change-scenarios` |
| 6 — Gate | `gate` | orchestrator | `investigation-gate` (STOP/CONTINUE) |
| 7 — Strategies (parallel) | `strategies` | `refactor-`, `incremental-replacement-`, `rewrite-strategy-planner` (+ optional retain/rearchitect/replatform/vendor) | 3+ strategy assessments |
| 8 — Work breakdown | `breakdown` | `work-breakdown-planner` | `work-packages` |
| 9 — Estimation | `estimates` | `estimator` | `estimates` (effort, calendar, AI execution, token/cost) |
| 10 — Synthesis | `synthesis` | `evidence-synthesizer` | `final-assessment` → `legacy-system-assessment.md` |

Execution contract: [dag.json](./dag.json). Orchestrator mechanics: [orchestrator.md](./orchestrator.md).

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | How to run the assessment — operating model, dispatch guide, estimate dimensions (`name` + `description` frontmatter) |
| [rule.md](./rule.md) | Constraints and stop conditions specific to this agent |
| [workflow.md](./workflow.md) | Stage definitions — **what** each stage means (Stages 0–10, final report structure, completion criteria) |
| [methodology.md](./methodology.md) | Worker methodology — evidence/finding models, hierarchy, analysis techniques (§§1–27) |
| [orchestrator.md](./orchestrator.md) | **How** the orchestrator executes `dag.json` — registry, retries, failure handling, cost accounting |
| [workers.md](./workers.md) | Binding worker contracts — consumes/produces per worker |
| [schemas.md](./schemas.md) | Field contracts for every durable artifact (`EVID-`/`FIND-`/`CONTR-`/`WP-` IDs) |
| [dag.json](./dag.json) | Executable DAG — stage order, dependencies, parallel groups, required workers |
| [tests/](./tests/) | Static contract tests (`python3 -m unittest discover -s tests`) |

## Quick start

```text
/legacy-system-assessment-agent Assess <path-to-system> for <decision>.
Available: <git history / runtime / DB / docs / observability>.
Unavailable: <what you know is missing>.
```

The agent establishes the assessment boundary first (Stage 0), profiles the repo (Stage 1), then fans out evidence workers in parallel. It stops investigating when further evidence is unlikely to change strategy, risk, work breakdown, estimates, or confidence — sufficiently supported decision information over exhaustive archaeology.

## Cursor Command

Pair this agent with `/legacy-system-assessment-agent` at `.cursor/commands/legacy-system-assessment-agent.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).

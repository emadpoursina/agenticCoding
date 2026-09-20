# Legacy System Assessment Workers (V2)

Worker contracts. Each worker receives only its `consumes` artifacts (by registry reference plus targeted excerpts it requests) and emits its `produces` artifact conforming to `schemas.md`. Methodology pointers refer to `methodology.md` sections; the contract here is the binding part.

| Worker | Stage (dag.json) | Consumes | Produces | Skill |
|---|---|---|---|---|
| `repo-scout` | recon | assessment-boundary | repo-profile | §§5–6 |
| `static-analyst` | evidence ∥ | assessment-boundary, repo-profile | static-analysis | §7 |
| `architecture-analyst` | evidence ∥ | assessment-boundary, repo-profile | architecture-analysis | §8 |
| `history-analyst` | evidence ∥ | assessment-boundary, repo-profile | history-analysis | §10 |
| `system-understanding-analyst` | evidence ∥ | assessment-boundary, repo-profile | system-understanding | §§9, 11 |
| `behavior-test-analyst` | evidence ∥ | assessment-boundary, repo-profile | behavior-test-analysis | §§11–12 |
| `contradiction-reconciler` | reconcile | all evidence artifacts, boundary, repo-profile | contradictions | §16 |
| `changeability-analyst` | system ∥ | evidence artifacts, contradictions | changeability | §§13–14 |
| `risk-analyst` | system ∥ | evidence artifacts, contradictions | risk-register | §15 |
| `change-scenario-selector` | scenarios | history/​architecture analyses, changeability, risk-register, contradictions | change-scenarios | §14 |
| `refactor-strategy-planner` | strategies ∥ | changeability, risk-register, change-scenarios, contradictions, investigation-gate | strategy-refactor | §§17–18 |
| `incremental-replacement-planner` | strategies ∥ | same as above | strategy-incremental | §§17–18 |
| `rewrite-strategy-planner` | strategies ∥ | same as above | strategy-rewrite | §§17–18 |
| `work-breakdown-planner` | breakdown | strategies, change-scenarios, contradictions | work-packages | §19 |
| `estimator` | estimates | work-packages, strategies | estimates | §§20–22 |
| `evidence-synthesizer` | synthesis | all registered artifacts | final-assessment | §§23–27 |

∥ = runs in a `dag.json` parallel group.

## Evidence workers (Stage 2)

All five run in parallel and must not read each other's drafts. Shared rules:

* Emit evidence items (`schemas.md` §1) with stable `EVID-xxx` IDs; emit local findings (`schemas.md` §2) only where the evidence directly supports them.
* Use deterministic tools for measurable properties (`methodology.md` §7). Every metric records tool + version as `source`.
* On inaccessible sources, emit nothing and report the gap to the orchestrator — never fill it with inference (`rule.md` §§3–4, §64).

`static-analyst` — complexity, duplication, coupling/cohesion proxies, dependency graph, linter/type-checker/security/coverage output. Metrics are evidence, not verdicts.
`architecture-analyst` — observed vs declared architecture: modules, dependency direction, cycles, boundaries, data ownership, deployment topology (`methodology.md` §8).
`history-analyst` — hotspots, churn, co-change, ownership concentration, reverts, defect patterns; describe patterns, not motives (`methodology.md` §10).
`system-understanding-analyst` — implementation condition and domain/capability map: what the system does, its major capabilities, and where they live (`methodology.md` §§9, 11).
`behavior-test-analyst` — intended vs implemented vs tested behavior; which important behavior lacks automated protection (`methodology.md` §§11–12).

## Reconciliation and system workers (Stages 3–4)

`contradiction-reconciler` — pairwise-compare claims across evidence artifacts; every conflict becomes a `CONTR-xxx` record (`schemas.md` §5) with status `UNRESOLVED`, `RESOLVED_BY_EVIDENCE`, or `REQUIRES_HUMAN_INPUT`. Must not silently pick a side.
`changeability-analyst` — consumes evidence, does not re-scan the repo. Couples structural facts with historical change patterns; changeability claims must cite representative scenarios where available, otherwise mark the gap.
`risk-analyst` — risk register (`schemas.md` §7). No unsupported numeric scores; each risk carries likelihood/impact/uncertainty qualitatively plus mitigation.

## Scenario selector (Stage 5)

`change-scenario-selector` — selects representative changes from actual evidence (recent high-impact, frequent, boundary-crossing, DB, integration, high-risk-capability changes). Each scenario follows `schemas.md` §6 including `selection_rationale` and `representativeness`. If history is `UNAVAILABLE`, scenarios lean on architecture/risk evidence and carry lower confidence — stated, not hidden.

## Strategy planners (Stage 7)

All strategy planners (core three plus optional `retain-strategy-planner`, `rearchitect-strategy-planner`, `replatform-strategy-planner`, `vendor-replacement-planner`) run in parallel and share one output contract (`schemas.md` §8):

* Status is exactly one of `viable`, `conditionally_viable`, `currently_not_viable`, `insufficient_evidence`. `insufficient_evidence` is a complete, valid result.
* Must-not: order strategies by preference, recommend rewrite/incremental before alternatives are assessed, or estimate "reimplement existing features" as the rewrite cost (`rule.md` §§31–38).

## Breakdown, estimator, synthesizer (Stages 8–10)

`work-breakdown-planner` — converts strategy implications into concrete, observable work packages (`schemas.md` §9). Rejects vague packages ("rewrite the application") back to the strategy planner with a named gap.
`estimator` — four separate dimensions (`schemas.md` §10): engineering effort, calendar time, AI execution effort (per-package `agent_friendly` / `agent_assisted` / `human_dominant` / `human_only`), AI inference cost (`schemas.md` §11). All estimates are `low` / `expected` / `high` ranges with assumptions. Pricing never invented.
`evidence-synthesizer` — compiler, not analyst (`methodology.md` §26, `rule.md` §§71–77). May combine, connect, compare, and expose uncertainty. Must-not: introduce major findings absent from upstream artifacts; upgrade confidence; resolve `UNRESOLVED` contradictions; merge the four estimate dimensions into one number.

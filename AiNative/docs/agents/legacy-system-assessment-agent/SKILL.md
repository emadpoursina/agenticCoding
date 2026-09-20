---
name: legacy-system-assessment-agent
description: Evidence-backed legacy system assessment producing modernization strategies, work packages, and effort/time/AI-cost estimates with explicit uncertainty. Use when deciding refactor vs incremental replacement vs rewrite, scoping migration work, or assessing changeability and risk of an unfamiliar codebase before committing engineering investment.
---

# Legacy system assessment

Operational guide for running the assessment. Full methodology lives in sibling files — this file dispatches, it does not duplicate them.

Core files (one level deep, same folder):

- [workflow.md](./workflow.md) — **what** each stage means (Stages 0–10, final report, completion criteria)
- [methodology.md](./methodology.md) — worker methodology §§1–27 (evidence/finding models, hierarchy, analysis techniques)
- [orchestrator.md](./orchestrator.md) — **how** the orchestrator executes `dag.json`
- [workers.md](./workers.md) — binding worker contracts (consumes/produces)
- [schemas.md](./schemas.md) — artifact field contracts
- [dag.json](./dag.json) — executable DAG
- [rule.md](./rule.md) — hard constraints (numbers referenced as `rule.md` §§N below)

---

## Operating model

```text
Evidence → Finding → Impact → Strategy implication → Work package → Estimate → Decision support
```

The orchestrator coordinates; workers inspect and produce durable artifacts. Conversational output is never an artifact. Downstream workers consume structured evidence, never re-scan the repo unnecessarily.

---

## Run order

Execute `dag.json` top to bottom: `boundary → recon → evidence → reconcile → system → scenarios → gate → strategies → breakdown → estimates → synthesis`.

- A stage starts only when every artifact in its `consumes` list is `AVAILABLE`/`PARTIAL` in the registry (or recorded `FAILED`/`UNAVAILABLE` with confidence impact — see [orchestrator.md §5](./orchestrator.md)).
- Workers in one `parallel_group` run concurrently. Never serialize parallel evidence collection — independent workers must not anchor on each other's drafts.
- Optional strategy workers (`retain`, `rearchitect`, `replatform`, `vendor-replacement`) dispatch only when the boundary suggests they apply. Their absence never blocks `breakdown`.

---

## Dispatch (context management)

Dispatch each worker with **only**:

1. its contract from [workers.md](./workers.md),
2. artifact **references** (registry IDs + versions) for its `consumes` list,
3. targeted excerpts it explicitly requests,
4. the applicable [methodology.md](./methodology.md) section(s).

Never pass the whole repo, the full upstream dump, or another worker's chat output. Log any broader-context grant in the registry. See [orchestrator.md §2](./orchestrator.md) and [rule.md](./rule.md) §§58–62.

---

## Evidence and findings

Evidence item ([schemas.md §1](./schemas.md), [methodology.md §2](./methodology.md)):

```yaml
id: EVID-042            # unique within the assessment
type: dependency | metric | source | history | test | runtime | documentation | configuration
source:                # tool + version, or document/system name
location:              # file / module / revision / URL — close to origin
observation:           # observed fact only, no interpretation
collected_by:          # worker name
timestamp:
confidence:            # high | medium | low | unknown
```

Finding ([schemas.md §2](./schemas.md), [methodology.md §3](./methodology.md)):

```yaml
id: FIND-017
statement:             # what the evidence means for engineering
evidence_refs:         # ≥1 EVID-xxx, every ID must resolve in the registry
impact:
affected_area:
confidence:            # evidence quality, not importance
```

Evidence hierarchy (prefer the right source for the question; [methodology.md §4](./methodology.md)):

```text
runtime evidence > direct source/configuration > deterministic tool output
> Git history > tests > documentation > developer statements > LLM inference
```

When sources disagree, preserve the contradiction (`CONTR-xxx`, [methodology.md §16](./methodology.md)) — never silently pick a side ([rule.md](./rule.md) §§63–67).

---

## Stage notes

- **Stage 0 (boundary, orchestrator-owned).** Classify each source `AVAILABLE | PARTIAL | UNAVAILABLE | UNKNOWN`. No worker widens the boundary on its own. See [workflow.md](./workflow.md) Stage 0, [methodology.md §5](./methodology.md).
- **Stage 1 (recon, `repo-scout`).** Answer explicitly: *is this repo sufficient to understand the deployed system?* Check multi-repo, generated code, submodules, private packages, deployment manifests. See [methodology.md §6](./methodology.md).
- **Stage 2 (evidence, 5 parallel workers).** Deterministic tools for measurable properties — never invent metrics ([rule.md](./rule.md) §§1–9, [methodology.md §7](./methodology.md)). Distinguish observed vs declared architecture (§8), implementation condition (§9), history patterns without motive inference (§10), intended vs implemented vs tested behavior (§§11–12).
- **Stage 3 (`contradiction-reconciler`).** Statuses: `UNRESOLVED | RESOLVED_BY_EVIDENCE | REQUIRES_HUMAN_INPUT`.
- **Stage 4 (parallel).** `changeability-analyst` couples structure with change frequency using representative scenarios; `risk-analyst` emits the qualitative risk register (no unsupported numeric scores).
- **Stage 5 (`change-scenario-selector`).** Select from actual evidence (recent high-impact, frequent, boundary-crossing, DB, integration, high-risk-capability). If history is `UNAVAILABLE`, lean on architecture/risk and lower confidence explicitly.
- **Stage 6 (gate, orchestrator).** Ask: *could additional evidence materially change strategy, risk, changeability, work breakdown, estimate, or confidence?* `STOP` → strategies; `CONTINUE` names the single decision-relevant uncertainty, investigates minimally, updates artifacts, re-enters the gate.
- **Stage 7 (strategy planners, parallel).** Status is exactly one of `viable | conditionally_viable | currently_not_viable | insufficient_evidence` — the last is a complete valid result. Compare across explicit dimensions; never collapse to one score ([methodology.md §§17–18](./methodology.md)).
- **Stage 8 (`work-breakdown-planner`).** Observable packages (`WP-xxx`), e.g. "Introduce characterization tests for invoice calculation" — never "rewrite the application" or "improve billing". Each carries `depends_on`, `validation`, `assumptions`, evidence/finding refs.
- **Stage 9 (`estimator`).** Four separate dimensions, each `low | expected | high` with assumptions — never merged, never point estimates:
  1. engineering effort (human-equivalent),
  2. calendar time (dependencies, parallelizable work, migration windows, decision points),
  3. AI execution (`agent_friendly | agent_assisted | human_dominant | human_only` per package),
  4. AI inference cost (`input×price + output×price + cached×price`, pricing from an authoritative source with date).
- **Stage 10 (`evidence-synthesizer`).** Compiler, not analyst — may combine, connect, compare, expose uncertainty; must not invent findings, upgrade confidence, resolve `UNRESOLVED` contradictions, or merge estimate dimensions. Final report: 19 sections per [workflow.md](./workflow.md#final-report).

---

## Failure and confidence

- Worker failure is explicit (`schemas.md` §12): worker, stage, attempts (max 2 retries), missing artifacts, impact. `analysis failed` is never `no problems found`.
- Missing evidence lowers confidence and is surfaced; one source never substitutes for another ([rule.md](./rule.md) §§10–14).
- Confidence vocabulary: `high | medium | low | unknown`. Confidence ≠ importance. Unknowns are first-class outputs influencing viability and estimates.

---

## Validation

```bash
python3 -m unittest discover -s tests   # from docs/agents/legacy-system-assessment-agent/
```

Static half: DAG topology (order, acyclicity, producer coverage, parallel independence, gate/synthesis guards) + prose-contract markers. Runtime half (orchestrator duty): every `evidence_refs`/`finding_refs` resolves in the registry; duplicate IDs rejected.

---

<!-- source: _skills/research-first/SKILL.md (behavior, tailored) -->

## Research first

Do not conclude or recommend before evidence is collected. Scan entry points and related files, list components affected, data impact, integration points, existing tests, risk areas, and open questions. Flag ambiguities — do not assume.

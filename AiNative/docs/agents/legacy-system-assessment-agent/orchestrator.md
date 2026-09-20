# Legacy System Assessment Orchestrator (V2)

Companion to `workflow.md`. `workflow.md` defines **what** each stage means; this file defines **how** the orchestrator executes the DAG in `dag.json`. Methodology lives in `methodology.md`; hard constraints live in `rule.md`.

## 1. Execution order

Execute `dag.json` stages top to bottom: `boundary → recon → evidence → reconcile → system → scenarios → gate → strategies → breakdown → estimates → synthesis`.

* A stage starts only when every artifact in its `consumes` list is present in the registry (or recorded as failed/unavailable — see §5).
* Workers inside one `parallel_group` run concurrently. Never serialize them to "save coordination effort": parallel evidence collection is a correctness requirement (independent workers must not anchor on each other's drafts).
* Optional strategy workers (`optional_workers` in `dag.json`) are dispatched only when the assessment boundary suggests they apply (e.g. a credible vendor alternative exists). Their absence must not block `breakdown`.

## 2. Worker dispatch (context management)

Dispatch each worker with **only**:

1. its worker contract from `workers.md` (role, consumes, produces, must-not),
2. artifact **references** (registry IDs + versions) for its `consumes` list,
3. targeted excerpts or specific evidence items it explicitly requests,
4. the applicable `methodology.md` section(s).

Never pass the whole repository, the full upstream artifact dump, or another worker's conversational output. If a worker asks for broader context, grant the smallest superset that unblocks it and log the grant in the registry.

## 3. Artifact registry

The registry is the system's durable memory. For every artifact record:

```yaml
id:            # e.g. static-analysis
version:
produced_by:
stage:
status: AVAILABLE | PARTIAL | FAILED | SKIPPED
evidence_ids:  # EVID-xxx contained or referenced
finding_ids:   # FIND-xxx contained or referenced
location:      # where the artifact is stored
```

* IDs `EVID-xxx`, `FIND-xxx`, `CONTR-xxx`, `WP-xxx` must be unique within an assessment. Reject duplicates.
* Every finding referenced downstream must resolve to a finding in a registered artifact. Dangling `evidence_refs` / `finding_refs` fail validation (see `tests/test_v2_contracts.py` for the static DAG half; runtime reference checks run the same rule against the registry).
* Conversational summaries are not artifacts and must never satisfy a `consumes` dependency.

## 4. Retries

* Retry a failed worker at most twice with narrowed context before marking the artifact `FAILED` or `PARTIAL`.
* Record every attempt (worker, stage, attempt number, failure reason) in the failure record — schema in `schemas.md` §12.
* A `FAILED` artifact unblocks downstream stages only via §5; it never silently becomes "no problem found".

## 5. Failure and missing-evidence handling

* If a `consumes` artifact is `FAILED` or an evidence source is `UNAVAILABLE` in `assessment-boundary`, the orchestrator:
  1. lets the downstream worker run on the remaining evidence,
  2. requires the worker to lower confidence accordingly,
  3. records the gap in the registry with its impact on confidence.
* Never substitute one evidence source for another (e.g. documentation standing in for missing runtime behavior). `rule.md` §§10–14.

## 6. Assessment boundary and stopping gate

* `boundary` (Stage 0) runs first and is owned by the orchestrator — no worker may widen the boundary on its own. If a worker discovers the boundary is wrong (e.g. a second repository exists), it reports back; the orchestrator updates `assessment-boundary` and re-dispatches affected stages.
* `gate` (Stage 6) applies the minimum-sufficient-investigation question from `dag.json` (`stopping_question`). `STOP` proceeds to `strategies`; `CONTINUE` must name the single decision-relevant uncertainty being investigated, dispatch the smallest targeted re-investigation, update artifacts, and re-enter the gate. Looping without a named uncertainty is forbidden.

## 7. Token / cost accounting

Per worker invocation record (schema in `schemas.md` §11):

```yaml
worker:
model:
input_tokens: / output_tokens: / cached_tokens:
iterations: / tool_calls:
```

Aggregate per stage and per assessment. Cost uses `input_tokens × input_price + output_tokens × output_price + cached_tokens × cached_price` with recorded `pricing_source` and `pricing_date`. Never invent pricing (`rule.md` §§49–52).

## 8. Synthesis coordination

`synthesis` dispatches `evidence-synthesizer` last, with registry references to all upstream artifacts. The synthesizer compiles — it must not invent major findings absent from upstream artifacts (`dag.json` `forbids`; `rule.md` §§71–77). The orchestrator validates the final report against the 19-section structure in `workflow.md` ("Final Report") and rejects it if any section is missing or if a major conclusion/estimate lacks a traceable chain (conclusion → finding → evidence → source; estimate → work package → finding → evidence → assumptions).

## 9. Completion check

The assessment is complete only when `workflow.md` "Completion Criteria" all hold **and** every registry artifact is `AVAILABLE` or `PARTIAL` (none `FAILED`-unexplained), contradictions all carry a resolution status, and estimates all carry assumptions and ranges. Otherwise report the assessment as incomplete with explicit gaps — never as a clean bill of health.

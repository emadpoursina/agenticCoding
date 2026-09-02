# Data Model: PIV Recovery

**Feature**: `006-piv-recovery` | **Date**: 2026-09-01

Extends the 005 overlay. No new database. Native Kanban retry columns are not written. Types remain frozen dataclasses in `orchestrator.py`.

## Board task (unchanged)

`BoardTask` is still read-only. Recovery MUST NOT overwrite problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, or priority.

## Failure class (closed set)

**Entity**: `failure_class`

| Value | When |
|---|---|
| `TRANSIENT` | Checks did not yield a real project-check failure (`validation=blocked`, `status=blocked`, `next_action=retry`, not cannot-start) |
| `RETRYABLE` | Declared checks ran and failed (`validation=fail`) |
| `NON_RETRYABLE` | Cannot-start (`validation=blocked` and `status=failure`), or blocked without retry, or diagnosis failure/blocked without questions |
| `HUMAN_DECISION_REQUIRED` | Non-empty questions on diagnosis, debug, or validation |

Unknown values MUST NOT be stored. MUST NOT infer class from summary prose.

## Execution state (closed set)

Previous six values remain. This phase adds:

| Value | Meaning |
|---|---|
| `RETRYABLE_FAILURE` | A retryable or transient validation failure was accepted; a recovery cycle is starting or in progress. History only — start/resume do not return this state. |
| `BLOCKED` | Automatic recovery cannot continue. Occupies the slot. Human A/B. |

`FAILED` is still terminal (abandon from blocked, or discovery/planning/original-implementation failure with no validation outcome). `PR_CREATED` is still unused.

## Phase (closed set)

Previous: `discovery`, `planning`, `implementation`, `validation`.

This phase adds overlay phases (not YAML roles):

| Value | Execute call | Default worker |
|---|---|---|
| `diagnosis` | `execute_agent(role_agents["validation"], model_slot="validation")` | tester (validation map) |
| `debug` | `execute_role("implementation")` | builder (implementation map) |

## Diagnostic report

**Entity**: `DiagnosticReport`

| Field | Type | Rules |
|---|---|---|
| `task_id` | `str` | Current task |
| `phase` | `str` | Phase that failed or that diagnosis ran against (usually `validation`) |
| `attempt` | `int` | Attempt at diagnosis time |
| `failure` | `str` | Public failure text (validation summary / class). No secrets |
| `what_was_attempted` | `str` | Short public note (e.g. diagnosis ran / debug edited copy) |
| `current_state` | `str` | Overlay state when the report was written |
| `decision_required` | `str` | Empty when none |

Not a Telegram message. Not written into `BoardTask`. Passed into debug as `ExecutePayload.validation` via a stable public serialization (joined labeled lines). MUST NOT include transcripts or env.

## Escalation brief

Reuses `DecisionBrief`. When `state==BLOCKED`:

| Field | Rule |
|---|---|
| `phase` | Current overlay phase (`validation` / `diagnosis` / `debug`) |
| `decision` | Why recovery stopped (limit vs non-retryable) |
| `why_it_matters` | Fixed: `"Recovery cannot continue without a human choice."` |
| `options` | Exactly `A` = `"Abandon"` (or equivalent abandon text), `B` = `"Retry once"` |
| `recommended` | `A` when last class is `NON_RETRYABLE`; `B` when the block is retry-limit exhaustion |
| `reply_with` | `"option letter"` |

Parked diagnosis/debug/validation questions still use the 005 park brief (`why_it_matters` = `"{phase} cannot continue without this choice."`, options from the questions list, `recommended=None`).

## Workflow record (additions)

Existing `WorkflowRecord` fields remain. Add:

| Field | Type | Rules |
|---|---|---|
| `failure_class` | `str \| None` | Last classified validation or diagnosis outcome. `None` until a class is assigned |
| `diagnostic` | `DiagnosticReport \| None` | Latest diagnosis report; `None` until diagnosis has run |

`attempt` is no longer frozen at 1: original chain `1`; increments when a recovery cycle **starts** (automatic or blocked `B`). MUST NOT increment on parked-step resume, abandon, or a new start after `FAILED`.

`decision` is set for both `HUMAN_DECISION_REQUIRED` and `BLOCKED`.

`next_action`: advancing recovery uses `diagnose` / `debug` / `validate`; on park or blocked: `reply with the option letter`; `""` on `COMPLETED`/`FAILED`.

`steps` MUST include `RETRYABLE_FAILURE` rows when a cycle starts so reviewers can see recovery without a poller.

## Recovery attempt (derived)

Not stored separately. Automatic cycles used = `attempt - 1` after recoveries that started from the original validation, except operator `B` may push `attempt` past 4. Automatic stop when three cycles have been used (`attempt` would become 5 if a fourth automatic cycle started — it must not). After three failed recoveries the record is `BLOCKED` at `attempt==4`.

## PIV-complete (predicate)

Unchanged except implementation **or debug** may have edited the isolated copy. Validation passed. Still no PR. Publish count 0.

## State transitions

```text
(005 chain) --> VALIDATING
VALIDATING + pass --> COMPLETED
VALIDATING + questions --> HUMAN_DECISION_REQUIRED
VALIDATING + RETRYABLE|TRANSIENT, budget remains --> RETRYABLE_FAILURE --> diagnosis|validate
VALIDATING + NON_RETRYABLE --> BLOCKED (attempt unchanged)
RETRYABLE_FAILURE + diagnosis questions --> HUMAN_DECISION_REQUIRED
RETRYABLE_FAILURE + diagnosis fail/blocked no questions --> BLOCKED
RETRYABLE_FAILURE + debug questions --> HUMAN_DECISION_REQUIRED
RETRYABLE_FAILURE + debug fail, budget remains --> next diagnosis cycle
RETRYABLE_FAILURE + re-validate pass --> COMPLETED
RETRYABLE_FAILURE + re-validate RETRYABLE|TRANSIENT, budget remains --> next cycle
RETRYABLE_FAILURE + third cycle still RETRYABLE|TRANSIENT --> BLOCKED (attempt 4)
HUMAN_DECISION_REQUIRED + resume letter --> re-run parked step (attempt unchanged)
BLOCKED + resume A --> FAILED (slot free)
BLOCKED + resume B --> one granted cycle (attempt increments; shape from last class)
discovery|planning|original implementation fail (no validation outcome) --> FAILED (005)
```

| Event | Slot | Attempt |
|---|---|---|
| Recovery cycle starts | occupied | +1 |
| Parked resume | occupied | unchanged |
| `BLOCKED` | occupied | unchanged at block time |
| Abandon A | released | unchanged |
| `COMPLETED` / `FAILED` | released | as recorded |
| Second start while occupied (incl. `BLOCKED` / `RETRYABLE_FAILURE`) | refuse | unchanged |
| New start after `FAILED` | new run | `1` |

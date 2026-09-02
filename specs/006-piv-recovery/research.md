# Research: PIV Recovery

**Feature**: `006-piv-recovery` | **Date**: 2026-09-01

Phase 0 resolves Technical Context against the spec, constitution, V0 plan Phase 4, the 005 orchestrator contract, and `personalAgent/src/hermes_kanban/{orchestrator,executor}.py`. No `[NEEDS CLARIFICATION]` remains.

## 1. Where recovery lives

**Decision**: Extend the existing module `personalAgent/src/hermes_kanban/orchestrator.py`. Re-export any new public types from `hermes_kanban/__init__.py`. Contract checks stay in `personalAgent/tests/test_piv_orchestrator.py` (same file; recovery is the same start/resume API). Do not add `recovery.py`, a second orchestrator, or a workflow engine.

**Rationale**: Spec: “Recovery is added to the existing orchestrator, not a second orchestrator.” Constitution II/III: reuse the package; no second control plane. 005 already owns the slot, board seam, and chain loop. Recovery is classification + a bounded loop after validation, plus two extra phase names on the same record.

**Alternatives considered**:
- `hermes_kanban/recovery.py` imported by the orchestrator — extra file for ~one loop; split only if `orchestrator.py` becomes unreadable after the diff.
- A Hermes skill/worker for retry — this phase still has no background worker.
- Re-running `implementation` instead of diagnosis→debug — forbidden (FR-001/FR-004).

## 2. Language, tooling, dependencies

**Decision**: Unchanged from 005. Python 3.12 via uv. pytest + ruff already listed. **No new runtime dependencies.** Stdlib only (`dataclasses`, `replace`, existing imports).

**Rationale**: Constitution hard constraint; spec assumption.

**Alternatives considered**: asyncio retry worker, a state-machine library — new dependency and a second scheduler.

## 3. Diagnosis and debug mapping (deferred from clarify)

**Decision**:

| Step | How it runs | Model slot | Success criterion |
|---|---|---|---|
| Diagnosis | `executor.execute_agent(role_agents["validation"], ...)` — **not** `execute_role("validation")` | Validation (`model.roles.validation`) | Agent `status=success` with empty questions. MUST NOT run project checks. MUST NOT treat `validation==pass` as success. |
| Debug | `executor.execute_role("implementation", ...)` | Implementation | Same as implementation: file writes in the isolated copy, optional local commit. |
| Re-validate | existing `execute_role("validation")` | Validation | Project declared checks, unchanged. |

`execute_agent` today uses `_assignment_slot(None) → "planning"`. That would give diagnosis the planning model. **Surgical executor change**: add optional `model_slot: str | None = None` to `execute_agent` (passed through `_execute` / `_assignment_slot`). Recovery calls `execute_agent(..., model_slot="validation")`. Default omitted `model_slot` keeps today’s planning-slot behavior so 004 tests stay valid.

`workflow_phase` on assembled context for diagnosis is `agent` (existing execute_agent path). Overlay `current_phase` is `diagnosis` / `debug` (spec), independent of that context field.

Debug payload: same board mapping as implementation, plus `ExecutePayload.validation` = diagnostic report as a short public string (task, phase, attempt, failure, what was attempted, current state, decision required). That reuses `previous_validation` on `AssembledContext`. Do not extend `ExecutePayload`.

**Rationale**: FR-013; spec assumptions; constitution II (reuse execute, do not add methodology agents).

**Alternatives considered**:
- New roles `diagnosis`/`debug` in `_ROLES` and YAML — would require methodology/config changes this spec forbids.
- Calling `execute_role("validation")` for diagnosis — would re-run checks as the success criterion (forbidden).
- Leaving diagnosis on the planning model slot — contradicts “diagnosis shares the validation model assignment.”

## 4. Classification signals (no new ExecuteResult shape)

**Decision**: Pure function `classify_validation(result: ExecuteResult) -> str` on structured fields only: `questions`, `validation`, `status`, `next_action`. Priority (FR-002/FR-003):

1. Non-empty `questions` → `HUMAN_DECISION_REQUIRED`
2. Checks cannot start → `NON_RETRYABLE`
3. `validation == "fail"` (checks ran and failed) → `RETRYABLE`
4. `validation == "blocked"` and `next_action == "retry"` → `TRANSIENT`
5. `validation == "blocked"` (empty questions, next action not retry) → `NON_RETRYABLE`

**Cannot-start encoding** (existing executor, distinguished from transient): `_run_validation` maps spawn `OSError` (including missing command) to `validation="blocked"`, `status="blocked"`. That is **cannot-start**. Classifier treats `validation=="blocked"` **and** `status=="blocked"` **and** `next_action != "retry"` as `NON_RETRYABLE`, **and** also treats spawn-cannot-start as `NON_RETRYABLE` even when `next_action=="retry"` (clarification).

To tell cannot-start-with-retry apart from TRANSIENT (blocked + retry, checks *did* start), stamp cannot-start in the executor with **`status="failure"`** and **`validation="blocked"`** (checks never ran). Transient remains `status="blocked"`, `validation="blocked"`, `next_action="retry"`.

Surgical `_run_validation` change:

```text
OSError / FileNotFoundError (command missing or cannot execute)
  → validation="blocked", status="failure"   # cannot-start → NON_RETRYABLE
nonzero returncode
  → validation="fail", status="failure"      # RETRYABLE (unchanged)
all zero
  → validation="pass", status="success"      # pass (unchanged)
```

Update `personalAgent/tests/test_agent_executor.py` case `this-binary-does-not-exist-xyz` from `(blocked, blocked)` to `(blocked, failure)`.

**TRANSIENT in production**: current `_run_validation` has no timeout (`ponytail:` already on that function). V0 does not add a timeout. Contract checks inject TRANSIENT by subclassing `AgentExecutor.execute_role` to return a replaced `ExecuteResult` (`validation="blocked"`, `status="blocked"`, `next_action="retry"`, empty questions) after the first validation. Ceiling: live runs almost never emit TRANSIENT until a later timeout exists. Upgrade: bounded subprocess timeout in `_run_validation` returning blocked/blocked + retry.

Diagnosis `failure` / `blocked` without questions → classify as `NON_RETRYABLE` and `BLOCKED` (spec edge). Diagnosis questions → park. Debug failure without questions consumes the cycle; do not skip re-validate into a fake pass; if budget remains, start another diagnosis cycle, else `BLOCKED`.

**Rationale**: Spec “no new result shape”; clarification on cannot-start vs transient; constitution II.

**Alternatives considered**:
- Infer class from summary prose — forbidden.
- New `ExecuteResult.checks_started` field — extra shape the spec said V0 does not need.
- Treating all `blocked` as TRANSIENT — would retry missing-command forever (rejected in clarify).
- Adding subprocess timeout now — extra behavior not required to prove classification if tests can inject TRANSIENT.

## 5. Overlay vs native retry fields

**Decision**: Keep the 005 in-memory `WorkflowRecord` overlay. **Do not write** native Kanban `consecutive_failures`, `max_retries`, `last_failure_error`, `block_kind`. Add overlay fields: `failure_class`, `diagnostic`, incrementing `attempt`, states `RETRYABLE_FAILURE` and `BLOCKED`. Escalation reuses `DecisionBrief` (`decision` on the record) with fixed A/B.

`ponytail:` overlay only this phase. Ceiling: restart loses blocked/parked recovery (Phase 7). Upgrade: map attempt/blocked onto native retry fields without a second task table.

**Rationale**: Spec out of scope and assumptions; constitution III.

**Alternatives considered**: Writing `kanban.db` now — live Hermes home, not hermetic, Phase 7. Sidecar JSON in the worktree — dirties the copy.

## 6. State machine and attempt budget

**Decision**: Original chain is attempt `1`. Each recovery cycle **start** (automatic or blocked `B`) increments `attempt` and writes a `RETRYABLE_FAILURE` history row, then runs the cycle. Limit **3** automatic cycles. After the third cycle still retryable/transient → `BLOCKED`, `attempt==4`. First-validation `NON_RETRYABLE` → `BLOCKED`, `attempt` stays `1`, zero diagnosis/debug.

Operator `B` grants **one** extra cycle and does **not** reset the budget. Shape by last `failure_class`: retryable → diagnosis→debug→validate; transient or non-retryable → validate only.

Wait-return states: `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`. `RETRYABLE_FAILURE` is history, not a return (no background worker).

Active slot: previous four plus `RETRYABLE_FAILURE` and `BLOCKED`. `ResumeNotParkedError` when resume is neither parked nor blocked (same type; message can say parked-or-blocked). Invalid letter on blocked stays `BLOCKED`.

**Rationale**: US2/US3, FR-006/FR-011/FR-012.

**Alternatives considered**: Returning `RETRYABLE_FAILURE` from start — would require a worker. Resetting the 3-budget on `B` — forbidden.

## 7. Validation questions (behavior change from 005)

**Decision**: Non-empty questions on **validation, diagnosis, or debug** → `_park` (`HUMAN_DECISION_REQUIRED`), not `_fail`. Original **implementation** questions still `_fail`. Resume re-runs that parked phase; validation resume then `classify_validation`. Attempt does not increment on resume.

**Rationale**: Clarify session 2026-09-01. 005 contract item “validation questions → FAILED” is replaced by this feature’s contract.

**Alternatives considered**: Keeping validation questions as FAILED — rejected in clarify.

## 8. Public API

**Decision**: Same three operations. Wait until `COMPLETED` / `FAILED` / `HUMAN_DECISION_REQUIRED` / `BLOCKED`. No new entrypoints. No new exception types required (`ResumeNotParkedError` covers resume when not parked and not blocked).

**Rationale**: Spec public names; least code.

## 9. Checks and fixtures

**Decision**: One pytest module (existing). New tests for SC-007’s seven recovery behaviors. Recover-to-complete: validation command is a script **in the isolated copy** that fails until debug writes a passing script (stand-in `files` + `commit`). Cannot-start: missing binary command. Three-cycle limit: command always `false`. Blocked A/B: same fixture. Park diagnosis/validation: stand-in `questions`. TRANSIENT: executor subclass injection (research §4). Fixture methodology already has tester + builder; do not add a debugger folder to live AiNative.

**Rationale**: FR-016, SC-007, constitution IV/V.

**Alternatives considered**: Docker e2e, live model, live `kanban.db` — forbidden for this contract.

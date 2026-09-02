# Contract: PIV Recovery (in-process)

**Feature**: `006-piv-recovery` | **Package**: `hermes_kanban.orchestrator`

Extends [005 PIV orchestrator](../../005-piv-orchestrator/contracts/piv-orchestrator.md). Same three public operations. Git hosting, Telegram, restart persistence, and a background worker remain out of contract.

Types: [data-model.md](../data-model.md). Reuse executor / workspace / registry / adapter contracts. **Surgical executor addition**: `AgentExecutor.execute_agent(..., model_slot: str | None = None)` so diagnosis can use the validation model without running project checks. Omitted `model_slot` keeps the 004 planning-slot default.

## Wait / slot

`run_workflow` / `run_next_workflow` / `resume_workflow` MUST wait until `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. They MUST NOT return `RETRYABLE_FAILURE` (that state is written into `steps` only). They MUST NOT start a background worker.

Occupied slot: `QUEUED`, `RUNNING`, `VALIDATING`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, `BLOCKED`. Second start → `WorkflowBusyError`. `COMPLETED` and `FAILED` release the slot.

## Validation outcome (replaces 005 fail-without-retry)

After `execute_role("validation")`:

- `validation=="pass"` → `COMPLETED` (PIV-complete; remaining budget unused).
- Non-empty `questions` → park (`HUMAN_DECISION_REQUIRED`). Do not classify into retry. Do not `FAILED`.
- Else classify (`classify_validation`) and follow [research.md](../research.md) §4 / §6.

Discovery, planning, and **original implementation** (no validation outcome yet) keep 005: questions on implementation → `FAILED`; failure/blocked without questions → `FAILED`; no diagnosis.

## Classification

MUST use structured `ExecuteResult` fields only. Cannot-start (command missing / cannot execute): executor `validation="blocked"` and `status="failure"` → `NON_RETRYABLE` immediately (`BLOCKED`, attempt unchanged, 0 diagnosis, 0 debug, 0 automatic retries) even if `next_action=="retry"`.

## Recovery cycle

Budget: 3 automatic cycles after the original validation. Cycle start: append `RETRYABLE_FAILURE` to `steps`, increment `attempt`, then:

- `RETRYABLE` → diagnosis then debug then `execute_role("validation")`
- `TRANSIENT` → validation only (no diagnosis, no debug, no copy edit)

After three cycles still `RETRYABLE` or `TRANSIENT` → `BLOCKED`, `attempt==4`.

Diagnosis: `execute_agent(mapped validation agent, model_slot="validation")`. Payload includes task fields plus prior validation summary. Success criterion is not project checks. Persist `DiagnosticReport` on the record. Diagnosis questions → park. Diagnosis failure/blocked without questions → `NON_RETRYABLE` → `BLOCKED`.

Debug: `execute_role("implementation")` with `payload.validation` set from the diagnostic report. May edit the isolated copy and leave a local commit. Debug questions → park. Debug failure without questions: consume the cycle; MUST still not mark validation pass; if budget remains, start another diagnosis cycle; else `BLOCKED`.

Missing working copy during recovery → visible `MissingWorkspaceError` / fail path. MUST NOT prepare a second copy. MUST NOT discard dirty files.

## Resume

**Parked** (`HUMAN_DECISION_REQUIRED`): same 005 letter protocol, now also for diagnosis/debug/validation. Re-run that phase only. Attempt unchanged. After a parked **validation** re-run, classify. After parked diagnosis, continue the cycle (debug then validate) if questions are empty. After parked debug, re-validate.

**Blocked** (`BLOCKED`): listed letters `A` / `B` (case-insensitive).

- `A` → `FAILED`, release slot, do not publish. Later start allowed (new `run_id`, attempt `1`).
- `B` → leave `BLOCKED`, increment `attempt`, run **one** granted cycle: full diagnosis→debug→validate if last class was `RETRYABLE`; **validate only** if last class was `TRANSIENT` or `NON_RETRYABLE`. Then classify. Does not restore a budget of 3.

Not parked and not blocked → `ResumeNotParkedError`. Unlisted option → `InvalidDecisionError`; stay parked or blocked; 0 publishes.

## Record

In addition to 005:

- `state` includes `RETRYABLE_FAILURE` (history) and `BLOCKED` (wait-return)
- `current_phase` may be `diagnosis` or `debug`
- `attempt` increments on recovery cycle start only
- `failure_class` set after classification
- `diagnostic` set after a successful diagnosis (and MAY remain on later steps)
- `decision` set when parked **or** blocked (blocked uses fixed A/B; recommended `A` for `NON_RETRYABLE`, `B` for limit exhaustion)
- `steps` includes `RETRYABLE_FAILURE` when a cycle starts
- secrets / transcripts absent; `BoardTask` body unchanged; `pull_request` empty; 0 publishes; methodology unread-write; enrolled location unchanged

## Isolation / stand-in

Unchanged from 005. Checks inject `ModelService` + `MemoryTaskBoard`. TRANSIENT injection MAY subclass `AgentExecutor` in tests. MUST NOT require a live model, `kanban.db`, hosting, or Telegram.

## Executor cannot-start

`AgentExecutor` `_run_validation`: spawn `OSError` (missing command / cannot execute) MUST return `validation="blocked"` and `status="failure"` so the orchestrator can apply cannot-start → `NON_RETRYABLE` even when the model sets `next_action="retry"`.

## Errors

Same table as 005. `ResumeNotParkedError` also covers resume while `BLOCKED` is **not** the issue — blocked **is** resumable. Resume when `COMPLETED`/`FAILED`/`RUNNING`/etc. still `ResumeNotParkedError`.

## Out of contract

- Push / PR / merge / deploy / `PR_CREATED`
- Writing native `consecutive_failures` / `max_retries` / `block_kind`
- Telegram
- Container restart persistence
- Recovering discovery, planning, or original implementation failures
- Adding a debugger agent to live methodology
- Operator-configurable recovery limit
- Subprocess timeout (TRANSIENT in live `_run_validation`)

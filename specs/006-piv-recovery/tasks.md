---

description: "Task list for PIV Recovery implementation"
---

# Tasks: PIV Recovery

**Input**: Design documents from `/specs/006-piv-recovery/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Requested by spec SC-007, constitution IV, and [quickstart.md](./quickstart.md). Same contract module: `personalAgent/tests/test_piv_orchestrator.py`. Update cannot-start encoding in `personalAgent/tests/test_agent_executor.py`. Stand-in `ModelService` + `MemoryTaskBoard`. TRANSIENT via `AgentExecutor` subclass. Disposable git + methodology fixtures in `tmp_path`. Tests MUST NOT require a live model, live `kanban.db`, production repo, GitHub, Telegram, or `OPENAI_API_KEY`.

**Organization**: US1 and US2 are P1; US3 is P2. US1 is the recovery loop to `COMPLETED`. US2 is classification, budget, and `BLOCKED`. US3 is escalation resume and slot occupancy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

```text
personalAgent/src/hermes_kanban/orchestrator.py
personalAgent/src/hermes_kanban/executor.py
personalAgent/src/hermes_kanban/__init__.py
personalAgent/tests/test_piv_orchestrator.py
personalAgent/tests/test_agent_executor.py
personalAgent/tests/fixtures/ainative-full/    # existing; do not add debugger
personalAgent/tests/fixtures/projects/standard/
personalAgent/config/default.yaml               # unchanged
```

Do not add `recovery.py`. Do not write native Kanban retry columns. Do not edit `ainative.py`, `projects.py`, `workspace.py`, or `docker-compose.yml` except via existing public APIs. Do not add agents to live AiNative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing control-plane layout; no new package or methodology agents.

- [X] T001 Confirm `personalAgent/config/default.yaml` keeps `projects: []`, env **names** only for model credentials, and no `kanban.db` / `$HOME` / `HERMES_HOME` path. Do not edit `personalAgent/docker-compose.yml`.
- [X] T002 [P] Confirm fixture agents `scout`, `specs-planner`, `builder`, and `tester` already exist under `personalAgent/tests/fixtures/ainative-full/docs/agents/`. Do not add a debugger folder. Do not copy fixtures into live `AiNative/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Executor seams and overlay types recovery needs. No user-story loop until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add optional `model_slot: str | None = None` to `AgentExecutor.execute_agent` in `personalAgent/src/hermes_kanban/executor.py` and thread it through `_execute` / `_assignment_slot`. Omitted `model_slot` keeps today's planning-slot default. `model_slot="validation"` uses `model.roles.validation`. Add a check in `personalAgent/tests/test_agent_executor.py` that `execute_agent` with `model_slot="validation"` does not run project checks (not `execute_role("validation")`) and uses the validation assignment.
- [X] T004 Change `_run_validation` spawn `OSError` / missing command in `personalAgent/src/hermes_kanban/executor.py` to return `validation="blocked"` and `status="failure"` (cannot-start). Update `personalAgent/tests/test_agent_executor.py` case `this-binary-does-not-exist-xyz` from `(blocked, blocked)` to `(blocked, failure)`. Nonzero returncode stays `fail`/`failure`; all-zero stays `pass`/`success`.
- [X] T005 Extend `WorkflowRecord` in `personalAgent/src/hermes_kanban/orchestrator.py` with `failure_class: str | None = None` and `diagnostic: DiagnosticReport | None = None`. Add frozen `DiagnosticReport` (`task_id`, `phase`, `attempt`, `failure`, `what_was_attempted`, `current_state`, `decision_required`). Allow `current_phase` values `diagnosis` and `debug`. Allow `state` values `RETRYABLE_FAILURE` and `BLOCKED`. Expand `_ACTIVE_STATES` to include `RETRYABLE_FAILURE` and `BLOCKED`. Re-export `DiagnosticReport` from `personalAgent/src/hermes_kanban/__init__.py`.
- [X] T006 Add `classify_validation(result: ExecuteResult) -> str` in `personalAgent/src/hermes_kanban/orchestrator.py` per FR-002/FR-003 and [research.md](./research.md) §4: questions → `HUMAN_DECISION_REQUIRED`; cannot-start (`validation=="blocked"` and `status=="failure"`) → `NON_RETRYABLE` even if `next_action=="retry"`; `validation=="fail"` → `RETRYABLE`; `validation=="blocked"` and `status=="blocked"` and `next_action=="retry"` → `TRANSIENT`; other blocked → `NON_RETRYABLE`. MUST NOT read summary prose.

**Checkpoint**: Foundation ready — diagnosis can use the validation model without running checks; cannot-start is distinguishable from transient

---

## Phase 3: User Story 1 - Recover from a validation failure and finish the chain (Priority: P1) 🎯 MVP

**Goal**: First retryable validation failure runs diagnosis → debug (isolated copy only) → re-validate and can return `COMPLETED` on the same start call.

**Independent Test**: Fixture checks fail once then pass after a debug edit in the isolated copy. Start waits through diagnosis and debug, re-runs the same declared checks, returns `COMPLETED` with validation pass. Enrolled location unchanged; 0 publishes.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [US1] Extend `personalAgent/tests/test_piv_orchestrator.py`: enroll a fixture whose validation command is a workspace script that fails until rewritten; stand-in debug (`implementation` role on the recovery pass) writes a passing script and may `commit=True`. `run_workflow` returns `COMPLETED`, `validation_status=="pass"`, `attempt==2`, diagnosis ran (`execute_agent` / tester without treating checks as diagnosis success), debug changed only the isolated copy, enrolled HEAD unchanged, 0 `git push`. `steps` includes `RETRYABLE_FAILURE` then diagnosis then debug then validation. Existing happy-path `true` command still `COMPLETED` with `attempt==1` and 0 diagnosis. Same tmp_path / stand-in / no `OPENAI_API_KEY` / no `kanban.db` rules as 005.

### Implementation for User Story 1

- [X] T008 [US1] After validation `validation=="fail"` (retryable) with unused recovery budget, in `personalAgent/src/hermes_kanban/orchestrator.py`: append `RETRYABLE_FAILURE`, increment `attempt`, run diagnosis via `execute_agent(role_agents["validation"], model_slot="validation")` with task payload plus prior validation summary, store `DiagnosticReport`, then debug via `execute_role("implementation")` with `payload.validation` set from that report, then `execute_role("validation")` again using the project's declared checks. Diagnosis MUST NOT call `execute_role("validation")`. Debug MAY edit the isolated copy. Pass → `COMPLETED`. Prepare still once at start. MUST NOT publish, merge, deploy, write methodology, or edit the enrolled location. MUST NOT start a background worker.

**Checkpoint**: User Story 1 is independently testable — recover-to-complete on the start call

---

## Phase 4: User Story 2 - Classify failures, bound retries, and block (Priority: P1)

**Goal**: Every validation failure is classified. Transient re-validates only. Non-retryable and exhausted budget go `BLOCKED`. Pre-validation failures stay `FAILED`. Validation questions park.

**Independent Test**: Always-fail checks → three recovery cycles then `BLOCKED`, `attempt==4`. Missing binary → `BLOCKED` with 0 diagnosis. Transient injection → re-validate only. Discovery/planning/implementation failure still `FAILED` attempt 1.

### Tests for User Story 2 ⚠️

- [X] T009 [US2] Extend `personalAgent/tests/test_piv_orchestrator.py`: `false` command → `RETRYABLE` and diagnosis before debug while budget remains; injected TRANSIENT (`AgentExecutor` subclass returning `validation="blocked"`, `status="blocked"`, `next_action="retry"`) → 0 diagnosis, 0 debug file edits, attempt increments; missing binary → `NON_RETRYABLE`, `BLOCKED`, attempt `1`, 0 diagnosis, 0 debug; three failed recoveries → `BLOCKED`, `attempt==4`, no fourth automatic cycle; discovery/planning/original-implementation failure (including implementation questions) still `FAILED`, attempt `1`, 0 diagnosis; validation questions → `HUMAN_DECISION_REQUIRED` not `FAILED`; task body fields unchanged; secrets absent from record/diagnostic.

### Implementation for User Story 2

- [X] T010 [US2] Wire `classify_validation` after every validation result in `personalAgent/src/hermes_kanban/orchestrator.py`. `TRANSIENT` with budget: `RETRYABLE_FAILURE`, increment attempt, re-run validation only. `NON_RETRYABLE`: `BLOCKED` immediately, no diagnosis/debug. After 3 automatic cycles still retryable/transient: `BLOCKED`, `attempt==4`. Park non-empty questions on validation (and on diagnosis/debug when those run). Keep 005 `FAILED` for discovery/planning/original implementation with no validation outcome. Set `failure_class` on the record. `next_action` for recovery: `diagnose` / `debug` / `validate`; never invent a class from prose.
- [X] T011 [US2] Handle diagnosis failure/blocked without questions as `NON_RETRYABLE` → `BLOCKED` in `personalAgent/src/hermes_kanban/orchestrator.py`. Debug failure without questions consumes the cycle; do not skip re-validate into a fake pass; if budget remains, start another diagnosis cycle; else `BLOCKED`. Missing copy during recovery fails visibly; do not prepare a second copy.

**Checkpoint**: Classification, budget, and `BLOCKED` work without human resume yet

---

## Phase 5: User Story 3 - Escalate when blocked, resume, and keep one-task-at-a-time (Priority: P2)

**Goal**: `BLOCKED` records an A/B escalation brief. Resume A abandons; B grants one cycle shaped by last class. Parked diagnosis/debug/validation resume does not increment attempt. Slot includes `BLOCKED` and `RETRYABLE_FAILURE`.

**Independent Test**: Drive to `BLOCKED`, refuse second start, resume `A` → `FAILED` then new start allowed. Retryable `B` runs diagnosis→debug→validate. Non-retryable `B` re-runs validation only. Park diagnosis questions, resume `A`, attempt unchanged.

### Tests for User Story 3 ⚠️

- [X] T012 [US3] Extend `personalAgent/tests/test_piv_orchestrator.py`: `BLOCKED` record has escalation brief with `A` abandon and `B` retry once, recommended `A` for `NON_RETRYABLE` and `B` for limit exhaustion, `reply_with` option letter, no message send; resume `A`/`a` → `FAILED`, slot free, later start allowed; retryable `B` → one full recovery cycle; non-retryable `B` → validate only (0 diagnosis, 0 debug); invalid letter → `InvalidDecisionError`, still `BLOCKED`; diagnosis/debug/validation questions park, resume listed letter re-runs that step without incrementing attempt, validation resume then classifies; second start while `BLOCKED` or `RETRYABLE_FAILURE` → `WorkflowBusyError`; resume when not parked and not blocked → `ResumeNotParkedError`.

### Implementation for User Story 3

- [X] T013 [US3] When entering `BLOCKED` in `personalAgent/src/hermes_kanban/orchestrator.py`, set `decision` to a `DecisionBrief` with fixed options `A` (Abandon) and `B` (Retry once), `why_it_matters="Recovery cannot continue without a human choice."`, recommended `A` if last class `NON_RETRYABLE` else `B`, `next_action="reply with the option letter"`. Do not send a message. Slot stays occupied.
- [X] T014 [US3] Extend `resume_workflow` in `personalAgent/src/hermes_kanban/orchestrator.py`: parked diagnosis/debug/validation re-run that phase (attempt unchanged); after validation re-run, classify. Blocked `A` → `FAILED`, release slot. Blocked `B` → increment attempt, one granted cycle (full if last class retryable; validate-only if transient or non-retryable). Wait until `COMPLETED` / `FAILED` / `HUMAN_DECISION_REQUIRED` / `BLOCKED`. Unlisted option → `InvalidDecisionError` (stay parked/blocked). Neither parked nor blocked → `ResumeNotParkedError`. `_ACTIVE_STATES` already includes `BLOCKED` and `RETRYABLE_FAILURE` (T005).

**Checkpoint**: All three user stories independently functional. Stop — do not start GitHub hosting or Telegram

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: SC-007, existing packages green, no silent production targeting

- [X] T015 Keep existing checks green from `personalAgent/`: `uv run pytest tests/test_import.py tests/test_ainative_adapter.py tests/test_project_registry.py tests/test_workspace_manager.py tests/test_agent_executor.py tests/test_piv_orchestrator.py` and `uv run ruff check src tests`.
- [X] T016 Confirm `personalAgent/config/default.yaml` still has `projects: []`; no live model literals; no host-specific path; this diff does not write `kanban.db` retry columns; no new dependency in `personalAgent/pyproject.toml`; no agents added to live AiNative; no `git push` from production modules.
- [X] T017 [P] Stop after recovery contract checks pass. Do not start GitHub push/PR, Telegram, restart persistence, or adding agents to live methodology. Do not change `personalAgent/docker-compose.yml`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Immediate
- **Foundational (Phase 2)**: Blocks all user stories
- **User Story 1 (Phase 3)**: Recovery loop to `COMPLETED` — MVP
- **User Story 2 (Phase 4)**: Classification + budget + `BLOCKED`
- **User Story 3 (Phase 5)**: Blocked A/B + park/resume during recovery
- **Polish (Phase 6)**: After stories

### User Story Dependencies

- **US1 (P1)**: After Foundational
- **US2 (P1)**: After US1 loop exists (needs diagnosis/debug execute path)
- **US3 (P2)**: After US2 `BLOCKED` exists

### Parallel Opportunities

- T001 and T002 different files
- T003/T004 share `executor.py` — sequential
- T007, T009, T012 share `test_piv_orchestrator.py` — sequential
- Orchestrator implementation tasks share `orchestrator.py` — sequential
- Single implementer; do not split the module for false parallelism

---

## Parallel Example: User Story 1

```bash
Task: "Recover-to-complete tests in personalAgent/tests/test_piv_orchestrator.py"
Task: "Diagnosis then debug then re-validate in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup + Foundational (`model_slot`, cannot-start encoding, types, `classify_validation`)
2. US1 recover-to-complete
3. STOP and VALIDATE that check

### Incremental Delivery

1. US1 → first validation fail can finish
2. US2 → cannot loop forever; cannot-start blocks immediately
3. US3 → human off-ramp with the same letter protocol

---

## Notes

- Public names stay `run_workflow`, `run_next_workflow`, `resume_workflow`
- Diagnosis = validation-mapped agent, not validation role
- Debug = implementation role + diagnostic on `payload.validation`
- Automatic budget 3; `B` is one extra cycle, not a reset
- Overlay only; `ponytail:` native retry columns later
- TRANSIENT live timeout is out of this diff; tests inject it
- Conventional Commits if the owner asks to commit

## Phase 7: Convergence

- [X] T018 Pass the last validation `ExecuteResult.summary` into diagnosis `ExecutePayload` in `personalAgent/src/hermes_kanban/orchestrator.py` (do not substitute `BoardTask.acceptance_criteria`); extend `personalAgent/tests/test_piv_orchestrator.py` so the diagnosis stand-in context includes that summary per T008 (partial)

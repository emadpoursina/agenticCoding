# QA Review: PIV Orchestrator

**Purpose**: Walk the implement/converge diff against [spec.md](./spec.md), [plan.md](./plan.md), and [quickstart.md](./quickstart.md) one step at a time.
**Created**: 2026-08-31
**Feature**: [spec.md](./spec.md)
**How we use this**: One step per turn. I show the code. You say **pass**, **fail**, or **question**. We mark the step only after you decide. `[x]` here means the reviewer accepted that slice — not that tests passed.

**In-scope files**

- `personalAgent/src/hermes_kanban/orchestrator.py`
- `personalAgent/src/hermes_kanban/__init__.py`
- `personalAgent/tests/test_piv_orchestrator.py`

**Must stay untouched** (call it out if a step drifted)

- `ainative.py`, `projects.py`, `workspace.py`, `executor.py` (reuse only)
- `personalAgent/docker-compose.yml`
- live `AiNative/` agents
- `kanban.db` / a second task table

---

## Step 1 — Surgical surface

Look at: file list, `__init__.py` re-exports, `from_config` wiring.

- [x] R001 One new production module; no `orchestration/` package split. [plan, Constitution II]
- [x] R002 Public names are `run_workflow` / `run_next_workflow` / `resume_workflow`. [FR-001, FR-002, FR-010]
- [x] R003 `from_config` builds executor once and reuses `executor.workspaces` / `executor.registry`. Missing board → `MissingTaskBoardError`. [FR-003, T006]
- [x] R004 Adapter, registry, workspace, and executor modules were not rewritten. [plan surgical edits]

## Step 2 — Types, errors, board seam

Look at: dataclasses, error classes, `TaskBoard` / `MemoryTaskBoard`.

- [x] R005 Closed states: `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`. Phases: discovery → planning → implementation → validation. [FR-006]
- [x] R006 `BoardTask` is a frozen snapshot; orchestrator does not write body, owner, reviewer, or priority. [FR-007]
- [x] R007 Distinct orchestrator errors exist; adapter/registry/workspace/executor errors still propagate. [FR-015, T003]
- [x] R008 `MemoryTaskBoard` is in-process only (`ponytail:` names the kanban.db ceiling). No second SQLite file. [FR-014, Constitution III]

## Step 3 — Named start gates (before any agent)

Look at: `run_workflow` before `_run_from`. Test: `test_start_boundary_errors`, `test_invalid_priority_stops_before_discovery`, `test_dirty_copy_is_preserved`.

- [ ] R009 Path-like / empty task id → existing `InvalidTaskIdError`. Unknown task → `UnknownTaskError`. Project mismatch → `TaskProjectMismatchError`. [FR-015]
- [ ] R010 Invalid/missing priority → `InvalidPriorityError` before discovery. Unmet deps → `UnmetDependenciesError` before discovery. [FR-001, FR-003]
- [ ] R011 Orchestrator prepares a missing copy; dirty reuse keeps files and raises `DirtyWorkspaceError`; slot is released so a later start can succeed. [FR-003, T024]
- [ ] R012 Task fields on the execute payload come from the board (`problem` / `expected_result` / AC / priority). Start call does not take a task body. [FR-001, US1/AC6]

## Step 4 — Happy chain (US1)

Look at: `_run_from`. Test: `test_runs_board_task_in_isolated_copy_to_completion`.

- [ ] R013 Same call runs discovery → planning → implementation → validation and returns `COMPLETED`. [SC-001]
- [ ] R014 Empty questions auto-continue; `next_action` is never `wait for plan approval`. [SC-002, FR-004]
- [ ] R015 `PLAN.md` is loaded only after this run’s planning succeeds and is passed into implementation/validation — not into discovery or a planning re-run. [FR-005, T026]
- [ ] R016 Isolated copy on `feature/task-123` has plan + implementation files; enrolled HEAD is unchanged; no push. [FR-012, FR-013, SC-006]

## Step 5 — Explicit state and fail-without-retry (US2)

Look at: `_append` / `_fail` / `_complete`. Tests: `test_state_history_and_validation_failure_stop_without_retry`, `test_questions_in_implementation_fail`.

- [ ] R017 Record includes workflow name, phase, worker, attempt `1`, workspace path/branch, validation status, blockers, next action, empty PR slot. [FR-006, US2/AC2]
- [ ] R018 Steps history includes `QUEUED` then running phases then terminal state. [FR-006]
- [ ] R019 Validation fail → `FAILED`, `validation_status=fail`, no second implementation, attempt stays `1`, next action is not `retry`. [FR-008, SC-004]
- [ ] R020 Implementation/validation questions stop as `FAILED` (not a new park protocol). [spec assumption]

## Step 6 — Park, resume, re-park (US3)

Look at: `_park`, `resume_workflow`. Tests: `test_planning_questions_park_and_resume_with_letter`, `test_resume_reparks_without_implementing_or_incrementing_attempt`.

- [ ] R021 Non-empty discovery/planning questions → `HUMAN_DECISION_REQUIRED`; next phase has not started; options labeled A/B/C from the questions list; decision text is the step summary. [FR-009, SC-003]
- [ ] R022 Resume with listed letter (case-insensitive) re-runs the parked role with letter + option text; empty questions then auto-continue; attempt stays `1`. [FR-010]
- [ ] R023 Unknown letter, option text, or empty → `InvalidDecisionError` and the workflow stays parked. [US3/AC3]
- [ ] R024 A re-run that returns questions parks again; implementation has not started; attempt stays `1`. [US3/AC8]
- [ ] R025 Resume when not parked → `ResumeNotParkedError`. [FR-010]

## Step 7 — One slot and next-ready (US3)

Look at: `_assert_slot_free`, `run_next_workflow`. Tests: `test_reentrant_start_is_refused_while_running`, `test_next_ready_selects_priority_and_empty_board_fails`.

- [ ] R026 Second `run_workflow` / `run_next_workflow` while QUEUED/RUNNING/VALIDATING/HUMAN_DECISION_REQUIRED → `WorkflowBusyError`. [FR-011, SC-005]
- [ ] R027 `COMPLETED` / `FAILED` release the slot. Exception after claim also clears the slot. [FR-011, T024]
- [ ] R028 Next-ready skips ineligible projects, unmet deps, invalid priority; picks highest priority then oldest created across eligible projects. [FR-002]
- [ ] R029 Empty or only-unready board → `NoReadyTaskError` and no agent run. [FR-002, SC-005]

## Step 8 — Contract file vs SC-007

Look at: `personalAgent/tests/test_piv_orchestrator.py` vs [quickstart.md](./quickstart.md).

- [ ] R030 One contract module; stand-in `ModelService` + `MemoryTaskBoard`; disposable git/methodology under `tmp_path`; no `OPENAI_API_KEY`, no `kanban.db`, no live repo. [FR-014]
- [ ] R031 The seven SC-007 checks are present and would fail if the behavior broke: full chain, auto-continue, park, resume re-run, fail-without-retry, busy slot, next-ready. [SC-007]
- [ ] R032 Existing 001–004 tests are still in the regression set (`test_import`, adapter, registry, workspace, executor). [quickstart]

## Step 9 — Out of scope and leftovers

Look at: orchestrator for push/PR/Telegram/retry; config; secrets on records.

- [ ] R033 No git push, PR, merge, deploy, Telegram, background worker, or methodology write. [Out of Scope, FR-013]
- [ ] R034 No retry/debug/recovery from `FAILED`. [FR-008]
- [ ] R035 Secrets and transcripts are not fields on `WorkflowRecord` / `DecisionBrief`. [constitution, edge cases]
- [ ] R036 `ponytail:` comments remain on the in-memory board and process-local slot. [Constitution II]

---

## Session log

| Step | Verdict | Notes |
|------|---------|-------|
| 1 | pass | Surgical surface accepted |
| 2 | pass | Types, errors, board seam accepted |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |
| 9 | | |

## Notes

- Walk in order. Do not skip a fail — fix or explicitly accept the gap before the next step.
- Contract tests already passed in the implement/converge loop; this QA is a human read of the same behavior.
- After Step 9, the feature is review-complete for specified scope. Recovery, hosting, and Telegram stay later specs.

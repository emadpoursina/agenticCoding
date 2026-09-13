# Research: PIV Orchestrator

**Feature**: `005-piv-orchestrator` | **Date**: 2026-08-31

Phase 0 resolves every Technical Context choice against the spec, constitution, V0 plan §21–23 / §36–38 / Phase 3, discovery, and the live `personalAgent` tree (`ainative.py`, `projects.py`, `workspace.py`, `executor.py`). No `[NEEDS CLARIFICATION]` remains.

## 1. Where the orchestrator lives

**Decision**: One module in the existing control-plane package: `personalAgent/src/hermes_kanban/orchestrator.py`. Re-export public types from `hermes_kanban/__init__.py`. Checks in `personalAgent/tests/test_piv_orchestrator.py`.

**Rationale**: `src/hermes_kanban/` already holds the methodology adapter, project registry, workspace manager, and agent executor. Constitution III forbids a second control plane. Spec assumptions: reuse eligible-project resolve, context load, prepare/inspect, and role execute; do not duplicate Git safety, methodology loading, or model assignment. One module until the file is no longer readable — do not pre-split into state/board/selection files.

**Alternatives considered**:
- New top-level package `piv_orchestrator/` — extra install surface, unused.
- `hermes_kanban/orchestration/` package with several modules — premature; this phase is three public calls and a for-loop over four existing roles.
- A Hermes skill / gateway worker instead of this package — would skip the in-process contract later workers need, and this phase has no background worker.
- Forking Hermes dispatcher to route on `current_step_key` — forbidden (do not fork or rewrite Hermes).

## 2. Language, tooling, dependencies

**Decision**: Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff already in `[project.optional-dependencies] dev`. **No new runtime dependencies.** Stdlib: `pathlib`, `dataclasses`, `enum` (or string literals matching 004), `re`. Call existing modules; do not add httpx, pydantic, PyYAML, or a queue library.

**Rationale**: Constitution hard constraints. Spec assumption: no new third-party libraries. 004 already chose stdlib + `git` CLI + `urllib.request` for the live model path. The orchestrator adds no network of its own.

**Alternatives considered**:
- asyncio / a background thread per start — forbidden (FR-015; clarification: start and resume wait; no background worker).
- A workflow engine (Temporal, Prefect) — new dependency, a new control plane.
- Adding the orchestrator to the Hermes image — would fork Hermes.

## 3. Public operations and trust boundary

**Decision**: `PivOrchestrator` exposes exactly the spec names:

| Operation | Waits until | Success when |
|---|---|---|
| `run_workflow(project_id, task_id)` | `COMPLETED` / `FAILED` / `HUMAN_DECISION_REQUIRED` | Eligible project, known board task, valid priority, met dependencies, free slot, chain ran |
| `run_next_workflow()` | same | One ready task selected from the one board across eligible projects, then same as `run_workflow` |
| `resume_workflow(project_id, task_id, option)` | same | Slot is parked for that project+task; `option` is a listed letter (case-insensitive) |

`from_config(config_path, *, model_service=None, task_board)` builds `AgentExecutor.from_config` (live model when `model_service` omitted; checks inject a stand-in) and requires an injected `TaskBoard`. It MUST NOT guess a `kanban.db` path, `$HOME`, or `HERMES_HOME`. Missing `task_board` → `MissingTaskBoardError` at construction.

Before the first agent run, `run_workflow` MUST, in order:

1. Refuse if the single slot is occupied (`QUEUED` / `RUNNING` / `VALIDATING` / `HUMAN_DECISION_REQUIRED`) → `WorkflowBusyError`.
2. Validate `task_id` with existing path-like rules (`InvalidTaskIdError`). Empty/path-like MUST NOT be joined onto a filesystem path.
3. `registry.resolve_eligible_project(project_id)` then `load_project_context(project_id)`. Unknown / disabled / invalid location / missing project configuration → existing registry errors. MUST NOT invent a project path.
4. `task_board.get(task_id)`. Missing → `UnknownTaskError`. Task’s recorded `project_id` ≠ caller `project_id` → `TaskProjectMismatchError`.
5. Priority MUST be exactly `P0`/`P1`/`P2`/`P3`. Missing or invalid → `InvalidPriorityError` at the boundary. MUST NOT invent a priority.
6. Listed dependencies MUST all be satisfied (see §9). Unmet → `UnmetDependenciesError` at the boundary. Discovery MUST NOT start.
7. Write the operational record as `QUEUED` (attempt `1`, current phase `discovery`, next action discover, validation pending, empty PR slot, empty blockers).
8. `workspaces.prepare_workspace(project_id, task_id)` — allowed to create. Dirty reuse → existing `DirtyWorkspaceError` (MUST NOT discard dirty files). Protected work branch → existing `ProtectedBranchError`.
9. Run the chain (see §6). Update the record after every step. Return the terminal record.

`run_next_workflow` selects first (§9); if nothing ready → `NoReadyTaskError` (no agent run, no invented task id). Then the same path as `run_workflow` using the task’s recorded project identity.

`resume_workflow` MUST NOT start a new chain. Not parked, or parked for a different project+task → `ResumeNotParkedError`. Option not a listed letter (unknown, option text instead of the letter, empty) → `InvalidDecisionError`; stay parked; do not publish.

Any of those boundary failures MUST raise with that visible error, MUST NOT invent task/project/plan/validation fields, and MUST NOT start a background worker.

**Rationale**: FR-001–FR-003, FR-010, FR-015, US1/US3, clarifications on wait semantics, named-start priority, and no-ready-task.

**Alternatives considered**:
- Returning `None` / empty success when nothing is ready — forbidden (clarification: fail at the boundary).
- Requiring the caller to paste problem / expected-result / AC on start — forbidden (FR-001).
- Skipping prepare when inspect fails — forbidden (orchestrator prepares; execute still must not prepare).
- Fire-and-forget start — forbidden (no background worker this phase).

## 4. Task board seam (not a second database)

**Decision**: A `TaskBoard` Protocol is the read seam for the **one** existing board:

```text
TaskBoard.get(task_id) -> BoardTask
TaskBoard.list() -> tuple[BoardTask, ...]
```

Checks inject an in-memory fixture (`MemoryTaskBoard`) that holds structured `BoardTask` records. The orchestrator MUST NOT write the human-readable body, owner, reviewer, or priority. The orchestrator MUST NOT create `execution.db`, a second SQLite file, or a second task table.

`BoardTask` fields (source of truth for *what* to do):

| Field | Rule |
|---|---|
| `id` | Task identity. Same rules as workspace `task_id`. |
| `project_id` | Recorded project identity. Next-ready uses this; named start must match. |
| `problem`, `expected_result`, `platform`, `acceptance_criteria` | Human-readable. Orchestrator MUST NOT invent them. |
| `technical_notes`, `dependencies` | Optional. `dependencies` is a tuple of other task ids. |
| `owner`, `reviewer`, `priority` | Preserved. Priority validated at the trust boundary. |
| `created_at` | Comparable timestamp for oldest-first (fixture: ISO-8601 UTC string). |
| `complete` | Board-level done flag for **dependency** satisfaction only. Not PIV execution state. |

Live Hermes `kanban.db` is the production board (native `body` + `priority` + `assignee` + `task_links` + `project_id` + created column). A stdlib `sqlite3` reader that parses the AiNative task template headings (`## Problem`, `## Expected Result`, `## Platform`, `## Acceptance Criteria`, `## Technical Notes`, `## Dependencies`) plus owner/reviewer/priority columns is the upgrade when a Hermes worker is wired. **This phase does not implement that reader and does not open `kanban.db`.** Construction requires an injected board so checks never need a live Hermes home or a guessed DB path.

`ponytail:` fixture board in-process, not native SQLite. Ceiling: contract checks never hit `kanban.db`. Upgrade: `SqliteTaskBoard` (read-only) pointed at the isolated Hermes home by a later runtime spec — still no second task table.

**Rationale**: FR-001, FR-007, FR-014, constitution III, V0 §36–37, discovery (“structured execution-state overlay if native fields are insufficient”). Spec explicitly allows a fixture board for checks and forbids a parallel task store. 001–004 already left `kanban.db` unread so tests stay hermetic; this phase *reads* a board, so the Protocol is the minimum seam.

**Alternatives considered**:
- Writing a second SQLite `workflows.db` — forbidden.
- Parsing `kanban.db` in pytest — couples the contract to a live Hermes schema and home path; FR-014 forbids requiring a live task gateway.
- Extending `ExecutePayload` to carry the full task on `run_workflow` — the spec forbids requiring those fields on the start call.
- Mutating native Kanban `status` / card body with QUEUED/RUNNING — pollutes the human-readable card (FR-007) and confuses Hermes board columns with the PIV state machine.

## 5. Operational record: overlay now, native fields later

**Decision**: Execution state lives on an in-memory `WorkflowRecord` owned by the orchestrator instance (the V0 slot). Start/resume return that record. The record is updated after every step **before** the next agent run. It is not written into the task body.

Reuse host **field names** on the record where discovery already listed them; do not write `kanban.db` this phase (restart persistence is V0 Phase 7):

| WorkflowRecord | Native Kanban (later) | This phase |
|---|---|---|
| `project_id` | `project_id` | Set from the board task / caller |
| `workspace_path` | `workspace_path` | From prepare |
| `workspace_branch` | `branch_name` | `feature/task-<id>` from prepare |
| `workflow_name` | `workflow_template_id` | `workflow.default` (default `piv`) |
| `current_phase` | `current_step_key` | `discovery` / `planning` / `implementation` / `validation` |
| `state` | (no 1:1; native `status` is a board column) | Overlay enum only |
| `current_worker` | not assignee (owner stays on the card) | Agent that is running or last ran |
| `attempt` | not `consecutive_failures` | Always `1` |
| `validation_status` | none | `pending` until validation runs |
| `blockers` | `block_kind` is a different concept | Empty unless a step produced blockers; park uses the decision brief, not this list |
| `next_action` | none | Overlay |
| `pull_request` | none | Always empty/`None` this phase |
| `decision` | none | Overlay brief when parked |
| `run_id` | none | UUID hex per `run_workflow` / `run_next_workflow`; resume keeps it |

`ponytail:` in-memory slot, process-local. Ceiling: a container restart loses the parked brief (Phase 7). Upgrade: fill native `workspace_*` / `current_step_key` / `workflow_template_id` and persist the overlay fields Hermes cannot represent — still no second task table.

**Rationale**: Spec assumption (“native fields vs overlay is a planning choice; there is still no second task table”), V0 §38, FR-006/FR-007, constitution III. Native `status` is a Kanban column, not `QUEUED`/`RUNNING`/`VALIDATING`/`COMPLETED`/`FAILED`/`HUMAN_DECISION_REQUIRED`. Mapping those onto the card would be execution churn on the human board.

**Alternatives considered**:
- Writing `kanban.db` on every transition now — requires a live Hermes task row and couples checks to the isolated home; Phase 7 owns restart recovery.
- Sidecar JSON next to the worktree — dirties the copy (003 already rejected identity sidecars).
- Inferring state from `summary` prose — forbidden.

## 6. Chain, reuse, and payload mapping

**Decision**: After `QUEUED` + successful prepare, run existing `executor.execute_role` in this order, with **no plan-approval gate**:

```text
discovery → planning → implementation → validation
```

Each step is one existing role run. After a successful step with an empty `questions` list, the next step starts automatically on the same call.

Build `ExecutePayload` from the board task (never invented, never required on the start call):

| ExecutePayload | Source |
|---|---|
| `title` | `BoardTask.problem` |
| `description` | `BoardTask.expected_result`, plus a resume suffix when a decision was chosen (see §8) |
| `acceptance_criteria` | `BoardTask.acceptance_criteria` |
| `priority` | `BoardTask.priority` |
| `plan` | Text of `{workspace}/PLAN.md` after a successful planning step; `None` before that. MUST NOT invent a plan. |
| `validation` | Previous validation summary when present; `None` before validation. |

Owner, reviewer, platform, technical notes, and dependency ids stay on `WorkflowRecord.task`. They are not stuffed into `ExecutePayload` (004’s payload has no such slots; spec US1 scenario 6 only requires problem / expected result / AC / priority on later steps). Do **not** change `executor.py` this phase.

After planning `status=success`, the orchestrator reads `PLAN.md` from the isolated copy (path listed on `ExecuteResult.artifacts`, else `{workspace}/PLAN.md`) and passes that text into implementation and validation. Planning `status=failure` (including missing eight sections — already enforced by 004) → workflow `FAILED`, implementation MUST NOT start.

Implementation and validation `questions` in this phase are **not** a decision protocol: treat as `FAILED` (stop the chain). Only discovery and planning may park.

`execute_role` still inspects; it still MUST NOT prepare. The orchestrator prepared once at start. If the copy disappears underfoot during a later step, execute’s `MissingWorkspaceError` fails the workflow visibly. This phase MUST NOT call `prepare_workspace` a second time for the same task.

Implementation file writes and optional local commit remain the executor’s job. The orchestrator MUST NOT push, open a PR, merge, deploy, write methodology, or edit the enrolled project location.

**Rationale**: FR-003–FR-005, FR-012–FR-013, US1, 004 contract. Least code: a loop over four role names plus payload assembly.

**Alternatives considered**:
- Re-implementing model calls inside the orchestrator — duplicates 004.
- Calling `execute_agent` by hardcoded scout/specs-planner/builder/tester names — skips the configured role map.
- Extending `ExecutePayload` with `decision` / `owner` / `platform` — extra 004 surface the spec did not require; resume suffix on `description` is enough.
- Skipping discovery when the caller “already knows” — spec order is mandatory.

## 7. Execution state machine

**Decision**: Closed states (no `BLOCKED` / `RETRYABLE_FAILURE` / `PR_CREATED` this phase — those belong to recovery and hosting):

| State | When |
|---|---|
| `QUEUED` | Accepted; written before the first agent run of start/resume |
| `RUNNING` | Discovery, planning, or implementation is in progress or just finished without parking/failing |
| `VALIDATING` | Validation role is in progress |
| `COMPLETED` | Validation `status=success` and `validation=pass`. PIV-complete: isolated copy on `feature/task-<id>`, nothing published, no PR required |
| `FAILED` | Step `failure`, or `blocked` with empty questions, or implementation/validation questions, or planning success missing eight sections (already `failure` from execute). No retry, no diagnosis, no debug. Attempt stays `1` |
| `HUMAN_DECISION_REQUIRED` | Discovery or planning returned a non-empty `questions` list (questions win over `blocked`) |

Current phase is the role that is running or that just parked/failed. Current worker is that role’s mapped agent. Next action: `discover` / `plan` / `implement` / `validate` while advancing; empty on `COMPLETED`/`FAILED`; on park, “reply with the option letter”. Next action MUST NOT be `retry` or `wait for plan approval`.

The returned record SHOULD include a `steps` tuple (phase, worker, execute status, questions snapshot, summary) so checks can prove QUEUED → RUNNING through discovery/planning/implementation → VALIDATING → COMPLETED without a background poller (start waits until terminal).

**Rationale**: FR-006, FR-008, FR-012, US2, V0 Phase 3 vs Phase 4. V0 plan §26 lists extra states; this spec explicitly deferred them.

**Alternatives considered**:
- Emitting `RETRYABLE_FAILURE` / `PR_CREATED` now — out of scope; would invite retry/hosting code.
- Using `BLOCKED` as the parked state — spec’s parked state is `HUMAN_DECISION_REQUIRED`; blocked-without-questions is `FAILED`.
- Incrementing attempt on resume — forbidden (same attempt, with an answer).

## 8. Human decision: questions are options; resume re-runs

**Decision**: A non-empty `questions` tuple on discovery or planning is **one** decision. List items are mutually exclusive options labeled `A`, `B`, `C`, … in order (`chr(ord("A") + i)`). The parked step’s `summary` is the decision text. The orchestrator MUST NOT parse option strings into a different shape or invent options.

`DecisionBrief`:

- `project_id`, `task_id`, `phase`
- `decision` = that step’s summary
- `why_it_matters` = short fixed reason (`"{phase} cannot continue without this choice."`) — do not invent agent rationale
- `options` = labeled letters + the original strings
- `recommended` = `None` this phase (`ExecuteResult` has no recommended-option field; MUST NOT guess from prose)
- `reply_with` = `"option letter"` (A/B/C)

This phase MUST NOT send Telegram or any message. Parking is enough. The start/resume call returns the parked record.

Resume accepts the letter case-insensitively (`"a"` → `A`). Re-run the **same** parked role with the letter and option text available:

```text
description = expected_result + "\n\nHuman decision: {letter} — {option_text}"
```

The same suffix is included on later steps of that attempt. If the re-run’s questions list is empty, auto-continue (still no plan-approval gate). If it returns questions again, park again (same `run_id`, attempt still `1`). If it returns `failure` or `blocked` without questions → `FAILED`.

Empty questions: continue. Plan risks without questions are not a pause.

**Rationale**: Clarifications (questions are options; resume re-runs the parked step; auto-continue when the re-run is empty). FR-009–FR-010. Least code: label in order; string suffix instead of an executor schema change.

**Alternatives considered**:
- Skipping ahead to implementation after the letter — forbidden (plan may still have unanswered questions).
- Treating each question string as a sequential independent decision — forbidden.
- Sending Telegram on park — Phase 6; spec says parking is enough.
- Adding `recommended` by regex on `summary` — flaky; spec says “when supplied”.

## 9. Next-ready selection

**Decision**: One existing board, all enrolled eligible projects. `run_next_workflow` lists every board task and skips:

- project unknown, disabled, or invalid location (`resolve_eligible_project` raised) — skip, do not fail the whole scan
- priority not in `{P0, P1, P2, P3}` — skip (not ready; MUST NOT invent)
- any listed dependency unmet — skip. A dependency id is satisfied iff that id exists on the board and `complete is True`

Remaining tasks sort by priority (`P0` > `P1` > `P2` > `P3`), then oldest `created_at`. First remaining is started via the same path as `run_workflow` using **that task’s** `project_id`.

If none remain → `NoReadyTaskError`. MUST NOT invent a task identity or start discovery.

Named `run_workflow` does **not** skip: unmet deps or invalid/missing priority fail at the boundary.

**Rationale**: FR-002, clarifications (pool = one board across eligible projects; no-ready is a visible error; missing/invalid priority is not ready).

**Alternatives considered**:
- Selecting only from the caller’s last project — forbidden (pool is all eligible projects).
- Starting discovery when the board is empty — forbidden.
- Using native Hermes claim locks for selection this phase — no background dispatcher; in-process skip+sort is enough for V0 one-at-a-time.

## 10. One-at-a-time slot

**Decision**: One active `WorkflowRecord` per `PivOrchestrator` instance. Occupied while state is `QUEUED`, `RUNNING`, `VALIDATING`, or `HUMAN_DECISION_REQUIRED`. `COMPLETED` and `FAILED` release the slot so a new start is allowed. Parked occupies the slot.

`execution.max_concurrent_tasks` in `default.yaml` is already `1`. Do not read it to allow 2. Do not add a process-wide lock file.

Because start/resume block until terminal, a same-thread second start only naturally overlaps a **parked** run. Checks MUST also prove RUNNING overlap with a reentrant stand-in (`ModelService.complete` calls `run_workflow` and expects `WorkflowBusyError`). Do not start a background thread in production code.

**Rationale**: FR-011, constitution “concurrent workers” out of scope, US3 scenario 4.

**Alternatives considered**:
- Process-global file lock under `/tmp` — host-layout dependent; extra code; one instance is the V0 scheduler.
- Allowing a second start after park — would run two workflows; forbidden.
- A queue of pending starts — extra scheduler; this phase refuses.

## 11. Prepare, isolation, secrets, stand-in

**Decision**: Orchestrator calls `prepare_workspace` once per start (and not on resume unless the copy is missing — missing during resume/later step fails visibly; do not invent a second copy). Dirty reuse stays prepare’s refusal.

Work branch remains `feature/task-<task_id>`; still not `main`/`master`/project default. Publish count stays 0. Methodology writes still fail via existing `ReadOnlyError`.

Checks inject the 004 stand-in `ModelService` plus `MemoryTaskBoard`. Missing live credentials MUST NOT fail those checks. A live configured run still uses the executor’s live client (empty env → `MissingModelCredentialsError`).

Secrets (API keys, env values) MUST NOT appear on `WorkflowRecord`, `DecisionBrief`, or summaries. Do not copy `os.environ` onto the record.

Editor absence MUST NOT fail the workflow (already true of execute). Host-specific paths MUST NOT be defaulted.

**Rationale**: FR-003, FR-013–FR-014, 003/004 contracts, constitution V.

**Alternatives considered**:
- Execute-style “missing workspace fails” on start — forbidden (orchestrator prepares).
- Auto-reset dirty copies — forbidden (003).
- Requiring OpenRouter / Telegram / GitHub to prove the chain — forbidden.

## 12. Errors

**Decision**: Distinct orchestrator exceptions, all subclasses of `OrchestratorError`. Adapter / registry / workspace / executor errors propagate unchanged except as listed in §3.

| Type | When |
|---|---|
| `MissingTaskBoardError` | Construction without an injected board |
| `UnknownTaskError` | Task id not on the board |
| `TaskProjectMismatchError` | Named start `project_id` ≠ task’s recorded project |
| `InvalidPriorityError` | Named start missing/invalid priority |
| `UnmetDependenciesError` | Named start with unsatisfied dependency ids |
| `NoReadyTaskError` | `run_next_workflow` found nothing ready |
| `WorkflowBusyError` | Slot occupied |
| `ResumeNotParkedError` | Resume when not `HUMAN_DECISION_REQUIRED` for that project+task |
| `InvalidDecisionError` | Resume option not a listed letter |
| `OrchestratorError` | Base |

Reuse: `InvalidTaskIdError`, `DirtyWorkspaceError`, `ProtectedBranchError`, `MissingWorkspaceError`, `UnknownRoleError`, `UnknownAgentError`, `ReadOnlyError`, `UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`, `MissingProjectConfigurationError`, `MissingModelAssignmentError`, `MissingModelCredentialsError`.

**Rationale**: Spec wants visible, distinct failures at the trust boundary. Tests assert types. Same pattern as 002–004.

**Alternatives considered**: One error with a code enum — worse call-site checks. Swallowing registry errors — would hide unknown vs disabled vs bad location.

## 13. Checks and fixtures

**Decision**: One pytest file covering the seven SC-007 contract behaviors (and the extra spec edges that fit the same file): full chain to `COMPLETED`, auto-continue after planning, park on questions, resume with a listed letter (re-run parked step), fail validation without retry, refuse a second active workflow, select next ready by priority across eligible projects. Also: no-ready-task, unmet named deps, invalid priority, resume unknown letter, dirty copy at start, enrolled location unchanged, 0 publishes, attempt stays `1`, task body fields unchanged, secrets absent, implementation questions → `FAILED`, missing eight plan sections → `FAILED`.

Fixtures reuse 004: copy `tests/fixtures/ainative-full/` (with scout, specs-planner, builder, and tester under `docs/agents/`) and `tests/fixtures/projects/standard/` git-inited in `tmp_path`. Override validation commands to `true` / `false` as needed. `MemoryTaskBoard` in the test. Stand-in `ModelService` returns predetermined `ModelResponse` values per role (and a second planning response after resume). Production `projects: []` unchanged. Tests MUST NOT enroll a production repository or require a live model, live `kanban.db`, or Telegram.

**Rationale**: Constitution IV; spec SC-007 / FR-014; V0 disposable fixture.

**Alternatives considered**: Only Docker e2e — slower, not required. Hitting live Kanban in CI — forbidden by FR-014.

---

description: "Task list for PIV Orchestrator implementation"
---

# Tasks: PIV Orchestrator

**Input**: Design documents from `/specs/005-piv-orchestrator/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Requested by spec SC-007, constitution IV, and [quickstart.md](./quickstart.md). One contract module only: `personalAgent/tests/test_piv_orchestrator.py`. Stand-in `ModelService` + `MemoryTaskBoard`. Disposable git + methodology fixtures in pytest `tmp_path` (copy `personalAgent/tests/fixtures/ainative-full/` and `personalAgent/tests/fixtures/projects/standard/`, then `git init` + commit; tests let the orchestrator call `prepare_workspace`). Tests MUST NOT require a live model account, live `kanban.db`, production repo, GitHub account, Telegram, or `OPENAI_API_KEY`.

**Organization**: Tasks are grouped by user story. US1 and US2 are P1; US3 is P2. US1 (named `run_workflow` chain to `COMPLETED`) is sequenced first because it is the MVP remaining gap after Phase 2 execute. US2 adds the explicit state overlay and fail-without-retry on top of that chain. US3 adds park/resume, the one-at-a-time slot refuse, and `run_next_workflow`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Implementation lands in the existing `personalAgent/` package (not playground root, not live AiNative). Public API lives in one module until that file is unreadable — do not pre-split into `orchestration/` or state/board/selection packages. Do not add dependencies. Do not edit `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/src/hermes_kanban/projects.py`, `personalAgent/src/hermes_kanban/workspace.py`, or `personalAgent/src/hermes_kanban/executor.py` except importing their existing public APIs (and `projects._path_like_id` as [research.md](./research.md) allows). Do not add agents to live AiNative. Do not edit `personalAgent/docker-compose.yml`. Do not implement `SqliteTaskBoard` or open `kanban.db`.

```text
personalAgent/src/hermes_kanban/orchestrator.py
personalAgent/src/hermes_kanban/__init__.py
personalAgent/tests/test_piv_orchestrator.py
personalAgent/tests/fixtures/ainative-full/docs/agents/{scout,specs-planner,builder,tester}/  # existing; fixture only
personalAgent/tests/fixtures/projects/standard/   # existing; copy into tmp_path then git init
personalAgent/config/default.yaml                 # unchanged; projects: [] and no live model name literals
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing control-plane layout is the implementation target. No new package, no new fixture agents, no host-path or `kanban.db` config.

- [X] T001 Confirm `personalAgent/config/default.yaml` keeps `projects: []`, `workspace.root: /workspaces`, `workflow.default: piv`, `execution.max_concurrent_tasks: 1` (if present), and `model.openai_compatible.base_url_env` / `api_key_env` as env **names** only. MUST NOT write a live provider or model id as a required value. MUST NOT add a `kanban.db` path, `$HOME`, `HERMES_HOME`, `WORKSPACE_ROOT`, or a workstation path. Do not edit `personalAgent/docker-compose.yml`.
- [X] T002 [P] Confirm fixture-only agents `scout`, `specs-planner`, `builder`, and `tester` already exist under `personalAgent/tests/fixtures/ainative-full/docs/agents/{scout,specs-planner,builder,tester}/`. Do not add agents. Do not copy these folders into live `AiNative/`. Do not change `personalAgent/docker-compose.yml`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error types, overlay records, `TaskBoard` seam, `MemoryTaskBoard`, and `PivOrchestrator` construction. No user story work until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `OrchestratorError` and distinct subclasses `MissingTaskBoardError`, `UnknownTaskError`, `TaskProjectMismatchError`, `InvalidPriorityError`, `UnmetDependenciesError`, `NoReadyTaskError`, `WorkflowBusyError`, `ResumeNotParkedError`, `InvalidDecisionError` in `personalAgent/src/hermes_kanban/orchestrator.py`. Do not swallow adapter/registry/workspace/executor errors into one type — those propagate unchanged (`InvalidTaskIdError`, `DirtyWorkspaceError`, `ProtectedBranchError`, `MissingWorkspaceError`, `UnknownRoleError`, `UnknownAgentError`, `ReadOnlyError`, `UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`, `MissingProjectConfigurationError`, `MissingModelAssignmentError`, `MissingModelCredentialsError`).
- [X] T004 Add frozen dataclasses `BoardTask`, `DecisionOption`, `DecisionBrief`, `StepRecord`, and `WorkflowRecord` in `personalAgent/src/hermes_kanban/orchestrator.py` matching [data-model.md](./data-model.md). `BoardTask`: `id`, `project_id`, `problem`, `expected_result`, `platform` (default `""`), `acceptance_criteria`, `technical_notes` (default `""`), `dependencies` (`tuple[str, ...]`, default `()`), `owner` (default `""`), `reviewer` (default `""`), `priority`, `created_at`, `complete` (`bool`, default `False`). `DecisionOption`: `letter`, `text`. `DecisionBrief`: `project_id`, `task_id`, `phase`, `decision`, `why_it_matters`, `options` (`tuple[DecisionOption, ...]`), `recommended` (`str | None`, default `None`), `reply_with` (default `"option letter"`). `StepRecord`: `state`, `phase` (default `""`), `worker` (`str | None`), `execute_status` (`str | None`), `questions` (`tuple[str, ...]`, default `()`), `summary` (default `""`). `WorkflowRecord`: `run_id`, `state`, `workflow_name`, `current_phase`, `current_worker` (`str | None`), `attempt` (default `1`), `project_id`, `task_id`, `task` (`BoardTask`), `workspace_path` (`Path | None`), `workspace_branch` (`str | None`), `workspace_id` (`str | None`), `validation_status` (default `"pending"`), `blockers` (`tuple[str, ...]`, default `()`), `next_action`, `pull_request` (`None`, default `None`), `decision` (`DecisionBrief | None`), `chosen_option` (`str | None`), `steps` (`tuple[StepRecord, ...]`), `error` (`str | None`). Type-annotate public APIs. No reasoning/transcript/secret fields. Closed `state` values only: `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`. Closed `current_phase` values: `discovery`, `planning`, `implementation`, `validation`.
- [X] T005 Add `TaskBoard` Protocol (`get(task_id: str) -> BoardTask`, `list() -> tuple[BoardTask, ...]`) and in-memory `MemoryTaskBoard` in `personalAgent/src/hermes_kanban/orchestrator.py`. `MemoryTaskBoard` is constructed with a sequence of `BoardTask` records; `get` missing id → `UnknownTaskError`; `list` returns all records in insertion order. The orchestrator MUST NOT write `BoardTask` body, owner, reviewer, or priority. MUST NOT create `execution.db`, a second SQLite file, or a second task table. MUST NOT open Hermes `kanban.db`. Mark with `ponytail:` fixture board in-process, not native SQLite; ceiling: contract checks never hit `kanban.db`; upgrade: read-only `SqliteTaskBoard` against the isolated Hermes home when a later runtime spec wires a worker — still no second task table.
- [X] T006 Implement `PivOrchestrator.__init__(executor: AgentExecutor, workspaces: WorkspaceManager, registry: ProjectRegistry, task_board: TaskBoard)` and `PivOrchestrator.from_config(config_path: Path, *, model_service: ModelService | None = None, task_board: TaskBoard | None = None)` in `personalAgent/src/hermes_kanban/orchestrator.py`. `from_config` builds `AgentExecutor.from_config(config_path, model_service=model_service)` and takes `executor.workspaces` / `executor.registry` from that instance — do not construct adapter/registry/workspace a second time. Omitted or `None` `task_board` → `MissingTaskBoardError`. MUST NOT invent a `kanban.db` path, `$HOME`, or `HERMES_HOME`. Omitted `model_service` → live client via the executor (existing 004 rule). Hold at most one active `WorkflowRecord` on the instance (`None` until a start). `ponytail:` in-memory slot, process-local; ceiling: a container restart loses the parked brief (Phase 7); upgrade: fill native `workspace_*` / `current_step_key` / `workflow_template_id` and persist overlay fields Hermes cannot represent — still no second task table. Do not extract `hermes_kanban/orchestration/`.
- [X] T007 [P] Re-export `PivOrchestrator`, `TaskBoard`, `MemoryTaskBoard`, `BoardTask`, `DecisionOption`, `DecisionBrief`, `StepRecord`, `WorkflowRecord`, and the orchestrator error classes from `personalAgent/src/hermes_kanban/__init__.py`. Keep every existing adapter, registry, workspace, and executor export.

**Checkpoint**: Foundation ready — `from_config` wires executor + injected board; user story implementation can begin

---

## Phase 3: User Story 1 - Run discovery through validation for one task (Priority: P1) 🎯 MVP

**Goal**: Callers can `run_workflow(project_id, task_id)` for one eligible project and one board task. The start call waits until the chain finishes. Discovery → planning → implementation → validation with no plan-approval gate. Task fields come from the board. The orchestrator prepares the isolated copy before the first agent run.

**Independent Test**: Enroll a fixture project with declared validation checks. Put fixture task `123` on `MemoryTaskBoard` (problem, expected result, acceptance criteria, priority). Start the workflow. Confirm discovery runs, then planning writes the eight-section plan in the isolated copy, then implementation changes only that copy, then validation runs the project’s own checks and reports pass. Confirm no plan-approval stop. Confirm the enrolled project location is unchanged and nothing was published.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [US1] Add contract tests in `personalAgent/tests/test_piv_orchestrator.py` with helpers that: copy `tests/fixtures/ainative-full/` into `tmp_path` and `git init` + commit; copy `tests/fixtures/projects/standard/` into `tmp_path`, `git init`, set local `user.email`/`user.name`, commit; override the copied project’s `.ainative/project.yaml` validation commands to `true` (cheap pass; do not require the fixture to be a Python package); write operational YAML (`workspace.root` = a temp dir, `ainative.path` = the temp methodology, `projects:` listing the enrolled fixture, `model.roles.planning` / `implementation` / `validation` = **test** id strings such as `test-planning-model`, not production names); construct `MemoryTaskBoard` with task `id="123"`, matching `project_id`, non-empty `problem` / `expected_result` / `acceptance_criteria`, `priority="P1"`, `created_at` ISO-8601 UTC; construct `PivOrchestrator.from_config(..., model_service=stand_in, task_board=board)` where the stand-in is an in-test `ModelService` returning predetermined `ModelResponse` values **per role** (discovery: `status=success`, empty `questions`; planning: `status=success`, `plan_markdown` with all eight `## ` sections from 004, empty `questions`; implementation: `status=success`, optional `files` + `commit=True`; validation: `status=success`) with no network and no env. Cover: `run_workflow(project_id, "123")` waits and returns `WorkflowRecord` with `state == "COMPLETED"` after discovery → planning → implementation → validation; `{workspace}/PLAN.md` exists with the eight required sections; implementation file changes and any local commit exist only in the isolated copy on `feature/task-123`; enrolled HEAD/branch/files unchanged; 0 `git push`; `next_action` is never `"wait for plan approval"`; start does not require the caller to paste problem / expected-result / AC (those appear on the stand-in’s `AssembledContext` / execute payload from the board); no prepared copy at start still succeeds (orchestrator called `prepare_workspace`; execute is not asked to prepare); unknown task id → `UnknownTaskError` and no agent run; named start `project_id` ≠ task’s recorded project → `TaskProjectMismatchError`; missing or invalid priority (`""`, `"P4"`, `"high"`) → `InvalidPriorityError` before discovery; unmet dependency id → `UnmetDependenciesError` before discovery; empty or path-like `task_id` → existing `InvalidTaskIdError`; dirty existing copy at start → existing `DirtyWorkspaceError` and dirty files kept. Tests MUST NOT set `OPENAI_API_KEY`, MUST NOT bind a hardcoded workstation path, MUST NOT open `kanban.db`, and MUST NOT use a live production repo. Stand-in without env MUST succeed.

### Implementation for User Story 1

- [X] T009 [US1] Implement `run_workflow(project_id, task_id)` gates in `personalAgent/src/hermes_kanban/orchestrator.py` **before** the first agent run, in order: empty/path-like `task_id` → existing `InvalidTaskIdError` (reuse `projects._path_like_id`; do not join the raw id onto a filesystem path); `registry.resolve_eligible_project(project_id)` then `load_project_context(project_id)` (propagate `UnknownProjectError` / `DisabledProjectError` / `InvalidProjectLocationError` / `MissingProjectConfigurationError` unchanged; MUST NOT invent a project path); `task_board.get(task_id)` (missing → `UnknownTaskError`; MUST NOT invent problem / expected-result / AC text); task `project_id` ≠ caller `project_id` → `TaskProjectMismatchError`; `priority` not exactly `P0`/`P1`/`P2`/`P3` → `InvalidPriorityError` (MUST NOT invent a priority); any listed dependency unmet (id missing on the board or `complete is not True`) → `UnmetDependenciesError` (discovery MUST NOT start); write the operational record as `QUEUED` (`run_id` = UUID hex, `attempt=1`, `workflow_name` from `executor.settings.workflow_name`, `current_phase="discovery"`, `next_action="discover"`, `validation_status="pending"`, empty PR slot, empty blockers, `task` = the loaded `BoardTask` snapshot); `workspaces.prepare_workspace(project_id, task_id)` once — allowed to create; dirty reuse → existing `DirtyWorkspaceError` (MUST NOT discard dirty files); protected work branch → existing `ProtectedBranchError`. Slot-busy refuse is US3; US1 may store the record without refusing a second start. Import `_path_like_id` rather than copying a third path-like variant.
- [X] T010 [US1] Implement the discovery → planning → implementation → validation chain in `personalAgent/src/hermes_kanban/orchestrator.py`: after successful prepare, loop `execute_role` for roles `("discovery", "planning", "implementation", "validation")` on the same call (blocking until terminal). There MUST NOT be a plan-approval gate. Build `ExecutePayload` from the board task only: `title`←`problem`, `description`←`expected_result`, `acceptance_criteria`←`acceptance_criteria`, `priority`←`priority`, `plan=None` until planning succeeds, `validation=None` until validation has a summary. MUST NOT invent those fields; MUST NOT require them on the start call; MUST NOT stuff owner/reviewer/platform/notes/deps into `ExecutePayload` (keep them on `WorkflowRecord.task`). After planning `status=success`, read `PLAN.md` from the isolated copy (`ExecuteResult.artifacts` path if present, else `{workspace}/PLAN.md`) and pass that text as `payload.plan` into implementation and validation — MUST NOT invent a plan. Planning `status=failure` (including missing eight sections, already enforced by execute) → stop without starting implementation (US2 will set `FAILED`). After a successful step with an empty `questions` list, start the next role automatically. Do not park on questions yet (US3). Do not call `prepare_workspace` a second time for the same task. MUST NOT `git push`, open a PR, merge, deploy, write methodology, edit the enrolled location, or start a background worker. On validation `status=success` and `validation=pass`, set `state="COMPLETED"`, `validation_status="pass"`, `next_action=""`, `pull_request=None`, and return the record. Live methodology missing a mapped agent → existing `UnknownAgentError`; MUST NOT add agents to methodology. Do not change `personalAgent/src/hermes_kanban/executor.py`.

**Checkpoint**: User Story 1 is independently testable via named `run_workflow` to `COMPLETED` without park/resume, next-ready, or fail-without-retry coverage

---

## Phase 4: User Story 2 - Record explicit execution state and stop on failure (Priority: P1)

**Goal**: Every workflow has a machine-readable overlay record. Reviewers can read explicit state, phase, worker, attempt `1`, workspace, validation status, blockers, next action, and empty PR slot — never inferred only from summary prose. Phase `failure` or `blocked` without questions stops at `FAILED` with no retry. The human-readable board task body is not overwritten.

**Independent Test**: Run a fixture workflow that succeeds and confirm the recorded states include queued, running through discovery/planning/implementation, validating, then completed, with current phase and next action updating at each step. Run a fixture whose validation checks fail and confirm the workflow is `FAILED`, validation status is fail, next action is not “retry”, and implementation is not re-run.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [US2] Extend `personalAgent/tests/test_piv_orchestrator.py`: a successful `run_workflow` record has `state` in `{QUEUED, RUNNING, VALIDATING, COMPLETED, FAILED, HUMAN_DECISION_REQUIRED}` only (this story asserts the first five; park is US3); `steps` includes a `QUEUED` row (phase `""`, `execute_status is None`) then running discovery/planning/implementation, then `VALIDATING`, then `COMPLETED`; each step snapshot has `state`, `phase`, `worker`, `execute_status`, `questions`, `summary`; returned record includes `workflow_name` (`piv` default), `current_phase`, `current_worker`, `attempt == 1`, `workspace_path`, `workspace_branch` (`feature/task-123`), `workspace_id` (`ws-{project_id}-123`), `validation_status` (`pending` until validation, then `pass`), empty `blockers` when none, `next_action` (never `"retry"`, never `"wait for plan approval"`; `""` on `COMPLETED`/`FAILED`), `pull_request is None`; after planning success with empty questions, a `steps` row shows current phase becoming implementation and next action implement; override validation commands to `false` → `state == "FAILED"`, `validation_status == "fail"`, `next_action != "retry"`, implementation role is not executed a second time, `attempt == 1`; implementation or validation `questions` non-empty → `FAILED` (not parked); discovery/planning `blocked` with empty questions → `FAILED`; board task `problem` / `expected_result` / `platform` / `acceptance_criteria` / `technical_notes` / `dependencies` / `owner` / `reviewer` / `priority` on `record.task` match the seeded values after every state change (`MemoryTaskBoard` records unchanged); secrets/env values absent from `WorkflowRecord` / `steps` / `error` (no `os.environ` dump, no API keys). Same tmp_path / stand-in / no `OPENAI_API_KEY` / no `kanban.db` rules as T008.

### Implementation for User Story 2

- [X] T012 [US2] Update the overlay after every step in `personalAgent/src/hermes_kanban/orchestrator.py`: append a `StepRecord` on the `QUEUED` write and after each `execute_role` return, **before** the next agent run. While discovery/planning/implementation is in progress or just finished without park/fail, `state="RUNNING"`; while the validation role is in progress, `state="VALIDATING"`. `current_phase` is the role that is running or that just failed. `current_worker` is that role’s mapped agent (`executor.settings.role_agents[phase]`). `next_action` is `discover` / `plan` / `implement` / `validate` while advancing; `""` on `COMPLETED`/`FAILED`. `validation_status` stays `pending` until validation runs, then `pass`/`fail`/`blocked` from `ExecuteResult.validation` (project commands, not summary prose). `attempt` is always `1`. `pull_request` stays `None`. MUST NOT infer `state` from summary prose. MUST NOT write changing execution details into `BoardTask` / `MemoryTaskBoard`. MUST NOT include private reasoning, transcripts, or secrets on the record. Mark the in-memory overlay with the existing `ponytail:` (T006) if not already present.
- [X] T013 [US2] Implement fail-and-stop in `personalAgent/src/hermes_kanban/orchestrator.py`: any role `status=failure`, or `blocked` with an empty `questions` list, or implementation/validation with a non-empty `questions` list, or missing copy during a later step (`MissingWorkspaceError` from execute) → set `state="FAILED"`, set `error` to a public message (no secrets), stop the chain, do not diagnose/retry/debug, do not increment `attempt`, do not re-run implementation. Validation command fail → `validation_status="fail"`. Release the instance slot on `COMPLETED` and `FAILED` so a later start on the same instance is allowed (US3 owns the refuse-while-occupied path). `next_action` MUST NOT become `"retry"`. Park on discovery/planning questions is still US3.

**Checkpoint**: User Stories 1 and 2 both work independently — named chain to `COMPLETED` plus explicit overlay and fail-without-retry

---

## Phase 5: User Story 3 - Pause for a human decision, resume, and run only one task (Priority: P2)

**Goal**: Discovery/planning questions park at `HUMAN_DECISION_REQUIRED` with options labeled A/B/C. Resume with a listed letter re-runs the parked step and auto-continues when that re-run has empty questions. At most one active workflow. `run_next_workflow` selects P0→P3 then oldest across eligible projects, or fails with `NoReadyTaskError`.

**Independent Test**: Start a fixture whose planning result includes a questions list of two strings; confirm the start call returns `HUMAN_DECISION_REQUIRED` with those strings labeled `A` and `B`, implementation files are unchanged after planning, and a second start is refused. Resume with `A`; confirm planning re-runs with `A` available, then the chain continues through validation. Ask for the next ready task from a board with a blocked-dependency task, an older lower-priority ready task on one eligible project, and a newer higher-priority ready task on another eligible project; confirm the higher-priority ready task is chosen. Ask again on a board with nothing ready and confirm a visible no-ready-task failure.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US3] Extend `personalAgent/tests/test_piv_orchestrator.py`: planning (or discovery) `questions=("first option", "second option")` → `run_workflow` returns `state == "HUMAN_DECISION_REQUIRED"`, implementation files unchanged, `decision` brief has `project_id`, `task_id`, `phase` (`planning` or `discovery`), `decision` equal to that step’s `summary`, `why_it_matters == "{phase} cannot continue without this choice."`, `options` letters `A`/`B` with the original strings, `recommended is None`, `reply_with == "option letter"`, `next_action` mentions the option letter; resume `"A"` (and `"a"`) re-runs the parked role with execute `description` containing `Human decision: A — first option`, empty questions on that re-run auto-continues through validation, `attempt == 1`, `run_id` unchanged; resume unknown letter / option text / empty → `InvalidDecisionError`, still parked, 0 publishes; resume when not parked (never started, or after `COMPLETED`/`FAILED`) → `ResumeNotParkedError` and does not restart a completed/failed run; after `COMPLETED` or `FAILED`, a new `run_workflow` on the same instance is allowed; while parked (and via a reentrant stand-in whose `complete` calls `run_workflow` / `run_next_workflow` during `RUNNING`) a second start raises `WorkflowBusyError` and the first record is unchanged — do not start a background thread; `run_next_workflow` on a board with (1) unmet-dependency task, (2) older `P2` ready task on eligible project A, (3) newer `P0` ready task on eligible project B → starts the `P0` task; skip ineligible/disabled project tasks without failing the whole scan; empty board / only unmet deps / only ineligible / only invalid priority → `NoReadyTaskError` and no agent run; named start with unmet deps still `UnmetDependenciesError` (does not skip). Same fixture / stand-in / no live `kanban.db` rules as T008. Enroll a second disposable git project in the temp YAML for the cross-project selection check.

### Implementation for User Story 3

- [X] T015 [US3] Park on discovery/planning questions in `personalAgent/src/hermes_kanban/orchestrator.py`: a non-empty `questions` tuple on discovery or planning is one decision; label items `A`, `B`, `C`, … in order (`chr(ord("A") + i)`); MUST NOT parse strings into a different shape or invent options. Set `state="HUMAN_DECISION_REQUIRED"`, do not start the next phase, do not send a message. Fill `DecisionBrief`: `decision` = that step’s `ExecuteResult.summary`; `why_it_matters` = `"{phase} cannot continue without this choice."`; `options` = labeled letters + original strings; `recommended=None` (MUST NOT guess from prose); `reply_with="option letter"`; `next_action="reply with the option letter"`. `blocked` with questions → park (questions win). Empty questions still continue (US1). Implementation/validation questions stay `FAILED` (US2). Park occupies the slot. Attempt stays `1`.
- [X] T016 [US3] Implement `resume_workflow(project_id, task_id, option)` in `personalAgent/src/hermes_kanban/orchestrator.py`: not `HUMAN_DECISION_REQUIRED` for that `project_id`+`task_id` → `ResumeNotParkedError` (MUST NOT restart a completed or failed run). `option` empty, not a listed letter, or the option’s text instead of the letter → `InvalidDecisionError`; stay parked; do not publish. Listed letter is case-insensitive (`"a"` → `A`). On accept: leave parked state, write `QUEUED`, keep `run_id`, keep `attempt=1`, set `chosen_option` to the letter, re-run the **parked** discovery or planning role with `description = expected_result + "\n\nHuman decision: {letter} — {option_text}"`, include the same suffix on later steps of that attempt, then auto-continue if that re-run has an empty questions list (still no plan-approval gate). Re-run questions → park again (same `run_id`, attempt `1`). Re-run `failure` or `blocked` without questions → `FAILED`. MUST NOT call `prepare_workspace` on resume (missing copy during resume fails visibly via execute; do not invent a second copy). Wait until `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` and return that record. Do not start a background worker.
- [X] T017 [US3] Enforce one-at-a-time in `personalAgent/src/hermes_kanban/orchestrator.py`: if the instance slot is `QUEUED`, `RUNNING`, `VALIDATING`, or `HUMAN_DECISION_REQUIRED`, `run_workflow` and `run_next_workflow` raise `WorkflowBusyError` and leave the first workflow unchanged. `COMPLETED` and `FAILED` already release the slot (US2). Parked occupies the slot. Do not read `execution.max_concurrent_tasks` to allow 2. Do not add a process-wide lock file. Do not start a background thread in production code. Checks prove RUNNING overlap with the reentrant stand-in from T014.
- [X] T018 [US3] Implement `run_next_workflow()` in `personalAgent/src/hermes_kanban/orchestrator.py`: same slot gate as `run_workflow`. Pool is `task_board.list()` across all enrolled projects. Skip (do not fail the scan): `resolve_eligible_project` raised (unknown/disabled/invalid location); priority not in `{P0, P1, P2, P3}`; any listed dependency unmet. Among remaining, sort by priority rank (`P0` then `P1` then `P2` then `P3`) then oldest `created_at`; start the first via the same path as `run_workflow` using **that task’s** `project_id`. None remaining → `NoReadyTaskError` (MUST NOT invent a task identity or start discovery). Wait and return the same way as `run_workflow`. Named `run_workflow` still fails at the boundary on unmet deps / invalid priority (does not skip).

**Checkpoint**: All three user stories are independently functional. Stop — do not start recovery, GitHub hosting, or Telegram

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the seven SC-007 checks, keep existing packages green, and refuse silent production targeting

- [X] T019 Keep existing checks green from `personalAgent/`: `uv run pytest tests/test_import.py tests/test_ainative_adapter.py tests/test_project_registry.py tests/test_workspace_manager.py tests/test_agent_executor.py`. Do not rewrite `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/src/hermes_kanban/projects.py`, `personalAgent/src/hermes_kanban/workspace.py`, or `personalAgent/src/hermes_kanban/executor.py`. Confirm `test_import.py` still imports the package and that new orchestrator names remain re-exported from `personalAgent/src/hermes_kanban/__init__.py`.
- [X] T020 Run the quickstart validation from `personalAgent/`: `uv run pytest tests/test_piv_orchestrator.py` and `uv run ruff check src tests`. Fix any contract or lint failure in `personalAgent/src/hermes_kanban/orchestrator.py` / `personalAgent/tests/test_piv_orchestrator.py`. Confirm the seven SC-007 behaviors fail the test file if broken: full chain to `COMPLETED`, auto-continue after planning, park on questions, resume with a listed letter (re-run parked step), fail validation without retry, refuse a second active workflow, select next ready by priority across eligible projects.
- [X] T021 Confirm `personalAgent/config/default.yaml` still has `projects: []`, no live model name literals as required values, no host-specific path, no `kanban.db` path; this diff does not read/write Hermes `projects.db` / `kanban.db`, adds no new dependency in `personalAgent/pyproject.toml`, and does not add agents to live AiNative.
- [X] T022 Confirm `personalAgent/src/hermes_kanban/orchestrator.py` never invokes `git push`, `reset --hard`, `clean`, `clone`, `init`, or a second `prepare_workspace` for the same task. Tests create git and methodology fixtures only under `tmp_path`. Production module contains no provider/model name literals and no secrets on `WorkflowRecord` / `DecisionBrief`. `ponytail:` comments for the in-memory overlay and fixture `TaskBoard` remain, naming ceiling and upgrade path.
- [X] T023 [P] Stop after orchestrator contract checks pass. Do not start recovery/retry/debug, GitHub push/PR, Telegram, restart persistence, or adding agents to live methodology. Do not change `personalAgent/docker-compose.yml`. Do not implement `SqliteTaskBoard`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP named `run_workflow` chain to `COMPLETED`
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (chain exists); adds overlay history and fail-without-retry
- **User Story 3 (Phase 5)**: Depends on Foundational + US1 (and US2 fail paths for resume→`FAILED`); adds park/resume, slot refuse, next-ready
- **Polish (Phase 6)**: Depends on the stories being delivered

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependency on US2/US3
- **User Story 2 (P1)**: Depends on US1 chain; independently testable once `steps` / `FAILED` / unchanged task body exist
- **User Story 3 (P2)**: Depends on US1 chain (park is a branch in the same loop); independently testable via questions → park → resume letter, busy refuse, and next-ready selection

### Within Each User Story

- Tests MUST be written and FAIL before that story’s implementation
- Types/errors/board/construction before `run_workflow`
- Named-start gates before `prepare_workspace`
- Prepare once before `execute_role`
- Happy-path chain before overlay history and `FAILED`
- Overlay + fail-stop before park/resume
- Park before resume
- Slot refuse before next-ready (same instance must refuse overlapping starts)
- Story complete before moving to the next increment

### Parallel Opportunities

- T001 and T002 are different files and can run in parallel
- T007 is a different file from T006 and can run after T003–T006
- T019–T022 share verification; T023 is independent of T022 once implementation is done
- Test tasks T008, T011, T014 share `personalAgent/tests/test_piv_orchestrator.py` — sequential
- Implementation tasks T003–T006, T009–T010, T012–T013, T015–T018 share `personalAgent/src/hermes_kanban/orchestrator.py` — sequential
- US1/US2/US3 cannot be staffed in true parallel: they share one module and one test file. A single implementer should run them sequentially

---

## Parallel Example: User Story 1

```bash
# After Foundational (T007 is the only other-file task):
Task: "Re-export public orchestrator types from personalAgent/src/hermes_kanban/__init__.py"

# US1 tests then implementation are sequential (same two files):
Task: "Contract tests in personalAgent/tests/test_piv_orchestrator.py"
Task: "Implement run_workflow gates in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Implement discovery→validation chain in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Parallel Example: User Story 2

```bash
# After US1 chain exists — still one test file then one module:
Task: "Overlay and fail-without-retry contract tests in personalAgent/tests/test_piv_orchestrator.py"
Task: "Update WorkflowRecord after every step in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Implement FAILED stop with attempt 1 in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Parallel Example: User Story 3

```bash
# After US1/US2 — still one test file then one module:
Task: "Park/resume/slot/next-ready contract tests in personalAgent/tests/test_piv_orchestrator.py"
Task: "Park on questions + DecisionBrief in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Implement resume_workflow in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Enforce one-at-a-time WorkflowBusyError in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Implement run_next_workflow selection in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (confirm empty managed set + fixture roster; no `kanban.db` path)
2. Complete Phase 2: Foundational (types, `TaskBoard`, construction, re-exports)
3. Complete Phase 3: User Story 1 (`run_workflow` chain to `COMPLETED`)
4. **STOP and VALIDATE**: named start on fixture task `123`; discovery → planning (`PLAN.md`) → implementation (isolated copy only) → validation pass; no plan-approval stop
5. Demo on a disposable fixture; do not enroll a production repo; do not set `OPENAI_API_KEY`; do not open `kanban.db`

### Incremental Delivery

1. Setup + Foundational → construction wires existing executor + injected board
2. Add US1 → named chain independently → MVP
3. Add US2 → explicit overlay + fail-without-retry
4. Add US3 → park/resume + one slot + next-ready across eligible projects
5. Each story adds value without starting recovery, GitHub, or Telegram

### Parallel Team Strategy

This feature is one module plus one test file. Prefer a single implementer moving story-by-story. If two people: one owns fixture/stand-in/`MemoryTaskBoard` tests, the other owns `orchestrator.py`, integrating at each checkpoint. Do not split `orchestrator.py` into extra packages to create false parallelism.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec user stories US1–US3
- Public names are `run_workflow`, `run_next_workflow`, `resume_workflow`
- Roles: `discovery` → `scout`, `planning` → `specs-planner`, `implementation` → `builder`, `validation` → `tester`
- Questions on discovery/planning are options A/B/C; resume re-runs the parked step; attempt stays `1`
- One active slot per orchestrator instance; parked occupies it; `COMPLETED`/`FAILED` release it
- Next-ready: skip ineligible / unmet deps / invalid priority; `P0>P1>P2>P3` then oldest; none → `NoReadyTaskError`
- Task SoT is the existing board via `TaskBoard` (`MemoryTaskBoard` for checks). No second SQLite table
- Execution state is an in-memory `WorkflowRecord` overlay; card body is not overwritten
- Orchestrator prepares; execute still must not. Dirty reuse stays prepare’s error
- Local commit only on the task work branch in the isolated copy; 0 publishes
- Production `projects: []` until the owner names a non-critical repo
- Commit after each task or logical group if the owner asks; Conventional Commits (`feat:`, `test:`)
- Stop at any checkpoint to validate the story independently
- Avoid: second SQLite store, workflow engine, background worker, hardcoded model names, adding agents to live AiNative, rewriting adapter/registry/workspace/executor, starting recovery/GitHub/Telegram

---

## Phase 7: Convergence

- [X] T024 Release the instance slot when `run_workflow` or `resume_workflow` exits via an exception after claiming it (prepare `DirtyWorkspaceError` / `ProtectedBranchError`, or executor errors that propagate) so a later start is not refused by a leftover `QUEUED` / `RUNNING` occupancy in `personalAgent/src/hermes_kanban/orchestrator.py` per FR-011 (partial)
- [X] T025 Strengthen the resume contract check in `personalAgent/tests/test_piv_orchestrator.py` so it fails if resume skips the parked role (assert that role runs again, e.g. `planning` appears twice on the stand-in) per SC-007 (partial)
- [X] T026 Pass `PLAN.md` into implementation and validation only after this run's planning succeeds in `personalAgent/src/hermes_kanban/orchestrator.py`; do not preload it at `_run_from` entry into discovery or a planning re-run per T010 / FR-005 (partial)

---

## Phase 8: Convergence

- [X] T027 Strengthen the park contract check in `personalAgent/tests/test_piv_orchestrator.py` so it fails if the decision brief does not use that step's summary as decision text, does not keep the original question strings labeled A/B, or omits why_it_matters / reply_with / next_action option-letter protocol per US3/AC1 / FR-009 (partial)
- [X] T028 Add a resume re-park contract check in `personalAgent/tests/test_piv_orchestrator.py` that fails if a parked-step re-run with a new non-empty questions list starts implementation or increments attempt per US3/AC8 / SC-003 / FR-009 (partial)
- [X] T029 Strengthen invalid-resume assertions in `personalAgent/tests/test_piv_orchestrator.py` so the check fails if an unknown letter, option text, or empty option unparks the workflow (must stay `HUMAN_DECISION_REQUIRED`) per US3/AC3 / FR-010 (partial)
- [X] T030 Extend next-ready contract checks in `personalAgent/tests/test_piv_orchestrator.py` so they fail if ineligible/disabled projects or invalid priority abort the scan instead of skipping, and if a board with only those unready rows does not raise `NoReadyTaskError` per FR-002 / SC-005 / US3/AC7 (partial)

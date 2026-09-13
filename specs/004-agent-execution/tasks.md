---

description: "Task list for Agent Execution implementation"
---

# Tasks: Agent Execution

**Input**: Design documents from `/specs/004-agent-execution/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Requested by spec SC-007, constitution IV, and [quickstart.md](./quickstart.md). One contract module only: `personalAgent/tests/test_agent_executor.py`. Stand-in `ModelService`. Disposable git + methodology fixtures in pytest `tmp_path` (copy `personalAgent/tests/fixtures/ainative-full/` and `personalAgent/tests/fixtures/projects/standard/`, then `git init` + commit; tests call `prepare_workspace` then `execute_*`). Tests MUST NOT require a live model account, production repo, GitHub account, or `OPENAI_API_KEY`.

**Organization**: Tasks are grouped by user story. All three stories are P1. US1 (execute + context + payload + identity) is sequenced first because it is the MVP remaining gap after Phase 1. US2 adds planning artifact, implementation writes/commit isolation, validation-from-commands, and result shape on top of that execute. US3 adds per-role model assignment tagging, missing-assignment failure, methodology-write refuse, missing-workspace refuse, and protected-branch/no-publish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Implementation lands in the existing `personalAgent/` package (not playground root, not live AiNative). Public API lives in one module until that file is unreadable — do not pre-split into `executor/` or context/model/result packages. Do not add dependencies. Do not edit `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/src/hermes_kanban/projects.py`, or `personalAgent/src/hermes_kanban/workspace.py` except importing their existing public APIs (and `projects._parse_document` / `_path_like_id` as [research.md](./research.md) allows). Do not add agents to live AiNative — only fixture folders under `personalAgent/tests/fixtures/ainative-full/docs/agents/`. Do not edit `personalAgent/docker-compose.yml`.

```text
personalAgent/src/hermes_kanban/executor.py
personalAgent/src/hermes_kanban/__init__.py
personalAgent/tests/test_agent_executor.py
personalAgent/tests/fixtures/ainative-full/docs/agents/specs-planner/ # fixture only
personalAgent/tests/fixtures/ainative-full/docs/agents/builder/       # fixture only
personalAgent/tests/fixtures/ainative-full/docs/agents/scout/         # existing
personalAgent/tests/fixtures/ainative-full/docs/agents/tester/        # existing
personalAgent/tests/fixtures/projects/standard/                      # existing; copy into tmp_path then git init
personalAgent/config/default.yaml                                   # optional commented role/model slots; no live model names
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Fixture roster includes all four default role agents. Production config still has no live model literals and no enrolled projects.

- [X] T001 [P] Confirm fixture-only agents `specs-planner` and `builder` exist under `personalAgent/tests/fixtures/ainative-full/docs/agents/`. Minimal purpose + how-to (match `scout`/`tester`: a short AGENTS.md title/purpose and a SKILL.md how-to). Do not name a provider or model. Do not add `rule.md` unless needed for adapter completeness. Do not reference unresolved skills. Do not copy these folders into live `AiNative/`. Do not change `personalAgent/docker-compose.yml`.
- [X] T002 [P] Confirm `personalAgent/config/default.yaml` keeps `projects: []`, `workspace.root: /workspaces`, `workflow.default: piv`, and `model.openai_compatible.base_url_env` / `api_key_env` as env **names** only. MAY add commented `roles:` / `model.roles:` slots. MUST NOT write a live provider or model id as a required value. Do not hardcode `$HOME`, `WORKSPACE_ROOT`, or a workstation path. Do not edit `personalAgent/docker-compose.yml`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error types, records, settings load, ModelService protocol, and AgentExecutor construction. No user story work until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `ExecutorError` and distinct subclasses `UnknownRoleError`, `MissingWorkspaceError`, `MissingModelAssignmentError`, `MissingModelCredentialsError`, `InvalidExecutePayloadError`, `UnsafeWorkspaceWriteError` in `personalAgent/src/hermes_kanban/executor.py`. Do not swallow adapter/registry/workspace errors into one type — those propagate unchanged except missing workspace (mapped later).
- [X] T004 Add frozen dataclasses `ExecutePayload`, `AssembledContext`, `ModelResponse`, `ExecuteResult`, and `ExecutionSettings` in `personalAgent/src/hermes_kanban/executor.py` matching [data-model.md](./data-model.md). `ExecutePayload`: `title`, `description`, `acceptance_criteria`, `priority`, `plan`, `validation` (all `str | None`). `AssembledContext`: task slice (`id` plus optional fields as `str`), `project_id`, `project_name`, `repository`, `default_branch`, `project_context` (`ProjectContext`), `workspace_path` (`Path`), `workspace_branch`, `methodology_path`, `revision` (`Revision`), `workflow_name`, `workflow_phase`, `agent` (`AgentDefinition`), `dependencies` (`tuple[AgentDependency, ...]`), `previous_plan`, `previous_validation` (`str | None`), `model_assignment`. `ModelResponse`: `summary`, `files` (`dict[str, str]`), `commit` (`bool`), `plan_markdown` (`str | None`), `next_action` (`str | None`), `questions` (`tuple[str, ...]`), `status` (`str | None`). `ExecuteResult`: `status`, `summary`, `artifacts` (`tuple[Path, ...]`), `next_action` (`str | None`), `questions`, `identity` (`CorrelationIdentity`), `model_assignment`, `validation` (`str | None` — present only for validation role). `ExecutionSettings`: `workflow_name`, `role_agents` (`dict[str, str]`), `model_roles` (`dict[str, str]`), `base_url_env`, `api_key_env`. Type-annotate public APIs. No reasoning/transcript/secret fields.
- [X] T005 Implement `ExecutionSettings.from_config(config_path: Path)` in `personalAgent/src/hermes_kanban/executor.py`. Import and reuse `projects._parse_document` on the file text — do not add a third YAML scanner and do not add PyYAML. Read only `workflow.default` (default `piv` when omitted, must be non-empty), optional `roles.*` (apply defaults discovery→`scout`, planning→`specs-planner`, implementation→`builder`, validation→`tester`), `model.roles.{planning,implementation,validation}` (values MAY be empty at construction), and `model.openai_compatible.base_url_env` / `api_key_env`. Ignore other keys. Unreadable file → `ExecutorError`. MUST NOT invent model ids, MUST NOT substitute `$HOME` / `WORKSPACE_ROOT` / `AINATIVE_PATH` / `/workspaces`. Role names other than the four are not stored.
- [X] T006 Add `ModelService` Protocol (`complete(*, assignment: str, context: AssembledContext) -> ModelResponse`), stdlib `OpenAICompatibleModelService` (`urllib.request` POST `{base_url}/v1/chat/completions`, parse JSON into `ModelResponse`; parse failure is a completed run with `status=failure`, not an invented success), a small `_git` helper (`git -C <repo>` via `subprocess`; later callers: `status`, `add`, `commit`; this module MUST NOT call `push`, `reset --hard`, `clean`, `clone`, `init`, `worktree remove`, or enrolled `checkout`), and `AgentExecutor.__init__(adapter, registry, workspaces, settings, model_service)` / `AgentExecutor.from_config(config_path, *, model_service=None)` in `personalAgent/src/hermes_kanban/executor.py`. `from_config` builds `AiNativeAdapter.from_config`, `ProjectRegistry.from_config`, `WorkspaceManager.from_config`, and `ExecutionSettings.from_config` from the same path; omitted `model_service` → live client using env **names** from settings (do not read env at construction). Checks will inject a stand-in. `ponytail:` single-shot structured response (no tool loop, no streaming); upgrade is a Hermes-native tool-using worker later. Do not extract `hermes_kanban/git.py` or `executor/`.
- [X] T007 [P] Re-export `AgentExecutor`, `ExecutionSettings`, `ExecutePayload`, `AssembledContext`, `ModelResponse`, `ExecuteResult`, `ModelService`, and the executor error classes from `personalAgent/src/hermes_kanban/__init__.py`. Keep every existing adapter, registry, and workspace export.

**Checkpoint**: Foundation ready — `from_config` wires adapter + registry + workspace manager + settings; user story implementation can begin

---

## Phase 3: User Story 1 - Execute a named agent with a complete context (Priority: P1) 🎯 MVP

**Goal**: Callers can `execute_agent` for a listed methodology agent against one eligible project and one already-prepared workspace, with assembled context from adapters plus an optional execute payload, and a result whose worker identity is the agent that ran.

**Independent Test**: Prepare a fixture workspace for an eligible project and task `123`. Point the executor at a fixture methodology that lists `scout`. Execute `scout` with a fixture task payload. Confirm assembled context includes non-empty task, project, workspace, methodology revision (including commit SHA), and the scout definition. Confirm `worker_id` is `scout`. Omit previous-step outputs and confirm those slots are empty rather than invented. Supply a plan on the payload and confirm it is present unchanged.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [US1] Add contract tests in `personalAgent/tests/test_agent_executor.py` with helpers that: copy `tests/fixtures/ainative-full/` into `tmp_path` and `git init` + commit; copy `tests/fixtures/projects/standard/` into `tmp_path`, `git init`, set local `user.email`/`user.name`, commit; write operational YAML (`workspace.root` = a temp dir, `ainative.path` = the temp methodology, `projects:` listing the enrolled fixture, `model.roles.planning` / `implementation` / `validation` = **test** id strings such as `test-planning-model`, not production names); construct `WorkspaceManager` + `prepare_workspace` for task `123`; construct `AgentExecutor(..., model_service=stand_in)` where the stand-in is an in-test class returning a predetermined `ModelResponse` (no network, no env). Cover: `execute_agent("scout", ...)` returns a result; assembled context has non-empty `task.id`, `project_id`, `workspace_path`, `workspace_branch` (`feature/task-123`, not `main`/`master`/default), methodology path, non-empty `revision.sha`, and scout `agent`; `identity.worker_id == "scout"`; `identity.workspace_id == "ws-{project_id}-123"`; `identity.execution_id` is a new UUID hex (this execute, not prepare); omitted payload → `previous_plan` / `previous_validation` are `None` and optional task fields are `""`; supplied `payload.plan` is present unchanged; scout supporting skills match `resolve_agent_dependencies` (not a second copy of methodology on disk); result dataclass has no reasoning/transcript/secret attributes. Tests MUST NOT set `OPENAI_API_KEY`, MUST NOT bind a hardcoded workstation path, and MUST NOT use a live production repo. Stand-in without env MUST succeed.

### Implementation for User Story 1

- [X] T009 [US1] Implement `execute_agent(name, project_id, task_id, *, payload=None)` gates in `personalAgent/src/hermes_kanban/executor.py` **before** the model is asked, in order: empty/path-like `task_id` → existing `InvalidTaskIdError` (reuse `projects._path_like_id`; do not join the raw id onto a filesystem path); `registry.resolve_eligible_project` then `load_project_context` (propagate `UnknownProjectError` / `DisabledProjectError` / `InvalidProjectLocationError` / `MissingProjectConfigurationError` unchanged); `workspaces.inspect_workspace(project_id, task_id)` — MUST NOT call `prepare_workspace`; dirty copy is allowed; `adapter.get_agent(name)` then `resolve_agent_dependencies` (unknown/reserved/path-like → existing `UnknownAgentError`; unresolved → `UnresolvedDependencyError`; MUST NOT join a caller-supplied name onto a path; MUST NOT run a partial context); `capture_revision` / `build_execution_context` with `workflow_phase="agent"`; resolve model assignment from the **planning** slot (bare `execute_agent`); empty/missing → leave for US3, but US1 tests always provide a non-empty planning id. Import `_path_like_id` rather than copying a third path-like variant.
- [X] T010 [US1] Assemble `AssembledContext` and complete the run in `personalAgent/src/hermes_kanban/executor.py`: task `id` = `task_id`; optional payload fields become `""` or `None` (plan/validation) when omitted — MUST NOT invent; MUST NOT read `kanban.db`; project fields from loaded `ProjectContext`; workspace path/branch from inspect; methodology path + `Revision`; `workflow_name` from settings; `agent` + `dependencies` from the adapter; `model_assignment` = the planning-slot id; call `model_service.complete(assignment=..., context=...)`; return `ExecuteResult` with explicit `status` (`success` when the stand-in/model response is usable; invalid/omitted model `status` → `success` if the run completed), `summary` / `next_action` / `questions` from the response, empty `artifacts` for this story, `identity` (`CorrelationIdentity` with `worker_id` = the agent name, `workspace_id` = `ws-{project_id}-{task_id}`, new `execution_id` UUID hex per execute), `model_assignment` tagged, `validation=None`. MUST NOT put private reasoning, transcripts, or env secrets on the result. Do not write `PLAN.md` yet. Do not apply files or commit yet. Do not run validation commands yet.

**Checkpoint**: User Story 1 is independently testable via `execute_agent("scout")` + payload omit/supply + identity, without role mapping, plan artifact, file writes, or refuse-missing-assignment

---

## Phase 4: User Story 2 - Return a structured result for planning, implementation, and validation (Priority: P1)

**Goal**: `execute_role` maps the four roles onto methodology agents. Every completed run has an explicit status. Planning writes eight-section `PLAN.md` in the isolated copy. Implementation may write/commit only there. Validation status comes from declared command exits, not model prose.

**Independent Test**: On a fixture project with declared validation checks, execute planning, then implementation with that plan on the payload, then validation. Confirm `PLAN.md` is in the isolated copy with the required sections, implementation changed only that copy (local commit allowed), validation status comes from the project’s own commands, and every result has an explicit status. Execute discovery and confirm no eight-section plan is required. Map planning to a name that is not in the fixture roster and confirm unknown-agent failure.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [US2] Extend `personalAgent/tests/test_agent_executor.py`: successful execute result has `status` in `{success, failure, blocked}`, a `summary`, `artifacts` (tuple, possibly empty), `next_action` (possibly `None`), `questions` (possibly empty) — status MUST NOT be inferred only from summary prose; `execute_role("planning", ...)` writes `{workspace}/PLAN.md` with all eight `## ` sections (Problem understanding; Scope; Likely affected parts; Implementation approach; Acceptance-criteria mapping; Validation strategy; Risks; Open questions), lists that absolute path on `artifacts`, and a claimed-success body missing a section is `status=failure`; `execute_role("discovery", ...)` succeeds without requiring `PLAN.md`; `execute_role("implementation", ...)` with `payload.plan` set and stand-in `files` + `commit=True` writes/commits only under the worktree on `feature/task-123`, enrolled HEAD/branch/files unchanged, 0 `git push`; `execute_role("validation", ...)` runs the enrolled manifest’s commands with `cwd` = isolated copy — override the copied project’s `.ainative/project.yaml` validation commands to `true` / `false` / a missing binary so the contract does not need the fixture to be a Python package; all-zero → `validation=pass` and `status=success`; non-zero → `fail`/`failure`; cannot-start → `blocked`/`blocked`; stand-in prose claiming the opposite MUST NOT win; empty/missing commands still fail at `load_project_context` (`MissingProjectConfigurationError`), never invent generic checks; `execute_role("planning")` with roles remapped to a name not in the fixture roster → `UnknownAgentError` and no publish; unknown role name → `UnknownRoleError`. Same tmp_path / stand-in / no `OPENAI_API_KEY` rules as T008.

### Implementation for User Story 2

- [X] T012 [US2] Implement `execute_role(role, project_id, task_id, *, payload=None)` and planning-artifact + result-shape rules in `personalAgent/src/hermes_kanban/executor.py`: `role` MUST be `discovery` | `planning` | `implementation` | `validation` else `UnknownRoleError`; map through `settings.role_agents` then the same path as `execute_agent`; `workflow_phase` = the role; discovery and planning use the planning model slot (implementation/validation slots in US3 tagging). After `ModelResponse`, a **planning** run writes `{workspace_path}/PLAN.md` from `plan_markdown` (create the file even when sections are missing) and lists that path on `artifacts` only when all eight headings match (ATX `## `, case-insensitive, punctuation/whitespace stripped). Missing required sections → `status=failure` (do not treat as success). Discovery MUST NOT require this file. Planner how-to text is passed through as document text — MUST NOT install a planning framework into the control plane. Result `status` is the closed set `success`/`failure`/`blocked`; `artifacts` / `next_action` / `questions` always present (empty/`None` as allowed).
- [X] T013 [US2] Implement implementation file applies and optional local commit in `personalAgent/src/hermes_kanban/executor.py`: `ModelResponse.files` are workspace-relative UTF-8 paths; resolve each path and require it stays inside the isolated working copy (all-or-nothing: check every path before writing any); apply writes only in that copy; if `commit` is true **and** role is `implementation`, `assert_publish_allowed(inspect.branch, default_branch=...)` then `_git add -A` and `_git commit` **in the isolated copy only**. MUST NOT `push`, open a PR, merge, deploy, edit the enrolled location, or `checkout` enrolled HEAD. Non-implementation roles ignore `commit`. Enrolled location HEAD/branch must remain unchanged. `ponytail:` whole-file writes from the model list (no tool loop); upgrade is a Hermes-native tool-using worker.
- [X] T014 [US2] Implement validation-from-commands in `personalAgent/src/hermes_kanban/executor.py` for the `validation` role: after context assembly and the model-assignment gate, still call `ModelService.complete` (assignment gate applies; summary/questions may come from the model) then run `ProjectContext.validation_commands` in order with `cwd=workspace.path`, `shlex.split` each string, `subprocess.run` (**no** `shell=True`). Do not invent commands. Empty/missing already fail at `load_project_context`. All exit 0 → `result.validation=pass`, `status=success`; first executable missing / cannot start → `blocked`/`blocked`; first non-zero → `fail`/`failure`. Stop at the first non-success. **Overwrite** any status the model claimed. Capture stdout/stderr only for the model prompt; do not put transcripts on the result. `ponytail:` no subprocess timeout; upgrade is a bounded timeout when a project check hangs.

**Checkpoint**: User Stories 1 and 2 both work independently — named execute plus planning/implementation/validation role outcomes with explicit status

---

## Phase 5: User Story 3 - Assign models by role and refuse unsafe or incomplete runs (Priority: P1)

**Goal**: Each role uses its configured model assignment (discovery uses planning). Missing assignment, missing workspace, methodology writes, protected work branches, and publish are refused at the execute trust boundary. Agent documents are never the model source.

**Independent Test**: Execute planning and implementation with different configured model assignments and confirm each run is tagged with its role’s assignment (not a name from agent documents). Remove the assignment and confirm failure. Attempt a methodology write through the executor and confirm failure. Execute without a prepared workspace and confirm failure (no copy created). Confirm the work branch was never `main`/`master`/project default and that no publish occurred.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [US3] Extend `personalAgent/tests/test_agent_executor.py`: planning vs implementation with different `model.roles` ids → each `ExecuteResult.model_assignment` (and context assignment) equals that role’s id, not a string copied from AGENTS.md/SKILL.md; omitted/empty `model.roles.planning` (and discovery / bare `execute_agent`) → `MissingModelAssignmentError` and the model is not asked; same for empty implementation/validation slots on those roles; live `AgentExecutor.from_config` without injected stand-in and with empty/missing `OPENAI_BASE_URL` or `OPENAI_API_KEY` (or the configured env names) → `MissingModelCredentialsError` at execute; stand-in still succeeds with those env vars unset; model-requested write under the methodology path → `ReadOnlyError`, methodology tree unchanged; path that escapes the worktree or targets the enrolled location → `UnsafeWorkspaceWriteError`, enrolled tree unchanged; `execute_*` when no worktree exists for the task → `MissingWorkspaceError`, `prepare_workspace` was not called, no directory created under `workspace.root`; inspect of a protected branch (`main`/`master`/project default) → `ProtectedBranchError` and no checkout onto that branch; after any execute, executor performed 0 publishes (`push` / PR / remote update); path-like / reserved agent names (`template`, `_skills`, `../`) → `UnknownAgentError` with no filesystem join of the raw name; unknown / disabled / bad project → existing registry errors, no invented project path; secrets/env values absent from result/identity/summary. Tests MUST NOT require a live model account.

### Implementation for User Story 3

- [X] T016 [US3] Finish per-role model assignment in `personalAgent/src/hermes_kanban/executor.py`: slots `planning` / `implementation` / `validation`; discovery **and** bare `execute_agent` use the planning slot; missing or empty id → `MissingModelAssignmentError` before `complete` (MUST NOT invent a model or skip the service). Tag `AssembledContext.model_assignment` and `ExecuteResult.model_assignment` with that id, never the API key, never a name parsed from agent Markdown. Live client: missing/empty env value for `base_url_env` or `api_key_env` at execute → `MissingModelCredentialsError`; stand-in MUST NOT read those env vars. Do not read a debugging slot.
- [X] T017 [US3] Finish execute trust-boundary refuses in `personalAgent/src/hermes_kanban/executor.py`: wrap inspect failure (missing / not a git copy / wrong task) as `MissingWorkspaceError` — MUST NOT call `prepare_workspace`, MUST NOT create a working copy; after inspect, `assert_publish_allowed(inspection.branch, default_branch=...)` so a protected work branch never proceeds; file-apply path checks: resolved path under methodology → existing `ReadOnlyError` (methodology unchanged; do not copy methodology into the workspace or into `personalAgent/`); path outside the isolated copy or into the enrolled location → `UnsafeWorkspaceWriteError`; all-or-nothing (no partial writes). MUST NOT `git push`, open a PR, merge, deploy, or depend on a specific editor. MUST NOT execute instruction documents as programs. Do not write `kanban.db` / `projects.db`.

**Checkpoint**: All three user stories are independently functional. Stop — do not start PIV orchestration, GitHub hosting, or Telegram

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the seven SC-007 checks, keep existing packages green, and refuse silent production targeting

- [X] T018 Keep existing checks green from `personalAgent/`: `uv run pytest tests/test_import.py tests/test_ainative_adapter.py tests/test_project_registry.py tests/test_workspace_manager.py`. Do not rewrite `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/src/hermes_kanban/projects.py`, or `personalAgent/src/hermes_kanban/workspace.py`. Confirm `test_import.py` still imports the package and that new executor names remain re-exported from `personalAgent/src/hermes_kanban/__init__.py`.
- [X] T019 Run the quickstart validation from `personalAgent/`: `uv run pytest tests/test_agent_executor.py` and `uv run ruff check src tests`. Fix any contract or lint failure in `personalAgent/src/hermes_kanban/executor.py` / `personalAgent/tests/test_agent_executor.py`.
- [X] T020 Confirm `personalAgent/config/default.yaml` still has `projects: []`, no live model name literals as required values, no host-specific path; this diff does not read/write Hermes `projects.db` / `kanban.db`, adds no new dependency in `personalAgent/pyproject.toml`, and does not add `specs-planner` / `builder` / `debugger` to live AiNative.
- [X] T021 Confirm `personalAgent/src/hermes_kanban/executor.py` never invokes `git push`, `reset --hard`, `clean`, `clone`, `init`, or `prepare_workspace`. Tests create git and methodology fixtures only under `tmp_path`. Production module contains no provider/model name literals.
- [X] T022 [P] Stop after executor contract checks pass. Do not start PIV chaining, GitHub push/PR, Telegram, retry/debug, or adding agents to live methodology. Do not change `personalAgent/docker-compose.yml`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP `execute_agent` + context + payload + identity
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (`execute_agent` path exists); adds roles and role outcomes
- **User Story 3 (Phase 5)**: Depends on Foundational + US1; sequenced after US2 so file-apply / validation exist before methodology-write and assignment-refuse attach
- **Polish (Phase 6)**: Depends on the stories being delivered

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependency on US2/US3
- **User Story 2 (P1)**: Depends on US1 execute; independently testable once `execute_role`, `PLAN.md`, isolated writes/commit, and command-derived validation exist
- **User Story 3 (P1)**: Depends on US1 execute (and US2 writes for methodology-refuse); independently testable via assignment tags + refuse paths

### Within Each User Story

- Tests MUST be written and FAIL before that story’s implementation
- Types/errors/settings/construction before execute
- Gates before `ModelService.complete`
- Context + identity before planning writes / file applies / validation commands
- `execute_role` + result shape before implementation commit and validation exits
- Model-assignment tagging and refuse paths after the happy-path roles work
- Story complete before moving to the next increment

### Parallel Opportunities

- T001 and T002 are different files and can run in parallel
- T007 is a different file from T006 and can run after T003–T006
- T018–T021 share verification; T022 is independent of T021 once implementation is done
- Test tasks T008, T011, T015 share `personalAgent/tests/test_agent_executor.py` — sequential
- Implementation tasks T003–T006, T009–T010, T012–T014, T016–T017 share `personalAgent/src/hermes_kanban/executor.py` — sequential
- US1/US2/US3 cannot be staffed in true parallel: they share one module and one test file. A single implementer should run them sequentially

---

## Parallel Example: User Story 1

```bash
# After Foundational (T007 is the only other-file task):
Task: "Re-export public executor types from personalAgent/src/hermes_kanban/__init__.py"

# US1 tests then implementation are sequential (same two files):
Task: "Contract tests in personalAgent/tests/test_agent_executor.py"
Task: "Implement execute_agent gates in personalAgent/src/hermes_kanban/executor.py"
Task: "Assemble context and return identity in personalAgent/src/hermes_kanban/executor.py"
```

---

## Parallel Example: User Story 2

```bash
# After US1 execute exists — still one test file then one module:
Task: "Role-outcome contract tests in personalAgent/tests/test_agent_executor.py"
Task: "Implement execute_role + PLAN.md in personalAgent/src/hermes_kanban/executor.py"
Task: "Implement isolated writes/commit in personalAgent/src/hermes_kanban/executor.py"
Task: "Implement validation-from-commands in personalAgent/src/hermes_kanban/executor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (fixture `specs-planner`/`builder`; config has no live model names)
2. Complete Phase 2: Foundational (types, settings, ModelService protocol, construction, re-exports)
3. Complete Phase 3: User Story 1 (`execute_agent` + assembled context + payload + identity)
4. **STOP and VALIDATE**: scout execute on a prepared fixture workspace; payload omit vs supply; `worker_id` is `scout`
5. Demo on a disposable fixture; do not enroll a production repo; do not set `OPENAI_API_KEY`

### Incremental Delivery

1. Setup + Foundational → construction wires existing adapters + stand-in/live seam
2. Add US1 → first execute independently → MVP
3. Add US2 → planning artifact, isolated implementation writes/commit, validation from commands
4. Add US3 → role model tags + refuse missing assignment/workspace/methodology write/publish
5. Each story adds value without starting PIV, GitHub, or Telegram

### Parallel Team Strategy

This feature is one module plus one test file. Prefer a single implementer moving story-by-story. If two people: one owns fixture/stand-in tests, the other owns `executor.py`, integrating at each checkpoint. Do not split `executor.py` into extra packages to create false parallelism.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec user stories US1–US3
- Public names are `execute_agent`, `execute_role`
- Roles: `discovery` → `scout`, `planning` → `specs-planner`, `implementation` → `builder`, `validation` → `tester`
- Discovery uses the planning model slot; debugging is out of scope
- Plan artifact is `{workspace}/PLAN.md` with eight required sections
- Execute inspects; it MUST NOT call `prepare_workspace`
- Validation status comes from command exits (`shlex.split`, `cwd=workspace.path`)
- Local commit only on the task work branch in the isolated copy; 0 publishes
- Production `projects: []` until the owner names a non-critical repo
- Commit after each task or logical group if the owner asks; Conventional Commits (`feat:`, `test:`)
- Stop at any checkpoint to validate the story independently
- Avoid: second SQLite store, openai SDK, PyYAML, hardcoded model names, adding agents to live AiNative, rewriting adapter/registry/workspace, starting PIV/GitHub/Telegram

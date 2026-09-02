---
description: "Task list for AiNative Adapter implementation"
---

# Tasks: AiNative Adapter

**Input**: Design documents from `/specs/001-ainative-adapter/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ainative-adapter.md](./contracts/ainative-adapter.md), [quickstart.md](./quickstart.md)

**Tests**: Included. Spec SC-006, constitution IV, and the plan require one pytest contract module (`personalAgent/tests/test_ainative_adapter.py`) plus a fixture tree. Write tests first in each story; they MUST fail before implementation.

**Organization**: Tasks are grouped by user story. Implementation is one module (`personalAgent/src/hermes_kanban/ainative.py`) plus one test file — do not split into an `adapters/` package. Stop after adapter checks pass; do not start registry, workspaces, PIV, GitHub, Telegram, or `execute_agent`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Control-plane package: `personalAgent/src/hermes_kanban/`
- Checks: `personalAgent/tests/`
- Fixture methodology (documents only): `personalAgent/tests/fixtures/ainative/`
- Operational config already has `ainative.path` / `ainative.read_only` in `personalAgent/config/default.yaml` — do not hardcode host paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Committed fixture methodology so tests never depend on a live AiNative mount

- [X] T001 Create fixture methodology tree in `personalAgent/tests/fixtures/ainative/docs/8-agents/` with `scout/`, `tester/`, `critic/` (each `AGENTS.md`, `SKILL.md`, `rule.md`; scout `SKILL.md` contains `<!-- source: _skills/research-first/SKILL.md -->`), reserved `template/`, `_skills/research-first/SKILL.md`, `broken-deps/` (how-to references `_skills/missing-skill/SKILL.md`), and `empty-agent/` (no instruction files)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Trust-boundary types and construction. No user story can construct an adapter until this is done.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `AiNativeAdapterError` and subclasses (`InvalidMethodologyError`, `UnknownAgentError`, `IncompleteAgentError`, `UnresolvedDependencyError`, `RevisionError`, `ReadOnlyError`) in `personalAgent/src/hermes_kanban/ainative.py`
- [X] T003 Implement `AiNativeSettings` and `load_ainative_settings` (stdlib line scan of the `ainative:` block only: `path`, `read_only`; `ponytail:` two-scalar YAML subset) in `personalAgent/src/hermes_kanban/ainative.py`
- [X] T004 Implement `AiNativeAdapter.__init__` and `from_config` in `personalAgent/src/hermes_kanban/ainative.py` so missing/empty/non-dir path, missing `docs/8-agents/`, unreadable config, and `read_only` not true raise `InvalidMethodologyError` with no fallback path

**Checkpoint**: Foundation ready — a valid fixture path with `read_only=True` constructs; invalid settings fail at the boundary

---

## Phase 3: User Story 1 - Discover and load an agent by name (Priority: P1) 🎯 MVP

**Goal**: List roster names, load purpose/how-to/constraints as separate raw-text fields, resolve rule + referenced skills, reject unknown/reserved/path-like names

**Independent Test**: Point the adapter at the fixture tree. `list_agents()` includes `scout`, `tester`, `critic` and excludes `template` and `_skills`. `get_agent("scout")` has separate `purpose` / `howto` / `constraints` text (no concatenated blob). `template`, `_skills`, `../x`, and `a/b` raise `UnknownAgentError`. Resolve of `broken-deps` raises `UnresolvedDependencyError` with no partial list.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [US1] Add a tmp-copy + `git init` helper and contract tests for `list_agents` / `get_agent` (scout fields, omitted missing files, no instruction blob, `empty-agent` → `IncompleteAgentError`, reserved and path-like names → `UnknownAgentError`) in `personalAgent/tests/test_ainative_adapter.py`
- [X] T006 [US1] Add contract tests for `resolve_agent_dependencies` (scout returns `rule` + `research-first` skill items with kind/name/path/text; `broken-deps` → `UnresolvedDependencyError`; reserved names unknown) in `personalAgent/tests/test_ainative_adapter.py`

### Implementation for User Story 1

- [X] T007 [US1] Implement `AgentDefinition` and `list_agents` (sorted immediate subdirs of `docs/8-agents/`, skip `template` / `_skills` / non-directories) in `personalAgent/src/hermes_kanban/ainative.py`
- [X] T008 [US1] Implement `get_agent` in `personalAgent/src/hermes_kanban/ainative.py`: allowlist name against `list_agents()` before any path join; map `AGENTS.md`/`SKILL.md`/`rule.md` to optional path + `purpose`/`howto`/`constraints` raw text; none present or unreadable → `IncompleteAgentError`
- [X] T009 [US1] Implement `AgentDependency` and `resolve_agent_dependencies` in `personalAgent/src/hermes_kanban/ainative.py`: include `rule.md` as `kind="rule"` when present; unique `<!-- source: _skills/<name>/SKILL.md -->` from how-to as `kind="skill"`; missing/unreadable skill → `UnresolvedDependencyError` (no partial list)

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 - Stamp methodology revision onto execution context (Priority: P1)

**Goal**: Capture `{repository, sha, branch, dirty}` via `git` CLI and build an execution context that always includes methodology path, revision, and agent (workflow phase if supplied; no invented task/project/workspace)

**Independent Test**: Build a context for scout against a git-initialized fixture copy. Context has configured path, non-empty `sha`, `repository`, `branch` or `"detached"`, and `dirty`. Dirty working tree still succeeds with `dirty=True`. Non-git path raises `RevisionError`. Optional `workflow_phase` is echoed unchanged.

### Tests for User Story 2 ⚠️

- [X] T010 [US2] Add contract tests for `capture_revision` in `personalAgent/tests/test_ainative_adapter.py` (non-empty sha/repository/branch-or-detached, dirty fixture → success + `dirty=True`, non-git directory → `RevisionError`)
- [X] T011 [US2] Add contract tests for `build_execution_context` in `personalAgent/tests/test_ainative_adapter.py` (configured `methodology_path`, revision, given agent, optional `workflow_phase`; no task/project/workspace fields)

### Implementation for User Story 2

- [X] T012 [US2] Implement `Revision` and `capture_revision` in `personalAgent/src/hermes_kanban/ainative.py` using `git -C`: `rev-parse HEAD` → `sha`; `--abbrev-ref HEAD` (`HEAD` → `"detached"`); `remote get-url origin` else path string; `status --porcelain` non-empty → `dirty=True`; not a work tree → `RevisionError`
- [X] T013 [US2] Implement `ExecutionContext` and `build_execution_context` in `personalAgent/src/hermes_kanban/ainative.py` (`methodology_path` from settings, `revision` from `capture_revision(settings.path)`, store given agent, `workflow_phase` only when not `None`; omit task/project/workspace)

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 - Refuse writes and reject a missing methodology location (Priority: P1)

**Goal**: Construction already fails on invalid location (Phase 2). This story adds testable write refusal and the remaining trust-boundary checks so SC-004 / SC-005 / SC-006 hold.

**Independent Test**: Construct with missing/empty/non-dir/`read_only: false`/missing `docs/8-agents/` and confirm `InvalidMethodologyError` with no substitute path. On a valid adapter, `write_file` and `copy_tree` raise `ReadOnlyError`; fixture tree unchanged.

### Tests for User Story 3 ⚠️

- [X] T014 [US3] Add contract tests for `InvalidMethodologyError` at construction/`from_config` in `personalAgent/tests/test_ainative_adapter.py` (missing path, empty path, file-not-dir, missing `docs/8-agents/`, `read_only: false`, unreadable config; assert no substitute location)
- [X] T015 [US3] Add contract tests that `write_file` and `copy_tree` raise `ReadOnlyError` and leave `personalAgent/tests/fixtures/ainative/` (and the tmp copy) unchanged in `personalAgent/tests/test_ainative_adapter.py`

### Implementation for User Story 3

- [X] T016 [US3] Implement `write_file` and `copy_tree` on `AiNativeAdapter` in `personalAgent/src/hermes_kanban/ainative.py` to raise `ReadOnlyError` before any create/modify/delete/copy/`mkdir`

**Checkpoint**: All three user stories are independently functional; SC-006 five checks are covered

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Package surface, optional live-mount check, quickstart validation. Do not start other V0 phases.

- [X] T017 Re-export public types (`AiNativeSettings`, `load_ainative_settings`, `AiNativeAdapter`, `AgentDefinition`, `AgentDependency`, `Revision`, `ExecutionContext`, errors) from `personalAgent/src/hermes_kanban/__init__.py`
- [X] T018 Add optional live-mount `list_agents` test in `personalAgent/tests/test_ainative_adapter.py` (skip if `/ainative` and `AINATIVE_PATH` are absent; if present, listed names MUST be a subset of real folders; do not require `specs-planner`)
- [X] T019 Confirm `personalAgent/tests/test_import.py` still passes and no methodology copies exist under `personalAgent/` outside `personalAgent/tests/fixtures/ainative/`
- [X] T020 Run quickstart.md validation in `personalAgent/`: `uv run pytest tests/test_ainative_adapter.py tests/test_import.py` and `uv run ruff check src tests`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (fixture path exists for manual checks; construction code does not import the fixture) — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - Sequential in this repo: one module (`ainative.py`) and one test file, so stories cannot be edited in parallel without colliding
  - Priority order: US1 (MVP) → US2 → US3
- **Polish (Phase 6)**: Depends on US1–US3

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational; `build_execution_context` takes an `AgentDefinition` (from US1 `get_agent` or a constructed instance). Independently testable once US1 types exist
- **User Story 3 (P1)**: Construction failures are implemented in Phase 2; this story adds write APIs and the remaining contract tests. Independently testable without list/load/revision

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Types before methods (`AgentDefinition` before `get_agent`, `Revision` before `capture_revision`)
- Name allowlist before any path join
- Story complete before moving to the next

### Parallel Opportunities

- Almost none after Setup: `ainative.py` and `test_ainative_adapter.py` are shared. Do not mark same-file tasks `[P]`
- T001 (fixture documents) is the only isolated file-tree task
- T017 (`__init__.py`) can wait until types exist; do not parallel it with T007–T016 in the same file as tests

---

## Parallel Example: User Story 1

```bash
# Same-file story — run sequentially, not in parallel:
Task: "Add list/get_agent contract tests in personalAgent/tests/test_ainative_adapter.py"
Task: "Add resolve_agent_dependencies contract tests in personalAgent/tests/test_ainative_adapter.py"
Task: "Implement list_agents in personalAgent/src/hermes_kanban/ainative.py"
Task: "Implement get_agent in personalAgent/src/hermes_kanban/ainative.py"
Task: "Implement resolve_agent_dependencies in personalAgent/src/hermes_kanban/ainative.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (fixture tree)
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: pytest for list/load/resolve only
5. Demo: operator can list agents and load scout’s three instruction fields

### Incremental Delivery

1. Setup + Foundational → adapter constructs or fails at the boundary
2. Add User Story 1 → Test independently → MVP (discovery + load)
3. Add User Story 2 → Test independently → revision-stamped context
4. Add User Story 3 → Test independently → refused writes (SC-006 complete)
5. Polish → quickstart.md green. **Stop.** Do not start registry, workspaces, or PIV

### Parallel Team Strategy

Not applicable: one production file, one test file. One implementer, sequential by story.

---

## Notes

- `[P]` is unused: all implementation/tests share two files. That is intentional (constitution II / research: one module)
- `[Story]` label maps task to spec user stories US1–US3 (all P1; US1 is the MVP slice)
- Public names: `list_agents`, `get_agent`, `resolve_agent_dependencies`, `capture_revision`, `build_execution_context`, refused `write_file` / `copy_tree`
- Skill references: `<!-- source: _skills/<name>/SKILL.md -->`
- Dirty revision: succeed with `dirty=True`
- No new dependencies. No hardcoded workstation paths. Isolated Hermes home untouched

---

## Phase 7: Convergence

- [X] T021 CRITICAL Mark the two-scalar YAML subset in `load_ainative_settings` with a `ponytail:` comment naming the ceiling (two scalars; no nested YAML, quotes, or aliases) and the PyYAML upgrade path in `personalAgent/src/hermes_kanban/ainative.py` per Constitution II (missing)
- [X] T022 Reject empty and whitespace-only methodology paths at the trust boundary in `personalAgent/src/hermes_kanban/ainative.py` before `Path` resolution so they cannot bind to cwd; extend `personalAgent/tests/test_ainative_adapter.py` so empty path still raises `InvalidMethodologyError` when cwd contains `docs/8-agents/` per FR-002 (contradicts)

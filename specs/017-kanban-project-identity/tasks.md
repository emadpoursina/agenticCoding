---
description: "Implementation task list for Kanban Project Identity Mapping"
---

# Tasks: Kanban Project Identity Mapping

**Input**: Design documents from `/specs/017-kanban-project-identity/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/project-identity.md`, and `quickstart.md`

**Tests**: Test tasks are included because FR-012 and SC-001–SC-006 require focused resolution, translation, identity, reporting, and recovery checks. Write the focused checks with the matching implementation in each user-story phase.

**Organization**: Tasks are grouped by user story so each slice can be implemented and verified independently.

**Scope boundary**: No native `projects.db` write, no `kanban.db` write, no second project/task store, no runtime `projects.db` read, and no fuzzy or display-name matching. Protected-branch, merge, and deploy limits are unchanged.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other marked tasks after listed dependencies
- **[Story]**: Maps a task to US1–US3; setup, foundational, and polish tasks have no story label
- Every task names the exact file or command surface it changes or verifies

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing package surfaces and the configuration points the mapping touches.

- [X] T001 [P] Confirm the Python 3.12/uv package, pytest, Ruff, registry, board, runtime, orchestrator, config, and test surfaces in `personalAgent/pyproject.toml`, `personalAgent/src/hermes_kanban/projects.py`, `personalAgent/src/hermes_kanban/board.py`, `personalAgent/src/hermes_kanban/runtime.py`, `personalAgent/src/hermes_kanban/orchestrator.py`, `personalAgent/config/default.yaml`, and `personalAgent/tests/`; preserve the existing dependency set.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the alias field, validation, and canonical resolver before any story behavior.

**⚠️ CRITICAL**: No user-story implementation should begin until this phase is complete.

- [X] T002 Add `kanban_project_ids: tuple[str, ...] = ()` as the last field of `ProjectRecord` in `personalAgent/src/hermes_kanban/projects.py`, keeping existing keyword construction and equality valid.
- [X] T003 Parse `kanban_project_ids` (scalar or list) in `load_project_entries` and reject empty, non-string, or path-like aliases in `personalAgent/src/hermes_kanban/projects.py`.
- [X] T004 Add the second-pass alias uniqueness check to `_validate_records` so no alias duplicates another alias or equals any project's operational id in `personalAgent/src/hermes_kanban/projects.py`.
- [X] T005 Build `_by_kanban_id` and implement `canonical_id(value) -> str` (operational id returns itself, alias maps to its operational id, otherwise `UnknownProjectError`) in `ProjectRegistry` in `personalAgent/src/hermes_kanban/projects.py`.
- [X] T006 Route `get_project` through `canonical_id` so `resolve_eligible_project` and `load_project_context` accept either form in `personalAgent/src/hermes_kanban/projects.py`.

**Checkpoint**: Aliases parse, validate, and resolve exactly; collisions and path-like values fail at construction.

## Phase 3: User Story 1 - Run a card whose project_id is the native id (Priority: P1) 🎯 MVP

**Goal**: A card carrying a declared native id selects and runs the enrolled project.

**Independent Test**: Seed a temporary `kanban.db` card with `project_id = p_fixture`, declare it as an alias, run `--next-ready`, and verify the harness starts and the worktree is under the operational id.

### Tests for User Story 1

- [X] T007 [US1] Add registry checks in `personalAgent/tests/test_project_registry.py` for alias resolution through `canonical_id`, `get_project`, `resolve_eligible_project`, and `load_project_context`, plus collision/path-like/empty/duplicate rejection.
- [X] T008 [US1] Add board and end-to-end checks in `personalAgent/tests/test_kanban_project_identity.py` for native-id translation at `SqliteTaskBoard`, `run_next_workflow` selection, worktree placement under the operational id, and a near-miss alias that must not resolve.

### Implementation for User Story 1

- [X] T009 [US1] Add the optional `resolve_project_id` parameter to `SqliteTaskBoard` and canonicalize `BoardTask.project_id` in `_task`, leaving undeclared ids unchanged, in `personalAgent/src/hermes_kanban/board.py`.
- [X] T010 [US1] Build the registry and pass a wrapped `canonical_id` resolver to `SqliteTaskBoard` on both the `HERMES_KANBAN_DB` and `HERMES_HOME` paths in `build_live_orchestrator` in `personalAgent/src/hermes_kanban/runtime.py`.

**Checkpoint**: A declared alias selects and runs the enrolled project, and no native id leaks past the board.

## Phase 4: User Story 2 - Keep one identity across records and restart (Priority: P1)

**Goal**: Overlay, workspace, publish, and status identities use the operational id, and restart recovery still finds the worktree.

**Independent Test**: Run a card to completion, reload the orchestrator from the overlay, and confirm reclaim resolves the same worktree and identities use the operational id.

### Tests for User Story 2

- [X] T011 [P] [US2] Add checks in `personalAgent/tests/test_kanban_project_identity.py` for `record.project_id`, overlay content, `CorrelationIdentity`, and publish identity using the operational id.
- [X] T012 [P] [US2] Add checks in `personalAgent/tests/test_kanban_project_identity.py` for resume with either id form and for reclaim of a legacy overlay whose `project_id` is an alias.

### Implementation for User Story 2

- [X] T013 [US2] Canonicalize the incoming `project_id` in `resume_workflow` before comparing to the parked record in `personalAgent/src/hermes_kanban/orchestrator.py`.
- [X] T014 [US2] Canonicalize a legacy `record.project_id` in `_board_record`/`become_ready` before the task-project mismatch check and reclaim path math in `personalAgent/src/hermes_kanban/orchestrator.py`.
- [X] T015 [US2] Confirm status output in `personalAgent/src/hermes_kanban/messaging.py` shows the operational id and that no edit is needed there or in `workspace.py` beyond receiving the canonical id.

**Checkpoint**: Every operational artifact and restart path uses the operational id.

## Phase 5: User Story 3 - Fail loudly on an unmapped id (Priority: P2)

**Goal**: An undeclared native id is named instead of silently producing "no ready task".

**Independent Test**: Seed a card with an undeclared native id, run `--next-ready`, and confirm the error names it and no GitHub action occurs.

### Tests for User Story 3

- [X] T016 [US3] Add checks in `personalAgent/tests/test_kanban_project_identity.py` for the `NoReadyTaskError` message naming the unmapped id, direct `--task` failing closed, and no push or pull request.

### Implementation for User Story 3

- [X] T017 [US3] Collect unmapped skipped card ids in `run_next_workflow` and include them in the `NoReadyTaskError` message in `personalAgent/src/hermes_kanban/orchestrator.py`.
- [X] T018 [US3] Add each project's declared aliases to `StartupDiagnostic` and render them in the `--doctor` output in `personalAgent/src/hermes_kanban/runtime.py` and `personalAgent/src/hermes_kanban/startup_context.py`.

**Checkpoint**: Unmapped ids fail closed and are named; `--doctor` lists declared aliases as metadata only.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete feature, update configuration and docs, and record delivery.

- [X] T019 [P] Declare `kanban_project_ids` for the enrolled project in `personalAgent/config/default.yaml`.
- [X] T020 [P] Document the field, the one-time `projects.db` discovery command, and the container-recreate step in `personalAgent/README.md`.
- [X] T021 [P] Run the focused and complete checks from `specs/017-kanban-project-identity/quickstart.md`; run `uv run pytest` and `uv run ruff check src tests` from `personalAgent/`.
- [X] T022 Update `personalAgent/CHANGELOG.md` and the root `CHANGELOG.md` with the semantic-version entry for the mapping fix.
- [X] T023 Re-read `specs/017-kanban-project-identity/spec.md`, `plan.md`, and `quickstart.md` against the implementation; confirm no native write, second store, or fuzzy matching was introduced.

---

## Phase 7: Live verification discoveries (2026-09-20)

**Purpose**: Record the two additional wiring gaps found and fixed while proving the feature on the live install.

- [X] T024 [P] Resolve the native Kanban database per enrolled project (`kanban/boards/<id>/kanban.db`) with legacy fallback in `personalAgent/src/hermes_kanban/runtime.py`, with path-resolution checks in `personalAgent/tests/test_kanban_project_identity.py`.
- [X] T025 [P] Sanitize drifted advisory result paths (bare-string artifacts, invalid changes/output references) in `personalAgent/src/hermes_kanban/pi.py`, replacing the run-killing rejection, with coercion checks in `personalAgent/tests/test_harness_adapter.py`.
- [X] T026 Prove the full pipeline live: `--doctor` exit 0 with the declared alias, card selection from the per-board database, a completed Pi run, project validation pass, feature-branch push, and PR #2 on the disposable practice repo.

---

## Dependencies & Execution Order

- T002–T006 (foundational) block all user-story work.
- US1 (T007–T010) is the MVP and blocks US2 runtime validation.
- US2 (T011–T015) and US3 (T016–T018) can proceed after T009–T010.
- Polish (T019–T023) runs after all story work and the full check gate.

## Parallel Opportunities

- T007 and T008 are separate files and can be written in parallel.
- T011 and T012 can be written in parallel.
- T019 and T020 are independent documentation/config edits.

## Implementation Strategy

1. Foundational alias contract first (T002–T006).
2. MVP: board translation plus live wiring (T007–T010); stop and verify selection and worktree placement.
3. Identity consistency and legacy recovery (T011–T015).
4. Fail-closed reporting and doctor output (T016–T018).
5. Config, docs, full gate, changelog (T019–T023).

## Notes

- Do not add a new dependency; use the standard library and existing pytest/ruff.
- Keep `ProjectRecord.id` as the only operational key; no worktree or overlay rename.
- Unmapped ids must stay fail-closed; the change is the report, not the safety behavior.

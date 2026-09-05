---

description: "Task list for Live Hermes PIV Bridge (read-only SqliteTaskBoard, dispatcher/CLI entry, named-repo smoke)"
---

# Tasks: Live Hermes PIV Bridge

**Input**: Design documents from `/specs/010-live-piv-bridge/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/live-piv-bridge.md, quickstart.md

**Tests**: Required. Spec FR-013–FR-015 / SC-001–SC-005 and constitution IV demand one pytest module (`personalAgent/tests/test_live_piv_bridge.py`) that fails if the live adapter, column eligibility, live constructor, chain-to-`PR_CREATED`, or smoke gate break. Tests listed below MUST be written to fail before the matching implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Include exact file paths in descriptions

## Path Conventions

Package lives under `personalAgent/`. Source: `personalAgent/src/hermes_kanban/`. Tests: `personalAgent/tests/`. New files: `personalAgent/src/hermes_kanban/board.py`, `personalAgent/src/hermes_kanban/runtime.py`, `personalAgent/src/hermes_kanban/__main__.py`, `personalAgent/tests/test_live_piv_bridge.py`. Keep `MemoryTaskBoard` in `orchestrator.py`. Do not add `execution.db`. Do not edit `AiNative/`. Do not fork Hermes sources. Do not start concurrent workers / Obsidian / learning.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing package, Python 3.12, pytest/ruff, and no new libraries. Isolated Hermes home stays `HERMES_HOME`; never default the board to `$HOME/.hermes`.

- [X] T001 Confirm `personalAgent/pyproject.toml` stays Python `>=3.12,<3.14` with **no** new runtime dependencies (stdlib `sqlite3` only for the live board)
- [X] T002 [P] Confirm `personalAgent/pyproject.toml` already lists pytest and ruff under `[project.optional-dependencies] dev`; do not add another test framework
- [X] T003 [P] Confirm `personalAgent/docker-compose.yml` already sets `HERMES_HOME=/opt/data` and does not write `~/.hermes` root; note the package is not yet importable in the worker (US4 mounts it)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `BoardTask.column`, live eligibility, worker claim exception, and keep check-only `from_config`. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add optional `column: str = ""` on frozen `BoardTask` in `personalAgent/src/hermes_kanban/orchestrator.py` so existing `MemoryTaskBoard` fixtures stay eligible (empty column = 005 behavior)
- [X] T005 Add `IneligibleColumnError(OrchestratorError)` in `personalAgent/src/hermes_kanban/orchestrator.py` for named start of a card whose `column` is non-empty and not in `{todo, ready}` (except the worker claim in T007)
- [X] T006 Add `allow_running_task_id: str | None = None` on `PivOrchestrator.__init__` in `personalAgent/src/hermes_kanban/orchestrator.py`; `from_config` keeps accepting an injected `MemoryTaskBoard` (do not open `kanban.db` here; do not default `$HOME/.hermes`)
- [X] T007 In `run_workflow` / `run_next_workflow` in `personalAgent/src/hermes_kanban/orchestrator.py`, skip/refuse non-empty `column` outside `{todo, ready}` except named start when `column == running` **and** `task_id == allow_running_task_id`; next-ready MUST never select `running` / `triage` / `scheduled` / `blocked` / `review` / `done` / `archived`; empty eligible set → `NoReadyTaskError` with 0 agent runs (no poll, no Backlog fallback); keep existing P0–P3 then oldest `created_at` sort
- [X] T008 [P] Re-export `IneligibleColumnError` from `personalAgent/src/hermes_kanban/__init__.py`

**Checkpoint**: Foundation ready — fixtures with empty `column` still run; live column rules exist; user stories can proceed

---

## Phase 3: User Story 1 - Native Kanban is the only live task source (Priority: P1) 🎯 MVP

**Goal**: Read-only `SqliteTaskBoard` over a native-shaped `kanban.db`. Production construction uses that adapter at `{HERMES_HOME}/kanban.db` and refuses `MemoryTaskBoard`. Missing file / unknown id / incomplete card / wrong column fail at the trust boundary with 0 agent runs. No second task store.

**Independent Test**: Point the adapter at a temp Kanban-shaped SQLite file with one fixture card. `get` returns stored body fields. File bytes/mtime unchanged. Live constructor refuses `MemoryTaskBoard`. Missing file or unknown id fails before any agent run.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [US1] Add a temp SQLite helper in `personalAgent/tests/test_live_piv_bridge.py` that creates installed-shape `tasks` / `task_links` (not the operator’s live board) and a groomed body with `## Problem`, `## Expected Result`, `## Platform`, `## Acceptance Criteria`, `## Technical Notes`, `## Dependencies`, `## Owner`/`## Reviewer` optional, `## Priority` exact `P0`–`P3`
- [X] T010 [US1] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that `SqliteTaskBoard.get` maps id, `project_id`, body headings, `task_links` dependencies, `assignee` → owner, `created_at` ISO-8601 UTC, `complete` from `done`/`archived`, `column` from `status`; MUST NOT invent missing headings; MUST NOT map native INTEGER `priority` 0 to P0 (SC-001)
- [X] T011 [US1] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that get/list/start leave the temp DB bytes/mtime unchanged (0 INSERT/UPDATE/DELETE), missing/unreadable file and unknown id fail visibly with 0 agent runs, and after a run there is still exactly one task DB file
- [X] T012 [US1] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that `build_live_orchestrator` requires `HERMES_HOME` → `{HERMES_HOME}/kanban.db`, constructs `SqliteTaskBoard`, and fails closed if a caller passes `MemoryTaskBoard` (`MissingTaskBoardError` or equivalent)

### Implementation for User Story 1

- [X] T013 [US1] Implement `SqliteTaskBoard` in `personalAgent/src/hermes_kanban/board.py`: open `file:{path}?mode=ro`; `get` / `list` per `contracts/live-piv-bridge.md` and research field mapping; `list` does not filter by column; MUST NOT create `kanban.db`; MUST NOT write rows
- [X] T014 [US1] Parse card body headings in `personalAgent/src/hermes_kanban/board.py`; incomplete required headings or invalid `## Priority` stay incomplete at the trust boundary (do not invent text)
- [X] T015 [US1] Implement `build_live_orchestrator` in `personalAgent/src/hermes_kanban/runtime.py`: `HERMES_HOME` required (no `$HOME/.hermes` default); missing env/file → visible error, 0 runs; refuse `MemoryTaskBoard`; call existing `become_ready`
- [X] T016 [US1] Re-export `SqliteTaskBoard` and `build_live_orchestrator` from `personalAgent/src/hermes_kanban/__init__.py`

**Checkpoint**: User Story 1 is independently testable: temp native board reads through `SqliteTaskBoard`; live constructor never builds `MemoryTaskBoard`

---

## Phase 4: User Story 2 - Dispatcher runs one live task through pull request and notice (Priority: P1)

**Goal**: One `main` entry (Hermes worker and CLI) calls existing `run_workflow` / `run_next_workflow` / `resume_workflow`. A successful live task loads project context, uses isolated `feature/task-<id>`, runs discovery → planning → implementation → validation, recover-or-block, commits only on that branch, publishes via `LiveGitHost` (checks inject `MemoryGitHost`), records `PR_CREATED`, emits existing `pr_created`. No second orchestrator, scheduler, or Telegram-only start.

**Independent Test**: Fixture live board + disposable enrolled project + `MemoryGitHost` + stand-in model. Confirm chain, isolated branch, commit only there, `PR_CREATED`, existing notice, 0 default-branch commits, 0 merges, 0 deploys, 0 secrets, methodology unchanged.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [US2] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` for named start of an eligible `todo`/`ready` card: project context loaded, worktree `feature/task-<id>`, discovery then planning then implementation then validation, `PR_CREATED` with number and HTML URL, existing `pr_created` send (or skip if messaging off), 0 `main`/`master` commits, 0 merges, 0 deploys, 0 secrets on the record (SC-002, SC-003)
- [X] T018 [US2] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` for recover-or-block (existing budget), next-ready highest P0–P3 then oldest among complete `todo`/`ready` only, empty eligible set → `NoReadyTaskError` / 0 agent runs, and `column=running` allowed only when id equals `allow_running_task_id` / `HERMES_KANBAN_TASK`
- [X] T019 [US2] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that `main` supports named `--task` / `HERMES_KANBAN_TASK`, `--next-ready`, and `--resume` and does not start a background worker or a new Telegram kind

### Implementation for User Story 2

- [X] T020 [US2] Implement `main(argv) -> int` in `personalAgent/src/hermes_kanban/runtime.py`: one start surface; named task → `run_workflow` after board `get` supplies `project_id`; `--next-ready` → `run_next_workflow`; `--resume` → `resume_workflow`; pass `allow_running_task_id` from `HERMES_KANBAN_TASK`; omitted `git_host` → `LiveGitHost`; messaging as 008 (`HermesTelegramChannel` when enabled + home chat; else skip-send)
- [X] T021 [US2] Add `personalAgent/src/hermes_kanban/__main__.py` that calls `runtime.main` so `python -m hermes_kanban --config …` is the worker/CLI entry
- [X] T022 [US2] Confirm `run_workflow` still uses existing workspace `feature/task-<id>`, PIV chain, recover-or-block, feature-branch-only commit, `LiveGitHost` publish, `_emit("pr_created", …)` in `personalAgent/src/hermes_kanban/orchestrator.py` — surgical eligibility only; do not rewrite adapter/registry/executor/github/messaging

**Checkpoint**: User Stories 1 and 2: native board read + one dispatcher entry can finish a fixture task through `PR_CREATED` and the existing notice

---

## Phase 5: User Story 3 - Safe checks: temp board fixtures, simulated hosting, named-repo smoke (Priority: P1)

**Goal**: Focused pytest uses temp Kanban + `MemoryGitHost` + stand-in model (no github.com, live chat, or operator board). Existing suite and ruff stay green. Smoke requires explicit `owner/name` that matches **both** GitHub remote `owner/name` **and** enrolled `ProjectRecord.name`; otherwise 0 pushes.

**Independent Test**: Run `tests/test_live_piv_bridge.py` hermetically. Invoke smoke with no/blank name → 0 pushes. Invoke with matching disposable name in fixture → would target that repo’s feature branch only. Mismatch → refuse before any push.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T023 [US3] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that smoke with missing/blank `--repo` / empty-by-default env performs 0 `MemoryGitHost.pushes` and 0 PR opens (SC-005)
- [X] T024 [US3] Add failing checks in `personalAgent/tests/test_live_piv_bridge.py` that smoke proceeds only when `requested == github owner/name == ProjectRecord.name`; mismatch or missing enrollment → visible error, 0 pushes; matching name → feature branch only, never `main`/`master`, never a silently picked production repo (SC-005)
- [X] T025 [US3] Confirm `personalAgent/tests/test_live_piv_bridge.py` uses only `tmp_path` boards and `MemoryGitHost`; MUST NOT require github.com, live Telegram, a live model, or `$HOME/.hermes/personal-agent/kanban.db` as the only gate (SC-004)

### Implementation for User Story 3

- [X] T026 [US3] Implement `--smoke --repo owner/name` in `personalAgent/src/hermes_kanban/runtime.py` (same `main`): refuse before `push_feature_branch` / `upsert_pull_request` unless the three names match; allowed smoke still never pushes `main`/`master`
- [X] T027 [US3] Document dispatcher CLI, pytest, ruff, smoke, and credentials-outside-git in `personalAgent/README.md` (GitHub SSH agent, existing Telegram token/chat, model key — never written into the repo)

**Checkpoint**: Checks are hermetic; smoke is fail-closed unless the named disposable identity matches both GitHub and enrollment

---

## Phase 6: User Story 4 - Inspect first; extend Hermes; do not rewrite methodology (Priority: P2)

**Goal**: Live entry fits installed Hermes 0.21 worker hooks (adapt, do not fork). Package importable in `hermes-personal-agent` with `HERMES_HOME=/opt/data`. 0 AiNative writes. 0 second bot. Inspection already recorded in `research.md`; this phase wires Compose and proves the change set stays a bridge.

**Independent Test**: Methodology tree diff has 0 writes. Compose/docs show `python -m hermes_kanban` as the one dispatcher-facing call. Native `kanban.db` remains the board. No `on_kanban_dispatch_tick` work starter.

### Implementation for User Story 4

- [X] T028 [US4] Mount or install `personalAgent` into `hermes-personal-agent` in `personalAgent/docker-compose.yml` so `python -m hermes_kanban` works with `HERMES_HOME=/opt/data` (wiring only; do not fork `hermes_cli`)
- [X] T029 [US4] Confirm the live entry does **not** subscribe `on_kanban_dispatch_tick` to start PIV, does not add a claiming plugin, and does not add a Telegram-only start path (document the worker env `HERMES_KANBAN_TASK` in `personalAgent/README.md`)
- [X] T030 [US4] Confirm 0 files under `AiNative/` are modified by this feature; messaging still uses existing `pr_created` kind and already-connected chat

**Checkpoint**: All user stories independently functional; Hermes is extended, not rewritten

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full regression, lint, version history, quickstart gate. Stop after this live-bridge slice.

- [X] T031 Run `uv run pytest tests/test_live_piv_bridge.py` then `uv run pytest` in `personalAgent/` and keep 001–009 modules green
- [X] T032 [P] Run `uv run ruff check src tests` in `personalAgent/`
- [X] T033 [P] Update `CHANGELOG.md` and `personalAgent/CHANGELOG.md` (and `personalAgent/pyproject.toml` / `__version__` if the package bumps) for the live bridge: read-only `SqliteTaskBoard`, one dispatcher/CLI entry, named-repo smoke; no second task store; no concurrent workers / Obsidian / learning
- [X] T034 Confirm `specs/010-live-piv-bridge/quickstart.md` commands work: focused pytest, full pytest, ruff, documented `python -m hermes_kanban` invocations, smoke refuse-by-default; report files changed, test results, runtime commands, and remaining external credentials (those stay outside git)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP live board adapter
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 `SqliteTaskBoard` / `build_live_orchestrator` (dispatcher entry needs the live board)
- **User Story 3 (Phase 5)**: Depends on Foundational; smoke `main` flag belongs with US2 `main` — implement T026 after T020 exists; smoke **tests** can be written against a recording host once `main` exists
- **User Story 4 (Phase 6)**: Depends on Foundational; Compose mount can proceed in parallel with US1–US3 (different file); do not block pytest on Docker
- **Polish (Phase 7)**: Depends on the stories you are delivering

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — independently testable as read-only SQLite get/list + live constructor without publishing
- **User Story 2 (P1)**: After US1 adapter exists — independently testable with temp board + `MemoryGitHost` + stand-in model
- **User Story 3 (P1)**: After `main` exists — independently testable as smoke refuse/match with 0 network
- **User Story 4 (P2)**: After Phase 2 — independently testable as Compose/docs + empty `AiNative/` diff; inspection notes already in `research.md`

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Board adapter before live constructor
- Live constructor before `main`
- `main` before smoke subcommand
- Story complete before moving to next priority unless staffed on different files

### Parallel Opportunities

- T002 / T003 after T001
- T008 in parallel with T004–T007 once the error class name is fixed
- US4 Compose (`T028`) in parallel with US1–US3 (different file)
- T032 / T033 in parallel after tests are green
- Do **not** parallelize multiple edits to `personalAgent/tests/test_live_piv_bridge.py` or `personalAgent/src/hermes_kanban/runtime.py`

---

## Parallel Example: User Story 1

```bash
# After T009 fixture helper exists, implement board + constructor (different files):
Task: "Implement SqliteTaskBoard in personalAgent/src/hermes_kanban/board.py"
Task: "Re-export SqliteTaskBoard and build_live_orchestrator from personalAgent/src/hermes_kanban/__init__.py"
# Then T015 runtime constructor (depends on board.py)
```

## Parallel Example: User Story 4 vs US1

```bash
Task: "Mount personalAgent into hermes-personal-agent in personalAgent/docker-compose.yml"
Task: "Implement SqliteTaskBoard in personalAgent/src/hermes_kanban/board.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (read-only native board + live constructor)
4. **STOP and VALIDATE**: temp SQLite get/list; live constructor refuses `MemoryTaskBoard`
5. Then US2 for the operator-visible wait-return (`PR_CREATED`)

### Incremental Delivery

1. Setup + Foundational → column rules and empty-column fixtures still pass
2. Add US1 → Test independently → live board is source of truth
3. Add US2 → Test independently → dispatcher finishes one fixture task
4. Add US3 → Test independently → hermetic checks + fail-closed smoke
5. Add US4 → Compose import + no methodology writes
6. Polish → changelog, full pytest, ruff, quickstart report

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (`board.py` / live constructor)
   - Developer B: User Story 4 (`docker-compose.yml` / README Hermes hook) — avoid `runtime.py` until US2
   - Developer C: wait for US1 then US2 `runtime.py` / `__main__.py`
3. US3 smoke shares `runtime.py` — do not staff in parallel with US2

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Whole-project `scratch/implimentation.md` is background only — do not start later milestones
- Avoid: vague tasks, same-file conflicts, `MemoryTaskBoard` on the live entry, second task DB, AiNative writes, `$HOME/.hermes` board default

---

## Phase 8: Convergence

- [X] T035 CRITICAL: Constrain `--smoke --next-ready` so it can start only an eligible card on the already-validated disposable project (`requested == github owner/name == ProjectRecord.name`); refuse with 0 pushes if next-ready would select another enrolled project per Constitution V, FR-015, SC-005 (contradicts)
- [X] T036 After a matching `--smoke --repo owner/name` gate, run the live publish path for that named repository’s feature branch (named task or next-ready on that project only); do not return success after verify-only when the contract says gate then publish per FR-015, US3/AC4, plan: smoke (partial)
- [X] T037 Prove smoke refuse through `main` in `personalAgent/tests/test_live_piv_bridge.py` with a recording `MemoryGitHost`: missing/blank `--repo` or empty-by-default env → 0 `pushes` and 0 PR opens before any workflow start per FR-013, US3/AC3 (partial)

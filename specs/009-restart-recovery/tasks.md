---

description: "Task list for Restart Recovery (persist overlay, reclaim one interrupted run, recover workspace, prevent duplicate workers)"
---

# Tasks: Restart Recovery

**Input**: Design documents from `/specs/009-restart-recovery/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/restart-recovery.md, quickstart.md

**Tests**: Required. Spec SC-001–SC-008 / FR-001–FR-017 and constitution IV demand one pytest contract file (`personalAgent/tests/test_restart_recovery.py`) that fails if persistence, reclaim, workspace recover, or duplicate prevention break. Tests listed below MUST be written to fail before the matching implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Include exact file paths in descriptions

## Path Conventions

Package lives under `personalAgent/`. Source: `personalAgent/src/hermes_kanban/`. Tests: `personalAgent/tests/`. New seam: `personalAgent/src/hermes_kanban/persist.py`. Recover path: `personalAgent/src/hermes_kanban/workspace.py`. Do not add `recovery.py` (Phase 4 owns that word). Do not write `kanban.db` / `projects.db`. Do not start Phase 8.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing package/config; no new dependencies; overlay dir is a required mounted path, not `$HOME`.

- [X] T001 Confirm `personalAgent/config/default.yaml` sets `execution.overlay_dir: /var/lib/hermes-kanban`, keeps `execution.max_concurrent_tasks: 1` and `projects: []`; MUST NOT default overlay to `$HOME`, `~/.hermes`, `/tmp`, or the workspace root
- [X] T002 [P] Confirm `personalAgent/pyproject.toml` adds **no** new runtime libraries (stdlib `json` / `os.replace` / `threading` / `time` only)
- [X] T003 [P] Bind a named or host volume onto `/var/lib/hermes-kanban` in `personalAgent/docker-compose.yml` so a container restart keeps overlay files (application still reads the YAML path, not `HOME`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persist helper, overlay-dir trust boundary, start-up gate, heartbeat files, error types. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create `personalAgent/src/hermes_kanban/persist.py` with frozen `OverlaySnapshot` (`record`, `slot` `occupied`|`free`, `schema` literal `v0`), `write_overlay` (write `overlay.json.tmp` then `os.replace` onto `overlay.json`), `read_overlay` (MUST NOT parse `.tmp` as truth; missing file → `None`), `touch_alive`, and `alive_is_fresh` (`ttl_s=60.0`, injected `clock`)
- [X] T005 Implement overlay-dir validation in `personalAgent/src/hermes_kanban/persist.py`: required existing writable directory; missing / not a directory / not writable → `InvalidOverlayDirError`; MUST NOT invent `$HOME`, `~/.hermes`, `/tmp`, or workspace root
- [X] T006 Add `SlotHeldError` in `personalAgent/src/hermes_kanban/persist.py` (second live copy while `alive` is fresh). Keep `WorkflowBusyError` in `personalAgent/src/hermes_kanban/orchestrator.py` for a second start while **this** process holds the slot
- [X] T007 Add `overlay_dir: Path` and optional `clock` (`Callable[[], float] | None`, omitted → `time.time`) on `PivOrchestrator.__init__` in `personalAgent/src/hermes_kanban/orchestrator.py`; `from_config` MUST load `execution.overlay_dir` from operational YAML and MUST call `become_ready()` before the instance accepts `run_workflow` / `run_next_workflow`
- [X] T008 Add `become_ready(self) -> WorkflowRecord | None` on `PivOrchestrator` in `personalAgent/src/hermes_kanban/orchestrator.py`: if another copy’s `alive` is fresh → `SlotHeldError` and 0 workers; missing overlay → idle ready; refuse `run_workflow` / `run_next_workflow` until this method has succeeded; two calls on the same held instance MUST NOT start a second chain
- [X] T009 Persist a complete overlay snapshot after each complete record mutation in `personalAgent/src/hermes_kanban/orchestrator.py` (atomic `write_overlay` only). Mark the overlay file (not Kanban rows) with a `ponytail:` comment: ceiling one JSON document for the single V0 slot; upgrade map identities onto native Kanban columns later. NEVER write `kanban.db` / `projects.db`. NEVER put secrets in the snapshot
- [X] T010 While the slot is held (`QUEUED` / `RUNNING` / `VALIDATING` / `RETRYABLE_FAILURE` / `HUMAN_DECISION_REQUIRED` / `BLOCKED`), keep `alive` fresh in `execution.overlay_dir` from `personalAgent/src/hermes_kanban/persist.py` (tick ≤ 15s daemon thread + on successful snapshot write). Stop refreshing on `PR_CREATED` / `FAILED` (slot free). Crash MUST NOT require deleting `alive`. Mark 15s file heartbeat with a `ponytail:` comment
- [X] T011 [P] Re-export `OverlaySnapshot`, `InvalidOverlayDirError`, `SlotHeldError`, `write_overlay`, `read_overlay`, `touch_alive`, `alive_is_fresh` from `personalAgent/src/hermes_kanban/__init__.py`

**Checkpoint**: Foundation ready — overlay dir is required; snapshots can round-trip; `become_ready` is the start-up gate; user stories can proceed

---

## Phase 3: User Story 1 - Restart does not lose or corrupt the active run (Priority: P1) 🎯 MVP

**Goal**: After process/container restart, the same execution record is still readable: same identities, last complete snapshot, terminal/parked/blocked unchanged, board body untouched.

**Independent Test**: Start a fixture workflow, stop the orchestrator during an in-progress phase, construct a new `PivOrchestrator` on the same `overlay_dir`. Confirm the execution record still exists with the same identities and a coherent state. Repeat with a finished run and a parked run.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [US1] Add failing contract checks in `personalAgent/tests/test_restart_recovery.py` for readable snapshot after simulated restart (`RUNNING`/`VALIDATING`/`RETRYABLE_FAILURE`): same `execution_id` / `task_id` / `project_id` / `workspace_id` / `run_id`; not empty or mixed; `.tmp` never treated as truth (SC-001)
- [X] T013 [US1] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for terminal `COMPLETED`/`FAILED`/`PR_CREATED` unchanged with 0 automatic workers, and for `HUMAN_DECISION_REQUIRED`/`BLOCKED` still occupying the slot with 0 automatic workers (SC-004)
- [X] T014 [US1] Add failing checks in `personalAgent/tests/test_restart_recovery.py` that owner, reviewer, priority, and problem / expected-result / acceptance-criteria on `MemoryTaskBoard` are unchanged after restart (execution details not copied into the board body)

### Implementation for User Story 1

- [X] T015 [US1] Round-trip `WorkflowRecord` through `overlay.json` in `personalAgent/src/hermes_kanban/persist.py` / `personalAgent/src/hermes_kanban/orchestrator.py` (`workspace_path` as string on disk, `Path` in memory; `sends` preserved; `worker_id` MAY change later; `attempt` / `publish_attempt` MUST NOT increase because the process died)
- [X] T016 [US1] On `become_ready` in `personalAgent/src/hermes_kanban/orchestrator.py`, load last complete snapshot: idle if none; retain last-finished and free the slot for `PR_CREATED`/`FAILED`; occupy with no worker for parked/blocked; corrupt sole file → visible error, do not invent a run
- [X] T017 [US1] Confirm `personalAgent/tests/test_restart_recovery.py` uses only `tmp_path` overlay dir + injected `clock`; MUST NOT bind `$HOME` / `HERMES_HOME` or require Docker kill / live `kanban.db`

**Checkpoint**: User Story 1 is independently testable: a new orchestrator on the same overlay dir reads one coherent snapshot

---

## Phase 4: User Story 2 - Interrupted work resumes or safely restarts without a second worker (Priority: P1)

**Goal**: Start-up automatically reclaims the interrupted run (resume next completed phase, or safe-restart the in-progress phase once) with the same execution identity. No second worker, no Resume press, no steal while `alive` is fresh.

**Independent Test**: Interrupt during implementation. After `become_ready`, exactly one worker continues (or that phase re-runs once), `execution_id` unchanged, second `run_workflow` is `WorkflowBusyError`, second live copy with fresh `alive` is `SlotHeldError`.

### Tests for User Story 2

- [X] T018 [US2] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for reclaim of an interrupted in-progress run: at most one worker, same `execution_id`, second `run_workflow`/`run_next_workflow` → `WorkflowBusyError`, no second working copy, two `become_ready` on the same instance → 0 second chains (SC-002)
- [X] T019 [US2] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for resume vs safe-restart: completed phase in snapshot → next phase runs; in-progress phase → that phase runs once; `QUEUED` starts the pending phase; `attempt` / `publish_attempt` unchanged by the crash; `task_start` MUST NOT fire again on reclaim
- [X] T020 [US2] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for automatic start-up (`from_config`/`become_ready` reclaims **before** a new start is accepted; 0 `resume_workflow` calls) and dual copy (fresh `alive` → `SlotHeldError`; clock +61s silence → reclaim allowed) (SC-007)

### Implementation for User Story 2

- [X] T021 [US2] Implement reclaim grain in `become_ready` in `personalAgent/src/hermes_kanban/orchestrator.py`: phase completed → resume next; phase in progress (`RUNNING`/`VALIDATING`/`RETRYABLE_FAILURE` with no completed `steps` result for `current_phase`) → safe-restart that phase once; `QUEUED` → start pending phase; keep `task_id`/`execution_id`/`project_id`/`workspace_id`/`run_id`; wait-return the same as 008 (`PR_CREATED`/`FAILED`/`HUMAN_DECISION_REQUIRED`/`BLOCKED`)
- [X] T022 [US2] On safe-restart of `github` in `personalAgent/src/hermes_kanban/orchestrator.py`, reuse existing `GitHost.upsert` for the same head (0 second PRs from restart alone). On safe-restart of diagnosis/debug/validation, do **not** increment Phase 4 `attempt` solely because the process died (SC-005)
- [X] T023 [US2] Do not emit a new Telegram kind and do not re-deliver `task_start` on reclaim in `personalAgent/src/hermes_kanban/orchestrator.py` / `personalAgent/src/hermes_kanban/messaging.py`; later park/block/PR may still emit as 008. `resume_workflow` stays the parked/blocked **letter** path, not process-death recovery

**Checkpoint**: User Stories 1 and 2: snapshot survives; one worker reclaims automatically; second copy/start is refused

---

## Phase 5: User Story 3 - Working copy and work branch are discoverable after restart (Priority: P1)

**Goal**: Reclaim uses `recover_workspace` (same identities, dirty allowed, no fetch). Missing copy + local feature branch recreates that worktree. Missing both → `BLOCKED`. Unrelated copies stay isolated.

**Independent Test**: Interrupt with files in the task copy; restart; same path and branch; other task copies untouched. Repeat with copy removed but local feature branch present, and with both missing.

### Tests for User Story 3

- [X] T024 [US3] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for recover of an existing (possibly dirty) copy: same `workspace_id`/`execution_id`/path/branch `feature/task-<id>`; uncommitted files kept; enrolled project location unchanged; other task copies isolated; `inspect_workspace` still reports branch, dirty, changes (SC-003)
- [X] T025 [US3] Add failing checks in `personalAgent/tests/test_restart_recovery.py` for missing copy + local feature branch → worktree add with same identities never on `main`/`master`/default; missing copy and local branch → `BLOCKED` visible reason, 0 hang, 0 foreign copy adopted; GitHub/network down + local copy present → continue with **0** `git fetch` (SC-008)

### Implementation for User Story 3

- [X] T026 [US3] Implement `recover_workspace(project_id, task_id, *, workspace_id, execution_id, branch)` on `WorkspaceManager` in `personalAgent/src/hermes_kanban/workspace.py`: same eligibility/task-id/protected-branch checks as prepare; MUST NOT `git fetch`; MUST NOT mint new ids; dirty of **this** task allowed; foreign path → `InvalidWorkspaceError`; missing path + local `feature/task-<id>` → `git worktree add`; missing both → error mapped to `BLOCKED`
- [X] T027 [US3] Call `recover_workspace` (never `prepare_workspace`) from reclaim in `personalAgent/src/hermes_kanban/orchestrator.py`; keep `prepare_workspace` dirty-reuse rules unchanged for **new** runs (`DirtyWorkspaceError`)
- [X] T028 [US3] Confirm `personalAgent/tests/test_workspace_manager.py` still passes: new prepare still refuses dirty reuse; recover path is additive and does not share copies across tasks

**Checkpoint**: All three stories independently functional on injected clock + temp overlay/workspace dirs

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression, lint, version history, quickstart gate. Stop before Phase 8.

- [X] T029 Run `uv run pytest tests/test_restart_recovery.py tests/test_telegram_messaging.py tests/test_github_publish.py tests/test_piv_orchestrator.py tests/test_workspace_manager.py tests/test_agent_executor.py` in `personalAgent/` and keep 001–008 tests green (`from_config` now requires `execution.overlay_dir` and `become_ready`)
- [X] T030 [P] Run `uv run ruff check src tests` in `personalAgent/`
- [X] T031 [P] Update `CHANGELOG.md` (and package version if this repo keeps one) for restart recovery: durable overlay, automatic reclaim, workspace recover, duplicate prevention; no second task store; no Phase 8
- [X] T032 Confirm `specs/009-restart-recovery/quickstart.md`: contract file uses stand-in model, `MemoryTaskBoard`, `MemoryGitHost`, temp dirs, injected clock; 0 live Docker kill / github.com / Telegram required; optional Compose restart documented as later proof only

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP persistence
- **User Story 2 (Phase 4)**: Depends on Foundational + a readable overlay from US1 (reclaim needs a snapshot)
- **User Story 3 (Phase 5)**: Depends on Foundational; product-complete reclaim needs US2 `become_ready` chain plus recover
- **Polish (Phase 6)**: Depends on the stories you are delivering

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — independently testable as snapshot round-trip without reclaim workers
- **User Story 2 (P1)**: After US1 snapshot exists — independently testable with a fixture overlay and a stub workspace if recover is not yet implemented (fail closed / skip recover until US3)
- **User Story 3 (P1)**: After recover API exists — independently testable by calling `recover_workspace` then wiring it into reclaim; do not block MVP snapshot tests on git worktree recreate

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Persist helpers before orchestrator wiring
- Snapshot load before reclaim
- Reclaim before recover wiring
- Story complete before moving to the next increment you intend to ship

### Parallel Opportunities

- T001 and T002/T003 (config vs compose vs pyproject) can run together
- T012 / T013 / T014 are the **same test file** — do not parallelize
- T018 / T019 / T020 same file — sequential
- T024 / T025 same file — sequential
- T004 (`persist.py`) and T011 (`__init__.py`) can proceed after types exist; T007–T010 are sequential on `orchestrator.py`
- T026 (`workspace.py`) can start once US3 tests exist; serialize with T027 (`orchestrator.py`)
- T030 and T031 can run in parallel after tests are green

---

## Parallel Example: User Story 1

```bash
# Sequential in the same test file (do not split across agents):
Task: "Failing readable-snapshot checks in personalAgent/tests/test_restart_recovery.py"
Task: "Failing terminal/parked checks in personalAgent/tests/test_restart_recovery.py"
Task: "Failing board-body unchanged checks in personalAgent/tests/test_restart_recovery.py"

# After tests fail, persist round-trip vs become_ready load (coordinate if both touch orchestrator.py):
Task: "WorkflowRecord overlay round-trip in personalAgent/src/hermes_kanban/persist.py"
Task: "become_ready snapshot load in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Parallel Example: User Story 3

```bash
# Recover API vs orchestrator reclaim wiring (different files after tests exist):
Task: "recover_workspace in personalAgent/src/hermes_kanban/workspace.py"
Task: "Call recover_workspace from become_ready in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: pytest snapshot round-trip, terminal/parked unchanged, board body untouched
5. Demo with a new orchestrator on the same `tmp_path` overlay dir

### Incremental Delivery

1. Setup + Foundational → overlay dir + persist helper + start-up gate
2. US1 → restart does not lose the record
3. US2 → one worker reclaims automatically; second copy/start refused
4. US3 → same working copy/branch; dirty kept; missing both → `BLOCKED`
5. Each story keeps 008 wait-returns; crash does not bump Phase 4 budget or open a second PR

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1+2 (`persist.py` + `orchestrator.py` reclaim)
   - Developer B: User Story 3 tests and `recover_workspace` in `workspace.py` — still serialize `test_restart_recovery.py`

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec US1 (persist), US2 (reclaim / no duplicate worker), US3 (workspace recover)
- Public start names unchanged: `run_workflow`, `run_next_workflow`, `resume_workflow`; start-up adds `become_ready`
- One V0 slot; 60s alive TTL; reclaim grain = whole phase; no fetch on recover; no Resume press
- Stop after restart-recovery contract checks; do not start Phase 8 full E2E or live Docker kill
- Verify tests fail before implementing
- Commit after each task or logical group only if the operator asks
- Avoid: second task DB, `recovery.py`, `kanban.db` writes, new Telegram kind, incrementing `attempt` on crash, stealing a live copy

---

## Phase 7: Convergence

- [X] T033 Expand `personalAgent/tests/test_restart_recovery.py` so the contract fails if snapshot round-trip, terminal/parked unchanged, reclaim one-worker, resume vs safe-restart, `SlotHeldError` vs `WorkflowBusyError`, dirty recover, recreate-from-local-branch, missing both → `BLOCKED`, or offline no-fetch break per FR-001–FR-017

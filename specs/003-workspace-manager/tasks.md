---

description: "Task list for Workspace Manager implementation"
---

# Tasks: Workspace Manager

**Input**: Design documents from `/specs/003-workspace-manager/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Requested by spec SC-006, constitution IV, and [quickstart.md](./quickstart.md). One contract module only: `personalAgent/tests/test_workspace_manager.py`. Git repos are created in pytest `tmp_path` (copy `personalAgent/tests/fixtures/projects/standard/` then `git init` + commit). Tests MUST NOT bind to a live production checkout or a GitHub account.

**Organization**: Tasks are grouped by user story. All three stories are P1. US1 (prepare) is sequenced first because US2 safety and US3 identity attach to `prepare_workspace`. US2 is sequenced before US3 so dirty/invalid reuse is refused before clean reuse is added.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Implementation lands in the existing `personalAgent/` package (not playground root, not AiNative). Public API lives in one module until that file is unreadable — do not pre-split into `workspace/` or git/safety/identity packages. Do not add dependencies. Do not edit `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/src/hermes_kanban/projects.py` (import `_path_like_id` only), or `personalAgent/docker-compose.yml`.

```text
personalAgent/src/hermes_kanban/workspace.py
personalAgent/src/hermes_kanban/__init__.py
personalAgent/tests/test_workspace_manager.py
personalAgent/tests/fixtures/projects/standard/   # existing; copy into tmp_path then git init
personalAgent/config/default.yaml                 # already has workspace.root: /workspaces
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing control-plane layout is the implementation target. No new package, fixture tree, or host-path config.

- [X] T001 Confirm `personalAgent/config/default.yaml` keeps `workspace.root: /workspaces` and `projects: []`. Do not hardcode a workstation path, `$HOME`, `WORKSPACE_ROOT`, or a real repository. Do not edit `personalAgent/docker-compose.yml` (it already mounts workspaces at `/workspaces`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error types, records, workspace-root trust boundary, and a small git CLI helper. No user story work until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `WorkspaceError` and distinct subclasses `InvalidWorkspaceRootError`, `InvalidTaskIdError`, `InvalidProjectRepositoryError`, `MissingDefaultBranchError`, `ProtectedBranchError`, `DirtyWorkspaceError`, `InvalidWorkspaceError`, `GitRefreshError` in `personalAgent/src/hermes_kanban/workspace.py`.
- [X] T003 Add frozen dataclasses `PreparedWorkspace`, `WorkspaceInspection`, and `CorrelationIdentity` in `personalAgent/src/hermes_kanban/workspace.py` matching [data-model.md](./data-model.md): `PreparedWorkspace` has `path` (`Path`), `branch`, `project_id`, `task_id`, `workspace_id`, `execution_id`, `worker_id` (`str | None`), `remote` (`str | None`). `WorkspaceInspection` has `path`, `branch`, `dirty` (`bool`), `changes` (`tuple[str, ...]`). `CorrelationIdentity` has `task_id`, `execution_id`, `project_id`, `workspace_id`, `worker_id` (`str | None`). Type-annotate public APIs. No reasoning/transcript fields.
- [X] T004 Implement `load_workspace_root(config_path: Path) -> Path` and `WorkspaceManager.__init__(workspace_root: Path, registry: ProjectRegistry)` / `WorkspaceManager.from_config(config_path: Path, registry: ProjectRegistry | None = None)` in `personalAgent/src/hermes_kanban/workspace.py`. Trust boundary: raise `InvalidWorkspaceRootError` for missing/unreadable config, missing/empty `workspace.root`, or a root that is missing / not a directory / unreadable. MUST NOT substitute `/workspaces`, `$HOME`, `./workspaces`, or `WORKSPACE_ROOT`. Scan only the `workspace:` mapping for a `root` scalar (`ponytail:` line-oriented YAML subset, same ceiling as `load_ainative_settings`; upgrade is owner-approved PyYAML). Do not share a YAML helper with `projects.py`. `from_config` uses the given `registry` or `ProjectRegistry.from_config(config_path)`. Do not `stat` enrolled project locations at construction.
- [X] T005 Add a small `_git` helper in `personalAgent/src/hermes_kanban/workspace.py` that runs `git -C <repo>` via `subprocess` (stdlib only). Import and reuse `projects._path_like_id` for later identity checks — do not copy a third path-like variant. Allowed callers later: `status`, `rev-parse`, `remote`, `fetch`, `worktree add`/`list`, porcelain/diff names, `show-ref`. This module MUST NOT call `push`, `reset --hard`, `clean`, `clone`, `init`, `worktree remove`, or `checkout` of the enrolled HEAD. Do not extract `hermes_kanban/git.py`.
- [X] T006 [P] Re-export `WorkspaceManager`, `load_workspace_root`, `PreparedWorkspace`, `WorkspaceInspection`, `CorrelationIdentity`, and the workspace error classes from `personalAgent/src/hermes_kanban/__init__.py`. Keep every existing adapter and registry export.

**Checkpoint**: Foundation ready — `from_config` validates the workspace root; user story implementation can begin

---

## Phase 3: User Story 1 - Prepare an isolated working copy for one task (Priority: P1) 🎯 MVP

**Goal**: Callers can prepare a dedicated git worktree for one eligible project + one task under the configured workspace root, on `feature/task-<task_id>`, without using the enrolled location as the edit directory.

**Independent Test**: Point the manager at operational YAML whose `workspace.root` is a temp directory and at a disposable enrolled git fixture. Prepare task `123`. Confirm a worktree exists only for that task on a non-protected feature branch. Prepare a second task for the same project and confirm a different path. Confirm the enrolled location’s current branch is unchanged.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [US1] Add contract tests in `personalAgent/tests/test_workspace_manager.py` with a helper that copies `tests/fixtures/projects/standard/` into `tmp_path`, `git init`s, sets local `user.email`/`user.name`, commits, and writes operational YAML (`workspace.root` = a temp dir, `projects:` listing that fixture). Cover: prepare task `123` returns a worktree at `{root}/{project_id}/123` on `feature/task-123` (not `main`/`master`/default); enrolled current branch unchanged; two task ids → two different mutable paths; missing/empty/non-directory workspace root → `InvalidWorkspaceRootError` with no substitute path; empty or path-like `task_id` (`/`, `\`, `..`) → `InvalidTaskIdError` and no filesystem join of the raw id; unknown / disabled / bad enrolled location → existing `UnknownProjectError` / `DisabledProjectError` / `InvalidProjectLocationError`; enrolled path that is not a git work tree → `InvalidProjectRepositoryError` (no `git init`); missing default-branch ref → `MissingDefaultBranchError`; dirty files in the enrolled location still allow preparing a **new** task worktree. Tests MUST NOT use a hardcoded workstation path or a live production repo.

### Implementation for User Story 1

- [X] T008 [US1] Implement `prepare_workspace` identity and eligibility gates in `personalAgent/src/hermes_kanban/workspace.py`: empty/path-like `task_id` → `InvalidTaskIdError` (reuse `_path_like_id`; do not join the raw id onto a path first); then `registry.resolve_eligible_project(project_id)` and propagate registry errors unchanged; enrolled location not a git work tree (`rev-parse --is-inside-work-tree`) → `InvalidProjectRepositoryError` (do not `git init` or clone); declared default branch missing as a ref → `MissingDefaultBranchError` (do not guess a different base than `ProjectRecord.default_branch`).
- [X] T009 [US1] Implement new-worktree create in `prepare_workspace` in `personalAgent/src/hermes_kanban/workspace.py`: path `{workspace_root}/{project.id}/{task_id}` after validation; work branch `feature/task-<task_id>`; if that name is `main`, `master`, or the project default → `ProtectedBranchError` and do not check it out; `git worktree add` from the enrolled location onto the local default branch (no remote handling yet); MUST NOT change the enrolled location’s current branch; MUST NOT `rmtree` sibling task directories; return `PreparedWorkspace` with non-empty `path`, `branch`, `project_id`, `task_id`, `workspace_id` (`ws-{project_id}-{task_id}`), `execution_id` (`uuid.uuid4().hex`), `worker_id=None`, `remote=None`. No agent/model/push/PR calls.

**Checkpoint**: User Story 1 is independently testable via first-time prepare + two-task isolation without inspect, reuse, or fetch

---

## Phase 4: User Story 2 - Refuse unsafe Git situations (Priority: P1)

**Goal**: The manager is the Git safety boundary: no protected work branch, no dirty reuse, no shared mutable copy, no overwrite of another task’s files, inspect reports branch and change status, publish of a protected branch is refused (this phase does not publish).

**Independent Test**: Prepare a valid fixture workspace. Attempt a protected work/publish branch and confirm `ProtectedBranchError`. Dirty the existing task copy, prepare again, and confirm `DirtyWorkspaceError` with files kept. Two tasks never share a path. `assert_publish_allowed` refuses `main`/`master`/project default. Inspect reports branch, dirty flag, and change summary.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [US2] Extend `personalAgent/tests/test_workspace_manager.py`: prepare/assert that would use `main`, `master`, or a non-`main` project default as the work/publish branch raises `ProtectedBranchError` with no checkout onto that branch; second prepare of the same project+task when the copy has uncommitted (including untracked) changes raises `DirtyWorkspaceError`, those files remain, and a sibling task directory under the root is not deleted; a feature branch already checked out in another worktree (including enrolled) is not shared (`InvalidWorkspaceError`); inspect of a clean copy reports expected branch, `dirty` false, empty `changes`; after a local file change inspect reports `dirty` true and a non-empty porcelain change summary; missing / not-a-git-copy / mismatched path → `InvalidWorkspaceError` with no delete/overwrite; `assert_publish_allowed` on `feature/task-123` succeeds (allowed later) and performs 0 publishes; empty `branch` or empty `default_branch` → `ProtectedBranchError`; when a local bare `origin` exists and fetch/`{remote}/{default}` fails → `GitRefreshError`. Do not use `github.com`.

### Implementation for User Story 2

- [X] T011 [US2] Implement `inspect_workspace(project_id, task_id)` in `personalAgent/src/hermes_kanban/workspace.py`: same eligibility and `task_id` rules as prepare; missing / not a git work tree / mismatched task path → `InvalidWorkspaceError`; return current branch (`rev-parse --abbrev-ref HEAD`), `dirty` from `git status --porcelain` (untracked counts), and `changes` as porcelain lines (empty tuple when clean). MUST NOT create, repair, reset, delete, or publish.
- [X] T012 [US2] Implement `assert_publish_allowed(branch, *, default_branch)` in `personalAgent/src/hermes_kanban/workspace.py`: refuse (`ProtectedBranchError`) when `branch` is `main`, `master`, `default_branch`, or either name is empty; otherwise return. MUST NOT push. Call the same protected-name check from `prepare_workspace` before `worktree add` / before returning an existing copy.
- [X] T013 [US2] Finish Git safety inside `prepare_workspace` in `personalAgent/src/hermes_kanban/workspace.py`: if remotes exist, record remote identity (`origin` URL if present, else first remote) and `git fetch` from the enrolled location (fetch MUST NOT check out or reset enrolled HEAD); fetch failure or missing `{remote}/{default_branch}` after fetch → `GitRefreshError`; no remotes → skip fetch, `remote=None`; existing dirty copy → `DirtyWorkspaceError` (leave files; do not reset/clean; do not touch other task paths); existing path that is not git / wrong branch / different repo/task, or feature branch already checked out elsewhere → `InvalidWorkspaceError` (do not overwrite). New worktree base with a remote is `{remote}/{default_branch}` after a successful fetch.

**Checkpoint**: User Stories 1 and 2 both work independently — prepare is safe to call twice only when the copy is not dirty; inspect and the publish gate exist

---

## Phase 5: User Story 3 - Stamp a correlation identity on every prepare (Priority: P1)

**Goal**: Every successful prepare returns task, execution, project, and workspace identities (optional worker). Re-preparing a valid clean copy keeps `workspace_id` stable and issues a new `execution_id`. No second workspace/task store. No private reasoning.

**Independent Test**: Prepare a fixture workspace and confirm identity fields are present and non-empty. Prepare a second task and confirm workspace identities differ. Prepare the same task again on a valid clean copy and confirm `workspace_id` unchanged while `execution_id` is new. Confirm the record has no reasoning/transcript text.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US3] Extend `personalAgent/tests/test_workspace_manager.py`: successful prepare has non-empty `task_id`, `execution_id`, `project_id`, `workspace_id`; two different tasks → different `workspace_id` and different `execution_id`; reuse of a valid clean copy on `feature/task-<id>` keeps `workspace_id` (`ws-{project_id}-{task_id}`) and issues a new `execution_id`; omitted/`None`/`""` `worker_id` → result `worker_id is None`; supplied non-empty `worker_id` is stored as given (not invented); dataclass fields include no reasoning/transcript/diff-body attributes; after prepare, nothing under `personalAgent/` holds a copied application repo (only tests’ temp trees); this phase does not write Hermes `kanban.db` / `projects.db`.

### Implementation for User Story 3

- [X] T015 [US3] Implement clean reuse in `prepare_workspace` in `personalAgent/src/hermes_kanban/workspace.py`: if `{root}/{project.id}/{task_id}` already exists, is a valid git copy, is on `feature/task-<task_id>`, and `status --porcelain` is empty, reuse that path — same `workspace_id`, new `execution_id`, do not `worktree add` again. Do not pull/rebase the feature branch onto latest default. Dirty/invalid paths stay on the US2 errors.
- [X] T016 [US3] Finish correlation identity on `PreparedWorkspace` in `personalAgent/src/hermes_kanban/workspace.py`: `workspace_id` is always `ws-{project_id}-{task_id}`; `execution_id` is a new UUID hex on every successful prepare (create or reuse); `worker_id` is the caller string when non-empty, else `None`; reuse host field names `path` / `branch` / `project_id` (later Kanban `workspace_path` / `branch_name` / `project_id`) and do not add a SQLite file, sidecar in the worktree, or `kanban.db` write. MUST NOT include instruction text, full diffs, chain-of-thought, or model transcripts.

**Checkpoint**: All three user stories are independently functional. Stop — do not start PIV, GitHub hosting, or agent execution

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the six SC-006 checks, keep existing packages green, and refuse silent production targeting

- [X] T017 Keep existing checks green from `personalAgent/`: `uv run pytest tests/test_import.py tests/test_ainative_adapter.py tests/test_project_registry.py`. Do not rewrite `personalAgent/src/hermes_kanban/ainative.py` or `personalAgent/src/hermes_kanban/projects.py`.
- [X] T018 Run the quickstart validation from `personalAgent/`: `uv run pytest tests/test_workspace_manager.py` and `uv run ruff check src tests`. Fix any contract or lint failure in `personalAgent/src/hermes_kanban/workspace.py` / `personalAgent/tests/test_workspace_manager.py`.
- [X] T019 Confirm `personalAgent/config/default.yaml` still has `workspace.root: /workspaces` and `projects: []`, no host-specific path, no production repo enrolled; this diff does not read/write Hermes `projects.db` / `kanban.db` and adds no new dependency in `personalAgent/pyproject.toml`.
- [X] T020 Confirm `personalAgent/src/hermes_kanban/workspace.py` never invokes `git push`, `reset --hard`, `clean`, `clone`, `init`, `worktree remove`, or enrolled `checkout`. Tests create git fixtures only under `tmp_path`.
- [X] T021 [P] Stop after workspace contract checks pass. Do not start PIV, GitHub push/PR, Telegram, model calls, or agent execution. Do not change `personalAgent/docker-compose.yml`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP prepare
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (`prepare_workspace` create path)
- **User Story 3 (Phase 5)**: Depends on Foundational + US1; sequenced after US2 so dirty/invalid reuse is already refused
- **Polish (Phase 6)**: Depends on the stories being delivered

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependency on US2/US3
- **User Story 2 (P1)**: Depends on US1 prepare; independently testable once inspect, the publish gate, and refuse paths exist
- **User Story 3 (P1)**: Depends on US1 prepare (identity fields) and should follow US2 refuse-dirty; independently testable via reuse + identity assertions

### Within Each User Story

- Tests MUST be written and FAIL before that story’s implementation
- Types/errors/construction before prepare
- Task-id + eligibility gates before `worktree add`
- First-time create before dirty/invalid/fetch handling
- Inspect and publish gate before clean reuse
- Clean reuse before worker_id / no-store identity finish
- Story complete before moving to the next increment

### Parallel Opportunities

- T006 is a different file from T005 and can run after T002–T004
- T017–T019 share verification but T021 is independent of T020 once implementation is done
- Test tasks T007, T010, T014 share `personalAgent/tests/test_workspace_manager.py` — sequential
- Implementation tasks T002–T005, T008–T009, T011–T013, T015–T016 share `personalAgent/src/hermes_kanban/workspace.py` — sequential
- US1/US2/US3 cannot be staffed in true parallel: they share one module and one test file. A single implementer should run them sequentially

---

## Parallel Example: User Story 1

```bash
# After Foundational (T006 is the only other-file task):
Task: "Re-export public workspace types from personalAgent/src/hermes_kanban/__init__.py"

# US1 tests then implementation are sequential (same two files):
Task: "Contract tests in personalAgent/tests/test_workspace_manager.py"
Task: "Implement prepare gates in personalAgent/src/hermes_kanban/workspace.py"
Task: "Implement worktree create in personalAgent/src/hermes_kanban/workspace.py"
```

---

## Parallel Example: User Story 2

```bash
# After US1 prepare exists — still one test file then one module:
Task: "Git-safety contract tests in personalAgent/tests/test_workspace_manager.py"
Task: "Implement inspect_workspace in personalAgent/src/hermes_kanban/workspace.py"
Task: "Implement assert_publish_allowed in personalAgent/src/hermes_kanban/workspace.py"
Task: "Finish dirty/invalid/fetch handling in personalAgent/src/hermes_kanban/workspace.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (confirm empty managed set + configured workspace root)
2. Complete Phase 2: Foundational (types, root validation, git helper, re-exports)
3. Complete Phase 3: User Story 1 (`prepare_workspace` create path)
4. **STOP and VALIDATE**: isolated worktree on `feature/task-<id>`, enrolled branch unchanged, two tasks → two paths
5. Demo prepare on a disposable fixture; do not enroll a production repo

### Incremental Delivery

1. Setup + Foundational → construction validates `workspace.root`
2. Add US1 → first-time prepare independently → MVP
3. Add US2 → refuse protected/dirty/shared; inspect; publish gate
4. Add US3 → clean reuse + correlation identity
5. Each story adds value without starting PIV, GitHub, Telegram, or model calls

### Parallel Team Strategy

This feature is one module plus one test file. Prefer a single implementer moving story-by-story. If two people: one owns git-fixture tests, the other owns `workspace.py`, integrating at each checkpoint. Do not split `workspace.py` into extra packages to create false parallelism.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec user stories US1–US3
- Public names are `prepare_workspace`, `inspect_workspace`, `assert_publish_allowed`
- Worktree path `{root}/{project_id}/{task_id}`; work branch `feature/task-<task_id>`
- Protected set is always `main`, `master`, and the project default
- Production `projects: []` until the owner names a non-critical repo
- Commit after each task or logical group if the owner asks; Conventional Commits (`feat:`, `test:`)
- Stop at any checkpoint to validate the story independently
- Avoid: second SQLite store, GitPython, PyYAML, hardcoded host paths, `git clone`/`init` of enrolled trees, rewriting the adapter or registry, starting PIV/GitHub/Telegram

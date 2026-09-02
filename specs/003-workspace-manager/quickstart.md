# Quickstart: Workspace Manager

**Feature**: `003-workspace-manager`

Validation guide for the workspace, Git-safety, and identity contract. Implementation lives in `personalAgent/` (existing control-plane package). Do not start agent execution, PIV, GitHub push/PR, Telegram, or model calls to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/workspace-manager.md](./contracts/workspace-manager.md). Eligible projects: [project registry contract](../../002-project-registry/contracts/project-registry.md).

## Prerequisites

- Python 3.12 and uv (see `personalAgent/.python-version`)
- `git` on PATH
- This repo’s `personalAgent` checkout

A live managed project and a GitHub account are **not** required. Contract tests build disposable git repositories under pytest’s `tmp_path` (optionally copying `personalAgent/tests/fixtures/projects/standard/` then `git init` + commit). Production `config/default.yaml` MUST keep `projects: []` until the owner names a non-critical repo. Tests MUST NOT bind the workspace root to a hardcoded workstation path.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests construct a temp directory as `workspace.root` and enroll a temp git fixture via the project registry. Docker already mounts workspaces at `/workspaces`; application code reads **configured** `workspace.root`, not `WORKSPACE_ROOT` from the host `.env`.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_workspace_manager.py
uv run ruff check src tests
```

Keep existing tests passing (`tests/test_import.py`, `tests/test_ainative_adapter.py`, `tests/test_project_registry.py`).

## Expected outcomes (SC-006)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| Prepare fixture workspace | Eligible git fixture + valid task id returns a worktree under the configured root on `feature/task-<id>`, not on `main`/`master`/default; enrolled location’s current branch is unchanged |
| Refuse protected work branch | Prepare or `assert_publish_allowed` that would use `main`, `master`, or the project default as the work/publish branch raises `ProtectedBranchError`; no checkout onto that branch |
| Refuse dirty reuse | Second prepare of the same project+task when the copy has uncommitted changes raises `DirtyWorkspaceError`; those files remain; other task directories are untouched |
| Refuse shared copy | Two task ids receive two different mutable paths; a branch already checked out elsewhere is not shared |
| Inspect reports branch and change status | Clean copy: expected branch, `dirty` false, empty changes. After a local file change: `dirty` true and a non-empty change summary |
| Identity fields present | Successful prepare has non-empty `task_id`, `execution_id`, `project_id`, `workspace_id`; reuse of a clean copy keeps `workspace_id` and issues a new `execution_id`; no reasoning text |

Also required by the spec (same test file is fine):

- Missing/empty/non-directory workspace root → `InvalidWorkspaceRootError`; no substitute path
- Path-like or empty `task_id` → `InvalidTaskIdError`; no filesystem join of the raw id
- Unknown / disabled / bad enrolled location → existing registry errors (`UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`)
- Enrolled path that is not a git repository → `InvalidProjectRepositoryError`; no `git init`
- Missing default branch ref → `MissingDefaultBranchError`
- Remote present and fetch fails → `GitRefreshError`
- Dirty enrolled location does not block preparing a **new** task worktree
- `assert_publish_allowed` on a non-protected feature branch succeeds (allowed later) and performs 0 publishes
- After prepare, nothing under `personalAgent/` holds a copied application repo (only tests’ temp trees)

## Fixture

Do not point tests at a real application repository. In `tmp_path`:

1. Copy or recreate the standard project fixture files.
2. `git init`, set local `user.email` / `user.name`, commit.
3. Ensure the default branch matches the enrolled record (typically `main`).
4. Write operational YAML with `workspace.root` = a temp directory and `projects:` listing that fixture.

A second local bare repository may stand in as `origin` when testing fetch; do not use `github.com`.

## Out of scope for this guide

Docker e2e, writing `kanban.db`, `git push`, pull requests, PIV, Telegram, model calls, and auto-reset of dirty copies. Those wait for later specs.

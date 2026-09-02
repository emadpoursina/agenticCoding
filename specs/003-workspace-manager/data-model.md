# Data Model: Workspace Manager

**Feature**: `003-workspace-manager` | **Date**: 2026-08-30

In-process Python types (dataclasses). No database. Working copies are git worktrees on disk under a configured root. Identity fields are returned on the prepare record; they are not a second store.

## Settings (trust-boundary input)

**Entity**: workspace root loaded from operational config

Loaded from a caller-supplied YAML path; never inferred from the developer machine. Other config keys are ignored by this loader (`projects:` is read only by `ProjectRegistry`).

| Field | Type | Rules |
|---|---|---|
| `root` | `Path` | Required. Non-empty. Must exist as a readable directory at construction / `from_config`. |

**Validation**: Runs at `WorkspaceManager` construction. Failure → `InvalidWorkspaceRootError`. No fallback path (`/workspaces`, `$HOME`, env).

**Ignored**: Every config key other than `workspace.root`. Missing `workspace:` or `root` → `InvalidWorkspaceRootError` (not an empty-root success).

## Isolated working copy

**Entity**: `PreparedWorkspace` (success result of `prepare_workspace`)

The versioned checkout for exactly one project identity and one task identity. Not the enrolled project location.

| Field | Type | Rules |
|---|---|---|
| `path` | `Path` | Absolute location under the workspace root: `{root}/{project_id}/{task_id}`. Maps later to Kanban `workspace_path`. |
| `branch` | `str` | `feature/task-<task_id>`. Never a protected name. Maps later to Kanban `branch_name`. |
| `project_id` | `str` | Enrolled identity. Maps later to Kanban `project_id`. |
| `task_id` | `str` | Validated caller task identity. |
| `workspace_id` | `str` | Stable `ws-{project_id}-{task_id}` for this project+task copy. |
| `execution_id` | `str` | Unique per successful prepare (`uuid4` hex). |
| `worker_id` | `str \| None` | Set only when the caller supplied a non-empty worker identity. |
| `remote` | `str \| None` | Remote URL when a remote exists; omitted (`None`) when the fixture is local-only. |

**Layout**: `{workspace_root}/{project.id}/{task_id}/` after identity checks. Unrelated tasks MUST NOT share this directory.

**Origin**: `git worktree add` from the eligible project’s `location`. The enrolled location’s current branch MUST remain unchanged.

## Feature branch

**Entity**: work-branch name (string rule, not a stored row)

| Field | Type | Rules |
|---|---|---|
| name | `str` | Exactly `feature/task-<task_id>`. No extra slug. |
| base | `str` | Project default branch. With a remote: `{remote}/{default_branch}` after a successful fetch. Without a remote: local default. |

**Protected set** (must not be the work branch; `assert_publish_allowed` refuses them):

- `main`
- `master`
- the eligible project’s `default_branch`

## Correlation identity

**Entity**: `CorrelationIdentity`

Subset of `PreparedWorkspace` used to reconstruct which run happened where. Not a transcript.

| Field | Type | Rules |
|---|---|---|
| `task_id` | `str` | Non-empty. Not path-like. |
| `execution_id` | `str` | Unique per successful prepare. |
| `project_id` | `str` | Enrolled id. |
| `workspace_id` | `str` | Stable for the same project+task working copy. |
| `worker_id` | `str \| None` | Optional. |

**Forbidden contents**: private reasoning, chain-of-thought, model transcript text, full file diffs, methodology instruction bodies.

`PreparedWorkspace` MAY embed these fields directly (no separate persistence). Callers MAY treat the prepare result as the identity record.

## Workspace inspection

**Entity**: `WorkspaceInspection`

Point-in-time report. Inspect MUST NOT repair, delete, reset, or publish.

| Field | Type | Rules |
|---|---|---|
| `path` | `Path` | The inspected working copy. |
| `branch` | `str` | Current branch (`rev-parse --abbrev-ref HEAD`). |
| `dirty` | `bool` | `True` iff `git status --porcelain` is non-empty (untracked counts). |
| `changes` | `tuple[str, ...]` | Porcelain status lines when `dirty`; empty tuple when clean (omit-equivalent). |

## Relationships

```text
config YAML workspace.root  --(construction)-->  WorkspaceManager
ProjectRegistry.resolve_eligible_project  -->  ProjectRecord
ProjectRecord.location (enrolled git repo) + task_id
    --(prepare)-->  git worktree at {root}/{project_id}/{task_id}
    --(return)-->  PreparedWorkspace
PreparedWorkspace.path  --(inspect)-->  WorkspaceInspection
```

- One workspace root per manager instance.
- One working copy directory per `(project_id, task_id)`.
- Many `execution_id` values may refer to the same `workspace_id`.
- Enrolled `ProjectRecord.location` is never the edit directory.
- Disk paths under the workspace root that belong to other tasks have **no** relationship that allows deletion.

## State transitions

```text
prepare_workspace(project_id, task_id)
  ├─ bad root (construction)     → InvalidWorkspaceRootError
  ├─ bad task id                 → InvalidTaskIdError
  ├─ registry eligibility fail   → Unknown / Disabled / InvalidProjectLocation
  ├─ enrolled not a git repo     → InvalidProjectRepositoryError
  ├─ default branch missing      → MissingDefaultBranchError
  ├─ remote fetch fails          → GitRefreshError
  ├─ work branch protected       → ProtectedBranchError
  ├─ path dirty existing copy    → DirtyWorkspaceError (files kept)
  ├─ path invalid / mismatch /
  │  branch checked out elsewhere → InvalidWorkspaceError (no overwrite)
  ├─ path missing                → create worktree → PreparedWorkspace (new execution_id)
  └─ path clean expected branch  → reuse → PreparedWorkspace (same workspace_id, new execution_id)

inspect_workspace
  ├─ missing / not git / mismatch → InvalidWorkspaceError
  └─ valid                        → WorkspaceInspection (clean or dirty)

assert_publish_allowed(branch, default_branch=...)
  ├─ main / master / default     → ProtectedBranchError
  └─ other                       → success (allowed later; this phase does not publish)
```

No agent, push, PR, or Kanban-row states in this phase.

## Validation summary (trust boundaries)

| Boundary | What fails |
|---|---|
| Construction / `from_config` | Workspace root shape and existence |
| `prepare_workspace` | Task id, project eligibility, git repo, default branch, refresh, protected work branch, dirty/invalid existing copy |
| `inspect_workspace` | Missing, invalid, or mismatched working copy |
| `assert_publish_allowed` | Protected branch names |

Host-to-container mapping of a folder onto the configured workspace root is environment configuration (Compose volumes), not a manager default.

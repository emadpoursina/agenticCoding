# Contract: Workspace Manager (in-process)

**Feature**: `003-workspace-manager` | **Package**: `hermes_kanban.workspace`

Library API, not HTTP. Callers are later Hermes workers in the same Python process. Agent execution, model calls, Git hosting (push/PR), and Telegram are **not** in this contract.

Types: see [data-model.md](../data-model.md). Workspace errors subclass `WorkspaceError`. Project eligibility errors are the existing `ProjectRegistryError` types and MUST propagate unchanged.

## Construction

```python
def load_workspace_root(config_path: Path) -> Path: ...

class WorkspaceManager:
    def __init__(self, workspace_root: Path, registry: ProjectRegistry) -> None: ...

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        registry: ProjectRegistry | None = None,
    ) -> WorkspaceManager: ...
```

**Trust boundary**: `__init__` / `from_config` / `load_workspace_root` validate the workspace root. They MUST raise `InvalidWorkspaceRootError` when:

- `config_path` is missing or unreadable (for `from_config` / `load_workspace_root`)
- `workspace.root` is absent or empty
- the resolved root is missing, not a directory, or unreadable

They MUST NOT substitute `/workspaces`, the developer home directory, `WORKSPACE_ROOT`, or any other path.

`load_workspace_root` reads only the `workspace.root` scalar; other YAML keys are ignored.

`from_config` uses `registry` when provided; otherwise `ProjectRegistry.from_config(config_path)`. Eligibility is still checked per call, not at construction (a disabled project may appear in the registry).

## Prepare

```python
def prepare_workspace(
    self,
    project_id: str,
    task_id: str,
    *,
    worker_id: str | None = None,
) -> PreparedWorkspace: ...
```

- MUST call `resolve_eligible_project(project_id)` first. Unknown / disabled / invalid location → existing registry errors. MUST NOT invent a project path.
- `task_id` empty or path-like (`/`, `\`, `..`, extra segments) → `InvalidTaskIdError`. MUST NOT join the raw id onto a filesystem path before this check.
- Enrolled location not a git work tree → `InvalidProjectRepositoryError`. MUST NOT `git init` or clone from a network remote.
- Project default branch missing as a ref → `MissingDefaultBranchError`. MUST NOT guess a different base than the registry record (including its `main` fallback already applied on the record).
- If the enrolled repo has a remote: record remote identity; `git fetch` that remote (prefer `origin`). Fetch failure, or `{remote}/{default_branch}` missing after fetch → `GitRefreshError`. If there is no remote, skip fetch; `remote` on the result is `None`.
- Work branch MUST be `feature/task-<task_id>`. If that name is protected (`main`, `master`, or the project default) → `ProtectedBranchError`. MUST NOT check out a protected branch as the task work branch.
- Working copy path MUST be `{workspace_root}/{project.id}/{task_id}` using the enrolled id and the validated task id.
- New copy: `git worktree add` from the enrolled location onto the base ref above. MUST NOT change the enrolled location’s current branch.
- Existing clean copy on the expected branch: reuse. Same `workspace_id`, new `execution_id`.
- Existing dirty copy: `DirtyWorkspaceError`. MUST NOT reset, clean, discard, or overwrite. MUST NOT delete another task’s directory.
- Existing invalid / mismatched / non-git path, or feature branch already checked out in another worktree: `InvalidWorkspaceError`. MUST NOT overwrite.
- `worker_id` omitted, `None`, or `""` → result `worker_id` is `None`. MUST NOT invent a worker name.
- Result MUST include non-empty `task_id`, `execution_id`, `project_id`, `workspace_id`, `path`, and `branch`. MUST NOT include reasoning or transcript text.
- MUST NOT execute agents, call models, push, open pull requests, merge, deploy, or send notifications.

## Inspect

```python
def inspect_workspace(self, project_id: str, task_id: str) -> WorkspaceInspection: ...
```

- Same `project_id` / `task_id` identity rules as prepare (eligibility + task id). Inspecting a path that does not exist or is not this task’s valid copy → `InvalidWorkspaceError`.
- MUST return current branch, `dirty`, and `changes` (empty when clean).
- MUST NOT create, repair, reset, delete, or publish as a side effect.

## Publish gate

```python
def assert_publish_allowed(self, branch: str, *, default_branch: str) -> None: ...
```

- `branch` in `{main, master, default_branch}` → `ProtectedBranchError`.
- Any other branch: return (allowed later).
- This phase MUST NOT publish, push, or create a pull request.
- `default_branch` is the project’s default (caller supplies it from the project record). Empty `branch` or empty `default_branch` → `ProtectedBranchError` (refuse, do not guess).

## Out of contract

- Writing Hermes `kanban.db` / `projects.db`
- `git push`, PR creation, merge, SSH, network clone
- Automatic cleanup or reset of dirty copies
- Concurrent task scheduling (isolation is still required)
- `execute_agent`, PIV, Telegram, methodology mutation
- Enrolling projects (use the project registry)

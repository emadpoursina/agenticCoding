# Contract: Project Registry (in-process)

**Feature**: `002-project-registry` | **Package**: `hermes_kanban.projects`

Library API, not HTTP. Callers are later Hermes workers in the same Python process. Workspace creation, agent execution, model calls, Git hosting, and Telegram are **not** in this contract.

Types: see [data-model.md](../data-model.md). Errors: all subclass `ProjectRegistryError`.

## Construction

```python
def load_project_entries(config_path: Path) -> list[ProjectRecord]: ...

class ProjectRegistry:
    def __init__(self, projects: list[ProjectRecord]) -> None: ...

    @classmethod
    def from_config(cls, config_path: Path) -> ProjectRegistry: ...
```

**Trust boundary**: `from_config` / `load_project_entries` / `__init__` validate the managed set. They MUST raise `InvalidProjectConfigError` when:

- `config_path` is missing or unreadable (for `from_config` / `load_project_entries`)
- An entry omits `id`, `name`, `repository`, or `location`, or any of those is empty
- Two entries share an `id`, `repository`, or location (trailing-slash-normalized)
- A config `id` is path-like
- A named `manifest` is absolute, empty, or would escape the project root
- `settings` contains a non-scalar value

They MUST NOT substitute a repository found on disk. Missing `projects:` is an empty managed set. `__init__` MAY accept an already-validated list (tests); it MUST still reject duplicates and invalid ids if the caller passes them.

`load_project_entries` reads only the `projects:` sequence; other YAML keys are ignored.

`from_config` MUST NOT `stat` locations. Location existence is an eligibility check.

## Read operations

```python
def list_projects(self) -> list[ProjectRecord]: ...
```

- Returns every configured operational record, including disabled.
- Order: config file order.
- MUST NOT read any project source tree.
- Empty list is valid.

```python
def get_project(self, project_id: str) -> ProjectRecord: ...
```

- `project_id` MUST be an exact configured `id`.
- Unknown ids, path-like names, and `../` identities → `UnknownProjectError` (same type). MUST NOT join the raw id onto a filesystem path.
- Result is the operational record only (no knowledge files).

```python
def resolve_eligible_project(self, project_id: str) -> ProjectRecord: ...
```

- Same identity rules as `get_project` (`UnknownProjectError`).
- `enabled is False` → `DisabledProjectError`.
- Location missing, empty, not a directory, or unreadable → `InvalidProjectLocationError`. MUST NOT fall back to another directory.
- On success, returns the operational record (still no knowledge files).

```python
def load_project_context(self, project_id: str) -> ProjectContext: ...
```

- MUST apply `resolve_eligible_project` first (same errors).
- Chosen structured source: named `manifest` if set, else `.ainative/project.yaml`. MUST NOT search the tree. MUST NOT fall back from a named path to the default path.
- Named path missing / non-file / unreadable, or default path missing / missing required fields / empty validation commands → `MissingProjectConfigurationError`.
- Unparseable structured source → `MalformedManifestError`.
- Named manifest or AI context pointer that escapes the project root → `UnsafePathError`.
- Listed AI context pointer missing or unreadable → `MissingProjectConfigurationError` (required pointer).
- MUST NOT invent validation or development commands.
- MUST NOT persist the bundle. MUST NOT copy project knowledge into the control-plane tree.

## Overlay

When both sides declare `name`, `default_branch`, or commands, the **project-side** value is what `ProjectContext` exposes. `id` and enrollment `repository` stay operational. Manifest `repository` is `declared_repository`. `settings` pass through unchanged.

## Out of contract

- Creating worktrees, branches, or workspaces
- Writing to Hermes `projects.db` / `kanban.db`
- Auto-enrolling `discovered_repos` or any unlisted directory
- Interpreting `settings` keys
- `execute_agent`, PIV, GitHub, Telegram
- Mutating the project repository

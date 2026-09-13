# Contract: AiNative Adapter (in-process)

**Feature**: `001-ainative-adapter` | **Package**: `hermes_kanban.ainative`

Library API, not HTTP. Callers are later Hermes workers in the same Python process. `execute_agent` is **not** in this contract.

Types: see [data-model.md](../data-model.md). Errors: all subclass `AiNativeAdapterError`.

## Construction

```python
class AiNativeSettings:
    path: Path
    read_only: bool

def load_ainative_settings(config_path: Path) -> AiNativeSettings: ...

class AiNativeAdapter:
    def __init__(self, settings: AiNativeSettings) -> None: ...

    @classmethod
    def from_config(cls, config_path: Path) -> AiNativeAdapter: ...
```

**Trust boundary**: `__init__` and `from_config` validate settings. They MUST raise `InvalidMethodologyError` when:

- `config_path` is missing or unreadable (for `from_config` / `load_ainative_settings`)
- `ainative.path` or `ainative.read_only` is absent from config
- `path` is empty, missing, not a directory, or lacks `docs/agents/`
- `read_only` is not `true`

They MUST NOT substitute another location. Callers never receive an instance bound to a guessed path.

`load_ainative_settings` reads only the `ainative:` mapping; other YAML keys are ignored.

## Read operations

```python
def list_agents(self) -> list[str]: ...
```

- Returns sorted names of agent folders under `{path}/docs/agents/`.
- Excludes `template`, `_skills`, and non-directories.
- Empty roster is allowed (still a valid location).

```python
def get_agent(self, name: str) -> AgentDefinition: ...
```

- `name` MUST be an exact member of `list_agents()`.
- Unknown names, `template`, `_skills`, nested paths, `../` names → `UnknownAgentError` (same type, no disk join of the raw name).
- Listed folder with none of `AGENTS.md` / `SKILL.md` / `rule.md` → `IncompleteAgentError`.
- Present but unreadable instruction file → `IncompleteAgentError` (or a subclass); MUST NOT omit the field.
- MUST NOT include a concatenated instruction blob.

```python
def resolve_agent_dependencies(self, name: str) -> list[AgentDependency]: ...
```

- Same name identity rules as `get_agent` (`UnknownAgentError`).
- Result items: `kind` (`"rule"` | `"skill"`), `name`, `path`, `text`.
- Includes `rule.md` as `kind="rule"` when that file exists.
- Includes each unique `<!-- source: _skills/<name>/SKILL.md -->` from the how-to file as `kind="skill"`.
- Missing or unreadable referenced skill → `UnresolvedDependencyError`; MUST NOT return a partial list.
- `get_agent` MAY still succeed when resolve would fail.

```python
def capture_revision(self, path: Path) -> Revision: ...
```

- Returns `{repository, sha, branch, dirty}` as in the data model.
- Not a git work tree, or empty SHA → `RevisionError`.
- Dirty work tree → success, `dirty=True`, `sha` remains HEAD.

```python
def build_execution_context(
    self,
    agent: AgentDefinition,
    *,
    workflow_phase: str | None = None,
) -> ExecutionContext: ...
```

- `methodology_path` is the configured settings path.
- `revision` is `capture_revision(methodology_path)`.
- `agent` is stored as given.
- `workflow_phase` included only when not `None`.
- MUST NOT invent task, project, or workspace values.

## Refused writes

These methods exist so the read-only guarantee is testable. They MUST raise `ReadOnlyError` and MUST NOT create, modify, delete, or copy any file.

```python
def write_file(self, relative_path: str, content: str) -> None: ...
def copy_tree(self, destination: Path) -> None: ...
```

## Errors

| Exception | Condition |
|---|---|
| `InvalidMethodologyError` | Config/path/`read_only`/agents-root failures at the boundary |
| `UnknownAgentError` | Name not in roster (including reserved and path-like) |
| `IncompleteAgentError` | Listed agent with no readable instruction files, or unreadable instruction file |
| `UnresolvedDependencyError` | Referenced `_skills/<name>/SKILL.md` missing or unreadable |
| `RevisionError` | `path` is not a versioned repository / SHA unreadable |
| `ReadOnlyError` | `write_file` / `copy_tree` |

## Out of contract

- `execute_agent`
- Model calls, PIV, worktrees, GitHub, Telegram
- Writing AiNative, copying methodology into workspaces or this repo
- Loading config keys other than `ainative.path` / `ainative.read_only`

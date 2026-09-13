# Data Model: AiNative Adapter

**Feature**: `001-ainative-adapter` | **Date**: 2026-08-28

In-process Python types (dataclasses). No database. AiNative folders on disk remain the source of truth; these types are the read model the adapter returns.

## Settings (trust-boundary input)

**Entity**: `AiNativeSettings`

Loaded from operational config; never inferred from the developer machine.

| Field | Type | Rules |
|---|---|---|
| `path` | `Path` | Non-empty. Must exist and be a directory. Must contain `docs/agents/` as a directory. Not a file. |
| `read_only` | `bool` | Must be `true`. `false` or missing → construction fails. |

**Validation**: Runs at adapter construction (`from_config` / `__init__`). Failure → `InvalidMethodologyError`. No fallback path.

**Ignored**: Every other config key (`workspace`, `github`, `execution`, …).

## Agent definition

**Entity**: `AgentDefinition`

A named folder under `{methodology}/docs/agents/{name}/`. Not a process.

| Field | Type | Rules |
|---|---|---|
| `name` | `str` | Exact folder name; identical to a `list_agents()` entry. |
| `purpose_path` | `Path \| None` | `{agent}/AGENTS.md` if that file exists; else omitted. |
| `howto_path` | `Path \| None` | `{agent}/SKILL.md` if present. |
| `constraints_path` | `Path \| None` | `{agent}/rule.md` if present. |
| `purpose` | `str \| None` | Unmodified UTF-8 contents of `AGENTS.md` when the file exists; omitted when it does not. |
| `howto` | `str \| None` | Unmodified UTF-8 contents of `SKILL.md` when present. |
| `constraints` | `str \| None` | Unmodified UTF-8 contents of `rule.md` when present. |

**Validation**:
- `name` must be a single path segment in the roster. Reserved (`template`, `_skills`) and path-like names are not loadable (`UnknownAgentError`).
- If all three files are absent, load fails (`IncompleteAgentError`).
- If a named file exists but cannot be read, load fails (do not omit).
- No concatenated instruction field.

**Relationships**: One definition per listed folder. Dependencies are a separate list (below), not embedded as a blob.

**State**: Stateless. Re-read from disk on each `get_agent` (working-tree text, not HEAD blobs).

## Agent dependency

**Entity**: `AgentDependency`

One supporting rule or skill used when a later executor assembles context.

| Field | Type | Rules |
|---|---|---|
| `kind` | `"rule"` \| `"skill"` | Discriminator. |
| `name` | `str` | For `rule`: the agent name. For `skill`: the `_skills/<name>/` folder name. |
| `path` | `Path` | Absolute path of the file that was read. |
| `text` | `str` | Unmodified UTF-8 file contents. |

**Derivation**:
1. If `{agent}/rule.md` exists and is readable → one `rule` item.
2. Each unique `<!-- source: _skills/<name>/SKILL.md -->` in the how-to document → one `skill` item from `{agents_root}/_skills/<name>/SKILL.md`.
3. Any referenced skill missing or unreadable → entire resolve fails; no partial list.

**Relationships**: Belongs to one agent. `_skills` is not an agent. Skills appear only as dependencies.

## Revision

**Entity**: `Revision`

Stamp of which methodology snapshot was read, and whether the working tree may differ from that commit.

| Field | Type | Rules |
|---|---|---|
| `repository` | `str` | `origin` URL if `git remote get-url origin` succeeds; otherwise the path string that was captured. |
| `sha` | `str` | Non-empty `HEAD` commit identity. Never invented. |
| `branch` | `str` | Current branch name, or `"detached"` when `rev-parse --abbrev-ref HEAD` is `HEAD`. |
| `dirty` | `bool` | `true` when `git status --porcelain` is non-empty; else `false`. |

**Validation**: Path must be a git work tree with a readable `HEAD`. Otherwise `RevisionError`. Dirty does not fail.

**State**: Point-in-time. Capture again for a later stamp; do not cache across process lifetime as if it were a lock.

## Execution context

**Entity**: `ExecutionContext`

Stable bundle for a later executor. This phase does not run the agent.

| Field | Type | Rules |
|---|---|---|
| `methodology_path` | `Path` | The configured settings path (not a guessed substitute). |
| `revision` | `Revision` | Capture of `methodology_path`. |
| `agent` | `AgentDefinition` | The definition passed in (already loaded). |
| `workflow_phase` | `str \| None` | Present only when the caller supplied it; stored unchanged. |

**Absent in this phase**: `task`, `project`, `workspace`. Do not invent IDs or paths.

**Relationships**: Context *references* methodology in place (paths + text already on `agent`); it does not copy the tree.

## Methodology location (filesystem, not a row)

Not stored. The configured directory is the entity. Invariants:

- Read in place.
- Must contain `docs/agents/`; do not scan the rest of the tree for agents.
- Symlinks: follow the configured path as given.
- Concurrent readers allowed; no writer in this adapter.

## State transitions

None. The adapter does not own Kanban or workflow state. `workflow_phase` is an opaque string echoed onto the context when provided.

## Roster rules (derived)

```text
docs/agents/
├── scout/                 # agent
├── tester/                # agent
├── critic/                # agent
├── template/              # NEVER an agent
└── _skills/<name>/        # NEVER an agent; skill files only via resolve
```

`list_agents` = sorted directory names except `template` and `_skills` (and non-directories).

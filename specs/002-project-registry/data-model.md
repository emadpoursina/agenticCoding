# Data Model: Project Registry

**Feature**: `002-project-registry` | **Date**: 2026-08-29

In-process Python types (dataclasses). No database. Operational records come from configuration; project knowledge stays in the project tree. These types are the read model the registry returns.

## Settings (trust-boundary input)

**Entity**: managed-set entries loaded from operational config

Loaded from a caller-supplied YAML path; never inferred from the developer machine. Other config keys are ignored.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Required. Non-empty. Not path-like (`/`, `\`, `..`, extra segments). Unique in the set. |
| `name` | `str` | Required. Non-empty. |
| `repository` | `str` | Required. Non-empty. Unique in the set (enrollment identity). |
| `location` | `str` | Required. Non-empty path string from config. Unique after trailing-slash normalize. Existence is **not** required at construction. |
| `default_branch` | `str \| None` | Optional. Empty/missing → `None` here; overlay uses `"main"` later if the project also omits it. |
| `enabled` | `bool` | Optional. Missing → `True`. |
| `manifest` | `str \| None` | Optional project-relative path. If set: relative, no root escape. Existence checked at context load, not construction. Missing → use `.ainative/project.yaml`. |
| `settings` | `dict[str, str]` | Optional opaque map. Missing → `{}`. Values MUST be scalars (stored as strings). Nested maps/lists in `settings` fail construction. Keys are not interpreted this phase. |

**Validation**: Runs at registry construction (`from_config` / `__init__`). Failure → `InvalidProjectConfigError`. No fallback project. Duplicate `id`, `repository`, or `location` fails the whole load (not “skip the bad row”).

**Ignored**: Every other config key (`ainative`, `workspace`, `github`, …). Missing `projects:` key → empty list (valid).

## Operational record

**Entity**: `ProjectRecord`

Control-plane identity for one enrolled project. Not the project’s knowledge base.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Configured identity. |
| `name` | `str` | Operational name (context overlay may replace with project-side name). |
| `repository` | `str` | Enrollment identity. Never silently retargeted. |
| `location` | `Path` | Configured local/workspace location. |
| `default_branch` | `str` | Operational declaration or `"main"` if both sides omit (see overlay). On the record itself: configured value if present, else `"main"` as the operational fallback *for listing* when the project has not been loaded. |
| `enabled` | `bool` | Explicit flag; missing config key stored as `True`. |
| `settings` | `dict[str, str]` | Opaque copy from config. |
| `manifest` | `str \| None` | Named project-relative structured source, or `None` meaning `.ainative/project.yaml`. |

**List/get**: Return this record only. Do not attach README text, architecture, tests, or AI knowledge.

**State**: Immutable snapshot of configuration. Re-read config only on new registry construction.

**Listing default branch**: `list_projects` / `get_project` MUST NOT read the project tree (SC-001). They return the operational `default_branch` (configured or `"main"`). Project-side override appears only on `ProjectContext`.

## Operational manifest

**Entity**: `ProjectManifest`

Parsed structured fields from the chosen project-side file.

| Field | Type | Rules |
|---|---|---|
| `name` | `str` | Required. |
| `description` | `str \| None` | Optional. |
| `repository` | `str` | Required in the file. Recorded as the project’s declaration; does not change enrollment. |
| `default_branch` | `str` | Required. |
| `workflow` | `str \| None` | From `workflow.default` when present. |
| `validation_commands` | `tuple[str, ...]` | Required. Non-empty. Exact strings from the file; never invented. |
| `development_commands` | `tuple[str, ...] \| None` | Optional. `None` if omitted; empty list if the key exists and is empty (empty is allowed for optional development; it is **not** allowed for validation). |
| `ai_context` | `tuple[str, ...]` | Optional list of project-relative paths. Default empty. Each path is validated at load. |

**Selection**: operational `manifest` if set, else `.ainative/project.yaml`. No search. No fallback.

**Validation**: Missing file, missing required fields, empty `validation.commands`, or unreadable file → `MissingProjectConfigurationError`. Unparseable subset YAML → `MalformedManifestError`. Out-of-root `manifest` path → `UnsafePathError`.

## Project context

**Entity**: `ProjectContext`

In-memory bundle for a later executor. Not persisted.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Operational. |
| `name` | `str` | Project-side wins. |
| `repository` | `str` | Operational enrollment identity. |
| `declared_repository` | `str` | Manifest `repository` (may differ). |
| `default_branch` | `str` | Project-side wins; else operational; else `"main"`. |
| `location` | `Path` | Configured location that passed eligibility. |
| `workflow` | `str \| None` | From manifest when declared. |
| `validation_commands` | `tuple[str, ...]` | Project-side, required, unchanged. |
| `development_commands` | `tuple[str, ...] \| None` | Project-side when declared. |
| `settings` | `dict[str, str]` | Operational, unchanged. |
| `overview` | `str \| None` | Text of first existing overview slot file. |
| `agent_instructions` | `str \| None` | Text of first existing agent/AI slot file. |
| `contributing` | `str \| None` | Text of `CONTRIBUTING.md` when present. |
| `architecture` | `str \| None` | Text of first existing architecture slot file. |
| `ai_context_files` | `tuple[ContextFile, ...]` | Text of each listed AI context pointer. |
| `tooling_paths` | `tuple[str, ...]` | Project-relative names from the closed root set that exist. |

**Entity**: `ContextFile`

| Field | Type | Rules |
|---|---|---|
| `path` | `str` | Project-relative POSIX path as listed. |
| `text` | `str` | Unmodified UTF-8 contents. |

**Conventional slot candidates** (first existing file wins; omit slot if none):

| Slot | Files |
|---|---|
| overview | `README.md`, `README` |
| agent_instructions | `AGENTS.md`, `CLAUDE.md` |
| contributing | `CONTRIBUTING.md` |
| architecture | `docs/architecture.md`, `ARCHITECTURE.md` |

**Tooling closed set** (project root only, path not text): `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`.

**Validation**:
- Call `resolve_eligible_project` first (unknown / disabled / bad location fail before any project file is copied into the bundle).
- Required pointers that are missing, unreadable, or out of root fail the load.
- Optional conventional files that are unreadable are omitted.
- The registry MUST NOT write this bundle to disk.

## Relationships

```text
config YAML  --(construction)-->  list[ProjectRecord]
ProjectRecord.location + ProjectRecord.manifest  --(load)-->  ProjectManifest
ProjectRecord + ProjectManifest + conventional files  --(overlay)-->  ProjectContext
```

- One `ProjectRecord` per configured `id`.
- One chosen manifest file per load.
- Zero or more conventional text slots; zero or more AI context files; zero or more tooling paths.
- Disk repositories that are not in the managed set have **no** relationship.

## State transitions

Operational `enabled` is not a workflow. Eligibility is a gate, not a stored state.

```text
configured
  ├─ list / get     → ProjectRecord (always, if id exists)
  ├─ disabled       → resolve/load fail (DisabledProjectError)
  ├─ bad location   → resolve/load fail (InvalidProjectLocationError)
  └─ eligible
        ├─ missing/malformed manifest → load fail
        └─ valid manifest             → ProjectContext (in-memory)
```

No workspace, branch, or worktree states in this phase.

## Validation summary (trust boundaries)

| Boundary | What fails |
|---|---|
| Construction / `from_config` | Shape of the managed set |
| `get_project` | Unknown / path-like id |
| `resolve_eligible_project` | Unknown, disabled, invalid location |
| `load_project_context` | All of the above, plus manifest/path/pointer failures |

Host-to-container path mapping is environment configuration (Compose volumes), not a registry default.

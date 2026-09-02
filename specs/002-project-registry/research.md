# Research: Project Registry

**Feature**: `002-project-registry` | **Date**: 2026-08-29

Phase 0 resolves every Technical Context choice against the spec, constitution, V0 plan §12–14, discovery, and the live `personalAgent` tree. No `[NEEDS CLARIFICATION]` remains.

## 1. Where the registry lives

**Decision**: One module in the existing control-plane package: `personalAgent/src/hermes_kanban/projects.py`. Re-export public types from `hermes_kanban/__init__.py`. Checks in `personalAgent/tests/test_project_registry.py` plus a small fixture tree under `personalAgent/tests/fixtures/projects/`.

**Rationale**: `src/hermes_kanban/` is already the control-plane package (`ainative.py` is the only feature module). Constitution III forbids a second control plane. Spec FR-017: reuse the existing package; do not add a second project store. One module until the file is no longer readable — do not pre-split into types/config/loader files. Mirror the adapter: construction + four public operations.

**Alternatives considered**:
- New top-level package `project_registry/` — extra install surface, unused.
- `hermes_kanban/registry/` package with several modules — premature; this phase is list/get/resolve/load.
- Wrapping Hermes `projects.db` as the managed-set source — see §3.

## 2. Language, tooling, dependencies

**Decision**: Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff already in `[project.optional-dependencies] dev`. **No new runtime dependencies.** Stdlib only: `pathlib`, `dataclasses`, `re`. No `git` (this phase does not capture revision). No SQLite.

**Rationale**: Constitution hard constraints and `pyproject.toml` already pin this. Spec assumption: configuration parsing and file discovery use platform capabilities already present.

**Alternatives considered**:
- PyYAML / pydantic — owner did not approve new deps.
- GitPython / subprocess git — not needed; spec says a missing git repo at the location is still a valid context load.
- Adding the registry to the Hermes image — would fork Hermes (forbidden).

## 3. Persistence: config vs `projects.db`

**Decision**: The managed set is loaded from operational YAML (`projects:` in a caller-supplied config path; production: `personalAgent/config/default.yaml`). Records live in memory for the process. This phase does **not** read or write Hermes `projects.db`, does **not** create a second SQLite file, and does **not** enroll `discovered_repos`.

`config/default.yaml` gains an explicit empty list:

```yaml
projects: []
```

A missing `projects:` key is treated as an empty list (valid; nothing auto-discovered). Tests pass a temp config; they never bind to a hardcoded workstation path or a live production checkout.

**Rationale**: Spec FR-001 / FR-018 and V0 plan §12: “Use a simple configuration-backed registry for V0. Do not introduce a database unless Hermes' existing persistence architecture requires it.” Discovery notes `projects.db` has `projects`, `project_folders`, **`discovered_repos`**. Querying that store as the managed set would auto-surface disk repos, which FR-018 and US3 forbid. Constitution III forbids a *second* project/task database; it does not require this phase to wrap native discovery. README’s “Hermes `projects.db` + config-backed operational settings” remains the long-term picture: later phases that persist `project_id` onto Kanban tasks may use native `projects.db`; this phase’s job is enrollment + context load from config.

**Alternatives considered**:
- Native `projects.db` as SoT — conflicts with explicit enrollment and no-auto-discovery.
- A new `registry.db` in this package — second project store (FR-017).
- Env-only project list — skips structured fields and makes host pytest accidentally bind to a laptop path.
- Defaulting empty config to `../some-repo` — silent substitute; SC-007 forbids it.

## 4. Operational YAML shape

**Decision**: Scan only the `projects:` block from the caller-supplied config. Other keys (`ainative`, `workspace`, `github`, …) are ignored (FR-020). Each list item is a mapping with:

| Key | Required | Notes |
|---|---|---|
| `id` | yes | Exact identity string; not path-like |
| `name` | yes | Operational name; project-side may override later |
| `repository` | yes | Enrollment identity (URL or owner/name string as configured) |
| `location` | yes | Local/workspace path string from config, not from `$HOME` defaults |
| `default_branch` | no | Fallback `main` if omitted here *and* omitted on the project |
| `enabled` | no | Missing → enabled (`true`) |
| `manifest` | no | Project-relative path; omit → `.ainative/project.yaml` |
| `settings` | no | Opaque string-to-string map; missing → `{}` |

Construction (or `from_config`) validates required fields, duplicate `id`, duplicate `repository` strings, duplicate `location` strings (trailing-slash normalized, no `stat`), path-like config IDs, and that a named `manifest` is a relative path that does not escape `.`. It does **not** require the location to exist yet — SC-001 lists/resolves identity without reading the project tree. Existence and “is a directory” are `resolve_eligible_project` / `load_project_context` checks.

**Rationale**: FR-002–FR-008, US1, US3. Locations come from configuration. Empty managed set is valid.

**Alternatives considered**:
- Stat location at construction — would make `list_projects` depend on disk layout and break SC-001’s “without reading the source tree.”
- JSON config — would replace the already-written operational YAML.
- Interpreting `settings` keys (retries, heartbeats, models) — forbidden this phase.

## 5. YAML subset parser

**Decision**: A line-oriented indent parser in `projects.py` covering the two document shapes this feature needs: (1) a `projects:` sequence of mappings with an optional nested `settings:` scalar map; (2) a project manifest mapping with optional nested `workflow.default`, `validation.commands` / `development.commands` (lists of scalars), and `ai.context` (list of scalars). Support comments, 2-space indent, unquoted scalars, `true`/`false`, and flow empties `[]` / `{}`.

`ponytail:` this is not YAML. It will not parse aliases, tags, multiline `|`/`>`, quoted escape sequences, or nested sequences of mappings beyond the `projects:` list. Upgrade: owner-approved PyYAML if either document grows.

Do **not** refactor `load_ainative_settings` in this phase (no unrequested shared YAML abstraction). Two independent scanners of the same file is the existing pattern.

**Rationale**: No new deps. The adapter already established a documented subset. The manifest in V0 plan §13 is nested lists, so the two-scalar scanner is not enough.

**Alternatives considered**:
- PyYAML — new dependency.
- JSON-only manifests — contradicts the standard `.ainative/project.yaml` convention already specified.
- Hand-rolled per-key regexes with no nest support — cannot express `validation.commands` lists.

## 6. Public operations and identity

**Decision**: `ProjectRegistry` exposes exactly the spec names:

| Operation | Success when |
|---|---|
| `list_projects()` | Every configured operational record, including disabled |
| `get_project(id)` | Exact configured ID |
| `resolve_eligible_project(id)` | Configured, enabled, location exists as a readable directory |
| `load_project_context(id)` | Eligible (FR-005) **and** chosen structured source supplies required fields |

Caller `id` must be an exact configured ID. Path-like names (`/`, `\`, `..`, extra path segments) share `UnknownProjectError` with unknown IDs. **Never** join a caller-supplied identity onto a filesystem path (FR-004). Config IDs that are path-like fail at construction (`InvalidProjectConfigError`), not as “unknown.”

**Rationale**: FR-003–FR-005, FR-009, edge cases on path-like identities.

**Alternatives considered**:
- `get_project` returning `None` — forbidden (empty record).
- Auto-picking the only configured project when id is omitted — not in this phase’s contract.
- Searching `location` by joining `id` — path traversal.

## 7. Eligibility vs list

**Decision**: Disabled projects appear in `list_projects()` and `get_project()`. They fail `resolve_eligible_project` and `load_project_context` with `DisabledProjectError`. Missing / non-directory / unreadable location fails those two with `InvalidProjectLocationError` and does not fall back to another directory. Unknown ID is always `UnknownProjectError`.

**Rationale**: US3, FR-005, FR-008. Distinct visible errors, not one generic exception with a string the caller must parse (callers may still read the message).

**Alternatives considered**: One exception class with a code enum — slightly less code, worse call-site checks. Filtering disabled out of `list_projects` — contradicts US1 scenario 5.

## 8. Manifest selection

**Decision**: If the operational record’s `manifest` is set, that project-relative file is the only structured source. If omitted, `.ainative/project.yaml` only. No tree search. No fallback from a named path to the standard path. Named path must be relative and stay inside the project root after resolve (`Path.is_relative_to`). Missing, non-file, unreadable, or out-of-root named path → trust-boundary failure (`MissingProjectConfigurationError` or `UnsafePathError` as appropriate).

Required fields in the chosen file: `name`, `repository`, `default_branch`, `validation.commands` (non-empty list). Optional: `description`, `workflow.default`, `development.commands`, `ai.context`.

**Rationale**: FR-012–FR-015 and the 2026-08-29 clarifications.

**Alternatives considered**:
- Walking the tree for `project.yaml` / `package.json` name — forbidden.
- Inventing `pytest` / `npm test` when validation is missing — FR-011 / FR-014.
- Requiring `.ainative/project.yaml` even when `manifest` is named — contradicts US4 scenario 2.

## 9. Conflict rule and context overlay

**Decision**: When building `ProjectContext`:

| Field | Winner |
|---|---|
| `id`, `enabled` | Always operational (enabled is not on the context identity; it gated the load) |
| `repository` (enrollment) | Always operational; never retarget |
| `name`, `default_branch`, validation/development commands | Project-side when declared |
| Manifest `repository` | Recorded on the parsed manifest / context as the project’s declaration; does not change enrollment |
| `settings` | Operational, returned unchanged, not interpreted |

Default branch chain: project declaration → operational record → `"main"`.

**Rationale**: Spec assumptions on conflict; FR-007.

**Alternatives considered**: Operational always wins — would make the hybrid model a lie. Silently changing enrollment `repository` to the manifest URL — retargeting.

## 10. Conventional slots and tooling paths

**Decision**: Closed per-slot filenames, first existing file wins, omit the slot if none. No globs. Unreadable *optional* conventional files are omitted (they were not declared required). Unreadable *required* files (chosen manifest, listed AI context pointers) fail the load.

| Slot | Candidates |
|---|---|
| `overview` | `README.md`, `README` |
| `agent_instructions` | `AGENTS.md`, `CLAUDE.md` |
| `contributing` | `CONTRIBUTING.md` |
| `architecture` | `docs/architecture.md`, `ARCHITECTURE.md` |

AI context pointers: each path relative, in-root, required; text included in the bundle.

Tooling: at project root only, include every existing name from `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json` as a project-relative path string. No file text. No recursion. No lockfiles. Missing names omitted. Zero matches is success.

The bundle is in-memory only. The registry does not write copies under `personalAgent/` or into Hermes home.

**Rationale**: FR-009, FR-010, FR-016, clarifications on bundle shape.

**Alternatives considered**:
- Concatenating all Markdown into one prompt blob — later executor concern; this phase returns structured slots.
- Including `package-lock.json` / `uv.lock` — closed set excludes them.
- Persisting a cache of file text — second knowledge base (FR-016).

## 11. Errors

**Decision**: Distinct exception types, all subclasses of `ProjectRegistryError`:

| Type | When |
|---|---|
| `InvalidProjectConfigError` | Unreadable config, missing required operational fields, duplicate id/repository/location, path-like config id, non-scalar `settings` values |
| `UnknownProjectError` | Caller id not in the managed set, including path-like ids |
| `DisabledProjectError` | `resolve_eligible_project` / `load_project_context` on `enabled: false` |
| `InvalidProjectLocationError` | Location missing, empty, not a directory, or unreadable at eligibility/context |
| `MissingProjectConfigurationError` | Chosen structured source absent or missing required fields / validation commands |
| `MalformedManifestError` | Chosen source exists but cannot be parsed as the supported subset |
| `UnsafePathError` | Named manifest or AI context pointer escapes the project root |

**Rationale**: Spec wants visible, distinct failures. Tests assert types.

**Alternatives considered**: Returning `None` / empty records — forbidden. Collapsing all into `ProjectRegistryError` — weaker SC-002.

## 12. Checks and fixture

**Decision**: One pytest file covering the six SC-006 contract behaviors plus named-manifest, conflict (branch `main` vs `master`), path-like ids, duplicate config, missing location, empty managed set, unlisted disk repo, tooling-paths-not-text, and pointer escape. Committed fixture: `tests/fixtures/projects/standard/` with `README.md`, `AGENTS.md`, `pyproject.toml`, and `.ainative/project.yaml` (required structured fields + a validation command). Other layouts are built in `tmp_path` so tests do not depend on a live production checkout.

Production `config/default.yaml` stays `projects: []` until the owner names a non-critical real project.

**Rationale**: Constitution IV; spec SC-006; V0 target is a disposable fixture.

**Alternatives considered**: Only live-checkout tests — flaky, production-safety risk. A second test framework — forbidden.

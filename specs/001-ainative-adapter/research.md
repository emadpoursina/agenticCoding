# Research: AiNative Adapter

**Feature**: `001-ainative-adapter` | **Date**: 2026-08-28

Phase 0 resolves every Technical Context choice against the spec, constitution, discovery report, and the live `personalAgent` + AiNative trees. No `[NEEDS CLARIFICATION]` remains.

## 1. Where the adapter lives

**Decision**: One module in the existing control-plane package: `personalAgent/src/hermes_kanban/ainative.py`. Re-export the public types from `hermes_kanban/__init__.py`. Checks in `personalAgent/tests/test_ainative_adapter.py` plus a fixture tree under `personalAgent/tests/fixtures/ainative/`.

**Rationale**: `src/hermes_kanban/` is already the control-plane package (scaffold only: `__version__`). Constitution III forbids a second control plane and forbids duplicating AiNative. The V0 plan’s `hermes/adapters/ainative/` tree is conceptual; AGENTS.md already names `src/hermes_kanban/`. One module until the file is no longer readable — do not pre-split into types/config/git files.

**Alternatives considered**:
- New top-level package `ainative_adapter/` — extra install surface, unused.
- `hermes_kanban/adapters/ainative/` package with several modules — premature layout; this phase is list/load/resolve/revision/context.
- Copying agent Markdown into `personalAgent/` — forbidden by FR-011 and constitution III.

## 2. Language, tooling, dependencies

**Decision**: Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff already in `[project.optional-dependencies] dev`. **No new runtime dependencies.**

**Rationale**: Constitution hard constraints and `pyproject.toml` already pin this. Spec assumption: configuration parsing and revision capture use platform capabilities.

**Alternatives considered**:
- PyYAML / GitPython / pydantic — owner did not approve new deps; stdlib + `git` CLI cover the need.
- Adding the adapter to the Hermes image instead of this package — would fork Hermes (forbidden).

## 3. Operational configuration

**Decision**: Load only `ainative.path` and `ainative.read_only` from the existing YAML at a **caller-supplied** config path (production: `personalAgent/config/default.yaml`, whose path is `/ainative` and `read_only: true`). Other keys are ignored. Missing keys, missing file, or `read_only` that is not true fail at construction. Do not read `AINATIVE_PATH` as a silent fallback when YAML is invalid. Do not default the path to a host checkout.

Parse those two keys with a line-oriented scan of the `ainative:` block (stdlib). Do not parse the rest of the file.

**Rationale**: FR-001–FR-003. `config/default.yaml` already has the keys. Docker Compose already mounts `${AINATIVE_PATH}:/ainative:ro`; the *application* must see the container path from config, not `os.environ` guessed from the developer laptop. Host `AINATIVE_PATH` in `.env` is Compose-only (documented in `.env.example`).

`ponytail:` the scanner understands a YAML mapping of two scalar keys (`path`, `read_only: true|false`). It will not parse nested YAML, quotes, or aliases. Upgrade path: ask the owner for PyYAML if the `ainative:` block grows.

**Alternatives considered**:
- PyYAML — new dependency.
- JSON-only config — would replace the already-written operational YAML.
- Env-only (`AINATIVE_PATH`) — skips `read_only` and makes host pytest accidentally bind to the live mount.
- Defaulting missing path to `../AiNative` — silent substitute; FR-002 / SC-005 forbid it.

## 4. Agent roster and name identity

**Decision**: Agents are immediate subdirectories of `{methodology}/docs/8-agents/`. Skip `template` and `_skills` (and non-directories). `list_agents()` returns those folder names, sorted, for determinism. `get_agent` / `resolve_agent_dependencies` accept a name only if it is **exactly** in that list (single path segment, no `/`, `\`, or `..`). Unknown, reserved, and path-like names share `UnknownAgentError`. Never `join` a caller-supplied name onto the agents root before the allowlist check.

File contract (already in AiNative `docs/8-agents/README.md`): `AGENTS.md` (purpose), `SKILL.md` (how-to), `rule.md` (constraints). Each becomes an optional path **and** a raw-text field (`purpose` / `howto` / `constraints`) when the file exists; omit both when it does not. No concatenated blob. If a listed folder has none of the three files, `get_agent` fails (`IncompleteAgentError`). An existing file that cannot be read is a failure, not an omit (omit would claim the file is absent).

**Rationale**: FR-004–FR-006 and clarifications (exact names; reserved folders). Live tree currently has critic, plan-reviewer, pr-reviewer, prd-writer, project-bootstrapper, scout, task-groomer, tester — plus reserved `template` and `_skills`. Discovery once listed `specs-planner`; it is not in the current tree. Tests MUST use a fixture, not the live mount’s roster.

**Alternatives considered**:
- Hardcoding scout/tester/critic — roster is discovered (spec assumption).
- Treating `template` as an agent — forbidden.
- Path-join then resolve — path traversal.

## 5. Skill / rule dependency resolution

**Decision**: Parse the how-to document for HTML comments of the form `<!-- source: _skills/<name>/SKILL.md -->` (AiNative’s documented copy-inline convention). Each distinct `<name>` loads `{agents_root}/_skills/<name>/SKILL.md`. If that file is missing or unreadable, `resolve_agent_dependencies` fails (`UnresolvedDependencyError`) and returns nothing. Deduplicate by skill name, first-seen order. Include the agent’s own `rule.md` as `{kind: "rule", name: <agent>, path, text}` when that file exists. Skill items: `{kind: "skill", name: <folder>, path, text}`.

**Rationale**: FR-007 and the live `SKILL.md` files (scout → research-first, tester → test-execution, critic → verification, etc.). The adapter does not execute skills; it attaches raw text. The skill library is never an agent.

**Alternatives considered**:
- Returning only inline SKILL.md (already copied into the agent) — would skip the library snapshot the spec asks to attach, and would not fail when the source file is gone.
- YAML frontmatter `skills:` list — not how current agents declare sources.
- Skipping missing skills — forbidden by clarification.

## 6. Revision capture

**Decision**: Call the `git` CLI via `subprocess` (no GitPython). `capture_revision(path)`:

| Field | Source |
|---|---|
| `sha` | `git -C path rev-parse HEAD` (must be non-empty) |
| `branch` | `git -C path rev-parse --abbrev-ref HEAD`; if the result is `HEAD`, store `"detached"` (not a fake branch) |
| `repository` | `git -C path remote get-url origin`; if that fails, the configured/requested `path` as a string |
| `dirty` | `True` iff `git -C path status --porcelain` is non-empty (untracked counts) |

Not a work tree → `RevisionError`. Dirty tree still succeeds; `sha` stays HEAD; documents continue to be read from the working tree. `git` must be on `PATH` (true in this Docker image and on the host used for pytest).

**Rationale**: FR-008, US2, constitution III (platform-native). Spec forbids inventing a SHA when there is no repo.

**Alternatives considered**:
- GitPython — new dependency.
- Reading `.git/HEAD` by hand — reimplements porcelain; breaks worktrees/submodules.
- Failing when dirty — contradicts the 2026-08-28 clarification.
- Using `git describe` — empty on shallow/un-tagged clones.

## 7. Execution context

**Decision**: `build_execution_context(agent, *, workflow_phase=None)` returns a dataclass with `methodology_path`, `revision` (of the configured methodology path), `agent` (the given `AgentDefinition`), and `workflow_phase` if supplied. Do not add `task` / `project` / `workspace` fields populated with invented values; omit them from the type (or keep them as `None` only if a later phase needs a stable slot — this phase omits them so callers cannot confuse empty with loaded).

**Rationale**: FR-009. Later executor phases will extend the type; this phase must not pretend those slots exist.

**Alternatives considered**:
- Always including empty task/project/workspace dicts — spec allows absence; empty dicts look like loaded data.
- Snapshotting files into the context — would copy methodology (FR-011).

## 8. Read-only enforcement

**Decision**: Construction requires `read_only is True` and a real directory containing `docs/8-agents/`. Public mutating methods `write_file(relative_path, content)` and `copy_tree(destination)` always raise `ReadOnlyError` **before** any filesystem write, copy, or mkdir. No other adapter method creates, modifies, or deletes under the methodology path. Reads use `Path.read_text` only.

**Rationale**: FR-010–FR-011, US3, SC-004. The contract check needs a callable write attempt; adding silent no-op writes would swallow failure.

**Alternatives considered**:
- chmod the mount from Python — Docker already mounts `:ro`; the adapter must still refuse even if the host files are writable.
- Omitting write methods and only documenting “don’t write” — SC-006 requires a refused-write check that can fail if behavior breaks.

## 9. Errors

**Decision**: Distinct exception types, all subclasses of `AiNativeAdapterError`:

| Type | When |
|---|---|
| `InvalidMethodologyError` | Missing/empty/non-dir path, missing `docs/8-agents/`, `read_only` not true, unreadable config |
| `UnknownAgentError` | Name not in `list_agents()`, including reserved and path-like names |
| `IncompleteAgentError` | Listed folder with none of the three instruction files |
| `UnresolvedDependencyError` | Referenced shared skill missing or unreadable |
| `RevisionError` | Path is not a git work tree or SHA cannot be read |
| `ReadOnlyError` | Any write/copy/delete through the adapter |

**Rationale**: Spec wants visible, distinct failures (not empty definitions, not generic crashes). Tests assert types.

**Alternatives considered**: One exception with a code enum — slightly less code, worse call-site checks. Returning `None` / `[]` — forbidden.

## 10. Checks

**Decision**: One pytest file covering the five SC-006 contract behaviors plus the identity, dirty-revision, missing-skill, and incomplete-agent edges. Fixture methodology tree (git-initialized in tmp) so CI does not need the live mount. Optional live-mount test marked skip if `/ainative` or `AINATIVE_PATH` is absent; if present, assert only that listed names are a subset of real folders (do not assert `specs-planner`).

**Rationale**: Constitution IV (one runnable check set; integration-style when contracts/schemas change). Spec: fixture preferred.

**Alternatives considered**: Only live-mount tests — flaky, depends on AiNative checkout. A second test framework — forbidden.

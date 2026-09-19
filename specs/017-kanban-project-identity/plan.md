# Implementation Plan: Kanban Project Identity Mapping

**Branch**: `017-kanban-project-identity` | **Date**: 2026-09-17 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/017-kanban-project-identity/spec.md`

## Summary

Add an optional `kanban_project_ids` alias list to each enrolled project in
the operational config, validate it at registry construction, and expose a
`ProjectRegistry.canonical_id()` resolver. Construct the live
`SqliteTaskBoard` with that resolver so a card's native `p_…` project id is
translated to the operational id before it reaches the orchestrator. Every
downstream artifact (overlay, workspace path, correlation identity, publish
identity, status) therefore keeps using the operational id. Resume input and
legacy overlay records are canonicalized as well. Unmapped ids stay
fail-closed, but `--next-ready` now names them, and `--doctor` prints each
project's declared aliases.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via the existing `uv`
package in `personalAgent/`; Markdown and the existing subset YAML config.

**Primary Dependencies**: Existing stdlib-only Hermes package
(`dataclasses`, `re`, `pathlib`, `sqlite3`, `typing.Protocol`), the
`_parse_document` YAML subset, `ProjectRegistry`, `WorkspaceManager`,
`SqliteTaskBoard`, `PivOrchestrator`, and the current pytest / ruff
toolchain. No new dependency.

**Storage**: The existing native `kanban.db` is read-only; the existing
overlay JSON is unchanged in shape. No new database, table, or migration is
introduced. The alias declaration lives in `config/default.yaml`.

**Testing**: Focused additions to `tests/test_project_registry.py` and a new
`tests/test_kanban_project_identity.py` with a real temporary `kanban.db`;
existing orchestrator, live-bridge, recovery, and workspace suites;
`uv run pytest` and `uv run ruff check src tests`.

**Target Platform**: Linux Hermes container for live behavior, with
macOS/Linux temporary-path fixtures. No runtime read of `projects.db`.

**Project Type**: In-process Python control plane and CLI with filesystem
configuration and a read-only native board.

**Performance Goals**: Resolve one id per card with a dict lookup; no extra
file reads, polling, or schema access.

**Constraints**: Exact-match only; no fuzzy or display-name matching;
fail closed on unmapped ids; never write the native board; keep
`surgical edits`; no new dependency; do not change protected-branch,
merge, or deploy limits.

**Scale/Scope**: One live board, a handful of enrolled projects, one alias
list per project, the existing single execution slot, and one focused
fixture suite.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research: PASS

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | Spec written and clarified before implementation. |
| II. Least Code (Ponytail) | PASS | One new field, one resolver, one board parameter; reuses the existing registry, board, orchestrator, and parser. |
| III. Platform-native | PASS | Reads the native board as-is; declares the mapping in our own config; no second store; no `projects.db` coupling. |
| IV. Trust-boundary tests | PASS | Alias validation, canonical resolution, board translation, and unmapped-id reporting receive focused checks. |
| V. Human authority | PASS | No native state write or merge/deploy change; aliases are declared by the operator. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Python standard library and current pytest/ruff cover the feature. |
| Secrets and isolated home | PASS | Alias ids are non-secret metadata; diagnostics unchanged in shape. |
| Surgical edits | PASS | Changes are limited to `projects.py`, `board.py`, `runtime.py`, `orchestrator.py`, config, tests, and docs. |

### Post-design: PASS

The design canonicalizes at a single boundary (the native-store adapter),
keeps `ProjectRecord.id` as the only downstream key, and adds no new state
or dependency. Unmapped ids remain fail-closed with a clearer report. No
constitution violation remains.

## Project Structure

### Documentation (this feature)

```text
specs/017-kanban-project-identity/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── project-identity.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source and tests

```text
personalAgent/
├── src/hermes_kanban/
│   ├── projects.py       # alias field, validation, canonical_id, alias-aware get_project
│   ├── board.py          # optional resolver; canonicalize project_id in _task
│   ├── runtime.py        # build registry, pass resolver, extend --doctor output
│   └── orchestrator.py   # canonicalize resume input + legacy record; enriched no-ready error
├── tests/
│   ├── test_project_registry.py        # alias parsing/validation/resolution
│   └── test_kanban_project_identity.py # real-kanban.db end-to-end identity checks
├── config/default.yaml   # declare kanban_project_ids for ich-mag-dich
├── README.md             # document the field and the one-time discovery command
└── CHANGELOG.md          # Fixed entry + version bump
```

`executor.py`, `persist.py`, `workspace.py`, `github.py`, `messaging.py`,
and the harness records are behaviorally unchanged; they only benefit from
receiving the canonical id. `workspace.py` already keys paths and
`CorrelationIdentity` off `project.id`, so no edit is required there.

**Structure Decision**: Keep the flat package and existing fixture style.
Put alias declaration in the config, resolution in `ProjectRegistry`, and
translation at the single native-store adapter (`SqliteTaskBoard`), which is
the only place that reads native ids.

## Implementation Design

### 1. Declare and validate aliases (`projects.py`)

- Add `kanban_project_ids: tuple[str, ...] = ()` as the last field of
  `ProjectRecord` so existing keyword construction and equality stay valid.
- Parse `kanban_project_ids` in `load_project_entries`; accept a scalar or a
  list, normalize to a tuple, and reject empty/non-string entries and
  path-like ids using the existing `_path_like_id`.
- In `_validate_records`, add a second pass: every alias must be unique
  across all aliases and must not equal any project's operational `id`.
- Add `canonical_id(value) -> str`: return the value when it is an
  operational id, translate a declared alias, otherwise raise
  `UnknownProjectError`. Build `_by_kanban_id` in `__init__`.
- Route `get_project` through `canonical_id` so `resolve_eligible_project`
  and `load_project_context` accept either form.

### 2. Canonicalize at the native-store boundary (`board.py`)

- Add `SqliteTaskBoard(db_path, *, resolve_project_id: Callable[[str], str] | None = None)`.
- In `_task`, when a resolver is present and the raw `project_id` is a
  non-empty string, replace it with `resolver(raw)`. The resolver wrapper
  returns the raw value on `UnknownProjectError`, preserving the existing
  skip-vs-raise semantics exactly.
- Leave `_REQUIRED_COLUMNS`, dependency parsing, and read-only connection
  behavior untouched.

### 3. Wire the resolver and doctor output (`runtime.py`)

- In `build_live_orchestrator`, build `ProjectRegistry.from_config(config_path)`
  and pass a wrapped `registry.canonical_id` to `SqliteTaskBoard` on both the
  `HERMES_KANBAN_DB` and `HERMES_HOME` paths.
- Extend `build_startup_diagnostic` and `StartupDiagnostic` to carry each
  project's declared aliases (metadata only), and render them in the
  `--doctor` output. Keep it secret-safe and body-free.

### 4. Canonicalize resume/legacy and improve the no-ready report (`orchestrator.py`)

- In `resume_workflow`, canonicalize the incoming `project_id` via the
  registry before comparing to `record.project_id`.
- In `_board_record`/`become_ready`, canonicalize a legacy
  `record.project_id` before the task-project mismatch check and reclaim
  path math.
- In `run_next_workflow`, track skipped-unmapped card ids; when no task is
  ready and at least one card was skipped for an unknown project id, raise
  `NoReadyTaskError` naming those ids. Also expose a small helper to render
  safe unmapped metadata. Keep the single error type so `runtime.main`
  behavior is unchanged.

### 5. Config, docs, and delivery

- Add `kanban_project_ids: [p_f1577341]` to the `ich-mag-dich` entry in
  `config/default.yaml`.
- Document the field, the one-time discovery command
  (`sqlite3 projects.db "select id, slug from projects;"`), and the
  container-recreate step in `README.md`.
- Add a `Fixed` entry and version bump in `CHANGELOG.md`.

### 6. Verify

- Add registry unit checks and the new real-board identity suite.
- Run `uv run pytest` and `uv run ruff check src tests`.
- Record the operator runbook (read native id → declare → recreate →
  `--doctor` → `--next-ready`) in `quickstart.md`.

## Dependency and Execution Order

| ID | Work package | Depends on | Parallel |
|---|---|---|---|
| A | Alias field, validation, `canonical_id` in `projects.py` | None | Blocks B/C |
| B | Board resolver wiring in `board.py` | A | B with C |
| C | Runtime resolver + doctor output in `runtime.py` | A | C with B |
| D | Orchestrator resume/legacy/no-ready changes | A | After A |
| E | Tests for registry and board identity | A–D | After interfaces settle |
| F | Config, README, CHANGELOG; run pytest + ruff | E | Final serialized gate |

## Phase 1 Acceptance and Verification

- A card carrying a declared alias selects and runs the enrolled project.
- The worktree, overlay record, correlation identity, and publish identity
  use the operational id.
- Alias collisions, path-like aliases, and duplicate aliases fail at
  construction.
- An unmapped id fails closed and is named in the `--next-ready` error.
- `--resume` and restart recovery work with either id form, including a
  legacy overlay.
- `--doctor` lists declared aliases without secrets or bodies.
- `uv run pytest` and `uv run ruff check src tests` pass.

## Complexity Tracking

No constitution violations require justification.

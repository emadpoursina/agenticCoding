---

description: "Task list for Project Registry implementation"
---

# Tasks: Project Registry

**Input**: Design documents from `/specs/002-project-registry/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Requested by spec SC-006, constitution IV, and [quickstart.md](./quickstart.md). One contract module only: `personalAgent/tests/test_project_registry.py`. Extra layouts are built in pytest `tmp_path`. Tests MUST NOT bind to a live production checkout.

**Organization**: Tasks are grouped by user story. US3 (eligibility) is sequenced before US2 (context load) because `load_project_context` MUST call `resolve_eligible_project` first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Implementation lands in the existing `personalAgent/` package (not playground root, not AiNative). Public API lives in one module until that file is unreadable — do not pre-split into `registry/` or types/config/loader packages. Do not add dependencies. Do not edit `personalAgent/src/hermes_kanban/ainative.py` or `personalAgent/docker-compose.yml`.

```text
personalAgent/src/hermes_kanban/projects.py
personalAgent/src/hermes_kanban/__init__.py
personalAgent/tests/test_project_registry.py
personalAgent/tests/fixtures/projects/standard/
personalAgent/config/default.yaml
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Enroll an empty managed set in operational config and commit the disposable fixture the contract tests will copy into `tmp_path`

- [X] T001 Add an explicit empty managed set `projects: []` to `personalAgent/config/default.yaml`. Do not hardcode a host path, `$HOME`, or a real repository. Other existing keys stay as they are.
- [X] T002 [P] Create overview slot `personalAgent/tests/fixtures/projects/standard/README.md` with a short fixture description (not a copy of a real app repo).
- [X] T003 [P] Create agent/AI slot `personalAgent/tests/fixtures/projects/standard/AGENTS.md` with a short fixture instruction paragraph.
- [X] T004 [P] Create standard manifest `personalAgent/tests/fixtures/projects/standard/.ainative/project.yaml` with required fields `name`, `repository`, `default_branch`, and a non-empty `validation.commands` list (e.g. `uv run pytest`). Optional `description` / `workflow.default` / `development.commands` allowed. Parser subset only: 2-space indent, unquoted scalars, no aliases or multiline `|`.
- [X] T005 [P] Create closed-set tooling file `personalAgent/tests/fixtures/projects/standard/pyproject.toml` (minimal valid TOML is enough; tests assert the path, not the file text).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types, subset YAML, and construction-time validation of the managed set. No user story work until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Add `ProjectRegistryError` and distinct subclasses `InvalidProjectConfigError`, `UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`, `MissingProjectConfigurationError`, `MalformedManifestError`, `UnsafePathError` in `personalAgent/src/hermes_kanban/projects.py`.
- [X] T007 Add frozen dataclasses `ProjectRecord`, `ProjectManifest`, `ProjectContext`, and `ContextFile` in `personalAgent/src/hermes_kanban/projects.py` matching [data-model.md](./data-model.md): `ProjectRecord` has `id`, `name`, `repository`, `location` (`Path`), `default_branch` (`str`, operational fallback `"main"` for listing), `enabled` (`bool`, missing config → `True`), `settings` (`dict[str, str]`, missing → `{}`), `manifest` (`str | None`). `ProjectContext` includes `declared_repository`, conventional text slots (`overview`, `agent_instructions`, `contributing`, `architecture`), `ai_context_files`, `tooling_paths`. Type-annotate public APIs.
- [X] T008 Implement a line-oriented indent YAML subset parser in `personalAgent/src/hermes_kanban/projects.py` covering (1) a `projects:` sequence of mappings with optional nested `settings:` scalar map and (2) a manifest mapping with optional `workflow.default`, `validation.commands` / `development.commands`, `ai.context`. Support comments, 2-space indent, unquoted scalars, `true`/`false`, `[]` / `{}`. Ignore keys other than `projects:` when scanning operational config. Mark with `ponytail:` this is not YAML; upgrade is owner-approved PyYAML. Do not refactor `load_ainative_settings`.
- [X] T009 Implement `load_project_entries(config_path: Path) -> list[ProjectRecord]` and `ProjectRegistry.__init__` / `ProjectRegistry.from_config` in `personalAgent/src/hermes_kanban/projects.py`. Trust boundary: raise `InvalidProjectConfigError` for missing/unreadable config, empty/missing `id`/`name`/`repository`/`location`, duplicate `id`/`repository`/trailing-slash-normalized `location`, path-like config `id` (`/`, `\`, `..`, extra segments), named `manifest` that is absolute/empty/would escape `.`, or non-scalar `settings` values. Missing `projects:` → empty list (valid). MUST NOT `stat` locations. MUST NOT substitute a disk repository.
- [X] T010 Re-export `ProjectRegistry`, `load_project_entries`, record/context/manifest types, and the error classes from `personalAgent/src/hermes_kanban/__init__.py`. Keep every existing adapter export.

**Checkpoint**: Foundation ready — `from_config` can load an empty or valid managed set; user story implementation can begin

---

## Phase 3: User Story 1 - Resolve a managed project by identity (Priority: P1) 🎯 MVP

**Goal**: Callers can list the explicit managed set and fetch an operational record by exact ID without reading the project tree or copying project knowledge.

**Independent Test**: Point the registry at a temp config that lists the standard fixture (and optionally a second disabled project). `list_projects()` returns identities and enabled flags. `get_project(id)` returns the operational record. Unknown / path-like / `../` ids raise `UnknownProjectError`. Records do not include README/architecture/test text.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [US1] Add contract tests in `personalAgent/tests/test_project_registry.py` (helper: write a temp YAML `projects:` list pointing `location` at a copy of `tests/fixtures/projects/standard` under `tmp_path`): list one enabled fixture returns id/name/repository/location/default_branch/enabled/`settings` map; optional second disabled entry appears with `enabled is False`; `get_project` matches list; unknown, path-like, and `../` ids raise `UnknownProjectError` (not `None`, not an empty record); listed records have no knowledge-file fields. Tests MUST NOT use a hardcoded workstation path.

### Implementation for User Story 1

- [X] T012 [US1] Implement `ProjectRegistry.list_projects()` in `personalAgent/src/hermes_kanban/projects.py`: return every configured `ProjectRecord` in config-file order, including disabled; do not read any project source tree; empty list is valid.
- [X] T013 [US1] Implement `ProjectRegistry.get_project(project_id: str)` in `personalAgent/src/hermes_kanban/projects.py`: exact configured `id` only; unknown, path-like, and `../` identities raise `UnknownProjectError`; MUST NOT join the caller id onto a filesystem path; return the operational record only (no knowledge files). `settings` pass through unchanged and are not interpreted.

**Checkpoint**: User Story 1 is independently testable via list/get/unknown-id without calling `load_project_context`

---

## Phase 4: User Story 3 - Refuse ineligible projects and never silently pick a real repository (Priority: P1)

**Goal**: The managed set is explicit. Empty config, disabled projects, missing locations, and invalid config fail at the trust boundary with distinct errors. Unlisted directories are never enrolled.

**Independent Test**: Empty `projects:` lists nothing and does not invent a disk repo. Disabled fixture fails `resolve_eligible_project` / later context load with `DisabledProjectError`. Missing location fails with `InvalidProjectLocationError` and no substitute path. An unlisted real directory is never returned. Bad config entries fail construction.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US3] Extend `personalAgent/tests/test_project_registry.py`: empty `projects:` → empty list; an unlisted directory created next to the fixture is never listed or resolved; `enabled: false` → `resolve_eligible_project` raises `DisabledProjectError`; location missing / file-instead-of-directory / unreadable → `InvalidProjectLocationError` with no fallback directory; duplicate `id` or duplicate `repository`/`location` → `InvalidProjectConfigError`; omitted required operational field → `InvalidProjectConfigError`.

### Implementation for User Story 3

- [X] T015 [US3] Implement `ProjectRegistry.resolve_eligible_project(project_id: str)` in `personalAgent/src/hermes_kanban/projects.py`: same identity rules as `get_project` (`UnknownProjectError`); `enabled is False` → `DisabledProjectError`; location missing, empty, not a directory, or unreadable → `InvalidProjectLocationError` with no substitute path; success returns the operational record (still no knowledge files).

**Checkpoint**: Eligibility is a gate. User Stories 1 and 3 both work without loading context

---

## Phase 5: User Story 2 - Load project context from the project repository (Priority: P1)

**Goal**: For an eligible project, read project-side truth in place and return an in-memory bundle: operational identity, parsed manifest fields, conventional slot text, closed-set tooling paths. Do not invent commands. Do not persist a second knowledge base.

**Independent Test**: Resolve the fixture and `load_project_context`. Bundle has operational identity, `README.md`/`AGENTS.md` text when present, the fixture’s own validation commands, and `pyproject.toml` as a relative path (not file text). Hide/remove the structured source or strip validation commands → `MissingProjectConfigurationError`, no guessed `pytest`/`npm test`. Control plane still has no copied knowledge base outside the committed fixture and tests.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T016 [US2] Extend `personalAgent/tests/test_project_registry.py`: load of the standard fixture includes id, enrollment `repository`, name, default branch, README and AGENTS text, exact `validation.commands` from the fixture manifest, and `pyproject.toml` in `tooling_paths` (path string, not file contents); missing or hidden `.ainative/project.yaml` or empty `validation.commands` raises `MissingProjectConfigurationError` with no invented commands; after load, nothing under `personalAgent/` except the committed fixture and tests holds a copy of the project’s instructions/architecture/tests.

### Implementation for User Story 2

- [X] T017 [US2] Parse the chosen structured source (default `.ainative/project.yaml` when `manifest` is omitted) into `ProjectManifest` in `personalAgent/src/hermes_kanban/projects.py`. Required: `name`, `repository`, `default_branch`, non-empty `validation.commands`. Optional: `description`, `workflow.default`, `development.commands`, `ai.context`. Missing file / missing required fields / empty validation → `MissingProjectConfigurationError`. Unparseable subset YAML → `MalformedManifestError`. MUST NOT search the tree. MUST NOT invent commands.
- [X] T018 [US2] Implement conventional text-slot and tooling-path discovery in `personalAgent/src/hermes_kanban/projects.py`. Slots (first existing file wins; omit if none): overview `README.md` then `README`; agent/AI `AGENTS.md` then `CLAUDE.md`; contributing `CONTRIBUTING.md`; architecture `docs/architecture.md` then `ARCHITECTURE.md`. No globs, no other instruction filenames. Unreadable optional conventional files are omitted. Tooling at project root only, paths not text, include every existing name from `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`; omit missing; zero matches is success; no recursion; no lockfiles.
- [X] T019 [US2] Implement `ProjectRegistry.load_project_context(project_id: str)` in `personalAgent/src/hermes_kanban/projects.py`: call `resolve_eligible_project` first (same errors); overlay per [contracts/project-registry.md](./contracts/project-registry.md) (`id` and enrollment `repository` operational; `name` / `default_branch` / commands project-side; manifest `repository` → `declared_repository`; `settings` unchanged); return in-memory `ProjectContext` only — MUST NOT write the bundle to disk or into Hermes home.

**Checkpoint**: User Story 2 is independently testable on the fixture. Do not start workspaces or PIV.

---

## Phase 6: User Story 4 - Prefer existing project conventions; use a standard manifest only when needed (Priority: P2)

**Goal**: Named project-relative manifests are used when the operator sets `manifest`; default `.ainative/project.yaml` is not required then. Project-side name/branch/commands win. Malformed or escaping paths fail at the trust boundary.

**Independent Test**: Load a fixture with README + AGENTS + standard manifest. Load a fixture whose operational `manifest` names a non-standard relative file and confirm that file is used (default path not required). Operational `default_branch: main` + project `master` → context branch is `master`. Malformed manifest fails visibly.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [US4] Extend `personalAgent/tests/test_project_registry.py` with `tmp_path` layouts (not the committed standard tree): named `manifest` other than `.ainative/project.yaml` is used and the default file is not required; no fallback to `.ainative/project.yaml` when the named file is missing; operational `default_branch: main` + project `default_branch: master` → context `default_branch == "master"`; unparseable chosen source → `MalformedManifestError`; named manifest or `ai.context` pointer that escapes the project root → `UnsafePathError`; missing listed AI context pointer → `MissingProjectConfigurationError`.

### Implementation for User Story 4

- [X] T021 [US4] Implement named-manifest selection in `personalAgent/src/hermes_kanban/projects.py`: if `ProjectRecord.manifest` is set, that relative path is the only structured source (`Path.is_relative_to` project root); missing/non-file/unreadable named path → `MissingProjectConfigurationError` with no fallback; out-of-root → `UnsafePathError`. If omitted, `.ainative/project.yaml` only.
- [X] T022 [US4] Finish context overlay and AI context pointers in `personalAgent/src/hermes_kanban/projects.py`: project-side `name`, `default_branch`, validation/development commands win; default-branch chain is project → operational → `"main"`; each `ai.context` path is relative, in-root, required; load unmodified UTF-8 into `ContextFile`; missing/unreadable pointer → `MissingProjectConfigurationError`; out-of-root pointer → `UnsafePathError`. Enrollment `repository` is never retargeted.

**Checkpoint**: All four user stories are independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the contract, keep the existing adapter green, and refuse silent production targeting

- [X] T023 Keep existing checks green: `uv run pytest tests/test_import.py tests/test_ainative_adapter.py` from `personalAgent/` (do not rewrite `personalAgent/src/hermes_kanban/ainative.py`).
- [X] T024 Run the quickstart validation from `personalAgent/`: `uv run pytest tests/test_project_registry.py` and `uv run ruff check src tests`. Fix any contract or lint failure in `personalAgent/src/hermes_kanban/projects.py` / `personalAgent/tests/test_project_registry.py`.
- [X] T025 Confirm `personalAgent/config/default.yaml` still has `projects: []`, no host-specific path, no production repo enrolled; this diff does not read/write Hermes `projects.db` / `kanban.db` and adds no new dependency in `personalAgent/pyproject.toml`.
- [X] T026 [P] Stop after registry checks pass. Do not start workspaces, Git safety, PIV, GitHub, Telegram, or model calls. Do not change `personalAgent/docker-compose.yml`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP identity API
- **User Story 3 (Phase 4)**: Depends on Foundational — eligibility gate; sequenced before US2
- **User Story 2 (Phase 5)**: Depends on Foundational + US3 (`resolve_eligible_project`)
- **User Story 4 (Phase 6)**: Depends on User Story 2 (extends manifest selection and overlay)
- **Polish (Phase 7)**: Depends on the stories being delivered

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependency on US2/US3/US4
- **User Story 3 (P1)**: Can start after Foundational — uses `list_projects`/`get_project` for unlisted-repo checks but does not need context load
- **User Story 2 (P1)**: Depends on US3 eligibility; independently testable once `resolve_eligible_project` exists
- **User Story 4 (P2)**: Depends on US2 `load_project_context`; independently testable with extra `tmp_path` layouts

### Within Each User Story

- Tests MUST be written and FAIL before that story’s implementation
- Types/parser/construction before list/get
- List/get before eligibility
- Eligibility before context load
- Default-path load before named-manifest / overlay edge cases
- Story complete before moving to the next priority increment

### Parallel Opportunities

- T002, T003, T004, T005 (different fixture files) can run in parallel
- T010 waits on T006–T007 (same public types) but is a different file from the fixture tasks
- T012 and T013 share `personalAgent/src/hermes_kanban/projects.py` — sequential
- Test tasks T011, T014, T016, T020 share `personalAgent/tests/test_project_registry.py` — sequential
- T017–T019, T021–T022 share `projects.py` — sequential
- T026 is independent of T023–T025 once implementation is done
- US1 and US3 can proceed in parallel after Foundational only if staffed on different concerns; they still share `projects.py`, so a single implementer should run them sequentially

---

## Parallel Example: User Story 1

```bash
# Fixture files (Phase 1) — different paths:
Task: "Create overview slot personalAgent/tests/fixtures/projects/standard/README.md"
Task: "Create agent/AI slot personalAgent/tests/fixtures/projects/standard/AGENTS.md"
Task: "Create standard manifest personalAgent/tests/fixtures/projects/standard/.ainative/project.yaml"
Task: "Create tooling file personalAgent/tests/fixtures/projects/standard/pyproject.toml"

# US1 tests then implementation are sequential (same two files):
Task: "Contract tests in personalAgent/tests/test_project_registry.py"
Task: "Implement list_projects() in personalAgent/src/hermes_kanban/projects.py"
Task: "Implement get_project() in personalAgent/src/hermes_kanban/projects.py"
```

---

## Parallel Example: User Story 3

```bash
# After Foundational + US1 list/get:
Task: "Refusal contract tests in personalAgent/tests/test_project_registry.py"
Task: "Implement resolve_eligible_project() in personalAgent/src/hermes_kanban/projects.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (empty `projects: []` + committed fixture)
2. Complete Phase 2: Foundational (types, parser, `from_config`)
3. Complete Phase 3: User Story 1 (`list_projects` / `get_project`)
4. **STOP and VALIDATE**: list known fixture, reject unknown id, no knowledge copy
5. Demo identity resolution; do not enroll a production repo

### Incremental Delivery

1. Setup + Foundational → construction validates the managed set
2. Add US1 → list/get independently → MVP
3. Add US3 → eligibility independently → no silent production target
4. Add US2 → fixture context load with the project’s own validation commands
5. Add US4 → named manifest + project-side overlay
6. Each story adds value without starting workspaces, PIV, GitHub, or Telegram

### Parallel Team Strategy

This feature is one module plus one test file. Prefer a single implementer moving story-by-story. If two people: one owns fixture + tests, the other owns `projects.py`, integrating at each checkpoint. Do not split `projects.py` into extra packages to create false parallelism.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec user stories US1–US4
- Public names are `list_projects`, `get_project`, `resolve_eligible_project`, `load_project_context`
- Closed tooling set and conventional slots are in FR-010 / research §10 — do not invent extra filenames
- Production `projects: []` until the owner names a non-critical repo
- Commit after each task or logical group if the owner asks; Conventional Commits (`feat:`, `test:`)
- Stop at any checkpoint to validate the story independently
- Avoid: second SQLite store, wrapping `discovered_repos`, PyYAML, hardcoded host paths, rewriting the AiNative adapter

---

## Phase 8: Convergence

- [X] T027 Add a contract assertion in `personalAgent/tests/test_project_registry.py` that after `load_project_context` nothing under `personalAgent/` except the committed fixture and tests holds a copy of the project's instructions, architecture, or tests per SC-005 / FR-016 (partial)
- [X] T028 Continue to the next conventional-slot candidate in `_optional_slot` in `personalAgent/src/hermes_kanban/projects.py` when a candidate path exists but is not a file (or cannot be stat'd) instead of omitting the whole slot per FR-010 (partial)

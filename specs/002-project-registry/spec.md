# Feature Specification: Project Registry

**Feature Branch**: `002-project-registry`

**Created**: 2026-08-29

**Status**: Draft

**Input**: User description: "specify project registry section based on scratch/implimentation.md (hybrid registry: operational metadata in the control plane, project-specific truth in each project repository, plus project manifest and project context loading)"

## Clarifications

### Session 2026-08-29

- Q: When a project already has structured metadata somewhere other than `.ainative/project.yaml`, how should the registry decide which file supplies name, default branch, and validation commands? → A: Operator names a project-relative manifest path on the operational record; if omitted, use `.ainative/project.yaml` only. Do not search the tree.
- Q: When project context is loaded successfully, what should the returned bundle include for files discovered in the project? → A: Structured manifest fields + text of instruction/docs files and listed AI context files; test/build/package configs as relative paths only.
- Q: Which files in a project count as the conventional overview, agent/AI instructions, contributing, and architecture slots that the loader reads as text? → A: Closed per-slot filenames: overview `README.md` then `README`; agent/AI `AGENTS.md` then `CLAUDE.md`; contributing `CONTRIBUTING.md`; architecture `docs/architecture.md` then `ARCHITECTURE.md`; plus AI context pointer files. First existing file wins; omit the slot if none.
- Q: What belongs in the operational record’s “operational settings” field in this phase? → A: Opaque key-value map from configuration; returned unchanged; no required keys; this phase does not interpret them. Missing means an empty map.
- Q: Which test, build, and package files appear in the context bundle as paths? → A: Closed project-root set only: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`. Include every name that exists; no recursion; omit missing names; do not fail if none exist.

## User Scenarios & Testing *(mandatory)*

Hermes is the operational control plane for software work. Each managed software project is a separate repository with its own architecture, instructions, conventions, tests, and project-specific AI knowledge. The control plane must know *which* projects it may work on and *how to find them*, without becoming the owner of those projects’ knowledge.

This feature is the hybrid project registry: the control plane stores operational project metadata (identity, repository, local location, default branch, enabled/disabled, operational settings). Each project repository remains the source of truth for what the project is. Before any later execution phase may act on a project, this feature must load that project’s instructions and conventions from the project itself.

The people who benefit are operators of the control plane and later workflow phases that will ask “which project is this, and what must a worker know before touching it?” This phase does not create workspaces, run agents, call models, or talk to Git hosting or messaging.

### User Story 1 - Resolve a managed project by identity (Priority: P1)

An operator (or a later worker) asks: “which projects are we allowed to work on, and what is project X?” The registry returns the managed set from operational configuration and, for a known identity, the operational record: project ID, name, repository, local/workspace location, default branch, enabled/disabled, and operational settings (an opaque key-value map from configuration, empty if omitted). Locations come from configuration — never from a hardcoded workstation path. The registry does not copy architecture, instructions, or tests into the control plane.

**Why this priority**: Later phases cannot claim a task, create a workspace, or load context without a stable project identity. This is the operational half of the hybrid model.

**Independent Test**: Point the registry at operational configuration that lists a small fixture project (and optionally a second disabled one). List projects and confirm identities and enabled flags. Resolve the fixture by ID and confirm the operational fields. Ask for an unknown identity and confirm a clear failure. Confirm no project documentation was copied into the control plane.

**Acceptance Scenarios**:

1. **Given** operational configuration that lists one enabled fixture project with identity, name, repository, local location, and default branch, **When** the caller lists projects, **Then** the result includes that project with those operational fields and an enabled flag of true.
2. **Given** the same configuration, **When** the caller resolves that project by ID, **Then** the result is the same operational record (ID, name, repository, local/workspace location, default branch, enabled, operational settings map) and does not include the project’s architecture, instructions, tests, or other knowledge files.
3. **Given** a valid configuration, **When** the caller resolves a project ID that is not in the managed set, **Then** the registry fails with a distinct, visible error (not an empty record and not a guessed project).
4. **Given** a valid configuration, **When** the caller lists or resolves projects, **Then** every location and repository value comes from configuration or from the project itself; none is a hardcoded workstation path.
5. **Given** two projects in configuration, one enabled and one disabled, **When** the caller lists projects, **Then** both appear, each with its enabled/disabled flag, and knowledge files from either repository are not copied into the control plane.

---

### User Story 2 - Load project context from the project repository (Priority: P1)

Before any execution agent may operate on a project, the control plane must discover that project’s instructions and conventions. The caller asks for project context for a resolved, enabled project. The registry inspects the project at its configured location and returns an in-memory context bundle for that caller: operational identity, parsed structured fields from the chosen manifest, the text of conventional slots that exist and of files listed as AI context pointers, and project-relative paths for closed-set tooling files at the project root. Project-specific truth is read in place from the project repository. The bundle is not persisted as a second knowledge base in the control plane.

**Why this priority**: The hybrid model fails if workers operate from a stale copy of project knowledge, or if they start work without discovering how this project is supposed to be built and checked.

**Independent Test**: Resolve the fixture project and load context. Confirm the bundle includes operational identity, the text of `README.md` and `AGENTS.md` when those files exist, structured validation/development commands when declared, and relative paths (not file text) for any closed-set tooling files present at the project root (for example `pyproject.toml`). Remove or hide the structured manifest and confirm the load fails clearly rather than inventing generic commands. Confirm the control plane still does not persist a copy of those files.

**Acceptance Scenarios**:

1. **Given** an enabled project whose repository contains `README.md`, `AGENTS.md`, and a structured operational manifest with validation commands, **When** the caller loads project context, **Then** the result includes operational identity (ID, name, repository, default branch), the text of those files, and the project’s own validation commands.
2. **Given** an enabled project, **When** the caller loads project context, **Then** the bundle includes the text of whichever conventional slots exist (overview, agent/AI instructions, contributing, architecture — first matching filename per slot) and of files listed as AI context pointers; tooling files from the closed project-root set that exist appear as project-relative paths only, not as file text. Absent optional slots and absent tooling names are omitted.
3. **Given** an enabled project that declares its own validation or development commands, **When** the caller loads project context, **Then** those commands are the ones returned. The loader MUST NOT invent generic test or build commands in their place.
4. **Given** an enabled project, **When** context is loaded, **Then** project knowledge is read from the project location; the returned bundle is in-memory for the caller and the control plane does not retain a duplicated knowledge base of that project.
5. **Given** an enabled project whose chosen structured source is missing or does not supply validation commands, **When** the caller loads project context, **Then** the load fails with a visible “missing project configuration” error rather than returning guessed commands.

---

### User Story 3 - Refuse ineligible projects and never silently pick a real repository (Priority: P1)

The managed set is explicit. The registry must not adopt a repository merely because it exists on disk. Disabled projects, missing locations, and invalid configuration fail at the trust boundary. The V0 target remains a disposable fixture until the owner names a non-critical real project. The system must not silently choose a production repository.

**Why this priority**: Silently working on the wrong repository, or on a disabled one, is a data-loss and production-safety failure. The constitution forbids silently picking a real production repository.

**Independent Test**: Construct the registry with empty configuration and confirm it does not invent a project. Disable the fixture and confirm context load and “eligible for work” resolution fail. Point a registered project at a missing location and confirm failure. Confirm a real repository that is not listed is never returned as managed.

**Acceptance Scenarios**:

1. **Given** operational configuration with an empty managed-project list, **When** the caller lists projects or asks for an eligible project, **Then** the result is empty and the registry does not substitute a repository found on disk.
2. **Given** a registered project whose enabled flag is false, **When** the caller asks to resolve it as eligible for work or to load project context for execution, **Then** the call fails with a distinct disabled-project error and no context bundle is returned.
3. **Given** a registered enabled project whose configured local location is missing, empty, not a directory, or unreadable, **When** the caller loads project context, **Then** the call fails at that boundary with a visible error and does not fall back to another directory.
4. **Given** a real software repository on disk that is not listed in the managed set, **When** the caller lists or resolves projects, **Then** that repository does not appear and is not used as the V0 target.
5. **Given** configuration that omits required operational fields (identity, repository, or local location) for an entry, **When** the registry is constructed or first asked to use that entry, **Then** it fails at the trust boundary for that entry (it does not skip silently or invent the missing fields).

---

### User Story 4 - Prefer existing project conventions; use a standard manifest only when needed (Priority: P2)

Projects already have conventions (project overview, agent/AI instruction files, contributing notes, test and build configuration). The registry must reuse those. A minimal standard operational manifest (default location: `.ainative/project.yaml`) exists for structured fields the control plane needs — name, description, repository, default branch, default workflow, validation commands, development commands, and AI context pointers — and is the structured source when the operational record does not name another file. If a project already has structured metadata at a different path, the operator names that project-relative path on the operational record; the registry uses that file and does not require a second standard manifest. The loader does not search the project tree for an equivalent file.

When both the operational record and the project declare the same field (name, default branch, validation commands), project-side truth wins.

**Why this priority**: This is how the hybrid model stays honest: the control plane does not become a second copy of the project, and new projects get a small standard file instead of an ad-hoc layout.

**Independent Test**: Load context from a fixture that has both conventional files (`README.md` + `AGENTS.md`) and a standard manifest (no named path); confirm both contribute. Load a fixture whose operational record names a non-standard project-relative manifest path and confirm that file is used and `.ainative/project.yaml` is not required. Load a fixture where the operational record says default branch `main` but the project says `master`, and confirm `master` is what context returns.

**Acceptance Scenarios**:

1. **Given** a project with `README.md`, `AGENTS.md`, and a standard operational manifest at `.ainative/project.yaml`, **When** context is loaded, **Then** the bundle includes the text of those conventional files and the structured fields from the manifest.
2. **Given** a project whose operational record names a project-relative manifest path other than `.ainative/project.yaml`, and that file exists with the required structured fields, **When** context is loaded, **Then** that named file is used for structured fields and `.ainative/project.yaml` is not required.
3. **Given** a project whose operational record says default branch `main` and whose project-side declaration says `master`, **When** context is loaded, **Then** the context’s default branch is `master`.
4. **Given** a new fixture project with no existing structured metadata, **When** the fixture is prepared for this feature’s checks, **Then** it uses the standard manifest at `.ainative/project.yaml` with at least name, repository, default branch, and validation commands.
5. **Given** a malformed operational manifest (unreadable or missing required structured fields), **When** context is loaded, **Then** the load fails at the trust boundary with a visible error.

---

### Edge Cases

- **Unknown project identity**: Distinct error; not an empty record; not a fallback to “the only project on disk.”
- **Disabled project**: Visible in the full list; rejected as eligible for work; context for execution is not loaded.
- **Missing or invalid local location**: Missing, empty, file-instead-of-directory, or unreadable path fails at the trust boundary. No silent substitute path.
- **Missing project configuration**: The chosen structured source (named manifest path, or `.ainative/project.yaml` when none is named) is absent or does not supply validation commands → fail with a missing-configuration error. Do not invent commands. Do not search the tree for another file.
- **Named manifest path**: If set, it MUST be relative to the project location and MUST NOT escape the project root. A missing, non-file, unreadable, or out-of-root named path fails at the trust boundary. It MUST NOT fall back to `.ainative/project.yaml`. If omitted, `.ainative/project.yaml` is the only structured source.
- **Partial conventional files**: If a slot’s filenames are all absent, omit that slot; do not fail solely because `README.md` or `CONTRIBUTING.md` is missing. Structured operational fields (identity, location, validation commands) remain required.
- **Conventional text slots**: First existing file wins; later names in the same slot are ignored unless also listed as an AI context pointer. Overview: `README.md` then `README`. Agent/AI: `AGENTS.md` then `CLAUDE.md`. Contributing: `CONTRIBUTING.md`. Architecture: `docs/architecture.md` then `ARCHITECTURE.md`. No directory glob and no other instruction filenames.
- **Context bundle contents**: Conventional text slots and files listed as AI context pointers are returned as text. Tooling files from the closed project-root set are returned as project-relative paths only. The in-memory bundle is not written into the control plane as a stored knowledge base.
- **Tooling path slots**: At the project root only, include every existing file from: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`. Do not recurse. Do not fail if none exist. Do not include lockfiles or other names.
- **Operational settings**: Opaque key-value map from the operational record. Missing or empty configuration yields an empty map. This phase returns the map unchanged and MUST NOT interpret keys (no retries, heartbeats, model routing, or workspace behavior).
- **AI context pointer paths**: Each pointer MUST be relative to the project location and MUST NOT escape the project root. A missing, unreadable, or out-of-root required pointer fails at the trust boundary.
- **Conflicting fields**: Project-side name, default branch, and validation/development commands override the operational record. Operational ID and enabled/disabled always come from the control plane.
- **Duplicate identities**: Two configuration entries with the same project ID fail at the trust boundary. Two entries pointing at the same repository with different IDs fail at the trust boundary.
- **Empty managed set**: Valid; list is empty; nothing is auto-discovered as a managed project.
- **Path-like or `../` identities**: Treated as unknown. The registry MUST NOT join a caller-supplied identity onto a filesystem path.
- **Unreadable knowledge file**: If a file the loader decided it must read (the chosen structured manifest, or a path the manifest lists as required AI context) cannot be read, load fails. Optional conventional files that are unreadable are omitted only when they were not declared required.
- **No versioned repository at the location**: Operational resolution of identity/location still succeeds. Context load still reads files that exist. This phase does not create branches or worktrees.
- **Host-specific paths**: Application behavior must not depend on a developer’s home directory layout. Mapping a host folder to a configured location is an environment concern, not a registry default.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registry MUST load the managed project set from operational configuration. It MUST NOT hardcode a workstation path or silently adopt repositories found on disk.
- **FR-002**: The registry MUST validate each configuration entry at the trust boundary (construction or first use). Required operational fields are: project ID, name, repository, and local/workspace location. Missing, empty, or duplicate IDs, duplicate repository locations, or a non-directory location MUST fail for that entry.
- **FR-003**: The registry MUST expose `list_projects()` returning every configured project’s operational record: ID, name, repository, local/workspace location, default branch, enabled/disabled, operational settings (empty map if omitted), and optional project-relative manifest path when set.
- **FR-004**: The registry MUST expose `get_project(id)` returning the operational record for an exact configured ID. Unknown IDs, path-like names, and `../` identities MUST fail with the same unknown-project error. The registry MUST NOT join a caller-supplied ID onto a filesystem path.
- **FR-005**: The registry MUST expose `resolve_eligible_project(id)` that succeeds only for a configured, enabled project whose local location exists as a directory. Disabled, unknown, or invalid-location projects MUST fail with a distinct, visible error.
- **FR-006**: Each operational record MUST include: project ID, name, repository, local/workspace location, default branch, enabled/disabled, and operational settings. Operational settings MUST be an opaque key-value map copied from configuration and returned unchanged. Missing settings MUST be an empty map. This phase MUST NOT require any keys in that map and MUST NOT interpret them. It MAY include an optional project-relative manifest path. It MUST NOT include copied project architecture, instructions, tests, or AI knowledge.
- **FR-007**: Default branch MUST come from the project’s own declaration when present; otherwise from the operational record; otherwise `main`.
- **FR-008**: Enabled/disabled MUST be an explicit operational flag. A missing flag defaults to enabled. Disabled projects remain listed and MUST NOT be eligible for work or context loading for execution.
- **FR-009**: The registry MUST expose `load_project_context(id)` only for an eligible project (FR-005). The result MUST include: operational identity (ID, name, repository, default branch); parsed structured fields from the chosen manifest (workflow, validation commands, development commands, AI context pointers when declared); the text of conventional slots that exist (FR-010) and of files listed as AI context pointers; and project-relative paths for tooling files that exist from the closed root set in FR-010.
- **FR-010**: Context loading MUST inspect these conventional text slots at the project location, using the first existing file in each list and omitting the slot if none exist: overview (`README.md`, then `README`); agent/AI instructions (`AGENTS.md`, then `CLAUDE.md`); contributing (`CONTRIBUTING.md`); architecture (`docs/architecture.md`, then `ARCHITECTURE.md`). Files listed as AI context pointers are additional text sources. The loader MUST NOT glob directories or inspect other instruction filenames. Tooling files MUST be taken only from this closed set at the project root, as project-relative paths (not file text), including every name that exists and omitting the rest: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`. The loader MUST NOT recurse, MUST NOT include lockfiles or other names, and MUST NOT fail solely because none of those files exist. Absent optional text slots are omitted, not invented.
- **FR-011**: If the project declares validation or development commands (via the chosen structured source), `load_project_context` MUST return those commands unchanged. The loader MUST NOT invent generic test or build commands when the project does not declare them; that case is a missing-configuration failure (FR-014).
- **FR-012**: The structured metadata file is selected from the operational record. If a project-relative manifest path is set, that file is the structured source and a second file at `.ainative/project.yaml` MUST NOT be required. If the path is omitted, the registry MUST use `.ainative/project.yaml` only. The registry MUST NOT search the project tree for an equivalent file. A named path MUST be relative to the project location and MUST NOT escape the project root; a missing, non-file, unreadable, or out-of-root named path MUST fail at the trust boundary with no fallback to `.ainative/project.yaml`.
- **FR-013**: The chosen structured source (named path or `.ainative/project.yaml`) MUST be able to declare: name, description, repository, default branch, default workflow, validation commands, development commands, and AI context pointers. The loader MUST NOT require every optional field; it MUST require name, repository, default branch, and validation commands from that file.
- **FR-014**: Missing project configuration (the chosen structured source is absent or does not supply validation commands) MUST fail with a visible missing-configuration error. The loader MUST NOT search for a substitute file.
- **FR-015**: A malformed or unreadable structured manifest MUST fail at the trust boundary. The loader MUST NOT skip it and guess.
- **FR-016**: Project knowledge MUST be read in place from the project repository. `load_project_context` MAY return an in-memory bundle to the caller. The registry MUST NOT persist a project knowledge base in the control plane, and MUST NOT treat the control plane as the owner of project architecture, instructions, conventions, tests, or project-specific AI knowledge.
- **FR-017**: The registry MUST reuse the control plane’s existing project-identity capability when one is already present. It MUST NOT introduce a second project store.
- **FR-018**: The V0 managed set MUST be explicit and configurable. The registry MUST NOT silently select a real production repository as the V0 target. A disposable fixture is the default until the owner names a non-critical real project.
- **FR-019**: The registry MUST NOT create workspaces or worktrees, execute agents, call models, create branches, push, open pull requests, send notifications, or orchestrate plan/implement/validate.
- **FR-020**: Operational configuration other than the managed-project set and the fields this feature needs to resolve a project MAY be ignored in this phase.

### Key Entities

- **Managed project (operational record)**: Control-plane identity for a software project the operator has explicitly enrolled. Fields: ID, name, repository, local/workspace location, default branch, enabled/disabled, operational settings (opaque key-value map; empty if omitted), optional project-relative manifest path. Not the project’s knowledge base.
- **Project repository**: The project’s own tree at the configured location. Owner of architecture, instructions, conventions, tests, and project-specific AI knowledge.
- **Operational manifest**: Structured project-side file declaring name, description, repository, default branch, default workflow, validation commands, development commands, and AI context pointers. The file used is the operational record’s project-relative manifest path if set, otherwise `.ainative/project.yaml`.
- **Project context**: In-memory bundle for a later executor: operational identity; parsed structured manifest fields; text of conventional slots and listed AI context files; project-relative paths for closed-set tooling files at the project root. Read from the project; not a copy stored in the control plane.
- **Managed set**: The explicit list of projects in operational configuration. The only projects this feature will list, resolve, or load. Disk contents outside this list are irrelevant.

### Out of Scope

This specification covers only the hybrid project registry, the operational manifest convention, and project context loading. Explicitly deferred:

- Workspace / worktree creation and Git safety (never work on main, never share dirty worktrees)
- Agent execution, model calls, and the methodology adapter (already specified separately)
- Plan → implement → validate orchestration
- Git hosting (push, pull requests, merge)
- Messaging / Telegram project-status commands
- Cross-project operational status (“what is blocked / what PR is waiting”)
- Concurrent work across projects
- Auto-discovery that enrolls repositories without an operator listing them
- `project-bootstrapper` (new-repo onboarding, not standard task execution)
- Copying or forking methodology
- Obsidian
- Automatic merge, production deploy, or protected-branch writes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given valid operational configuration, a caller can list managed projects and resolve a known enabled project’s identity, repository, location, default branch, and enabled flag on the first attempt without reading that project’s source tree.
- **SC-002**: 100% of unknown, path-like, disabled, or invalid-location project identities fail with a visible error (never an empty record, never a silently substituted repository).
- **SC-003**: 100% of eligible projects with declared validation commands return those exact commands in project context; 0% of loads invent generic test or build commands.
- **SC-004**: 100% of context loads for a missing location, missing structured configuration, or malformed manifest fail at the boundary; 0% succeed with guessed fields.
- **SC-005**: After listing, resolving, and loading context for a fixture project, a reviewer can confirm the control plane still does not contain a duplicated copy of that project’s instructions, architecture, or tests.
- **SC-006**: A reviewer can complete six contract checks — list managed projects, resolve known ID, reject unknown ID, reject disabled project, load fixture context with the project’s own validation commands, refuse missing configuration — and each check fails if that behavior breaks.
- **SC-007**: An unlisted real repository on disk is never returned as a managed or V0 target project (100% of list/resolve calls).

## Assumptions

- **This phase is registry + context loading only.** The methodology adapter already exists as a separate feature. Workspace management, Git safety, execution identity, PIV, Git hosting, and messaging are not started here.
- **Hybrid ownership is non-negotiable.** The control plane owns operational state (what is enrolled, where it lives, whether it is enabled). Each project owns project-specific truth. Methodology remains a separate read-only concern.
- **Configuration-backed V0.** The operator lists managed projects in operational configuration. The control plane’s existing project-identity capability is reused for persistence if it is already there; a second project database is not introduced. Auto-enrollment of discovered repositories is out of scope.
- **Standard manifest path** is `.ainative/project.yaml` when the operational record omits a manifest path (typical for fixture and new projects). Conventional text sources are the closed per-slot filenames in FR-010 (`README.md`/`README`, `AGENTS.md`/`CLAUDE.md`, `CONTRIBUTING.md`, `docs/architecture.md`/`ARCHITECTURE.md`) plus AI context pointers. Those files are inspected in place and are not replaced by the control plane. If a project already has structured metadata at another path, the operator names that project-relative path on the operational record; the loader uses that file only and does not search the tree.
- **Context bundle shape**: Conventional text slots and AI context pointer files contribute their text. Tooling files from the closed project-root set in FR-010 contribute a project-relative path only. The bundle is returned to the caller in memory and is not stored as control-plane knowledge.
- **Operational settings** are an opaque key-value map on the operational record. This phase stores and returns them unchanged, requires no keys, and does not interpret them. Missing settings are an empty map. Workspace, retry, heartbeat, and model-routing keys are later-phase concerns.
- **Manifest required fields** when the standard file is the structured source: name, repository, default branch, validation commands. Description, default workflow, development commands, and AI context pointers are optional.
- **Conflict rule**: Project-side name, default branch, and commands win. Operational ID and enabled/disabled always come from the control plane. Repository URL in the operational record is the enrollment identity; a differing project-side repository field is recorded on context but does not silently retarget enrollment.
- **V0 target.** Checks use a disposable fixture repository. The registry MUST make the real target configurable. A production repository is used only when the owner names it; this feature does not choose one.
- **Default branch fallback** is `main` when neither the project nor the operational record declares one. Many projects use `master`; that value is honored when declared.
- **Local location** is the configured path where the project tree can be read (inside the execution environment this is typically under the configured workspace root). Host-to-container mapping is environment configuration, not application code.
- **One registry, many entries, one later worker.** The registry may list multiple projects in V0. Running more than one task at a time is a later scheduling concern and is out of scope here.
- **Trust boundary**: Registry construction (or first load of configuration) validates the managed set. `load_project_context` is the boundary for project-side files. Invalid config or unreadable required project files fail there.
- **No new third-party libraries** without an explicit owner request. Configuration parsing and file discovery must use capabilities already present on the platform.
- **Checks** live with the existing control-plane package. One set of checks must fail if the six contract behaviors in SC-006 break. A fixture project tree is required; tests MUST NOT depend on a live production checkout.
- **Public operation names** (`list_projects`, `get_project`, `resolve_eligible_project`, `load_project_context`) are the agreed contract for this phase. Exact module layout inside the existing control-plane package is an implementation choice.
- **Telegram `/projects` and project-status summaries** are later operator surfaces that will consume this contract; they are not built here.
- **Implementation follows this spec**, then code; other V0 phases do not start until this registry’s checks pass and a later spec/plan asks for them.

# Feature Specification: Hermes Startup Context Files

**Feature Branch**: `016-hermes-startup-context`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Register Hermes AGENTS.md, persistent SYSTEM.md, and persistent USER.md as startup context files with exact container paths, revision-only operational records, clear startup validation, and simple placeholder instructions for the first delivery."

## Scope and baseline

Hermes needs three explicit startup context files: its own `AGENTS.md`, the
current deployment's persistent `SYSTEM.md`, and the operator's persistent
`USER.md`. These files remain the source of truth. Hermes registers their
configured container paths and file revisions, but does not copy their full
contents into Kanban, task records, worktrees, project repositories, or a
separate memory store.

The first delivery uses short, safe placeholder instructions in each file.
The operator will complete the real instructions later. `AGENTS.md` belongs
to the versioned Hermes repository. The actual `SYSTEM.md` and `USER.md`
remain in persistent Hermes data; the repository may contain only safe
templates for them.

The initial configured container paths are:

- Hermes instructions: `/opt/personal-agent/AGENTS.md`
- Runtime environment: `/opt/data/hermes-context/SYSTEM.md`
- Operator preferences: `/opt/data/hermes-context/USER.md`

The implementation must use the exact configured paths after mounts are
available. It must not translate or pass Mac host paths such as
`/Users/emad/...` into container code.

## Clarifications

### Session 2026-09-14

- Q: If SYSTEM.md or USER.md is not in the container when Hermes starts, what should happen? → A: Stop and say which file is missing. Hermes must not create those files automatically. Simple starter text is shipped as templates or repo files for the operator to copy in first.
- Q: After Hermes loads the three files, who should see their full text while working? → A: Only Hermes itself (startup, planning, health check). Coding jobs keep using the project’s own files.

This feature covers registration, startup loading, validation, precedence,
revision-only operational records, diagnostics, and placeholder content. It
does not include project-bootstrapper wiring or changes to the existing
`ich-mag-dich` validation command.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Load the three context files at startup (Priority: P1)

An operator starts Hermes with its configured container mounts available.
Hermes loads its own instructions, the deployment environment, and operator
preferences from the three exact configured paths before it handles commands.

**Why this priority**: Explicit startup context prevents repeated discovery and
keeps Hermes behavior grounded in the intended deployment and operator rules.

**Independent Test**: Start Hermes with three readable fixture files at the
configured paths and confirm that all three are loaded before the first
command is handled.

**Acceptance Scenarios**:

1. **Given** all three configured files exist and are readable, **When** Hermes
   starts, **Then** it loads all three files from their exact container paths
   before accepting commands.
2. **Given** a configured path is missing or unreadable, **When** Hermes starts,
   **Then** startup stops with a clear error naming the context role and path,
   and Hermes does not create the missing file.
3. **Given** a configured path is a directory, ambiguous, or otherwise not one
   readable file, **When** Hermes starts, **Then** it fails clearly without
   falling back to another path.
4. **Given** all three files loaded, **When** Hermes starts a coding job,
   **Then** that job is not given the full text of the three registered
   files and still uses the project's own instruction files.

---

### User Story 2 - Preserve one source of truth (Priority: P1)

An operator updates a registered context file in its persistent or versioned
location. Hermes records only enough path and revision information to identify
the loaded file, while later task and project records continue to refer to the
source file rather than containing a second copy.

**Why this priority**: Duplicated instructions can drift and cause Hermes to
use stale or conflicting context.

**Independent Test**: Start Hermes with fixture files, inspect operational
records, and confirm they contain paths and revisions but no full file
contents or copies in task, Kanban, worktree, or project records.

**Acceptance Scenarios**:

1. **Given** the three files load successfully, **When** Hermes records startup
   context, **Then** each record contains its role, exact path, and revision
   information only.
2. **Given** a task, worktree, project, or Kanban record is created after
   startup, **When** its context is inspected, **Then** it does not contain a
   copied body of any registered file.
3. **Given** a registered file changes, **When** Hermes starts again, **Then**
   the new revision is associated with the same source path.

---

### User Story 3 - Apply predictable context precedence (Priority: P2)

An operator can understand which instruction wins when platform rules,
Hermes instructions, runtime settings, project guidance, preferences, and
the current task disagree. Safety and protected-operation rules remain above
operator preferences and task requests.

**Why this priority**: A stable precedence order prevents a lower-priority
instruction from weakening safety or deployment constraints.

**Independent Test**: Provide conflicting fixture instructions at each layer,
start Hermes, and confirm the resulting behavior follows the documented order.

**Acceptance Scenarios**:

1. **Given** conflicting instructions, **When** Hermes resolves context, **Then**
   precedence is platform and safety, Hermes `AGENTS.md`, live runtime
   configuration over `SYSTEM.md`, project instructions, `USER.md`, and
   current task.
2. **Given** live runtime configuration conflicts with `SYSTEM.md`, **When**
   Hermes resolves the deployment setting, **Then** the live runtime
   configuration wins.
3. **Given** `USER.md` or the current task conflicts with safety, project
   validation, or protected-branch rules, **When** Hermes acts, **Then** those
   lower-priority instructions do not override the higher-priority rules.

### Edge Cases

- A configured file is missing, unreadable, a directory, empty when content is
  required, or resolves ambiguously: startup fails with the role and exact
  configured path, and no alternate path is searched. Missing persistent
  files are not created from templates at startup.
- Two context roles resolve to the same file: startup reports the ambiguous
  registration and does not silently share one file between roles.
- A configured path uses a Mac host location that is not mounted in the
  container: startup reports the container-visible path failure.
- A persistent `SYSTEM.md` or `USER.md` contains a secret: the file remains
  outside Git and diagnostics do not print its contents.
- A context file changes after startup: the current run keeps its loaded
  snapshot, and the next startup records the new revision.
- A lower-priority preference requests a forbidden operation: platform,
  Hermes, project, and protected-operation rules still win.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hermes MUST register exactly three startup context roles:
  Hermes instructions from `AGENTS.md`, runtime environment from `SYSTEM.md`,
  and operator preferences from `USER.md`.
- **FR-002**: Hermes MUST resolve each registered role from its exact
  configured container path after mounts are available. It MUST NOT search
  fallback paths or pass host-only paths into container code.
- **FR-003**: Before handling commands, Hermes MUST verify that every
  configured path exists, identifies one readable file, and is unambiguous.
  A failed check MUST stop startup and report the role, path, and reason
  without exposing file contents. Hermes MUST NOT create a missing
  `SYSTEM.md` or `USER.md` (or any other registered context file) in order
  to continue.
- **FR-004**: Hermes MUST load all three files during startup before handling
  commands, preserving the file contents for the current Hermes run without
  rewriting the source files. Full file text MUST be used only by Hermes
  itself for startup, planning, and health diagnostics. Hermes MUST NOT
  forward those full contents into coding-job or agent-execution payloads;
  those jobs continue to use the project's own instruction files.
- **FR-005**: Hermes MUST record only each context role's exact path and file
  revision as operational context. It MUST NOT copy full file contents into
  Kanban, task records, worktrees, project repositories, or a hidden memory
  database.
- **FR-006**: Context precedence MUST be platform and safety rules, Hermes
  `AGENTS.md`, live runtime configuration over `SYSTEM.md`, project
  instructions, `USER.md`, and current task instructions, in that order.
- **FR-007**: `AGENTS.md` MUST belong to the versioned Hermes repository.
  The actual `SYSTEM.md` and `USER.md` MUST remain in persistent Hermes data
  outside Git. Safe repository templates MAY be provided at
  `personalAgent/docs/context/SYSTEM.example.md` and
  `personalAgent/docs/context/USER.example.md`.
- **FR-008**: The first delivery MUST provide short, safe placeholder
  instructions in each of the three registered files or its corresponding
  safe template, clearly stating that the operator will complete the text
  later. Placeholder content MUST contain no passwords, API keys, tokens,
  private keys, or other secrets.
- **FR-009**: Startup diagnostics MUST report the configured AiNative root,
  available agents, configured projects, workspace root, active harness, and
  persistent state path alongside the context registration result.
- **FR-010**: The implementation MUST leave project-bootstrapper wiring and
  the existing `ich-mag-dich` validation behavior unchanged and out of scope.
- **FR-011**: Focused checks MUST cover successful startup loading, exact-path
  enforcement, missing and unreadable files, no auto-create on missing files,
  ambiguous registrations, precedence conflicts, revision-only records,
  content non-duplication, Hermes-only full-text use, and secret-safe
  diagnostics.

### Key Entities *(include if feature involves data)*

- **Startup context registration**: The three configured roles, their exact
  container paths, and the order in which they are loaded.
- **Context file**: One source file describing Hermes instructions, the
  runtime deployment, or operator preferences.
- **Context revision record**: Operational metadata containing a role, exact
  source path, and revision identifier without a copied file body.
- **Context precedence layer**: The ordered authority level used to resolve
  conflicting instructions.
- **Startup diagnostic**: A safe report of context validation and the known
  Hermes/AiNative runtime locations, without secrets or file contents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of valid startup fixtures, Hermes validates and loads
  all three registered context files before handling the first command.
- **SC-002**: In 100% of missing, unreadable, directory, ambiguous, and
  host-path fixtures, Hermes stops startup with a clear role-and-path error
  and performs no fallback lookup.
- **SC-003**: An operational-record audit finds zero full copies of registered
  file contents in Kanban, task records, worktrees, project repositories, or
  hidden memory storage.
- **SC-004**: In 100% of precedence fixtures, conflicts resolve in the
  documented order, with safety and platform rules remaining authoritative.
- **SC-005**: The first-delivery files or safe templates contain short
  placeholder instructions for all three roles and contain zero secrets.
- **SC-006**: A startup diagnostic reports all required deployment locations
  and context registration results without printing any context file body.

## Assumptions

- The initial deployment uses the three container paths documented above:
  `/opt/personal-agent/AGENTS.md`,
  `/opt/data/hermes-context/SYSTEM.md`, and
  `/opt/data/hermes-context/USER.md`. Deployment configuration remains the
  authority if it supplies different exact paths.
- The required mounts and persistent directories exist before Hermes startup.
  Hermes validates them and MUST NOT create missing `SYSTEM.md` or `USER.md`
  automatically. The first delivery ships simple starter templates (and
  `AGENTS.md` in the Hermes repo) so the operator can copy persistent files
  into place before start.
- A file revision is a stable identifier sufficient to tell whether the
  source file changed; the implementation may choose the existing repository
  convention for producing that identifier.
- Runtime configuration is live authority for deployment settings and wins
  over descriptive `SYSTEM.md` text when they disagree.
- `AGENTS.md` is safe to version. Actual `SYSTEM.md` and `USER.md` may
  contain deployment or personal information and therefore remain outside
  Git; only non-secret templates are versioned.
- Placeholder text is intentionally minimal for this first delivery. The
  operator will replace it with complete instructions in a later change.
- Missing persistent context files are an operator setup error, not an
  auto-create path.
- Full registered-file text is Hermes-only for this delivery; coding jobs
  keep project-local instructions.

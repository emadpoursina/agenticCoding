# Feature Specification: Kanban Project Identity Mapping

**Feature Branch**: `017-kanban-project-identity`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "The control plane matches a card to a project by the exact string in its config (`id: ich-mag-dich`), but Hermes Kanban stores a card's `project_id` as the native project's internal id (`p_f1577341`). The registry only accepts the config id, so every card is skipped or reported as 'no ready task'. Declare and validate a native-to-operational project identity mapping so supported flows work."

## Scope and baseline

The control plane keeps one operational project identity per enrolled
project: `ProjectRecord.id` from `config/default.yaml` (for the current
install, `ich-mag-dich`). Hermes Kanban stores each task's `project_id` as
the native `projects.db` internal id (for the same project,
`p_f1577341`). The two namespaces have no declared mapping today.

The result: a card created with `--project ich-mag-dich` is stored as
`project_id = p_f1577341`; the worker reads that native id and calls
`registry.resolve_eligible_project`, which accepts only `ich-mag-dich`.
`run_workflow` raises `UnknownProjectError`; `run_next_workflow` silently
skips the card and reports "no ready task". The failure is safe (nothing is
half-run, no repo or board write), but the project cannot run at all.

This feature declares the mapping in configuration, canonicalizes native
ids to the operational id at the native-store boundary, and makes an
unmapped id fail loudly instead of disappearing. It does not rewrite the
native `projects.db`, does not add fuzzy or display-name matching, and does
not introduce a second project or task store.

Terminology used below:

- **Operational id**: `ProjectRecord.id`, the config key used for
  workspaces, overlay records, GitHub, and Telegram.
- **Native id**: the Hermes `projects.db` internal id stored on a card's
  `project_id`.
- **Alias**: a declared native id that resolves to one operational id.

## Clarifications

### Session 2026-09-17

- Q: Where should the native-to-operational mapping live? → A: A declared
  alias list on each enrolled project in `config/default.yaml`
  (`kanban_project_ids`). No runtime read of `projects.db`.
- Q: What should happen when a card carries an id that is not enrolled and
  not a declared alias? → A: Keep the existing fail-closed behavior
  (`run_workflow` raises; `run_next_workflow` skips the card), but the
  no-ready result MUST name the unmapped id instead of the bare
  "no ready task".
- Q: Where should the plan and delivery artifacts live? → A: Spec Kit
  folder `specs/017-kanban-project-identity/`, matching the existing
  numbered specs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a card whose project_id is the native id (Priority: P1)

An operator creates a card through a supported Hermes flow using the
enrolled config id. Hermes stores the native `projects.db` id. Hermes picks
up the card and runs it against the enrolled project as if the config id
had been used.

**Why this priority**: Without this, no supported flow can start a job for
the enrolled project. This is the whole defect.

**Independent Test**: Seed a native Kanban fixture card whose
`project_id = p_fixture`, declare that id as an alias of the enrolled
project, run `--next-ready`, and confirm the harness starts for the
enrolled project.

**Acceptance Scenarios**:

1. **Given** a project enrolled as `fixture` that declares
   `kanban_project_ids: [p_fixture]`, **When** a card with
   `project_id = p_fixture` is run, **Then** the workflow uses operational
   id `fixture` and reaches the harness.
2. **Given** the same enrollment, **When** the card is selected by
   `--next-ready`, **Then** the card is eligible and is started.
3. **Given** a task is selected from the board, **When** its worktree is
   prepared, **Then** the worktree is created under
   `<workspace_root>/fixture/<task>`, never under the native id.

---

### User Story 2 - Keep one identity across records and restart (Priority: P1)

Every operational record produced for the run — overlay record, workspace
identity, GitHub publish identity, Telegram status output — uses the
operational id, and restart recovery can still find the worktree.

**Why this priority**: If the native id leaks past the board boundary, path
math and identity checks disagree (workspace boundary mismatch, blocked
reclaim), so a successful start would still fail later.

**Independent Test**: Run a card carrying the native id to completion, then
reload the orchestrator from the overlay and confirm reclaim resolves the
same worktree and that displayed identities are the operational id.

**Acceptance Scenarios**:

1. **Given** a card selected with native id `p_fixture`, **When** the
   workflow record is written, **Then** `record.project_id == "fixture"`.
2. **Given** a workflow parked mid-run, **When** the process restarts,
   **Then** `become_ready()` reclaims the same worktree and identity.
3. **Given** Telegram `/status` and `/projects`, **When** an operator
   reads them, **Then** the operational id is shown and a declared alias is
   accepted as input.

---

### User Story 3 - Fail loudly on an unmapped id (Priority: P2)

An operator adds a card for a project whose native id is not declared. The
worker reports which id could not be mapped instead of reporting "no ready
task".

**Why this priority**: The silent skip is what made this defect hard to
diagnose. Safety is already correct; only the report is missing.

**Independent Test**: Seed a card with an undeclared native id, run
`--next-ready`, and confirm the error names the unmapped id and leaves the
GitHub boundary untouched.

**Acceptance Scenarios**:

1. **Given** a card with an undeclared native id, **When** `--next-ready`
   runs, **Then** it reports the unmapped id and selects no task.
2. **Given** a card with an undeclared native id, **When** `--task` selects
   it directly, **Then** the run fails closed with a clear unmapped-id
   error.
3. **Given** `--doctor`, **When** a project declares aliases, **Then** the
   diagnostic lists them as metadata only.

### Edge Cases

- An alias equals another project's operational id or another project's
  alias: construction fails with `InvalidProjectConfigError`.
- An alias is empty, non-string, or path-like (`/`, `\`, `.`, `..`):
  construction fails.
- A card's `project_id` is empty: it remains unmapped and fail-closed.
- A card carries a near-miss alias (for example, one character different):
  it does not resolve; there is no fuzzy or prefix matching.
- A legacy overlay record stored the native id (pre-fix): restart
  canonicalizes it before the board comparison, so reclaim is not blocked.
- `--resume` and Telegram option replies arrive with either the operational
  id or a declared alias: both resolve to the same parked record.
- Two enrolled projects declare the same native id: construction fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each enrolled project MAY declare `kanban_project_ids`, a
  list of native Hermes project ids that resolve to that project's
  operational id. A single scalar value MUST be accepted and normalized to
  a one-element set.
- **FR-002**: The registry MUST reject, at construction, any alias that is
  empty, non-string, path-like, duplicated within a project, equal to any
  project's operational id, or equal to another project's alias.
- **FR-003**: `ProjectRegistry` MUST expose `canonical_id(value)`: an
  operational id returns itself; a declared alias returns its operational
  id; anything else raises `UnknownProjectError`. `get_project`,
  `resolve_eligible_project`, and `load_project_context` MUST accept an
  alias and behave exactly as for the operational id.
- **FR-004**: The native-store boundary (`SqliteTaskBoard`) MUST translate a
  card's native `project_id` to the operational id before the task reaches
  the orchestrator. Translation MUST be exact-match only; an undeclared id
  MUST be left unchanged rather than guessed.
- **FR-005**: The live board MUST be constructed with the registry's
  resolver. Board fixtures and offline checks that construct the board
  without a resolver MUST keep working.
- **FR-006**: No operational artifact MAY carry the native id as a project
  identity: overlay `project_id`, workspace path, `CorrelationIdentity`,
  publish identity, and status output MUST use the operational id.
- **FR-007**: `resume_workflow` MUST canonicalize its incoming project id
  before comparing it to the parked record, so either form resumes the same
  workflow.
- **FR-008**: Restart recovery MUST canonicalize a legacy overlay
  `project_id` before comparing it to the board task, so a pre-fix record
  does not block.
- **FR-009**: When `--next-ready` finds no eligible task and at least one
  card was skipped because its project id was unmapped, the error MUST name
  the unmapped id(s) as safe metadata. `--task` on an unmapped id MUST fail
  closed with a clear error.
- **FR-010**: `--doctor` MUST list each enrolled project's declared
  `kanban_project_ids` as metadata only, without reading `projects.db` and
  without printing file bodies or secrets.
- **FR-011**: The feature MUST NOT modify native `projects.db`, add a second
  project or task store, add a new dependency, or change protected-branch,
  merge, and deploy limits.
- **FR-012**: Focused checks MUST cover alias resolution at the registry and
  board boundaries, end-to-end selection and worktree placement, alias
  collision and path-like rejection, unmapped-id reporting, resume with
  either id form, and legacy overlay reclaim.

### Key Entities *(include if feature involves data)*

- **ProjectRecord aliases**: The declared `kanban_project_ids` on one
  enrolled project.
- **Canonical project id**: The operational id that every downstream
  artifact uses; the output of alias resolution.
- **Native card id**: A task's `project_id` as stored by Hermes Kanban.
- **Unmapped id report**: Safe metadata naming card project ids that did not
  resolve to an enrolled project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of fixtures where a card carries a declared alias,
  the workflow selects and runs the enrolled project.
- **SC-002**: In 100% of run fixtures, the prepared worktree path,
  `record.project_id`, and published identity use the operational id.
- **SC-003**: In 100% of collision and path-like alias fixtures, registry
  construction fails and no project is silently chosen.
- **SC-004**: In 100% of unmapped-id fixtures, the reported failure names
  the unmapped id, and no push, pull request, or board write occurs.
- **SC-005**: Restart recovery reclaims a workflow whose overlay was written
  before the mapping fix with no manual state edit.
- **SC-006**: `--doctor` output lists declared aliases and still prints no
  secrets or file bodies.

## Assumptions

- The operator reads each project's native id from `projects.db` once and
  declares it in `config/default.yaml`. Reading `projects.db` at runtime is
  explicitly out of scope.
- The container config mount is read-only; changing `config/default.yaml`
  is a repository change followed by a container recreate, not an in-place
  container edit.
- `ProjectRecord.id` remains the only operational key; existing overlays and
  worktrees that already use it are not migrated or renamed.
- The three currently failing forms (native id, display name, empty) are
  handled as: native id via alias; display name continues to be matched by
  `--smoke` through `ProjectRecord.name`; empty stays fail-closed.
- `AGENTS.md` and startup context behavior are unchanged.

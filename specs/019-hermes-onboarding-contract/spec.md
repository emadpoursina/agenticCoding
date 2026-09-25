# Feature Specification: Hermes onboarding contract (Kanban as the user-facing work queue)

**Feature Branch**: `hermes-onboarding-contract`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "I want to make some changes to my Hermes Project
Onboarding Contract" — hands-off doc: the onboarding contract must explicitly
define what Hermes guarantees after enrollment, with the Kanban board as the
user's primary interface for submitting work (top-level cards are desired
outcomes, not internal workflow states).

## Scope Summary

The current onboarding contract covers enrollment and scaffolding only
(17 preserved guarantees; 11 established onboarding behaviors). This feature
extends the contract so that after onboarding, the project's primary Kanban
board is the user-facing work queue: a user (operator) submits desired
outcomes as top-level **Feature Cards**; an internal task-generation phase
decomposes each Feature Card into independently executable child **Task
Cards**; executors run child tasks; a validator confirms the feature; and the
Feature Card completes. Internal workflow states (ready, specify, clarify,
confirm, plan, tasks, implement, converge, critic, tester, uat, pr-review,
publish) never appear as Kanban cards. All existing safety, idempotency, fail-closed,
scaffolding, and test guarantees are preserved unless they conflict with the
new contract.

## Clarifications

### Session 2026-09-23

- Q: Who assigns the task-generator execution profile to a newly created
  Feature Card? → A: System auto-applies the project-default task-generator
  at card creation; the operator may override it later. The default is
  selected by the card's Path (feature/change/job), which selects between the
  three available execution profiles/paths; the operator (or system policy)
  may choose among them.
- Q: Are all child Task Cards produced by the task-generator required for the
  parent Feature Card to complete? → A: Yes — all child Task Cards produced
  by the task-generator are required.
- Q: How is a parked human gate surfaced to the operator? → A: On the board:
  the parked card shows a visible gate marker/comment, and the operator
  resolves the gate there.
- Q: Is feature-level validation automated or human? → A: Automated
  validator; an operator gate applies only when the workflow raises one
  (clarification, UAT, architecture decision, blocked dependency).
- Q: How are manual board edits to child Task Cards handled (manual
  completion / deletion)? → A: The board is authoritative: manual completion
  counts toward the parent, deletion re-evaluates the parent, and the
  orchestrator records the decision durably.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator submits a desired outcome and the system completes it (Priority: P1)

An operator, after enrolling a repository once, opens the project's primary
Kanban board and creates a Feature Card describing a desired outcome (for
example, "add CSV export"). The system decomposes the outcome into child Task
Cards, executes them, validates the completed feature, and completes the
Feature Card. The operator never needs to know about the internal workflow,
its state names, orchestration internals, or the execution harness — they
interact only with the board.

**Why this priority**: This is the entire point of the change: the board
becomes the primary interface for submitting work, replacing internal
workflow enrollment as the contract's center of gravity.

**Independent Test**: Enroll a project, create one Feature Card, and observe
the end-to-end flow (decomposition → child cards → execution → validation →
completion) without any operator input beyond the card.

**Acceptance Scenarios**:

1. **Given** an enrolled project with its primary board, **When** a Feature
   Card is created on that board, **Then** the system treats it as a desired
   outcome and runs the task-generation phase on it (not as an internal
   workflow state card).
2. **Given** a Feature Card, **When** the task-generation phase runs, **Then**
   child Task Cards appear on the same board, each independently executable.
3. **Given** all required child Task Cards complete, **When** feature
   validation and any applicable human gates pass, **Then** the parent Feature
   Card completes; **Given** any required child is incomplete or validation
   fails, **Then** the parent does not complete.

### User Story 2 - Onboarding guarantees a complete, inspectable project contract (Priority: P1)

An operator onboards a repository once. They can read, from the project
itself, what Hermes guarantees: project identity (repository owner/name,
derived project id, native project, workspace location, default branch,
primary board), the workspace contract (safe clone/reuse, no overwrites,
explicit commit/push), and the project contract (readme, agent instructions,
project manifest declaring the feature-loop workflow, validation commands,
execution context). Re-running onboarding changes nothing.

**Why this priority**: Identity and workspace guarantees are the foundation
the Kanban contract sits on; they are also where regressions (conflicting
re-enrollment, overwrites) would do damage.

**Independent Test**: Run onboarding against a fresh repository and again
against an enrolled one; verify identity resolution, idempotency, and that
the declared files and workflow exist and are not duplicated or overwritten.

**Acceptance Scenarios**:

1. **Given** a repository with a single matching native project, **When**
   onboarding runs, **Then** the result records owner/name, project id,
   native project, workspace location, default branch, and the primary
   Kanban board for the project.
2. **Given** a repository already enrolled, **When** onboarding runs again,
   **Then** nothing is duplicated or overwritten and onboarding succeeds
   (idempotency preserved).
3. **Given** an ambiguous or conflicting enrollment (duplicate aliases,
   mismatched re-enrollment, absent native project when creation is not
   allowed), **When** onboarding runs, **Then** it fails closed with no
   partial enrollment.

### User Story 3 - The board shows work, not workflow (Priority: P2)

A user looking at the board sees only work items: Feature Cards (desired
outcomes) and child Task Cards. No card exists for an internal workflow state
such as ready, specify, clarify, confirm, plan, tasks, implement, converge,
critic, tester, uat, pr-review, or publish. Internal states live in orchestration
records, are durable across restarts, and are invisible on the board.

**Why this priority**: This is the most important architectural rule in the
hands-off doc, but it is fully exercised by stories 1 and 2; it earns its own
story because it is independently verifiable and guards against regressions
("a card per orchestrator state").

**Independent Test**: Inspect every card on an active project's board; assert
none represents an internal workflow state, and inspect orchestration records
to confirm internal states are still tracked there.

**Acceptance Scenarios**:

1. **Given** a project mid-feature, **When** the board is inspected, **Then**
   only Feature Cards and child Task Cards are present.
2. **Given** the internal workflow is between states, **When** the operator
   restarts the system, **Then** orchestration resumes from durable state
   (board plus orchestration records) without reconstructing any
   conversation, and no new workflow-state card appears.

### User Story 4 - Profiles describe execution strategy, never a provider (Priority: P2)

An operator assigns work to cards using execution profiles: a
task-generator profile (turns a Feature Card through the internal workflow
into child cards), an executor profile (executes one child Task Card), and a
validator profile (feature-level validation). Profiles name execution
strategies; they never name a model provider or vendor. Runtime and model
selection are resolved separately from the card/profile.

**Why this priority**: Prevents the classic "profile = provider" misuse and
keeps the dispatch model clean; independent of the board-user journey but
required for decomposition to work.

**Independent Test**: Attempt to create cards with profiles; verify
task-generator/executor/validator roles are recognized and assign-able, and
that a provider or vendor name as a profile is rejected.

**Acceptance Scenarios**:

1. **Given** a Feature Card, **When** it is assigned a task-generator
   profile, **Then** the system runs the internal decomposition and produces
   child cards.
2. **Given** a child Task Card, **When** an executor profile is assigned,
   **Then** a single executor can claim and complete the card independently
   of its siblings.
3. **Given** any card, **When** a profile value naming a provider or vendor
   is supplied, **Then** the system rejects it.

### User Story 5 - PRD import lands on the new hierarchy (Priority: P3)

An operator imports an optional PRD for an enrolled project. Each PRD section
becomes a top-level Feature Card (a desired outcome) on the primary board —
never a workflow-state card — and the normal decomposition flow takes over.

**Why this priority**: Preserves an existing optional capability and aligns
it with the new hierarchy; not needed for the core loop.

**Independent Test**: Import a multi-section PRD with card creation enabled;
verify every created card is a top-level Feature Card on the primary board
and none encodes a workflow state.

**Acceptance Scenarios**:

1. **Given** an enrolled project and a PRD with N sections, **When** PRD
   import runs with card creation, **Then** N top-level Feature Cards are
   created, each belonging to the project's primary board.
2. **Given** the same import in draft-only mode, **When** import runs,
   **Then** drafts are produced as files and nothing is written to the board
   (existing behavior preserved).

### Edge Cases

- What happens when the internal workflow hits a human gate (clarification
  questions, user acceptance, architecture decision, blocked dependency)?
  The gate parks durably, is associated with the Feature/Task Card it
  belongs to, is surfaced to the operator, and is never silently bypassed.
- What happens when the system restarts mid-feature? On startup the system
  reads the board and durable orchestration state and resumes; retry limits
  (attempts per state), park, and fail-closed behavior are preserved.
- What happens when a child Task Card fails? It is retried and/or parked
  per existing orchestration policy; its parent Feature Card stays open.
- What happens when onboarding runs with dry-run enabled? Nothing is
  written anywhere (existing guarantee preserved), and the projected
  primary-board result is part of the plan the operator can inspect.
- What happens when a repository is enrolled twice with conflicting
  identity (different owner, ambiguous slug match)? Onboarding fails closed
  (existing behavior preserved).
- What happens when a Feature Card is created but decomposition never
  produces children (e.g., generator fails)? The Feature Card remains open,
  the failure is durable and surfaced; no empty completion.
- What happens when the operator manually completes or deletes a child Task
  Card on the board? The board is authoritative: manual completion counts
  toward the parent, deletion re-evaluates the parent, and the orchestrator
  records the decision durably.

## Requirements *(mandatory)*

### Functional Requirements

*Project identity*

- **FR-001**: After onboarding, the system MUST have resolved and recorded
  the project identity: repository owner/name, the derived project id, the
  single matching native Hermes project, the workspace location of the
  clone, the default branch, and the project's primary Kanban board.
- **FR-002**: Onboarding MUST remain idempotent: re-running it for an
  already-enrolled repository MUST produce the same identity and board state
  without duplication.
- **FR-003**: Onboarding MUST fail closed on identity conflicts: absent
  native project (when creation is not permitted), ambiguous native project
  match, duplicate alias, or mismatched re-enrollment.

*Workspace contract*

- **FR-004**: The workspace contract MUST guarantee a safe clone or verified
  reuse of the existing clone, including origin and branch verification,
  before any scaffold work.
- **FR-005**: Scaffolding MUST create only missing files and MUST never
  overwrite existing project files; commit and push remain explicit
  opt-in behaviors, and dry-run MUST write nothing.
- **FR-006**: The methodology tree (AiNative) MUST remain read-only to
  onboarding; only paths and references to it may be recorded.

*Project contract*

- **FR-007**: Every onboarded project MUST expose, from the project itself:
  a readme, an agent-instructions file, and a project manifest declaring the
  feature-loop workflow, plus declared validation commands and execution
  context. Onboarding MUST NOT invent configuration beyond this contract.

*Kanban contract*

- **FR-008**: Every onboarded project MUST have a primary Kanban board that
  serves as the user-facing work queue for that project.
- **FR-009**: Top-level cards on the primary board MUST represent desired
  outcomes (Feature Cards). The board MUST NOT contain cards that represent
  internal workflow states (ready, specify, clarify, confirm, plan, tasks,
  implement, converge, critic, tester, uat, pr-review, publish).
- **FR-010**: Internal workflow states MUST be tracked by the orchestrator,
  durable and recoverable, and never surfaced as board cards.

*Card hierarchy*

- **FR-011**: A Feature Card MUST be representable as a parent; the
  task-generator role creates child Task Cards from it after the internal
  planning phase, and each child MUST reference its parent Feature Card.
- **FR-012**: Child Task Cards MUST be independently executable and MUST use
  the existing dependency mechanisms; a parent Feature Card MUST complete
  only when ALL child Task Cards produced by the task-generator are complete
  (all children required — none optional) and feature-level validation
  (plus any operator-raised human gates) has passed.

*Execution profiles*

- **FR-013**: The contract MUST define three execution roles as profile
  semantics: task-generator (Feature Card → internal planning → child Task
  Cards), executor (single child Task Card), and validator (feature-level
  validation of the completed Feature Card).
- **FR-014**: Profiles MUST express execution strategy only; the system MUST
  reject any profile value that names a model provider or vendor, and
  runtime/model selection MUST be resolved separately from card profiles.
- **FR-014a**: At Feature Card creation the system MUST auto-apply the
  project-default task-generator profile, selected by the card's Path
  (feature/change/job — the three available execution paths); the operator
  MAY override the assignment later. A provider/vendor name as the override
  remains rejected per FR-014.

*State ownership*

- **FR-015**: Ownership boundaries MUST hold with no duplicate workflow
  state: the Kanban board owns card identity, parent-child links,
  dependencies, assignee, profile, priority, lifecycle, comments, and
  history; the orchestrator owns workflow state, transitions, retries, human
  gates, attempts, and decisions; the methodology tree owns methodology,
  definitions, and skills (read-only); the executing agent/runtime owns
  execution tools, code, and artifacts.

*Lifecycle, gates, recovery*

- **FR-016**: The end-to-end lifecycle MUST be: Feature Card →
  task-generator → internal planning → child Task Cards → executors →
  validator → Feature Card complete, with internal states durable but
  invisible on the board.
- **FR-017**: Human gates (clarification, user acceptance, architecture
  decision, blocked dependency) MUST be durable, associated with the card
  they belong to, and never silently bypassed. A parked gate MUST be
  surfaced on the board as a visible gate marker/comment on the parked
  card, and the operator MUST be able to resolve the gate there.
- **FR-018**: After a restart, the system MUST resume from durable state
  (board plus orchestration records) without reconstructing any prior
  conversation, preserving existing retry, park, and fail-closed behavior.

*PRD import*

- **FR-019**: Optional PRD import MUST be preserved, with each PRD section
  producing a top-level Feature Card on the primary board (never a
  workflow-state card), and draft-only/dry-run behaviors preserved.

*Preservation*

- **FR-020**: All 17 existing onboarding guarantees (owner/name validation,
  derived project id, single native slug match, idempotency, fail-closed
  conflict handling, clone, validated reuse, scaffolding of the three
  project files, single control-plane section, scaffold commit message,
  opt-in push, config+overlay fallback, dry-run writes nothing, optional
  PRD→cards, read-only AiNative, no overwrite, no context-file copying) and
  all 11 established onboarding test behaviors MUST be preserved unless they
  conflict with this contract.

*New observable behaviors (testable contract additions)*

- **FR-021**: After onboarding, the primary board MUST exist and be
  discoverable for the enrolled project.
- **FR-022**: A Feature Card created on the primary board MUST belong to the
  enrolled project and to its primary board.
- **FR-023**: Child Task Cards MUST reference their parent Feature Card, and
  the parent MUST be identifiable from any child.
- **FR-024**: The task-generator MUST be represented as an execution
  profile/role, never as a workflow state or board card.
- **FR-025**: A child Task Card MUST be assignable to an executor (single
  card, single executor at a time).
- **FR-026**: Feature-level validation MUST be associated with the Feature
  Card, not with individual child tasks.
- **FR-027**: No card in the system MUST encode an internal workflow state,
  for any card path (feature/change/job paths included).
- **FR-028**: Feature-level validation MUST run as an automated validator
  (the validator profile); an operator gate is required only when the
  workflow raises one (clarification, UAT, architecture decision, blocked
  dependency). Absent a raised gate, completion MUST NOT wait on a human.
- **FR-029**: Manual board edits to child Task Cards MUST be honored with
  the board as authoritative: a manual child completion MUST count toward
  parent completion, and manual deletion of a child MUST trigger
  re-evaluation of the parent; the orchestrator MUST record each such
  decision durably.

### Key Entities *(include if feature involves data)*

- **Feature Card**: top-level board card representing a desired outcome;
  belongs to a project and its primary board; parent of child Task Cards;
  completes only after ALL child Task Cards produced by the task-generator
  complete (all required), automated feature validation passes, and any
  operator-raised human gates pass. At creation it receives a
  project-default task-generator profile selected by its Path
  (feature/change/job), overridable by the operator.
- **Task Card**: child board card produced by the task-generator; belongs to
  the same project/board; references its parent Feature Card; independently
  executable by one executor; carries its own dependencies, assignee,
  profile, and priority.
- **Primary Kanban Board**: the single user-facing work queue for an
  onboarded project; owns work items only (Feature and Task Cards), never
  internal workflow states.
- **Project Identity**: repository owner/name, derived project id, native
  project, workspace location, default branch, and primary board — resolved
  once at onboarding, idempotently.
- **Execution Profile**: an execution strategy attached to a card
  (task-generator, executor, validator); never a provider or vendor name;
  the task-generator default is auto-assigned by card Path
  (feature/change/job) and operator-overridable.
- **Workflow Record** (orchestrator-owned): durable internal state,
  transitions, attempts, decisions, and human gates for one Feature; not a
  board card.
- **PRD Section → Feature Card**: optional import mapping each PRD section
  to one top-level Feature Card.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can go from "onboard once" to "Feature Card
  completes" — create card, decomposition, child execution, validation,
  completion — without needing to know any internal workflow state name,
  orchestration concept, or harness mechanism.
- **SC-002**: 100% of cards visible on any active onboarded project's board
  are Feature Cards or child Task Cards; zero cards encode an internal
  workflow state (verifiable by board inspection during a mid-feature run).
- **SC-003**: Re-running onboarding on an enrolled project produces zero
  diffs to project files, identity records, and board state (full
  idempotency).
- **SC-004**: A restart at any point in the lifecycle resumes correctly from
  board plus orchestration state in 100% of tested interruption points,
  with no conversation reconstruction.
- **SC-005**: All existing onboarding behaviors (the established test suite)
  continue to pass unchanged, and every new contract behavior listed in
  FR-021..FR-029 has an automated check that fails if the behavior regresses.
- **SC-006**: Every human gate encountered in a feature run is recorded,
  associated with its card, surfaced on the board as a visible marker or
  comment on the parked card, and resolved only by the operator there —
  zero silent gate bypasses across a full feature run.
- **SC-007**: A Feature Card with all children complete and no raised gate
  completes via the automated validator with zero additional operator
  actions; manual completions and deletions of child cards are honored
  (board authoritative) with the orchestrator's decision recorded in 100%
  of tested manual-edit cases.

## Assumptions

- The implementation lives in the existing Hermes control-plane package
  (`personalAgent`), reusing its existing board model, registry,
  orchestrator, dispatcher, and profile mechanisms; this feature adds only
  missing contract behavior — no second task database, no board redesign,
  no orchestrator rewrite.
- The 17 existing onboarding guarantees and the 11 established onboarding
  test behaviors are treated as a preserved baseline; conflicts with the new
  contract are resolved in favor of the new contract only where the two
  genuinely collide, and such collisions are recorded in the plan.
- "Primary board" means the single native Hermes board the project is
  enrolled onto (one native board per install; per-project visibility by
  project identity), not a new per-project database.
- Parent/child and dependency representation reuses the existing card-body
  dependency/reference mechanisms rather than a new schema.
- The task-generator, executor, and validator roles map onto existing
  execution-role abstractions; where a role has no implementation yet, the
  contract requires the wiring to exist and be testable, not a new runtime.
- Human-gate associations (clarification, user acceptance, architecture
  decision, blocked dependency) ride the existing park/resume path.
- PRD sections map one-to-one to top-level Feature Cards; PRD title lines
  become card titles as today.
- Provider/runtime resolution stays configured in Hermes and is out of scope
  here beyond the "profiles are never providers" rule.

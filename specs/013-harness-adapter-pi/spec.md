# Feature Specification: Pi Harness Adapter

> **Superseded by `018-unified-feature-loop` for execution shape.** Live
> execution is now the Hermes-owned feature loop with one new Pi session
> per agent state (`AiNative/docs/systems/feature-loop.md`). The
> whole-playbook execution described in this spec is retired from the live
> path; this document is kept for history.

**Feature Branch**: `013-harness-adapter-pi`

**Created**: 2026-09-08

**Status**: Draft

**Input**: User description: "Implement a Harness Adapter so Hermes is orchestration only and Pi SDK is the first execution harness."

## Clarifications

### Session 2026-09-08

- Q: When this ships, what should happen to tasks already mid-way through the old Hermes Spec Kit short path? → A: Park them for a human with a clear reason; do not finish them on the old machine and do not auto-rewrite their history.
- Q: Should the old Hermes Spec Kit stage machine be fully removed from the live path, or kept disabled as a fallback switch? → A: Fully remove it from every live command, fallback, and recovery path.
- Q: What should happen when a harness run exceeds its time limit? → A: The run stops and returns `failed`; a start request without a timeout is rejected before the harness starts.
- Q: Which playbook identities may Hermes start in this version? → A: Only the Spec Kit orchestrate playbook; any other identity is rejected.
- Q: Where should parked human answers and resume context be stored? → A: On the existing Hermes task record; Spec Kit files stay in the worktree; no second database.

## User Scenarios & Testing *(mandatory)*

Hermes owns task selection, isolated worktrees, human decisions, validation,
Git safety, and pull requests. The selected harness owns agent execution and
the Spec Kit playbook. This feature moves the complete Spec Kit orchestration
flow into Pi while keeping the boundary between Hermes and a harness small,
generic, and replaceable.

### User Story 1 - Run the full Spec Kit playbook in Pi (Priority: P1)

An operator starts a real-style task in Hermes. Hermes prepares the isolated
task worktree and starts one Pi harness run. Pi runs the complete Spec Kit
playbook in the required order: specify, clarify when questions are needed,
plan, tasks, analyze only when the plan requires it, and implement/converge
until the work converges or becomes stuck. Pi writes the native Spec Kit
artifacts into the task worktree as it progresses.

**Why this priority**: The main value of the feature is removing Spec Kit
stage execution from Hermes while preserving one inspectable, end-to-end path.

**Independent Test**: Start a disposable task through the Hermes entry point
with a fixture Pi runtime and model. Verify that one isolated worktree
contains the native Spec Kit files, the playbook follows the required order,
and no Hermes-owned Spec Kit stage call is made.

**Acceptance Scenarios**:

1. **Given** an eligible task and a prepared feature worktree, **When** Hermes
   starts the Pi harness, **Then** Pi runs the full Spec Kit playbook and writes
   native specification, plan, task, and related artifacts only below that
   worktree.
2. **Given** the plan says analysis is needed, **When** Pi reaches that point,
   **Then** it runs analysis before implementation; when analysis is not
   needed, **Then** it proceeds directly to implementation.
3. **Given** implementation and convergence do not yet agree that the work is
   complete, **When** Pi continues the playbook, **Then** it alternates
   implementation and convergence until the work converges or the harness
   reports that it is stuck.
4. **Given** a task run, **When** the harness finishes, **Then** Pi has not
   pushed a branch, opened or updated a pull request, merged, deployed, or
   modified AiNative.

---

### User Story 2 - Start one generic harness run and receive one result (Priority: P1)

Hermes starts work using a framework-neutral harness request. The request
identifies the task, isolated worktree, selected playbook, execution limits,
and a named model profile reference. Hermes does not send plan, tasks,
implement, or converge as separate lifecycle calls. The harness adapter maps
that request to Pi and returns one normalized result.

**Why this priority**: A single stable boundary prevents Hermes from becoming
coupled to Pi or from growing a second Spec Kit state machine.

**Independent Test**: Send a valid start request through a fixture adapter and
verify that Pi receives the mapped task and model profile, that the adapter
returns one normalized result, and that no Pi-specific type or model name is
visible in the generic request or result.

**Acceptance Scenarios**:

1. **Given** a valid task, project, worktree, playbook identity, model profile
   reference, and safety limits, **When** Hermes starts work, **Then** the
   adapter starts exactly one harness run for that work attempt.
2. **Given** a harness run, **When** it ends, **Then** Hermes receives exactly
   one result with one of `completed`, `failed`, `needs_human`, or `stuck`,
   along with a safe reason and the next action when one exists.
3. **Given** a request to run a Spec Kit stage directly, **When** Hermes
   receives it, **Then** the request is rejected because stage sequencing is
   owned by the harness, not exposed as a Hermes API.
4. **Given** a recoverable failure, **When** Hermes retries, **Then** it
   starts a new whole harness run with diagnostic context rather than calling
   one Spec Kit stage itself.

---

### User Story 3 - Park and resume human decisions through Hermes (Priority: P1)

When Pi needs a person, it stops and returns a `needs_human` result. Hermes
shows the questions, records the task decision, and resumes the harness with
the answer. If the operator chooses skip, Hermes records the assumptions and
choice report, then asks for one continuation confirmation before Pi proceeds
to plan. Pi never chats with the operator directly.

**Why this priority**: Human authority and consequential decisions must remain
in the control plane even though execution moves to Pi.

**Independent Test**: Run fixtures that pause during specify/clarify and during
implementation. Verify the result is parked in Hermes, the recorded answer is
passed on resume, no later stage runs while parked, and one continue
confirmation is required after skip or clarification.

**Acceptance Scenarios**:

1. **Given** that specify or clarify produces consequential questions, **When**
   Pi reaches those questions, **Then** it returns `needs_human` with the
   questions and next action, and Hermes parks the task without starting plan.
2. **Given** the operator chooses skip, **When** Hermes handles the skip,
   **Then** Hermes self-answers the queued specify/clarify questions using
   documented assumptions, shows a choice report, and asks exactly one
   continuation confirmation before plan.
3. **Given** a human answer or continuation decision, **When** Hermes resumes
   the task, **Then** the harness receives the answer as resume context and
   continues its own playbook at the correct point.
4. **Given** the same stuck point has failed three times, **When** the third
   attempt ends, **Then** Hermes parks the task for a human and does not start
   a fourth automatic attempt.

---

### User Story 4 - Validate and publish only after the harness completes (Priority: P1)

After Pi reports that its playbook completed, Hermes runs the existing project
validation path. Harness completion is not a publish signal. A validation
failure follows the existing Hermes recovery rules and uses another whole
 harness run when workspace changes are needed. Only a validation pass reaches
the existing GitHub commit, feature-branch push, and pull-request workflow.

**Why this priority**: Keeping validation and publication in Hermes preserves
the existing safety boundary and prevents a harness from claiming completed
work as reviewed or published.

**Independent Test**: Drive fixture runs through successful completion,
validation failure, recovery, and validation pass. Verify no harness or
pre-validation path performs GitHub operations, and verify the existing
publish path runs only after validation passes.

**Acceptance Scenarios**:

1. **Given** a `completed` harness result, **When** Hermes receives it, **Then**
   Hermes validates the worktree using the existing project checks before any
   commit, push, or pull-request operation.
2. **Given** validation fails and workspace changes are needed, **When**
   Hermes recovers, **Then** it starts another whole harness run with the
   validation and diagnostic context; Hermes does not call Pi's implement
   stage directly.
3. **Given** validation passes, **When** Hermes publishes, **Then** it reuses
   the existing feature-branch and pull-request workflow and keeps merge,
   approval, deployment, and protected-branch writes unavailable to the
   harness.
4. **Given** the harness reports `failed`, `needs_human`, or `stuck`, **When**
   Hermes receives that result, **Then** validation and publishing do not run
   until the existing failure or human-decision rules allow a new attempt.

---

### User Story 5 - Remove the old Hermes Spec Kit stage machine (Priority: P1)

A maintainer can inspect the live Hermes path and find one generic harness
run, not a second path that sequences discovery, Spec Kit plan, tasks,
planning-complete, and implementation inside Hermes. The old stage machine is
deleted or disabled so it cannot run beside the Pi path.

**Why this priority**: Leaving the old path available would create two
competing Spec Kit machines and make behavior depend on which entry point was
selected.

**Independent Test**: Run the live-style task proof and inspect the available
Hermes execution entry points. Verify no Hermes command or fallback can invoke
Spec Kit stages individually, while existing workspace, validation, and
GitHub behavior remains reachable after a completed harness run.

**Acceptance Scenarios**:

1. **Given** the Pi harness is configured, **When** Hermes starts a task,
   **Then** it starts the generic harness boundary and never sequences
   `scout → plan → tasks → PLANNING_COMPLETE → implement` itself.
2. **Given** an old planning or implementation entry point is requested,
   **When** Hermes handles the request, **Then** it rejects it or starts the
   generic harness path and never runs the legacy stage machine as a fallback.
   There is no disable switch that can revive the removed path.
3. **Given** the existing AiNative tree, **When** this feature is delivered,
   **Then** no AiNative agent, methodology file, or project file is copied,
   modified, or added to support the harness.
4. **Given** a task already mid-way through the old Spec Kit short path,
   **When** this feature ships, **Then** Hermes parks it for a human with a
   clear reason and does not finish it on the removed machine or auto-rewrite
   its history.

### Edge Cases

- A task is already mid-way through the old Hermes Spec Kit short path when
  this feature ships: Hermes parks it for a human with a clear reason. It does
  not finish that work on the old machine and does not auto-rewrite history.
- The Pi runtime or adapter is unavailable, mismatched, or cannot start:
  Hermes returns a visible `failed` result before work begins and does not
  fall back to the removed stage machine.
- A start request has no timeout: Hermes rejects it before the harness starts.
- A harness run exceeds its timeout: the run stops and returns `failed`. It
  MUST NOT be treated as `completed`.
- A start request names a playbook other than Spec Kit orchestrate: Hermes
  rejects it. This version does not start a second playbook.
- The generic start request is incomplete, points outside the prepared
  worktree, names a protected branch, or contains a secret: Hermes rejects it
  before the harness starts.
- A model profile reference is missing or cannot be mapped by Pi: the run
  fails visibly without putting a provider name or model slug into the
  generic contract.
- Pi returns malformed output, an unknown status, unsafe artifact paths, or
  secret-bearing metadata: Hermes rejects the result and does not validate or
  publish it.
- Pi asks more than one human question batch: Hermes parks and resumes the
  whole run; it does not turn each question into a Hermes Spec Kit stage.
- A clarified or skipped run is resumed after a process restart: Hermes
  reloads the recorded decision and resume context without losing the native
  worktree artifacts.
- The worktree contains partial native artifacts after a crash: Hermes keeps
  them available for inspection and only resumes or restarts through the
  whole-run harness boundary.
- The harness tries to push, merge, open a pull request, deploy, write the
  default branch, write AiNative, or write another task's worktree: the
  operation is refused and the run cannot become `completed` from it.
- Validation fails after a completed playbook: existing Hermes validation and
  recovery rules decide whether to retry, park, or block; the harness does not
  publish a partial result.
- A later harness implementation is added: Hermes can select it through the
  same generic boundary without adding another Spec Kit stage machine.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hermes MUST provide one framework-neutral harness start boundary
  for a single task work attempt. The boundary MUST accept task identity,
  task description and context, isolated worktree location, repository
  context, playbook identity, execution constraints including a required
  wall-clock timeout, and a named model profile reference. A start request
  without a timeout MUST be rejected before the harness starts. When the
  timeout expires, the result MUST be `failed` (not `completed`) and that
  attempt MUST count toward the three whole-run retries.
- **FR-002**: The generic request and result MUST NOT contain Pi SDK types,
  Pi-specific client objects, Cursor model slugs, or a script of Spec Kit
  stages. Pi-specific translation MUST remain inside the Pi adapter.
- **FR-003**: Hermes MUST start one harness loop per work attempt. It MUST NOT
  expose separate Hermes lifecycle calls for specify, clarify, plan, tasks,
  analyze, implement, or converge.
- **FR-004**: The first adapter MUST map a valid generic request to Pi SDK and
  the Pi Spec Kit playbook without requiring Hermes orchestration changes for
  Pi-specific execution details.
- **FR-005**: Pi MUST run the full Spec Kit playbook in this order: specify,
  clarify questions when needed, one continue confirmation before plan, plan,
  tasks, analyze only when the plan requires it, and implement/converge until
  converged or stuck.
- **FR-006**: Pi MUST write native Spec Kit artifacts, including the
  specification, plan, and task list when those stages run, under the current
  task worktree. The artifacts MUST remain inspectable after the run and MUST
  not be replaced with a second Hermes plan or task database.
- **FR-007**: When Pi needs a human, it MUST stop and return `needs_human`
  with safe questions and a next action. Pi MUST NOT chat with the operator,
  answer consequential questions on its own, or bypass Hermes human authority.
- **FR-008**: When skip is active, Hermes MUST self-answer the specify/clarify
  questions using recorded assumptions, show a choice report, and require one
  continuation confirmation before the playbook proceeds to plan. Skip MUST
  not skip plan, tasks, analyze, implement, or converge.
- **FR-009**: Hermes MUST persist parked questions, skip/continue answers, and
  whole-run retry diagnostics on the existing Hermes task record. Spec Kit
  files MUST remain in the task worktree. Hermes MUST NOT add a second
  database to store resume context.
- **FR-010**: The normalized harness result MUST use exactly one of
  `completed`, `failed`, `needs_human`, or `stuck`, and MUST include a safe
  reason, worktree-relative native artifact paths when present, produced
  changes when present, logs or output reference when available, whether a
  whole-run retry is reasonable, and the next action or questions when needed.
- **FR-011**: Hermes MUST validate every harness request and result at the
  boundary.   It MUST reject missing identity, missing timeout, unknown playbook
  identity, invalid worktree or branch, paths that escape the worktree,
  unknown status, provider/model leakage, secret-bearing content, and
  fabricated or unreadable artifact paths.
- **FR-012**: The harness MUST write only inside the current task worktree on
  its feature branch. It MUST NOT write the enrolled project root, Hermes
  control-plane state, AiNative, another task worktree, or a protected/default
  branch.
- **FR-013**: The harness MUST NOT push, merge, open or update a pull request,
  deploy, approve as a human, or cancel unrelated work. Hermes remains the
  only owner of GitHub publication after validation.
- **FR-014**: Hermes MUST treat `completed` as playbook completion only. It
  MUST run the existing project validation path after completion and MUST
  reach the existing commit, feature-branch push, and pull-request path only
  after validation passes.
- **FR-015**: Validation recovery that needs workspace changes MUST start a
  new whole harness run with diagnostic context. Hermes MUST NOT call an
  individual Spec Kit stage or revive the removed Hermes stage machine.
- **FR-016**: Hermes MUST keep only orchestration-level states for harness
  execution, human parking, validation, publication, completion, failure, and
  stuck work. It MUST NOT add Hermes states or checkpoints for specify,
  clarify, plan, tasks, analyze, implement, or converge.
- **FR-017**: Hermes MUST retry a recoverable stuck point no more than three
  whole harness attempts. After the third failed attempt at the same stuck
  point, Hermes MUST park the task for a human.
- **FR-018**: Model selection MUST use a named profile reference that Hermes
  can pass generically and Pi can map independently. Hermes MUST NOT require
  or store Cursor model slugs, Pi client settings, or hardcoded provider names
  as part of the generic harness contract.
- **FR-019**: The old Hermes Spec Kit stage machine MUST be unwired and
  deleted from the live path so no command, fallback, or recovery path can
  sequence discovery, Spec Kit stages, `PLANNING_COMPLETE`, and
  implementation. Checks MAY remain only to prove that path is gone. Tasks
  that were mid-flight on that path MUST be parked for a human; they MUST
  NOT complete on the removed machine and MUST NOT auto-start Pi.
- **FR-020**: The implementation MUST preserve existing workspace isolation,
  Git safety, project validation, Kanban, messaging, and GitHub pull-request
  behavior. It MUST NOT modify AiNative or add a second task database,
  queue, event stream, or control plane.
- **FR-021**: Focused offline checks MUST prove the real-style path from task
  start through the generic contract, Pi adapter, native Spec Kit artifacts,
  human parking/resume, Hermes validation, and the existing pull-request
  workflow. Checks MUST use disposable worktrees and stand-ins rather than
  live GitHub, production repositories, or live credentials.
- **FR-022**: Operator documentation and version history MUST describe the
  generic harness boundary, Pi model-profile configuration, human
  question/skip/continue behavior, native artifact locations, validation and
  publication ownership, fixture checks, and credentials that remain outside
  the repository.
- **FR-023**: In this version Hermes MUST accept only the Spec Kit orchestrate
  playbook identity. Any other playbook identity MUST fail before the harness
  starts.

### Key Entities

- **Harness start request**: The framework-neutral description of one task
  attempt, including task, project, worktree, playbook, required timeout,
  model profile reference, safety limits, and optional resume context.
- **Harness result**: The normalized outcome of one harness loop, including
  status, reason, safe artifact paths, changes, output reference, retry
  guidance, questions, and next action.
- **Pi adapter**: The translation boundary that maps the generic request to
  Pi SDK and maps Pi's completion back to the generic result.
- **Spec Kit playbook**: The harness-owned ordered method of specifying,
  clarifying, planning, task creation, conditional analysis,
  implementation, and convergence.
- **Named model profile**: A provider-neutral configuration reference that Pi
  resolves to its own model and runtime settings.
- **Task worktree**: The isolated mutable feature-branch copy where the
  harness may read and write.
- **Human resume decision**: A recorded answer, skip assumption, or continue
  confirmation that Hermes passes back to a parked harness run.
- **Work attempt**: One Hermes start-to-result boundary invocation; retries
  create another whole attempt rather than another Hermes stage.

## Out of Scope

- A second harness implementation.
- A Hermes `/speckit-orchestrate` command or any Hermes-owned Spec Kit stage
  machine.
- Separate Hermes lifecycle APIs for specify, clarify, plan, tasks, analyze,
  implement, or converge.
- Rebuilding Telegram, Kanban, workspace management, validation, GitHub, or
  pull-request behavior already owned by Hermes.
- A live event stream; v1 uses one run, one normalized result, and
  `needs_human` when required.
- Modifying, copying, or installing agents or methodology into AiNative.
- A second task database, queue, control plane, or concurrent worker system.
- Hardcoding Cursor model slugs or Pi SDK details into Hermes configuration.
- Push, merge, deployment, protected/default-branch writes, or pull-request
  creation by the harness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful end-to-end fixture runs, Hermes starts
  exactly one generic harness run for the work attempt and receives exactly
  one normalized result.
- **SC-002**: In 100% of successful playbook fixtures, the observed stage
  order is specify, clarify/continue as needed, plan, tasks, optional
  analyze, implement/converge, with no stage skipped except the conditional
  analyze stage.
- **SC-003**: In 100% of successful playbook fixtures, native Spec Kit files
  are written below the isolated task worktree, and zero writes occur to
  AiNative, the enrolled project root, Hermes control-plane state, or a
  sibling worktree.
- **SC-004**: In 100% of question, skip, and continue fixtures, Pi does not
  chat with the operator, Hermes records the human decision, and the resumed
  run continues with that decision.
- **SC-005**: In 100% of repeated stuck-point fixtures, the third failed
  whole-run attempt parks for a human and zero fourth automatic attempts run.
- **SC-006**: In 100% of completed-playbook fixtures, Hermes runs validation
  before publication; in 100% of validation-failure fixtures, no branch push
  or pull-request operation occurs before a validation pass.
- **SC-007**: In 100% of validation-pass fixtures, the existing Hermes
  publication path produces the established pull-request result without any
  publication call from Pi.
- **SC-008**: In 100% of contract fixtures, generic request and result data
  contain no Pi SDK types, Cursor model slugs, private reasoning, tokens, or
  secrets.
- **SC-009**: In 100% of live-style fixtures, no Hermes path can invoke the
  removed `scout → plan → tasks → PLANNING_COMPLETE → implement` machine
  beside the generic harness path.
- **SC-010**: All focused fixture checks and existing project checks pass
  without a live GitHub account, production repository, or live model
  credentials.
- **SC-011**: An operator can locate the native Spec Kit artifacts, understand
  the human-decision and retry boundaries, configure a named model profile,
  and run the fixture proof from the delivered documentation in under ten
  minutes.

## Assumptions

- Pi SDK is the only execution harness delivered in this version. The generic
  boundary is provider-neutral so a future harness can be added as another
  adapter without changing Hermes orchestration.
- The current task worktree is prepared and isolated by Hermes before the
  harness starts. The harness does not create a second workspace.
- The Spec Kit playbook is implemented in Pi and follows the stage order and
  stop rules of the global `speckit-orchestrate` skill, without copying Cursor
  Task types, Cursor model slugs, or Cursor session rules.
- Clarify questions are a human gate. After clarification or skip, Hermes
  provides one continue confirmation before plan; routine implementation does
  not require another approval.
- Pi may retain its own internal execution state, but Hermes receives only
  the normalized boundary result and safe resume information.
- Native Spec Kit files such as `spec.md`, `plan.md`, and `tasks.md` are the
  source of truth and remain in the task worktree for inspection and later
  Hermes validation.
- A harness `completed` result means the Pi playbook ended successfully; it
  does not mean validation passed, a commit was published, or a pull request
  exists.
- Existing Hermes validation, bounded recovery, Git safety, project registry,
  task board, messaging, and GitHub publication paths remain authoritative.
- Whole-run recovery may start another harness attempt with diagnostics, but
  Hermes never resumes by calling one Spec Kit stage directly.
- The first proof uses disposable fixtures, a stand-in Pi runtime/model,
  temporary worktrees, and simulated GitHub behavior. No production project,
  live credentials, or live AiNative writes are needed.
- Configuration uses named model profile references. Pi owns the mapping to
  its model/provider settings, and secrets remain outside git.
- The existing project version-history convention continues, with a
  semver/changelog entry for the delivered implementation.
- V1 starts only the Spec Kit orchestrate playbook. Unknown playbook
  identities fail before start rather than mapping to a second method.
- Wall-clock timeout is required on the start request. Missing timeout is
  rejected before start. An expired timeout yields `failed` and counts as
  one whole-run attempt.
- Parked human and retry context lives on the existing Hermes task record;
  native Spec Kit files stay in the worktree.
- Mid-flight legacy Spec Kit short-path tasks are parked for a human when
  this feature ships. The live old path is deleted, not left behind a flag.

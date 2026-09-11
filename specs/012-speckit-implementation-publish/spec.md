# Feature Specification: Spec Kit Implementation and Publish

**Feature Branch**: `012-speckit-implementation-publish`

**Created**: 2026-09-07

**Status**: Superseded as the live implementation path (kept for history)

> **Live path:** Do not continue from `PLANNING_COMPLETE` through a Hermes
> Spec Kit `implement` step. Pi owns specify → plan → tasks → implement.
> Hermes still validates and opens the pull request after Pi completes.
> See `013-harness-adapter-pi` and `014-live-harness-gaps`. Do not keep
> the old path as a fallback.

**Input**: User description: "Wire the next Hermes Kanban slice from scratch/implimentation.md Phase 9: use the existing external-framework contract to run GitHub Spec Kit implement after the native plan and task files have been created in the isolated task worktree, then continue through the existing validation/recovery and GitHub publish paths. Do not copy a builder into live AiNative. Keep one active framework, isolated worktrees, builder-never-publish, and distinguish PLANNING_COMPLETE from PIV-complete."

## Clarifications

### Session 2026-09-07

- Q: If a task already finished planning (`PLANNING_COMPLETE`) and the work slot is free, should this new slice automatically start building from those saved plan files? → A: Yes. Any valid saved plan continues into build the next time Hermes picks that task (named task or next-ready). Invalid or incomplete handoffs still fail closed.
- Q: After that continued build passes the project’s checks, should Hermes also open or update the pull request, the same way a brand-new run would? → A: Yes. After checks pass, publish the feature branch and open or update the pull request using the existing GitHub step.

## User Scenarios & Testing *(mandatory)*

The prior live slice runs AiNative `scout`, then the one pinned GitHub Spec Kit provider creates its native plan and task-list files in the isolated task worktree and records `PLANNING_COMPLETE`. That planning checkpoint is not a completed build: no implementation, validation, or GitHub publish has run. This slice extends the same provider boundary with Spec Kit `implement`, then reuses Hermes's existing validation/recovery and orchestrator-owned GitHub publish behavior.

Live AiNative remains a read-only methodology. It is expected not to contain `specs-planner` or `builder`. The task worktree, native Spec Kit paths, configured Hermes model service, existing recovery state machine, existing GitHub host, and existing notification seam remain authoritative.

### User Story 1 - Implement from native Spec Kit artifacts (Priority: P1)

An operator starts an eligible live task. Hermes performs the existing discovery and Spec Kit planning steps, then passes the validated native plan and task-list paths from that same isolated worktree into Spec Kit `implement`. The implementation step uses the active pinned Spec Kit provider and Hermes's configured model service. It edits only the task worktree and feature branch, and never publishes a branch or pull request.

When the implementation succeeds, Hermes continues to validation without asking for routine plan approval. The operator does not paste plan text, install a framework per project, or provide a copied builder agent.

**Why this priority**: A plan and task list have no operational value until the selected framework can safely apply them in the isolated task worktree.

**Independent Test**: Use a disposable project, a scout-only AiNative fixture, a pinned Spec Kit runtime fixture, and a stand-in model. Verify call order `scout → plan → tasks → implement`, verify the implement context contains the native plan/task paths, verify files change only in the task worktree, and verify no AiNative `builder` lookup or publish call occurs.

**Acceptance Scenarios**:

1. **Given** an eligible task, a matching active Spec Kit runtime, and a prepared isolated worktree, **When** planning produces valid native plan and task files, **Then** Hermes invokes Spec Kit `implement` with those exact paths, the same provider identity and framework revision, and the configured Hermes model assignment.
2. **Given** a successful implementation request, **When** the provider writes code or project files, **Then** every write remains below the current task worktree on its feature branch; the enrolled project root, AiNative, runtime source, control-plane state, and sibling worktrees remain unchanged.
3. **Given** live AiNative without `specs-planner` or `builder`, **When** the live workflow reaches implementation, **Then** Hermes does not look up either missing role and does not copy either role into AiNative.
4. **Given** a successful implementation, **When** the step returns, **Then** Hermes proceeds to the existing validation path with the native plan/task handoff preserved; it does not create `PLAN.md`, `TASKS.md`, a second task store, or a second planning workspace.
5. **Given** implementation asks a consequential question, **When** the provider returns questions, **Then** Hermes parks at its existing human-decision state with the questions and next action, performs no validation or publish, and resumes the implement step only after a listed decision.

---

### User Story 2 - Validate the implementation and recover safely (Priority: P1)

After Spec Kit implementation, Hermes runs the project's existing validation checks through the existing validation/tester path. A validation pass marks the work PIV-complete, but it does not itself publish or merge anything. A validation failure follows the existing bounded classification and recovery rules. Any live recovery that needs to change the worktree uses the active Spec Kit `implement` lifecycle with the diagnostic and validation context; it never falls back to an AiNative builder.

The implementation, diagnosis, debug, and validation steps share the same task identity, feature branch, worktree, native artifact paths, and execution record. The enrolled project and methodology remain untouched.

**Why this priority**: Validation and recovery are already control-plane behavior. Reusing them prevents a new implementation-specific failure machine from bypassing established safety and human-decision rules.

**Independent Test**: Run fixtures where checks pass, fail once and recover, fail repeatedly, cannot start, or ask a question. Confirm the existing pass/retry/block/decision outcomes, confirm recovery edits use Spec Kit implement, and confirm no GitHub operation runs before validation passes.

**Acceptance Scenarios**:

1. **Given** Spec Kit implementation succeeds, **When** the existing validation checks pass, **Then** Hermes records validation as passed and enters the existing GitHub publish step; it does not treat the earlier planning checkpoint as PIV-complete.
2. **Given** validation fails in a way the existing recovery rules classify as retryable, **When** recovery runs, **Then** Hermes preserves the existing bounded diagnosis → implementation-fix → re-validation order, with the implementation-fix request routed through Spec Kit `implement` and no AiNative builder lookup.
3. **Given** validation fails as transient or non-retryable, **When** the existing recovery rules handle it, **Then** Hermes follows their existing validation-only retry or blocked outcome, does not invent a new retry loop, and does not publish.
4. **Given** validation or recovery asks a consequential question, **When** the question is returned, **Then** Hermes uses the existing human-decision state and resume behavior; it does not answer the question or publish partial work.
5. **Given** implementation, recovery, or validation fails before a validation pass, **When** the workflow returns, **Then** the result is the existing failure, parked, or blocked outcome and the remote has received zero feature-branch publishes for that run.

---

### User Story 3 - Publish only after validation through the existing GitHub path (Priority: P1)

Once validation has passed, Hermes uses the existing orchestrator-owned GitHub sequence: ensure a new commit only when needed, publish the task feature branch, and create or update one pull request against the project's default branch. This includes a continued run that started from a previously saved valid `PLANNING_COMPLETE` handoff; it does not stop at a local build. The existing pull-request identity, body, retry, protected-branch, no-merge, no-deploy, and existing `pr_created` notification behavior remain in force.

Spec Kit implement, recovery, and validation never publish directly. A human still owns review, merge, and deployment.

**Why this priority**: The live task must end as a reviewable pull request rather than stopping at a local implementation or a planning-only checkpoint.

**Independent Test**: Use the existing simulated GitHub host with a disposable worktree and stand-in model. Drive the live-style path through implementation and validation, then verify one feature-branch publish, one pull-request identity with number and URL, the existing notice, no protected-branch write, no merge, and no deployment.

**Acceptance Scenarios**:

1. **Given** a live-style task whose Spec Kit implementation and existing validation pass (including a run continued from a prior valid `PLANNING_COMPLETE` handoff), **When** the workflow reaches its terminal success, **Then** the orchestrator returns `PR_CREATED` with the existing pull-request number and HTML URL, and the pull request targets the configured default branch from the task feature branch.
2. **Given** an implementation step or recovery debug step, **When** it completes with local changes or a local commit, **Then** the remote remains unchanged until the orchestrator's post-validation GitHub step.
3. **Given** a pull request already exists for the task feature branch, **When** a later successful publish occurs, **Then** the existing pull request is updated according to the current GitHub contract and no duplicate pull request is opened.
4. **Given** any request to merge, approve as a human, deploy, amend, force-push, or push a protected/default branch, **When** it is made through this workflow, **Then** the existing boundary rejects it and the run cannot become `PR_CREATED` from that request.
5. **Given** a successful `PR_CREATED` outcome, **When** notices are enabled, **Then** Hermes uses the existing pull-request-created event and connected channel; it does not add another bot or event kind.

---

### User Story 4 - Preserve the planning handoff and control-plane safety (Priority: P1)

An operator or maintainer can inspect a completed run and see that native Spec Kit plan and task files were consumed by implementation, validation, and publish without being replaced by Hermes aliases. `PLANNING_COMPLETE` remains a distinct planning checkpoint and is never reported as PIV-complete or pull-request-created.

For the full live workflow in this feature, the checkpoint is recorded after native plan/task generation and before implementation while the single-task slot remains occupied. The workflow then continues in the same worktree. Existing planning-only records or recovered runs may continue only when their provider identity, native paths, worktree, and runtime revision validate; Hermes must fail closed rather than inventing artifacts or silently rerun a different provider.

**Why this priority**: The main safety risk is confusing “a plan exists” with “the task was built and checked.” Explicit handoff semantics prevent duplicate planning, premature slot release, and unsafe publishing.

**Independent Test**: Seed a valid planning handoff with native artifact paths and a matching worktree/runtime fixture. Resume the implementation path and confirm no plan/tasks call is repeated, the same worktree is used, and the final record distinguishes the planning checkpoint from PIV completion and `PR_CREATED`. Corrupt or escape one path and confirm the run fails closed before implementation.

**Acceptance Scenarios**:

1. **Given** valid native plan and task paths inside the current task worktree, **When** implementation starts, **Then** it consumes those paths unchanged and records them for later validation and operational inspection.
2. **Given** the full live workflow has reached its planning checkpoint, **When** Spec Kit implement is available, **Then** `PLANNING_COMPLETE` is a recorded intermediate outcome, not the final success state, not PIV-complete, and not a reason to free the active slot before implementation starts.
3. **Given** a prior valid `PLANNING_COMPLETE` handoff (including a run that previously freed the slot), **When** Hermes next picks that task by name or as next-ready, **Then** it occupies the slot, uses the saved native paths, does not rerun plan or tasks, and continues into Spec Kit `implement`. Incomplete or invalid handoffs fail closed under the existing recovery rules.
4. **Given** a native artifact is missing, unreadable, non-regular, secret-bearing, or outside the task worktree, **When** Hermes validates the handoff, **Then** it returns a visible failure or blocked result with no guessed path and performs zero implementation, validation, or publish calls.
5. **Given** any live execution, **When** a reviewer compares source locations and operational records, **Then** AiNative remains read-only, the enrolled project remains unchanged, no second task store exists, and secrets/transcripts/private reasoning are absent.

---

### Edge Cases

- **Missing native handoff**: A missing, unreadable, non-regular, secret-bearing, or worktree-escaping plan/task path fails closed. Hermes does not substitute `PLAN.md`, `TASKS.md`, model prose, or a newly invented path.
- **Provider drift**: A changed active provider, pinned version, runtime revision, or setup marker fails before the implement model call. Hermes does not silently select another framework.
- **Unsupported lifecycle step**: `specify` and `clarify` remain outside this feature. They must return the existing visible unsupported outcome; only `implement` is added to the previously supported `plan` and `tasks` steps.
- **Implementation model failure**: A model/runtime failure follows the existing failure or human-decision rules. No validation or publish occurs after a partial implementation result.
- **Partial implementation files**: Partial files remain in the isolated worktree for existing recovery/inspection rules; Hermes does not copy them into the enrolled root or claim success without the provider's explicit successful result.
- **Implementation asks a question**: Preserve questions and next action, park through the existing decision protocol, and do not answer or publish automatically.
- **Validation failure**: Use the existing `TRANSIENT`, `RETRYABLE`, `NON_RETRYABLE`, and human-decision behavior. Do not retry inside the adapter.
- **Recovery debug**: A retryable validation failure may invoke Spec Kit `implement` again with diagnostic context. A transient or non-retryable failure must not invoke it when the existing rules say not to.
- **Publish failure**: Existing GitHub authentication/permission and transient publish rules apply. Publish failure does not start diagnosis or alter the implementation retry budget.
- **Planning checkpoint state**: `PLANNING_COMPLETE` is never accepted as PIV-complete, `COMPLETED`, or `PR_CREATED`. A full run must not release the slot at that checkpoint.
- **Old or malformed overlay**: Existing overlay compatibility remains required. A prior planning record with invalid identity, paths, or worktree is rejected rather than resumed with guessed state.
- **Protected branches and side effects**: Default/protected branch writes, merge, approval-as-human, deploy, AiNative writes, second workspaces, second task stores, and secret-bearing records remain forbidden.
- **No live credentials in checks**: Contract checks use disposable worktrees, fixtures, simulated hosting, and stand-in model/messaging seams. They do not require GitHub, Telegram, production repositories, or live model credentials.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The active external-framework boundary MUST retain exactly one pinned GitHub Spec Kit provider and matching preinstalled runtime for every external step. It MUST reject zero or multiple active providers, unsupported providers, missing pins, missing runtimes, and runtime identity/revision mismatches before any implement model call.
- **FR-002**: The live workflow MUST sequence AiNative discovery (`scout`), Spec Kit `plan`, Spec Kit `tasks`, a recorded `PLANNING_COMPLETE` checkpoint, Spec Kit `implement`, existing validation/recovery, and the existing orchestrator-owned GitHub publish path in that order.
- **FR-003**: `PLANNING_COMPLETE` MUST remain distinct from PIV-complete, `COMPLETED`, and `PR_CREATED`. In a new full run it MUST be an intermediate checkpoint that MUST NOT release the active task slot or stop before implementation. A prior valid `PLANNING_COMPLETE` record whose slot is already free MUST remain eligible: the next named or next-ready selection of that task MUST occupy the slot and continue into Spec Kit `implement` without treating planning as terminal success.
- **FR-004**: The stable external-framework context/result contract MUST support `implement` while preserving the existing provider identity, version, runtime revision, task/project/worktree, configured model assignment, discovery summary, prior artifact paths, questions, next action, and normalized status fields. `specify` and `clarify` remain unexecuted in this feature.
- **FR-005**: Spec Kit `implement` MUST consume the validated native plan and task-list paths from the current isolated worktree. It MUST preserve those native files as the source of truth and MUST NOT create or require Hermes `PLAN.md` or `TASKS.md` aliases, a second canonical task list, or a second task store.
- **FR-006**: Spec Kit `implement` MUST use Hermes's existing configured model service and the active provider assignment. It MUST NOT launch Cursor, Claude Code, a framework-owned model runtime, a separate planning API, a per-project install, a per-run download, or a hardcoded model/provider.
- **FR-007**: All Spec Kit implementation and recovery writes MUST remain inside the already prepared task worktree on the task feature branch. The adapter MUST NOT create a second workspace or write the enrolled project root, AiNative, runtime source, control-plane repository/state, or another task's worktree.
- **FR-008**: Live implementation MUST NOT look up, require, copy, add, or modify an AiNative `builder` or `specs-planner` agent. AiNative remains a separate read-only provider for its existing roles, including discovery and any existing validation/diagnosis role.
- **FR-009**: A successful implementation result MUST be explicit and validated before validation begins. Missing artifacts, invalid status, unsafe paths, secret-bearing output, provider drift, model failure, or framework questions MUST flow through existing failure, blocked, or human-decision handling; Hermes MUST NOT fabricate success or silently continue.
- **FR-010**: Existing validation MUST run after successful Spec Kit implementation using the project's declared checks and the existing validation/tester seam. Validation MUST receive the native plan/task handoff and implementation context without requiring Hermes plan aliases.
- **FR-011**: Existing validation recovery MUST remain the only recovery state machine. Retryable failures MUST preserve the existing bounded diagnosis → implementation-fix → re-validation behavior, with live implementation fixes routed through Spec Kit `implement`; transient and non-retryable outcomes MUST retain their existing validation-only or blocked behavior.
- **FR-012**: Spec Kit implement, validation, diagnosis, and recovery MUST NOT publish, open/update a pull request, merge, approve as a human, deploy, amend, or force-push. Local commits on the isolated feature branch remain allowed under existing workspace rules.
- **FR-013**: After validation passes, the orchestrator MUST reuse the existing GitHub publish contract: enforce the task feature branch, ensure a history-preserving commit only when needed, publish only that branch, create or update one pull request against the configured default branch, require pull-request number and HTML URL, and emit the existing pull-request-created event. This MUST apply equally to a brand-new full run and to a continued run that began from a prior valid `PLANNING_COMPLETE` handoff.
- **FR-014**: GitHub publish MUST remain unreachable before validation pass. Publish failures MUST follow the existing GitHub classification and retry/block behavior and MUST NOT enter validation diagnosis/debug or silently mark the run successful.
- **FR-015**: The existing control-plane record MUST preserve the native plan/task paths, provider identity/version, framework revision, implementation outcome, validation outcome, recovery state, and final pull-request identity without storing model transcripts, private reasoning, tokens, or secrets. The human-readable task body MUST remain unchanged.
- **FR-016**: A valid recovered or previously completed planning handoff MUST use the same isolated worktree and native plan/task files without rerunning completed plan/tasks steps. Hermes MUST continue such a task into implementation the next time it is selected (named task or next-ready), then through existing validation and, on a validation pass, the existing GitHub publish path. Invalid or incomplete handoffs MUST fail closed before implementation. Existing overlay/restart and single-slot rules remain authoritative.
- **FR-017**: Focused offline checks MUST prove provider validation, scout-before-framework order, native path consumption, no planner/builder lookup, same-worktree implementation, implementation-question handling, validation/recovery behavior, no publish before pass, existing GitHub publish/notice behavior, `PLANNING_COMPLETE` semantics, slot protection, path/secret rejection, and no forbidden writes. They MUST use disposable fixtures and stand-ins rather than live GitHub, Telegram, model credentials, production repositories, or writable live AiNative.
- **FR-018**: All existing tests and style checks MUST remain passing. Delivery documentation MUST describe the active provider, implement handoff, native artifact locations, validation/recovery behavior, publish boundary, fixture commands, and external credentials that remain outside the repository.
- **FR-019**: The implementation contract MUST remain extensible for future external-framework lifecycle steps and future providers without copying their agents into AiNative or changing the stable context/result boundary. This feature executes only the existing planning steps plus `implement`.

### Key Entities *(include if feature involves data)*

- **Native implementation handoff**: The validated Spec Kit plan and task-list paths, plus provider identity and framework revision, carried from planning into implementation and later validation.
- **External implement result**: The normalized provider result describing implementation success, failure, blocked questions, summary, and safe workspace artifacts without private reasoning or secrets.
- **Planning checkpoint**: The recorded `PLANNING_COMPLETE` outcome after native plan/tasks exist. It is not PIV-complete and not `PR_CREATED`. A new full run keeps the slot occupied through this checkpoint. A previously freed valid checkpoint stays eligible until Hermes next selects that task, continues into implementation, and, after validation passes, uses the same GitHub publish path as a brand-new run.
- **PIV-complete run**: A run whose implementation (including any allowed recovery fixes) exists in the isolated feature worktree and whose existing project validation has passed, before GitHub publish.
- **Published feature run**: A PIV-complete run whose orchestrator-owned GitHub operation produced `PR_CREATED` with the existing pull-request number and HTML URL.
- **Isolated task worktree**: The one prepared mutable copy used by discovery handoff, Spec Kit implementation, validation, recovery, commit, and feature-branch publish.
- **Active external framework**: The one pinned GitHub Spec Kit identity used consistently for plan, tasks, implementation, and implementation fixes.

### Out of Scope

- Copying or creating a builder, planner, or other external-framework agent in live AiNative.
- Adding a second worker, scheduler, orchestrator, Kanban board, task database, or recovery machine.
- Supporting a second active framework or switching providers per lifecycle step.
- Implementing Spec Kit `specify` or `clarify` in this slice.
- Rebuilding validation, recovery, GitHub, Telegram, workspace, project-registry, or restart-persistence systems already delivered by prior features.
- Automatic merge, approval-as-human, deployment, protected/default-branch writes, force-push, or production changes.
- Live GitHub/Telegram/model proof as the focused automated test gate; disposable or explicitly named non-critical runtime proof remains subject to existing safeguards.
- Storing credentials, model transcripts, private reasoning, or secrets in project files, native artifacts, overlays, notices, pull requests, or version history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful live-style fixture runs, the observed provider/model order is `scout → plan → tasks → implement → validation`, with no AiNative `specs-planner` or `builder` lookup.
- **SC-002**: In 100% of successful implementation fixtures, the implement request receives the exact validated native plan/task paths from the same isolated worktree, and zero runs create `PLAN.md`, `TASKS.md`, a second task store, or a second workspace as a substitute.
- **SC-003**: In 100% of implementation and recovery fixtures, all file changes remain inside the task worktree and feature branch; the enrolled project root, AiNative, runtime source, control-plane state, and sibling worktrees remain byte-for-byte unchanged.
- **SC-004**: In 100% of validation-pass fixtures, `PLANNING_COMPLETE` is not returned as PIV-complete, the slot is not freed before implementation/validation, and the existing publish path returns `PR_CREATED` with a pull-request number and HTML URL.
- **SC-005**: In 100% of validation-failure fixtures, existing classification and bounded recovery behavior is preserved; retryable recovery uses Spec Kit implement for workspace fixes, while transient/non-retryable outcomes do not run an unauthorized implement or publish step.
- **SC-006**: In 100% of runs that do not reach validation pass, feature-branch publish and pull-request create/update occur zero times. In 100% of successful publish runs, no merge, deploy, protected/default-branch push, amend, force-push, or builder publish occurs.
- **SC-007**: In 100% of valid handoff-resume fixtures, completed native plan/tasks are consumed without rerunning those lifecycle steps; invalid or escaping handoffs cause zero implementation, validation, or publish calls.
- **SC-008**: All focused offline checks pass without GitHub, Telegram, live model credentials, production repositories, or writable live AiNative, and all pre-existing tests and style checks remain passing.
- **SC-009**: An operator can follow the delivered documentation to configure the single provider, locate native plan/task/implementation artifacts, understand the planning checkpoint and PIV-complete distinction, run fixture checks, and identify credentials that remain outside git.

## Assumptions

- **This is the Phase 9 implementation slice.** The prior external-framework planning adapter, existing validation/recovery, existing GitHub publish, Telegram notice, workspace, overlay, and restart seams are treated as delivered and are reused rather than redesigned.
- **Spec Kit is the only active provider.** The stable boundary remains provider-neutral, but this feature supports only the already pinned `github-spec-kit` runtime and the same identity for plan, tasks, implement, and implementation fixes.
- **The live full workflow continues automatically.** When implementation is enabled, Hermes records the planning checkpoint and continues in the same prepared worktree; it does not require a routine user approval or a second planning workspace. Any later valid `PLANNING_COMPLETE` task, including one whose slot was already freed by the prior planning-only slice, continues into build the next time Hermes picks that task, and after checks pass it uses the same pull-request publish step as a brand-new run.
- **`PLANNING_COMPLETE` is a checkpoint, not PIV-complete.** The prior planning-only behavior freed the slot because implementation was not wired. This feature changes the full live path so the checkpoint cannot be treated as terminal success before implementation and validation.
- **Native artifacts are the handoff.** Spec Kit owns the plan/task names and locations. Hermes validates and passes their paths; it does not rename, copy, summarize into competing canonical files, or write `kanban.db`.
- **Implementation output is provider-native.** The adapter may materialize provider-owned implementation files and local commits in the task worktree, but it does not publish. The existing workspace and Git safety rules remain authoritative.
- **Recovery reuses existing rules.** Validation classification, attempt limits, human decisions, overlay persistence, and GitHub publish retry behavior are unchanged. The only provider-specific change is that any live workspace-fixing implementation/debug call uses Spec Kit `implement`.
- **Prior planning handoffs continue when valid.** A saved native result is consumed if its provider identity, revision, paths, and worktree pass the existing trust checks. Invalid or incomplete saved state fails closed; Hermes does not guess or silently switch providers. Selection may be a named task id or next-ready among eligible cards.
- **Fixture checks remain hermetic.** Tests use temporary repositories/worktrees, scout-only AiNative and pinned-runtime fixtures, stand-in model/hosting/messaging seams, and no production credentials.
- **One active task remains the V0 limit.** A new-run planning checkpoint holds the slot until an existing terminal outcome such as `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. A previously freed valid `PLANNING_COMPLETE` task occupies the slot again only when Hermes next selects it.
- **Credentials remain outside git.** Existing model-provider, GitHub SSH/CLI, and Telegram credentials are supplied by runtime configuration and are not stored in source, specs, artifacts, overlays, notices, pull requests, or changelog entries.
- **Continued saved plans publish after a validation pass.** Stopping at a local build, or waiting for a separate publish command, is out of scope for this slice.

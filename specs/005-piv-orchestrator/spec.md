# Feature Specification: PIV Orchestrator

**Feature Branch**: `005-piv-orchestrator`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "based on scratch/implimentation.md, detect next step and specify it"

## Clarifications

### Session 2026-08-31

- Q: When discovery or planning returns a non-empty questions list (plain strings, as today’s agent run already does), how should those strings become the parked decision’s options so resume can accept a listed choice? → A: Questions list items are the mutually exclusive options, labeled A, B, C in list order; the step’s summary is the decision text; resume accepts that letter.
- Q: After the operator resumes a parked workflow with a listed option letter, does the orchestrator re-run the parked discovery or planning step with that answer, or skip it and start the next step? → A: Re-run the parked step with the chosen letter and option text in context; auto-continue if that re-run has an empty questions list. A new questions list parks again (same attempt).
- Q: When the caller asks for the next ready task, which projects’ tasks are in the selection pool? → A: The one existing board, across all enrolled eligible projects. Skip ineligible projects and unmet dependencies. Named start still requires a project identity.
- Q: What happens when next-ready selection finds no ready task (empty board, all unmet dependencies, missing or invalid priority, or only ineligible projects)? → A: Fail at the boundary with a visible no-ready-task error. Do not invent a task or start discovery. Missing or invalid priority is not ready; a named start with missing or invalid priority also fails at the boundary.
- Q: Do start and resume wait until the workflow parks or finishes, or do they return immediately while work continues in the background? → A: They wait until COMPLETED, FAILED, or HUMAN_DECISION_REQUIRED, then return that execution record. State is still recorded after every step. This phase has no background worker.

## User Scenarios & Testing *(mandatory)*

Hermes is the operational control plane. Phase 1 can enroll a project, load that project’s instructions, and prepare an isolated working copy. Phase 2 can run one methodology agent once and return a structured result. Nothing yet *chains* those runs into the standard workflow.

This feature is Phase 3: a caller can start the plan → implement → validate workflow for **one** task on **one** eligible project. The orchestrator is the operator of that chain. It claims (or is given) a task from the existing task board, prepares the isolated working copy if needed, runs discovery then planning then implementation then validation, records explicit execution state after every step, and stops when validation succeeds — or when a step fails, or when a consequential human decision is required.

There is **no** plan-approval gate. After a successful plan with no open questions, implementation starts automatically. The only pause is an unresolved consequential decision. Failures in this phase stop the chain; diagnosis, retry, and debug are the next phase. Publishing a branch, opening a pull request, and sending messages are later phases.

The people who benefit are operators of the control plane: they can say “run this task” (or “run the next ready task”) and watch a single explicit state instead of stitching four separate agent runs by hand. Methodology remains read-only. Project knowledge remains in the project. The existing task board remains the source of truth for *what* the work is. Execution state belongs to the control plane, not to the human-readable task body.

### User Story 1 - Run discovery through validation for one task (Priority: P1)

An operator asks: “run the standard workflow for task 123 on project A.” The orchestrator resolves that the project is eligible, loads the task’s human-readable fields from the existing task board (problem, expected result, platform, acceptance criteria, owner, reviewer, priority, optional technical notes, optional dependencies), and ensures an isolated working copy exists for that task.

It then runs, in order:

1. **Discovery** — gather project and task context for planning. Discovery is not required to write the eight-section plan.
2. **Planning** — produce the eight-section plan artifact inside the isolated working copy. The plan from this step is passed into implementation automatically.
3. **Implementation** — change only that isolated copy (local commit on the work branch is allowed). The enrolled project location is unchanged. Nothing is published.
4. **Validation** — run the project’s own declared checks and set pass / fail / blocked from those outcomes.

Each step is one existing agent run (discovery, planning, implementation, validation roles). The orchestrator supplies the task fields and previous-step outputs so the caller does not re-type them. The start call waits until the workflow is completed, failed, or parked, then returns that execution record. It does not wait for a human to approve the plan. When validation passes, the workflow is **PIV-complete** for this phase: implementation exists, validation passed, and the isolated copy is on the task work branch. A pull request is not required for this phase to succeed.

**Why this priority**: Without an automatic chain, Phase 2 is four manual calls. This is the remaining gap after agent execution, and the first vertical slice of the control plane’s actual job.

**Independent Test**: Enroll a fixture project with declared validation checks. Put a fixture task on the board (identity `123`, problem, expected result, acceptance criteria, priority). Start the workflow. Confirm discovery runs, then planning writes the eight-section plan in the isolated copy, then implementation changes only that copy, then validation runs the project’s own checks and reports pass. Confirm no plan-approval stop occurred. Confirm the enrolled project location is unchanged and nothing was published.

**Acceptance Scenarios**:

1. **Given** an eligible fixture project, a fixture task `123` on the board with problem, expected result, and acceptance criteria, and a fixture methodology that lists the four default role agents, **When** the caller starts the workflow for that project and task, **Then** the start call waits until the chain finishes, the orchestrator prepares (or reuses a valid) isolated working copy, runs discovery, then planning, then implementation, then validation, and the returned record is `COMPLETED` after validation passes.
2. **Given** the same setup, **When** planning succeeds with an empty questions list, **Then** implementation starts without a human approval step and the plan artifact from planning is supplied to implementation unchanged.
3. **Given** a successful workflow, **When** the caller inspects the enrolled project location and the isolated copy, **Then** file changes and any local commit exist only in the isolated copy on the task work branch; the enrolled location is unchanged; 0 branches were published.
4. **Given** a successful validation step, **When** the caller reads the workflow result, **Then** validation status is pass derived from the project’s declared checks (not from summary prose), and the workflow is PIV-complete without a pull request existing.
5. **Given** no prepared working copy for that task at start, **When** the caller starts the workflow, **Then** the orchestrator prepares one before the first agent run (it MUST NOT fail with missing-workspace when prepare would succeed).
6. **Given** a fixture task on the board, **When** the workflow runs, **Then** discovery and later steps receive that task’s problem, expected result, acceptance criteria, and priority from the board — the orchestrator MUST NOT invent those fields and MUST NOT require the caller to paste the task body on the start call.

---

### User Story 2 - Record explicit execution state and stop on failure (Priority: P1)

Every workflow has a machine-readable execution state. Reviewers can answer: what is happening, which phase is current, what just finished, what happens next, and whether the run is queued, running, validating, completed, failed, or waiting for a human. That answer MUST NOT be inferred from free-form notes.

States this phase uses:

| State | Meaning |
| ----- | ------- |
| `QUEUED` | Accepted, not yet running a phase |
| `RUNNING` | A non-validation phase is in progress (discovery, planning, or implementation) |
| `VALIDATING` | The validation phase is in progress |
| `COMPLETED` | Validation passed; PIV is done for this phase |
| `FAILED` | A phase ended in failure and this phase will not retry |
| `HUMAN_DECISION_REQUIRED` | A consequential decision is parked (see User Story 3) |

The record also includes: workflow name (the standard plan → implement → validate workflow), current phase, current worker (the agent that is running or last ran), attempt count (always `1` in this phase), workspace location and branch, validation status, blockers list (empty when none), next action, and pull-request slot (empty in this phase).

The human-readable task on the board keeps owner, reviewer, priority, and the problem / expected-result / acceptance-criteria body. The orchestrator MUST NOT write changing execution details into that body.

When a phase returns `failure`, the workflow transitions to `FAILED` and stops. It MUST NOT diagnose, retry, or start a debug loop. When a phase returns `blocked` without questions, the workflow also stops as `FAILED` (blocked-without-decision is not a retry). Recovery is the next phase.

**Why this priority**: A later recovery phase and a human looking at the board cannot act on a paragraph of text. State has to exist before retries or pull requests.

**Independent Test**: Run a fixture workflow that succeeds and confirm the recorded states include queued, running through discovery/planning/implementation, validating, then completed, with current phase and next action updating at each step. Run a fixture whose validation checks fail and confirm the workflow is `FAILED`, validation status is fail, next action is not “retry”, and implementation is not re-run.

**Acceptance Scenarios**:

1. **Given** a workflow that has been started, **When** the caller reads the record returned by start or resume (or the operational record written after each step), **Then** the state is one of `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` — never inferred only from summary prose.
2. **Given** a workflow in progress, **When** the caller reads the record, **Then** it includes workflow name, current phase (`discovery` / `planning` / `implementation` / `validation`), current worker, attempt count `1`, workspace location, work branch, validation status (pending until validation runs), blockers, next action, and an empty pull-request slot.
3. **Given** a successful planning step with empty questions, **When** the orchestrator advances, **Then** current phase becomes implementation and next action is implement — not “wait for plan approval”.
4. **Given** a validation step whose project checks fail, **When** that step finishes, **Then** execution state is `FAILED`, validation status is fail, the workflow does not start diagnosis or a second implementation, and attempt count remains `1`.
5. **Given** any state change, **When** the caller reads the human-readable task body, **Then** owner, reviewer, priority, and the problem / expected-result / acceptance-criteria text are unchanged by that state change.

---

### User Story 3 - Pause for a human decision, resume, and run only one task (Priority: P2)

If discovery or planning reports a non-empty questions list, the orchestrator treats those strings as one decision’s mutually exclusive options. It parks the workflow at `HUMAN_DECISION_REQUIRED` and does **not** start the next phase. It records a decision brief: project, task, current phase, the decision required (that step’s summary), why it matters, the options labeled `A`, `B`, `C` in list order, a recommended option when the agent supplied one, and how to reply (the option letter).

This phase does not send a message. Parking is enough. The start call has already returned the parked record. The operator resumes by supplying the chosen option letter. Resume re-runs the parked discovery or planning step with that letter and option text available, then continues automatically if that re-run has an empty questions list — without a separate plan-approval step. Resume also waits until completed, failed, or parked again.

V0 runs **one** workflow at a time. A second start is refused while another workflow is `QUEUED`, `RUNNING`, `VALIDATING`, or `HUMAN_DECISION_REQUIRED`. A parked decision occupies the slot so behavior stays deterministic.

The caller may also ask for the next ready task instead of naming one. Selection looks at the one existing board across all enrolled eligible projects. Ready means: the task’s project is eligible, priority is one of `P0`/`P1`/`P2`/`P3`, and dependencies are satisfied. Then highest priority (`P0` then `P1` then `P2` then `P3`), then oldest created. Ineligible projects, unmet dependencies, and missing or invalid priority are skipped. If nothing is ready, the call fails at the boundary. A named start whose dependencies are unmet, or whose priority is missing or invalid, fails at the boundary and does not begin discovery.

**Why this priority**: Automatic implementation after planning is the product rule, but silent guessing on architecture or product questions is not. One-at-a-time scheduling is the V0 reliability rule. Both are required for the chain to be safe, and both can be proven on fixtures without messaging or hosting.

**Independent Test**: Start a fixture whose planning result includes a questions list of two strings; confirm the start call returns `HUMAN_DECISION_REQUIRED` with those strings labeled `A` and `B`, implementation files are unchanged after planning, and a second start is refused. Resume with `A`; confirm planning re-runs with `A` available, then the chain continues through validation. Ask for the next ready task from a board with a blocked-dependency task, an older lower-priority ready task on one eligible project, and a newer higher-priority ready task on another eligible project; confirm the higher-priority ready task is chosen. Ask again on a board with nothing ready and confirm a visible no-ready-task failure.

**Acceptance Scenarios**:

1. **Given** a planning (or discovery) step whose structured result has a non-empty questions list, **When** that step finishes, **Then** execution state is `HUMAN_DECISION_REQUIRED`, the next phase has not started, and a decision brief exists with project, task, phase, decision text equal to that step’s summary, why it matters, options labeled `A`, `B`, `C` in list order, recommended option when supplied, and how to reply (the option letter).
2. **Given** a parked workflow whose options are `A` and `B`, **When** the operator resumes with listed letter `A` (case-insensitive), **Then** the workflow leaves `HUMAN_DECISION_REQUIRED`, re-runs the parked phase with letter `A` and that option’s text available, does not wait for plan approval, and if that re-run has an empty questions list continues to the next phase. Resume waits until completed, failed, or parked again.
3. **Given** a parked workflow, **When** the operator resumes with an option that was not listed (unknown letter, option text instead of the letter, or empty), **Then** the resume fails at the boundary, the workflow stays parked, and the isolated copy is not published.
4. **Given** a workflow in `QUEUED`, `RUNNING`, `VALIDATING`, or `HUMAN_DECISION_REQUIRED`, **When** the caller starts another workflow (named or next-ready), **Then** the start is refused and the first workflow is unchanged.
5. **Given** a board with one task whose dependencies are unmet and two ready tasks on eligible projects (higher priority newer, lower priority older), **When** the caller asks for the next ready task and no workflow is active, **Then** the unmet-dependency task is skipped and the higher-priority ready task is started, even if it belongs to a different eligible project than the older one.
6. **Given** a named start whose dependencies are unmet, **When** the caller starts that task, **Then** the call fails at the boundary and discovery does not run.
7. **Given** no ready tasks (empty board, only unmet dependencies, only ineligible projects, or only missing/invalid priority), **When** the caller asks for the next ready task and no workflow is active, **Then** the call fails at the boundary with a visible no-ready-task error and no agent run starts.
8. **Given** a parked planning step that is resumed with `A`, **When** that planning re-run again returns a non-empty questions list, **Then** execution state is `HUMAN_DECISION_REQUIRED` again, attempt count remains `1`, and implementation has not started.

---

### Edge Cases

- **Empty questions**: Valid. The workflow MUST continue to the next phase. Risks listed in the plan are not a pause by themselves.
- **Questions are options**: A non-empty questions list is one decision. List items are mutually exclusive options labeled `A`, `B`, `C` in order. The step’s summary is the decision text. Resume accepts that letter (case-insensitive). The orchestrator MUST NOT invent extra options or treat the strings as independent sequential decisions.
- **Resume re-runs the parked step**: Resume MUST re-run the parked discovery or planning role with the chosen letter and option text available to that step and later steps. It MUST NOT skip ahead to implementation while the parked plan still has unanswered questions. If the re-run’s questions list is empty, the chain auto-continues. If the re-run returns questions, park again. If the re-run returns `failure` or `blocked` without questions, go `FAILED`. Attempt count stays `1`.
- **Start and resume wait**: `run_workflow`, `run_next_workflow`, and `resume_workflow` MUST wait until `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` and return that record. This phase MUST NOT start a background worker. State is still written after every step (`QUEUED` before the first agent run).
- **No ready task**: `run_next_workflow` MUST fail at the boundary with a visible no-ready-task error. It MUST NOT invent a task identity or start discovery.
- **Missing or invalid priority**: Not ready. Next-ready skips it. Named start fails at the boundary. Valid priorities are `P0`, `P1`, `P2`, `P3` only. The orchestrator MUST NOT invent a priority.
- **Ineligible project on next-ready**: Skip that task and keep scanning. Do not fail the whole selection unless nothing eligible and ready remains.
- **Blocked phase with questions**: Park at `HUMAN_DECISION_REQUIRED` (questions win). Blocked without questions is `FAILED` in this phase.
- **Missing working copy at start**: Orchestrator prepares it. Missing copy *during* a later step (deleted underfoot) fails visibly; this phase MUST NOT invent a second copy for the same task.
- **Dirty existing copy at start**: Prepare already refuses dirty reuse. Start fails with that visible error and MUST NOT discard the dirty files.
- **Ineligible project**: Unknown, disabled, or invalid-location project fails with the registry’s existing distinct errors. The orchestrator MUST NOT invent a project path.
- **Unknown or empty task identity**: Fail at the boundary. Path-like identities fail the same way the workspace manager already fails them.
- **Task not on the board**: Fail with a visible unknown-task error. The orchestrator MUST NOT invent problem / expected-result / acceptance-criteria text.
- **Planning success without the eight required sections**: MUST NOT be treated as success; the workflow MUST NOT start implementation.
- **Validation checks missing on the project**: Fail with the existing missing-project-configuration error rather than inventing checks.
- **Live methodology missing a mapped agent**: Same unknown-agent failure as a single execute. This phase MUST NOT add agents to methodology.
- **Resume when not parked**: Fail at the boundary. MUST NOT restart a completed or failed workflow as a side effect of resume.
- **Completed or failed slot**: A new start is allowed after `COMPLETED` or `FAILED`. This phase does not define retry-from-failed (that is recovery).
- **Attempt count**: Always `1` on records this phase writes. It MUST NOT increment on resume (resume is the same attempt, with an answer).
- **Protected work branch**: The work branch MUST NOT be `main`, `master`, or the project’s default branch. Publish remains 0.
- **Methodology writes**: Any workflow step that would change methodology MUST fail. Methodology stays read-only.
- **Secrets**: Model secrets and environment secrets MUST NOT appear on execution state, decision briefs, or summaries.
- **Host-specific paths**: Behavior MUST NOT depend on a developer’s home directory layout.
- **Editor absence**: MUST NOT fail the workflow.
- **Stand-in vs live model**: Checks inject a stand-in. Missing live credentials MUST fail a real configured run; they MUST NOT fail checks that injected a stand-in.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orchestrator MUST expose `run_workflow(project_id, task_id)` that runs the standard discovery → planning → implementation → validation chain for one eligible project and one task. It MUST load human-readable task fields from the existing task board rather than requiring those fields on the start call. It MUST wait until `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` and return that execution record. It MUST NOT create a second task board. A named start whose priority is missing or invalid MUST fail at the boundary before discovery.
- **FR-002**: The orchestrator MUST expose `run_next_workflow()` that selects one ready task from the one existing board across all enrolled eligible projects and then behaves as `run_workflow` for that task (using the task’s recorded project identity). Selection MUST skip ineligible projects, unmet dependencies, and missing or invalid priority, then pick highest priority (`P0` > `P1` > `P2` > `P3`), then oldest created. If no ready task remains, the call MUST fail at the boundary with a visible no-ready-task error and MUST NOT invent a task. It MUST wait and return the same way as `run_workflow`.
- **FR-003**: Before the first agent run, the orchestrator MUST resolve an eligible project, load project context, load the task from the board, and prepare an isolated working copy when one is not already valid for that project and task. It MUST reuse the existing project, workspace, and agent-run operations rather than duplicating them. A named start whose dependencies are unmet MUST fail before discovery.
- **FR-004**: The chain MUST run in this order: discovery, planning, implementation, validation. Each step MUST be one existing role run (`discovery`, `planning`, `implementation`, `validation`). After a successful step with an empty questions list, the next step MUST start automatically. There MUST NOT be a plan-approval gate.
- **FR-005**: The orchestrator MUST pass previous-step outputs into later steps: discovery context into planning when present; the plan artifact into implementation and validation; validation is last. After resume, the chosen option letter and option text MUST be available to the re-run parked step and to later steps. It MUST NOT invent a plan or validation result that no step produced.
- **FR-006**: Every workflow MUST have an explicit execution state of `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED`. The record MUST include workflow name, current phase, current worker, attempt count, workspace location and branch, validation status, blockers, next action, and pull-request slot (empty in this phase). Status MUST NOT be determined only by reading summary prose. Start and resume MUST write `QUEUED` (or leave parked) before the first agent run of that call, then update the record after every step.
- **FR-007**: Execution state MUST live in the control plane’s operational record, not in the human-readable task body. The task body MUST keep problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, and priority without being overwritten by phase/status churn.
- **FR-008**: A phase result of `failure`, or `blocked` with an empty questions list, MUST set execution state to `FAILED` and MUST stop the chain. This phase MUST NOT diagnose, retry, debug, or increment attempt count.
- **FR-009**: A discovery or planning result with a non-empty questions list MUST set execution state to `HUMAN_DECISION_REQUIRED`, MUST record a decision brief (project, task, phase, decision required = that step’s summary, why it matters, options = the questions list labeled `A`, `B`, `C` in order, recommended option when supplied, how to reply = the option letter), and MUST NOT start the next phase. The questions strings ARE the options; the orchestrator MUST NOT parse them into a different shape or invent options. This phase MUST NOT send a message. The same rule applies to a re-run after resume.
- **FR-010**: The orchestrator MUST expose `resume_workflow(project_id, task_id, option)` that accepts a listed option letter (`A`, `B`, `C`, … matching list order, case-insensitive), re-runs the parked discovery or planning step with that letter and option text available, does not introduce a plan-approval gate, and waits until `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` before returning the execution record. An option that is not listed (unknown letter, the option’s text instead of its letter, or empty), or a resume when the workflow is not parked, MUST fail at the boundary.
- **FR-011**: At most one workflow MAY be `QUEUED`, `RUNNING`, `VALIDATING`, or `HUMAN_DECISION_REQUIRED` at a time. A second `run_workflow` or `run_next_workflow` MUST be refused while that slot is occupied. `COMPLETED` and `FAILED` MUST release the slot.
- **FR-012**: PIV-complete (`COMPLETED`) in this phase means: discovery and planning succeeded, implementation ran against the isolated copy, validation passed using the project’s declared checks, the work branch is the task feature branch, and nothing was published. A pull request MUST NOT be required.
- **FR-013**: Implementation file changes and any local commit MUST remain in the isolated working copy. The orchestrator MUST NOT publish, merge, deploy, write methodology, or change the enrolled project location.
- **FR-014**: Checks MAY inject a stand-in model service and a fixture task board. A live model service, live task gateway, and live hosting account MUST NOT be required to prove this phase.
- **FR-015**: `run_workflow` / `run_next_workflow` / `resume_workflow` are the trust boundary. Invalid project, task, workspace, mapping, active-slot conflict, no-ready-task, missing or invalid priority, or resume MUST fail there with a visible error. This phase MUST NOT run a background worker to advance the chain.

### Key Entities

- **Task (board record)**: Human-readable work item on the existing task board: identity, problem, expected result, platform, acceptance criteria, optional technical notes, optional dependencies, owner, reviewer, priority. Source of truth for *what* to do. Not the execution-state record.
- **Workflow run**: One plan → implement → validate execution for one project and one task, including the leading discovery step. Occupies the single V0 slot until completed, failed, or still parked.
- **Execution state**: Operational record of that run: explicit state, workflow name, current phase, current worker, attempt, workspace, validation, blockers, next action, pull-request slot. Control-plane owned.
- **Decision brief**: Parked human decision: project, task, phase, decision required (the parked step’s summary), why it matters, options (the questions list labeled `A`, `B`, `C` in list order), recommended option when supplied, how to reply (the option letter).
- **Ready task**: Board task whose recorded project is eligible, whose priority is `P0`/`P1`/`P2`/`P3`, and whose listed dependencies are satisfied — therefore eligible for `run_next_workflow` selection.
- **PIV-complete**: Validation has passed for this run. Hosting (push / pull request) is not part of this entity.

### Out of Scope

This specification covers chaining discovery → plan → implement → validate, explicit execution state, the human-decision pause/resume, and one-at-a-time selection from the existing task board. Explicitly deferred:

- Failure classification, bounded retry, diagnosis, debug loop (next phase)
- Re-running a `FAILED` workflow
- Git hosting: commit-to-remote, push, pull requests, merge
- SSH / credential forwarding for hosting
- Telegram / notifications (parking does not send a message)
- Container restart / interrupted-run recovery
- Concurrent execution of more than one workflow
- Learning / retrospectives / methodology-change proposals
- Adding agents to live methodology
- Installing an external planning framework into this control plane
- Editor-specific command files
- Critic / plan-reviewer as a required extra step
- `pr-reviewer`, `task-groomer`, `project-bootstrapper` as standard execution
- Debugger role
- Obsidian
- Automatic merge, production deploy, or protected-branch writes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an eligible fixture project and a fixture board task, a caller can complete discovery through validation on the first attempt with no plan-approval stop, and the start call returns `COMPLETED` after the project’s own checks pass.
- **SC-002**: 100% of successful planning steps with an empty questions list proceed to implementation automatically; 0% wait for plan approval.
- **SC-003**: 100% of discovery or planning steps with a non-empty questions list park at `HUMAN_DECISION_REQUIRED` and start 0 subsequent phases until a listed option letter is resumed. 100% of resumes re-run the parked step with that answer; 0% skip to implementation while that step still has unanswered questions.
- **SC-004**: 100% of phase failures stop the workflow at `FAILED` with attempt count `1`; 0% start diagnosis, retry, or debug in this phase.
- **SC-005**: 100% of overlapping starts are refused while a workflow is queued, running, validating, or parked; 100% of next-ready selections skip ineligible projects, unmet dependencies, and missing/invalid priority, then pick highest priority then oldest across eligible projects; 100% of empty next-ready calls fail at the boundary without starting an agent.
- **SC-006**: 100% of workflow file changes stay in the isolated copy on the task work branch; 0% of runs publish a branch, open a pull request, modify methodology, or rewrite the human-readable task body with execution churn.
- **SC-007**: A reviewer can complete seven contract checks — full chain to `COMPLETED`, auto-continue after planning, park on questions, resume with a listed letter (re-run parked step), fail validation without retry, refuse a second active workflow, select next ready by priority across eligible projects — and each check fails if that behavior breaks.

## Assumptions

- **This phase is orchestration only.** Methodology adapter, project registry, workspace manager, and single-run agent execution already exist. This feature adds the chain, execution state, human-decision pause/resume, and one-at-a-time selection. It does not start recovery, hosting, or messaging.
- **Existing task board.** The control plane already has a task board. This feature reads task fields from it (or from a fixture board in checks). It MUST NOT add a parallel task store. Checks MUST NOT require a live messaging gateway.
- **Task body format** matches the existing human-readable contract: problem, expected result, platform, acceptance criteria, optional technical notes, optional dependencies, plus owner, reviewer, and priority. Execution details do not belong in that body.
- **Caller may name a task or ask for next.** `run_workflow` is the named start (project plus task). `run_next_workflow` selects from the one board across eligible projects. Both occupy the same single slot. No ready task is a boundary failure, not an empty success.
- **Parked occupies the slot.** `HUMAN_DECISION_REQUIRED` counts as active so V0 stays one-task-at-a-time. The slot frees on `COMPLETED` or `FAILED`.
- **Empty questions means continue.** Only a non-empty questions list on discovery or planning is a consequential pause. That list is one decision’s mutually exclusive options, labeled `A`, `B`, `C` in order; the step’s summary is the decision text; resume is the matching letter. Plan risks without questions are not a pause. Implementation and validation questions in this phase are treated as failure-to-complete the chain (stop as `FAILED`) rather than a new decision protocol — those phases should not be asking product questions.
- **Resume re-runs the parked step.** The chosen letter and option text go into that discovery or planning re-run and later steps. Attempt stays `1`. A new questions list parks again. Retry-from-failure is out of scope.
- **Start and resume wait.** They return the execution record at `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED`. No background worker in this phase. How that record is stored on the host (native fields vs overlay) is a planning choice; there is still no second task table.
- **Valid priority is required to run.** Ready selection and named start both require `P0`/`P1`/`P2`/`P3`. Missing or invalid priority is not guessed.
- **Orchestrator prepares.** Unlike a single execute (which refuses a missing copy), the workflow start is allowed to prepare. Dirty-reuse refusal stays with prepare.
- **Local commit, no remote publish.** Implementation may leave a local commit on the work branch, as the executor already allows. This phase still publishes 0 times.
- **PIV-complete ≠ pull request.** Hosting is the next-but-one phase after recovery. `COMPLETED` here is validation passed.
- **Role mapping defaults** remain discovery → `scout`, planning → `specs-planner`, implementation → `builder`, validation → `tester`. Operators may remap in configuration. This phase does not add agents to methodology. Checks use a fixture tree that includes all four.
- **Stand-in model service and fixture board for checks.** Contract checks MUST NOT require a live model account, a live production project, a live hosting account, or a live messaging bot.
- **Workflow name** is the configured default (plan → implement → validate). Phases on the record are `discovery`, `planning`, `implementation`, `validation`.
- **Reuse existing operations.** The orchestrator MUST call existing eligible-project resolve, context load, prepare/inspect workspace, and role execute. It MUST NOT duplicate Git safety, methodology loading, or model assignment.
- **No second database.** Execution-state fields the host can already represent SHOULD fill those host fields. Fields the host cannot represent are returned on the workflow record. No new task table.
- **Trust boundary**: `run_workflow`, `run_next_workflow`, and `resume_workflow`. Invalid input fails there.
- **No new third-party libraries** without an explicit owner request.
- **Checks** live with the existing control-plane package. One set of checks must fail if the seven contract behaviors in SC-007 break.
- **Public operation names** (`run_workflow`, `run_next_workflow`, `resume_workflow`) are the agreed contract for this phase. Exact module layout inside the existing control-plane package is an implementation choice.
- **Implementation follows this spec**, then code; recovery, Git hosting, and messaging do not start until this feature’s checks pass and a later spec/plan asks for them.
- **Disposable fixture only.** Checks MUST NOT enroll a production repository. The owner names a non-critical real project later, when hosting end-to-end is required.

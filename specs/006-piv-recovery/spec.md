# Feature Specification: PIV Recovery

**Feature Branch**: `006-piv-recovery`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "Let's continue scratch/implimentation.md for next step" (Phase 4 — Recovery)

## Clarifications

### Session 2026-09-01

- Q: When validation finishes with a non-empty questions list, should the workflow park and wait for a letter reply, or still stop as failed the way the last phase did? → A: Park at `HUMAN_DECISION_REQUIRED`. Resume with a listed letter re-runs validation, then classifies that re-run.
- Q: When a run is blocked because the failure cannot be fixed by editing the workspace, should option B still try a recovery cycle, or only abandon with A? → A: B re-runs validation only when the last class was non-retryable; diagnosis and debug do not run. Retryable or transient blocks still get a full recovery cycle.
- Q: When the project’s declared checks cannot even start (missing command, cannot run), should the workflow block immediately for a human, or retry that as a temporary glitch? → A: Checks cannot start → `NON_RETRYABLE` → `BLOCKED` immediately. No automatic retries.

## User Scenarios & Testing *(mandatory)*

The control plane already chains discovery → planning → implementation → validation for one task, records explicit execution state, parks on discovery or planning questions, and **stops on failure without retry**. Attempt count stays at 1. That is enough to watch a happy path and a hard stop. It is not enough when the project’s own checks fail for a reason the workspace can still fix.

This feature is Phase 4: when **validation fails**, the orchestrator classifies the failure, and when the failure is recoverable it runs a bounded loop of **diagnosis → debug (fix in the isolated copy) → re-validate**. Transient execution errors re-run validation without a debug edit. After three recovery attempts, or when the failure is not recoverable by editing the workspace, the workflow enters **BLOCKED** and waits for a human. Parking still does not send a message. Publishing a branch, opening a pull request, and container restart recovery remain later phases.

The people who benefit are operators of the control plane: a failed check is no longer a dead end. The same start call that used to return `FAILED` on the first validation miss now either finishes after a bounded self-repair, or returns a blocked record a human can abandon or grant one more try. Methodology stays read-only. Project knowledge stays in the project. The existing task board stays the source of truth for *what* the work is. Execution state, retries, and blocked/escalation records belong to the control plane, not to the human-readable task body.

Discovery, planning, and original implementation failures without a validation outcome keep the previous phase’s stop-as-`FAILED` behavior. This feature **adds** classification, retry, debug, and blocked on top of the existing chain; it does not replace enrollment, workspace prepare, single agent runs, next-ready selection, or the discovery/planning decision protocol.

### User Story 1 - Recover from a validation failure and finish the chain (Priority: P1)

An operator starts the standard workflow for a fixture task. Implementation finishes. Validation runs the project’s own checks and they fail. Instead of stopping dead, the orchestrator records a retryable failure, runs diagnosis against the isolated copy (task, plan, what failed, attempt count), then runs a debug/fix step that may change only that copy, then re-runs the same project checks.

If validation then passes, the workflow is **PIV-complete** the same way as a first-attempt pass: implementation exists in the isolated copy, validation passed, the work branch is the task feature branch, nothing was published. The start call waits until that completed record is ready — recovery happens inside the same wait, not as a background worker.

Diagnosis is not a second validation: it must not treat “project checks passed” as its success criterion. Debug is allowed to edit the isolated copy and to leave a local commit on the work branch, under the same isolation rules as implementation. The enrolled project location, methodology, and any remote stay untouched.

**Why this priority**: The whole point of Phase 4 is that a check failure can be repaired in the workspace. Without this loop, the orchestrator still cannot finish a task whose first validation miss is fixable.

**Independent Test**: Enroll a fixture project whose declared checks fail once, then pass after the isolated copy is changed. Start the workflow. Confirm validation fails, diagnosis runs, debug changes only the isolated copy, validation runs again and passes, and the start call returns `COMPLETED`. Confirm the enrolled location is unchanged and nothing was published.

**Acceptance Scenarios**:

1. **Given** an eligible fixture project and a fixture task whose declared checks fail on the first validation and pass after a debug edit in the isolated copy, **When** the caller starts the workflow, **Then** the start call waits through diagnosis and debug, re-runs those same declared checks, and returns `COMPLETED` with validation status pass.
2. **Given** a retryable first validation failure, **When** recovery runs, **Then** diagnosis runs before debug, debug may change only the isolated copy (local commit allowed on the task work branch), and validation is run again using the project’s own declared checks — not invented generic checks and not inferred from diagnosis prose.
3. **Given** a successful recovery, **When** the caller inspects the enrolled project location and the isolated copy, **Then** file changes and any local commit exist only in the isolated copy on the task work branch; the enrolled location is unchanged; 0 branches were published; methodology is unchanged.
4. **Given** a diagnosis step, **When** it finishes successfully, **Then** a diagnostic report exists on the execution record (task, phase, attempt count, failure, what was attempted, current state, decision required if any) and the human-readable task body is unchanged.
5. **Given** no prepared working copy at start, **When** the caller starts a workflow that will recover, **Then** the orchestrator still prepares one before the first agent run, as the previous phase already requires.

---

### User Story 2 - Classify failures, bound retries, and block when recovery cannot continue (Priority: P1)

Every validation failure is classified before the orchestrator retries. It MUST NOT blindly re-run implementation. Classes:

| Class | Meaning | What happens |
| ----- | ------- | ------------ |
| `TRANSIENT` | The checks did not yield a real project-check failure (timeout, unavailable execution). | Re-run validation only. No diagnosis, no debug edit. Consumes one recovery attempt. |
| `RETRYABLE` | The project’s checks ran and failed (code/test failure the workspace can still fix). | Diagnosis → debug → re-validate. Consumes one recovery attempt. |
| `NON_RETRYABLE` | Recovery cannot fix this by editing the workspace (declared checks cannot start, missing configuration already past the boundary, authentication). | Do not diagnose or debug. Go `BLOCKED` immediately. Zero automatic retries. |
| `HUMAN_DECISION_REQUIRED` | A non-empty questions list (consequential choice). | Park with the existing decision protocol. Do not start debug. Attempt does not increment. |

The original discovery → planning → implementation → first validation is **attempt 1**. Each recovery cycle (either a transient re-validate or a diagnosis→debug→re-validate) increments attempt. The limit is **3 recovery attempts**. After the third recovery cycle still fails as retryable or transient, the workflow goes `BLOCKED` rather than starting a fourth. A `NON_RETRYABLE` validation outcome goes `BLOCKED` immediately, even on attempt 1.

States this phase adds (previous states remain):

| State | Meaning |
| ----- | ------- |
| `RETRYABLE_FAILURE` | A retryable or transient validation failure was accepted and a recovery cycle is starting or in progress |
| `BLOCKED` | Recovery cannot continue automatically; a human must abandon or grant one more try |

`FAILED` still means terminal, no automatic work, slot released — used when the operator abandons a blocked run, and for discovery / planning / original implementation failures that never produced a validation outcome (unchanged from the previous phase). `COMPLETED`, `QUEUED`, `RUNNING`, `VALIDATING`, and `HUMAN_DECISION_REQUIRED` keep their previous meanings. `PR_CREATED` is not used.

The record’s attempt count is no longer frozen at 1: it is `1` on the original chain and increases when a recovery cycle starts. Resume of a parked decision does **not** increment attempt. The start call waits until `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. `RETRYABLE_FAILURE` is recorded in history while recovery runs; it is not a wait-return by itself because there is still no background worker.

**Why this priority**: Unbounded retry can loop forever. Retrying a missing-configuration failure wastes attempts. Without `BLOCKED`, the operator cannot tell “needs a human” from “dead.” Classification and the limit are the safety net for the loop in User Story 1.

**Independent Test**: Inject a fixture whose checks fail every time. Confirm three recovery cycles run (diagnosis+debug+validate or transient re-validate as classified), then `BLOCKED`, attempt reflects original plus those cycles, and implementation is not started a fourth recovery time. Inject a non-retryable validation (declared checks cannot start, no questions) and confirm `BLOCKED` with zero diagnosis, zero debug, and zero automatic retries. Inject a check failure that the next debug fixes and confirm attempt incremented once and `COMPLETED`.

**Acceptance Scenarios**:

1. **Given** a validation status of fail (declared checks ran and failed), **When** classification runs, **Then** the class is `RETRYABLE` and, if recovery attempts used are under 3, the workflow records `RETRYABLE_FAILURE` and starts diagnosis then debug then validation.
2. **Given** a validation outcome classified `TRANSIENT`, **When** recovery attempts used are under 3, **Then** the orchestrator re-runs validation only (no diagnosis, no debug edit), increments attempt, and consumes one recovery attempt.
3. **Given** a validation outcome classified `NON_RETRYABLE` (declared checks cannot start, or blocked without questions and not marked transient), **When** that step finishes, **Then** execution state is `BLOCKED`, diagnosis and debug did not run, no automatic recovery cycle ran, and the slot is still occupied.
4. **Given** three recovery cycles that each end in retryable or transient validation failure, **When** the third cycle’s validation still fails that way, **Then** execution state is `BLOCKED`, a fourth recovery cycle does not start, and attempt equals 4 (original 1 + 3 recoveries).
5. **Given** a retryable failure on the first validation that debug then fixes, **When** the start call returns, **Then** attempt is 2, state is `COMPLETED`, and only one recovery cycle ran.
6. **Given** a discovery or planning failure, or an original implementation failure with no validation outcome (including a non-empty questions list on original implementation), **When** that step finishes, **Then** execution state is `FAILED` as in the previous phase — this feature MUST NOT start diagnosis for those steps.
7. **Given** a validation step whose structured result has a non-empty questions list, **When** that step finishes, **Then** execution state is `HUMAN_DECISION_REQUIRED` (not `FAILED`, not `BLOCKED`, not a recovery cycle). Resume with a listed letter re-runs validation; the re-run is then classified. Attempt does not increment on that resume.
8. **Given** any recovery state change, **When** the caller reads the human-readable task body, **Then** owner, reviewer, priority, and the problem / expected-result / acceptance-criteria text are unchanged.

---

### User Story 3 - Escalate when blocked, resume, and keep one-task-at-a-time (Priority: P2)

When the workflow is `BLOCKED`, the orchestrator records an escalation brief using the existing human-decision shape: project, task, current phase, the decision required, why it matters, options, a recommended option, and how to reply (the option letter). Parking is enough; this phase does not send a message.

Blocked options are always:

- **A**: Abandon — transition to `FAILED`, release the slot.
- **B**: Retry once — grant exactly one more recovery cycle. Shape depends on last class: diagnosis → debug → validate when retryable; validate-only when transient; **validate-only when non-retryable** (no diagnosis, no debug edit). After that validation, classify the new outcome (pass completes; questions park; remaining budget may start automatic recovery if the new class is retryable or transient; still non-retryable → `BLOCKED` again). This grant does not reset the three-attempt budget.

The operator resumes with the listed letter, same call as a parked planning question. Invalid letters fail at the boundary and leave the workflow blocked. `A`/`B` are case-insensitive.

If diagnosis, debug, or validation returns a non-empty questions list, the workflow parks at `HUMAN_DECISION_REQUIRED` with those strings labeled `A`, `B`, `C` in list order (existing protocol). This **replaces** the previous phase’s rule that validation questions were `FAILED`. Original implementation questions still `FAILED` (no validation outcome). Resume re-runs that parked step with the chosen letter and option text, then continues (recovery cycle or classification) if questions are empty. Attempt does not increment on that resume. A new questions list parks again.

`BLOCKED` and `RETRYABLE_FAILURE` occupy the single V0 slot together with `QUEUED`, `RUNNING`, `VALIDATING`, and `HUMAN_DECISION_REQUIRED`. A second start is refused while any of those are active. `COMPLETED` and `FAILED` release the slot. After abandon (`FAILED`), a new start for the same task is allowed (new run, attempt 1). Resume when not parked and not blocked fails at the boundary.

Next-ready selection, named start, dependency and priority rules, and one-board-across-eligible-projects behavior are unchanged.

**Why this priority**: Recovery without a human off-ramp either loops or dumps the task. The previous phase already proved letter-resume for planning questions; blocked escalation must reuse that protocol so operators are not taught a second reply language. Messaging is a later phase.

**Independent Test**: Drive a fixture to `BLOCKED` after three failed recoveries. Confirm a second start is refused and the escalation brief lists `A`/`B`. Resume `A` and confirm `FAILED` and a subsequent start is allowed. Drive another fixture to `BLOCKED` with last class retryable, resume `B`, and confirm one more diagnosis→debug→validate ran. Drive a fixture to `BLOCKED` with last class non-retryable, resume `B`, and confirm validation re-ran with zero diagnosis and zero debug. Park diagnosis on a questions list, resume with `A`, and confirm diagnosis re-ran with `A` and attempt did not increment. Park validation on a questions list, resume with a listed letter, and confirm validation re-ran then classified — not `FAILED` from the questions themselves.

**Acceptance Scenarios**:

1. **Given** a workflow in `BLOCKED`, **When** the caller reads the record, **Then** an escalation brief exists with project, task, phase, decision required, why it matters, options `A` (abandon) and `B` (retry once), a recommended option, and how to reply (the option letter). No message was sent.
2. **Given** a blocked workflow, **When** the operator resumes with `A` (case-insensitive), **Then** execution state is `FAILED`, the slot is released, the isolated copy is not published, and a later start is allowed.
3. **Given** a blocked workflow whose last class was retryable, **When** the operator resumes with `B`, **Then** the workflow leaves `BLOCKED`, runs exactly one recovery cycle (diagnosis then debug then validate), and either `COMPLETED`, `BLOCKED` again, `FAILED` (only if that cycle’s step is a non-validation hard failure), or `HUMAN_DECISION_REQUIRED`.
4. **Given** a blocked workflow whose last class was non-retryable, **When** the operator resumes with `B`, **Then** the workflow leaves `BLOCKED`, re-runs validation only, diagnosis and debug do not run, and the new validation outcome is classified (pass → `COMPLETED`; questions → park; still non-retryable → `BLOCKED` again).
5. **Given** a blocked workflow, **When** the operator resumes with an option that was not listed, **Then** the resume fails at the boundary, the workflow stays `BLOCKED`, and the isolated copy is not published.
6. **Given** a diagnosis, debug, or validation step whose structured result has a non-empty questions list, **When** that step finishes, **Then** execution state is `HUMAN_DECISION_REQUIRED`, the next recovery step has not started, attempt is unchanged, and resume with a listed letter re-runs that parked step (validation resume then classifies the re-run).
7. **Given** a workflow in `QUEUED`, `RUNNING`, `VALIDATING`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, or `BLOCKED`, **When** the caller starts another workflow, **Then** the start is refused and the first workflow is unchanged.
8. **Given** a parked or blocked workflow, **When** the operator resumes, **Then** resume waits until `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED` and returns that record.

---

### Edge Cases

- **Questions win**: A non-empty questions list on diagnosis, debug, or validation MUST park at `HUMAN_DECISION_REQUIRED` even if classification would otherwise retry or block. Discovery and planning questions keep the previous phase’s park/resume behavior. Original implementation questions still `FAILED`.
- **Validation questions**: Non-empty questions on a validation step MUST classify as `HUMAN_DECISION_REQUIRED` and park (do not start debug, do not `FAILED`). This replaces the previous phase’s validation-questions → `FAILED` rule. Resume re-runs validation with the chosen letter available, then classifies the re-run outcome.
- **Empty questions**: Valid. Recovery continues. Diagnostic risks without questions are not a pause by themselves.
- **Resume re-runs the parked step**: Same rule as the previous phase for discovery/planning, now also for diagnosis, debug, and validation parked on questions. Attempt does not increment on resume.
- **Blocked resume is not a parked step re-run**: `A` abandons. `B` grants one recovery cycle whose shape follows last class: full diagnosis→debug→validate when retryable; validate-only when transient or non-retryable. A retryable grant MUST NOT skip diagnosis. A non-retryable grant MUST NOT run diagnosis or debug.
- **Start and resume wait**: They MUST wait until `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. This phase MUST NOT start a background worker. `RETRYABLE_FAILURE` MUST still be written into history when a recovery cycle starts.
- **Attempt vs resume**: Attempt increments only when an automatic or operator-granted recovery cycle **starts**. It MUST NOT increment on decision resume, on abandon, or on a second start after `FAILED`.
- **Recovery budget**: At most 3 automatic recovery cycles after the first validation failure. Operator `B` from `BLOCKED` grants exactly one extra cycle even if the budget is exhausted. That extra cycle does not restore a full budget of 3.
- **Transient does not debug**: `TRANSIENT` MUST NOT run diagnosis or change the isolated copy. If the re-validate is still transient and budget remains, classify again. Three transients still `BLOCKED`.
- **Non-retryable does not consume the three as retries**: Declared checks that cannot start (missing command or cannot be executed) MUST classify as `NON_RETRYABLE` even if next action is `retry`. It goes `BLOCKED` immediately with recovery attempts used unchanged (attempt stays at the current value, typically 1 if this was the first validation). Zero automatic retries.
- **Diagnosis failure**: If diagnosis returns `failure` or `blocked` without questions, classify as `NON_RETRYABLE` and go `BLOCKED` (cannot repair without a diagnosis). Do not invent a diagnosis.
- **Debug failure without questions**: Consumes the current recovery cycle; re-validate MUST NOT be skipped into a fake pass. Treat as the cycle ending in failure: if budget remains, start another recovery from diagnosis; else `BLOCKED`.
- **Validation pass during recovery**: Immediate `COMPLETED`. Remaining budget is unused. PIV-complete still does not require a pull request.
- **Original implementation / discovery / planning failure**: `FAILED`, attempt stays 1, no classification into the recovery loop. This feature MUST NOT widen recovery to those steps.
- **Missing working copy during recovery**: Fail visibly (same as a later-step missing copy in the previous phase). MUST NOT invent a second copy for the same task. MUST NOT discard a dirty copy.
- **Ineligible project, unknown task, bad priority, unmet dependencies, no-ready-task, active slot**: Same boundary failures as the previous phase.
- **Planning success without eight sections**: Still MUST NOT start implementation (previous phase). Recovery does not repair a missing plan.
- **Live methodology missing a mapped agent**: Same unknown-agent failure. This phase MUST NOT add agents to methodology. Checks use a fixture tree that includes the agents diagnosis and debug will run.
- **Protected work branch**: Still forbidden. Publish remains 0. Merge and deploy remain forbidden.
- **Methodology writes**: Any recovery step that would change methodology MUST fail. Methodology stays read-only.
- **Secrets**: MUST NOT appear on execution state, diagnostic reports, escalation briefs, or summaries.
- **Host-specific paths**: Behavior MUST NOT depend on a developer’s home directory layout.
- **Editor absence**: MUST NOT fail recovery.
- **Stand-in vs live model**: Checks inject a stand-in. Missing live credentials MUST fail a real configured run; they MUST NOT fail checks that injected a stand-in.
- **Resume when completed or failed**: Fail at the boundary. MUST NOT restart as a side effect of resume.
- **Completed or failed slot**: A new start is allowed. A new start is a new run (new identity, attempt 1), not a continuation of the abandoned recovery budget.
- **One board, no second table**: Recovery MUST NOT create a parallel task store. Native retry counters on the existing board MAY remain unused this phase (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a validation step reports project-check failure (`validation_status` fail), the orchestrator MUST classify the outcome and MUST NOT immediately `FAILED` the workflow the way the previous phase did for that case. Discovery, planning, and original implementation failures with no validation outcome (including original implementation questions) MUST still end as `FAILED` without diagnosis. A non-empty questions list on validation MUST park at `HUMAN_DECISION_REQUIRED` instead of `FAILED`.
- **FR-002**: Classification MUST be exactly one of `TRANSIENT`, `RETRYABLE`, `NON_RETRYABLE`, `HUMAN_DECISION_REQUIRED`, derived from structured step results (status, validation status, questions list, next action), not from summary prose alone. Priority when more than one signal is present: questions list non-empty → `HUMAN_DECISION_REQUIRED`; then checks-cannot-start / `NON_RETRYABLE`; then `TRANSIENT`; then `RETRYABLE`. Checks that cannot start MUST NOT be classified `TRANSIENT` even when next action is `retry`.
- **FR-003**: Classification rules: non-empty questions → `HUMAN_DECISION_REQUIRED`; declared checks cannot start (command missing or cannot be executed) → `NON_RETRYABLE`; validation status fail (declared checks ran and failed) → `RETRYABLE`; validation status blocked, empty questions, next action `retry`, and checks were not a cannot-start → `TRANSIENT`; validation status blocked, empty questions, next action not `retry` → `NON_RETRYABLE`. The orchestrator MUST NOT invent a class that those signals do not support.
- **FR-004**: A `RETRYABLE` validation failure MUST, when fewer than 3 recovery cycles have been used, record `RETRYABLE_FAILURE`, increment attempt, run diagnosis, then debug, then validation. Debug MAY change the isolated copy and MAY leave a local commit on the task work branch. Diagnosis MUST NOT use “declared checks passed” as its success criterion and MUST NOT be skipped on a retryable path.
- **FR-005**: A `TRANSIENT` validation outcome MUST, when fewer than 3 recovery cycles have been used, record `RETRYABLE_FAILURE`, increment attempt, and re-run validation only. It MUST NOT run diagnosis and MUST NOT edit the isolated copy.
- **FR-006**: After 3 recovery cycles that each end in `RETRYABLE` or `TRANSIENT` failure, or on any `NON_RETRYABLE` validation (or diagnosis) outcome, the workflow MUST enter `BLOCKED`, occupy the slot, and MUST NOT start another automatic recovery cycle. Attempt MUST be 4 after three recoveries following the original attempt; a first-validation `NON_RETRYABLE` MUST `BLOCKED` with attempt still 1.
- **FR-007**: Every workflow record MUST use an explicit state of `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, or `BLOCKED`. The record MUST include workflow name, current phase (including `diagnosis` and `debug` when those steps run), current worker, attempt count, workspace location and branch, validation status, blockers, next action, pull-request slot (empty), classification of the last validation failure when one exists, and the latest diagnostic report when diagnosis has run. Status MUST NOT be determined only by reading summary prose.
- **FR-008**: Execution state, classification, attempt, diagnostic reports, and escalation briefs MUST live in the control plane’s operational record, not in the human-readable task body. The task body MUST keep problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, and priority without being overwritten by recovery churn.
- **FR-009**: A diagnostic report MUST include task, phase, attempt count, failure, what was attempted, current state, and decision required (empty when none). It MUST NOT contain secrets, private reasoning, or model transcripts.
- **FR-010**: `BLOCKED` MUST record an escalation brief in the existing decision shape with fixed options `A` (abandon → `FAILED`, release slot) and `B` (grant exactly one recovery cycle). This phase MUST NOT send a message. Recommended option MAY be `A` for `NON_RETRYABLE` and `B` when the block is retry-limit exhaustion.
- **FR-011**: `resume_workflow` MUST accept a listed option letter for both `HUMAN_DECISION_REQUIRED` and `BLOCKED`. Parked-step resume (discovery, planning, diagnosis, debug, or validation questions) still re-runs the parked step with the letter and option text and MUST NOT increment attempt. After a parked validation re-run, the orchestrator MUST classify that new outcome. Blocked `A` MUST `FAILED` and release the slot. Blocked `B` MUST run exactly one recovery cycle whose shape follows last class: diagnosis→debug→validate when retryable; validate-only when transient or non-retryable. A non-retryable `B` MUST NOT run diagnosis or debug. After that cycle’s validation, classify the new outcome (including starting automatic recovery if the new class is retryable or transient and budget remains). An option that is not listed, or resume when the workflow is neither parked nor blocked, MUST fail at the boundary.
- **FR-012**: `run_workflow` / `run_next_workflow` / `resume_workflow` MUST wait until `COMPLETED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED` and return that record. They MUST NOT start a background worker. At most one workflow MAY be in `QUEUED`, `RUNNING`, `VALIDATING`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, or `BLOCKED` at a time. A second start MUST be refused while that slot is occupied. `COMPLETED` and `FAILED` MUST release the slot.
- **FR-013**: Recovery MUST reuse existing eligible-project resolve, context load, workspace prepare/inspect, task-board reads, and agent-run operations. Diagnosis MUST be one existing agent run (default: the agent already mapped to validation). Debug MUST be one existing implementation-role run with the diagnostic report supplied as previous-step output. Re-validation MUST be the existing validation-role run against the project’s declared checks. This feature MUST NOT add agents to methodology, MUST NOT duplicate Git safety, and MUST NOT create a second task board.
- **FR-014**: Implementation and debug file changes and any local commit MUST remain in the isolated working copy. The orchestrator MUST NOT publish, merge, deploy, write methodology, or change the enrolled project location.
- **FR-015**: PIV-complete (`COMPLETED`) still means: discovery and planning succeeded, implementation (and any debug fixes) ran against the isolated copy, validation passed using the project’s declared checks, the work branch is the task feature branch, and nothing was published. A pull request MUST NOT be required.
- **FR-016**: Checks MAY inject a stand-in model service and a fixture task board. A live model service, live task gateway, live board file, live hosting account, and live messaging bot MUST NOT be required to prove this phase.
- **FR-017**: `run_workflow` / `run_next_workflow` / `resume_workflow` remain the trust boundary. Invalid project, task, workspace, mapping, active-slot conflict, no-ready-task, missing or invalid priority, or invalid resume MUST fail there with a visible error.

### Key Entities

- **Task (board record)**: Unchanged. Human-readable work item on the existing task board. Source of truth for *what* to do. Not the execution-state record.
- **Workflow run**: One plan → implement → validate execution, now including zero or more recovery cycles after validation failure. Occupies the single V0 slot until completed, failed, still parked, or blocked.
- **Execution state**: Operational record, extended with `RETRYABLE_FAILURE` and `BLOCKED`, incrementing attempt, last failure class, diagnostic report, and escalation brief. Control-plane owned.
- **Failure class**: `TRANSIENT` | `RETRYABLE` | `NON_RETRYABLE` | `HUMAN_DECISION_REQUIRED` for a validation (or diagnosis) outcome.
- **Recovery attempt**: One automatic cycle after a validation failure: either transient re-validate, or diagnosis → debug → re-validate. Maximum 3 automatic cycles per run, plus at most one extra cycle per blocked `B` resume.
- **Diagnostic report**: Structured note of what failed and what was tried. Not a Telegram message. Not written into the task body.
- **Escalation brief**: Decision brief used at `BLOCKED`, with fixed abandon/retry-once options. Same reply language (option letter) as a planning pause.
- **Decision brief**: Existing parked human decision (questions list labeled `A`, `B`, `C`). Now also used when diagnosis, debug, or validation returns questions.
- **PIV-complete**: Validation has passed for this run, including after recovery. Hosting is still not part of this entity.

### Out of Scope

This specification covers classification, bounded retry, diagnosis, debug in the isolated copy, `BLOCKED`, and human escalation via the existing letter-resume protocol. Explicitly deferred:

- Git hosting: commit-to-remote, push, pull requests, merge (`PR_CREATED`)
- SSH / credential forwarding for hosting
- Telegram / notifications (blocked does not send a message)
- Container restart / interrupted-run persistence (later reliability phase)
- Concurrent execution of more than one workflow
- Recovering discovery, planning, or original implementation failures (those stay `FAILED`)
- Learning / retrospectives / methodology-change proposals
- Adding a debugger (or any) agent folder to live methodology
- Installing an external planning framework into this control plane
- Editor-specific command files
- Writing native board retry counters (`consecutive_failures`, `max_retries`, `block_kind`) — overlay only this phase
- A second task database or a second task board
- Obsidian
- Automatic merge, production deploy, or protected-branch writes
- Operator-configurable recovery limit (V0 default is 3)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an eligible fixture project whose declared checks fail once and pass after a debug edit, a caller can complete the workflow on the start call: the returned record is `COMPLETED`, validation status is pass, and diagnosis plus debug ran exactly once.
- **SC-002**: 100% of first validation check-failures classified `RETRYABLE` start diagnosis before debug; 0% skip diagnosis on that path; 0% of `TRANSIENT` outcomes run diagnosis or edit the isolated copy.
- **SC-003**: 100% of runs stop automatic recovery after 3 recovery cycles; 0% start a fourth automatic cycle. After those three, state is `BLOCKED` and attempt is 4. 100% of `NON_RETRYABLE` validation outcomes (including declared checks that cannot start) go `BLOCKED` without diagnosis, debug, or an automatic retry.
- **SC-004**: 100% of discovery, planning, and original-implementation failures with no validation outcome still end `FAILED` with attempt 1 and 0 diagnosis runs. 100% of validation-step question lists park at `HUMAN_DECISION_REQUIRED` (not `FAILED`) without incrementing attempt; resume re-runs validation then classifies.
- **SC-005**: 100% of `BLOCKED` records include an `A`/`B` escalation brief; 100% of listed-letter resumes from `BLOCKED` either abandon to `FAILED` or run exactly one more recovery cycle; 100% of non-retryable `B` grants re-run validation with 0 diagnosis and 0 debug; 100% of diagnosis, debug, and validation question lists park at `HUMAN_DECISION_REQUIRED` without incrementing attempt.
- **SC-006**: 100% of overlapping starts are refused while a workflow is queued, running, validating, parked, in retryable failure, or blocked; 100% of recovery file changes stay in the isolated copy; 0% of runs publish a branch, open a pull request, modify methodology, or rewrite the human-readable task body with recovery churn.
- **SC-007**: A reviewer can complete seven contract checks — recover a first validation fail to `COMPLETED`, classify transient vs retryable vs non-retryable, hit the 3-cycle limit then `BLOCKED`, abandon from `BLOCKED` to `FAILED`, grant one extra cycle with `B` (validate-only when last class was non-retryable), park/resume diagnosis or validation questions without incrementing attempt, refuse a second active workflow during `BLOCKED` — and each check fails if that behavior breaks.

## Assumptions

- **This phase is recovery on top of the existing orchestrator.** Methodology adapter, project registry, workspace manager, agent execution, and the PIV chain already exist. This feature adds classification, bounded retry, diagnosis, debug, `BLOCKED`, and escalation. It does not start hosting, messaging, or restart persistence.
- **Validation failure is the only automatic recovery trigger.** The Phase 4 plan is validation failure → diagnosis → debug → retry. Discovery, planning, and original implementation failures remain terminal `FAILED` (previous phase). That keeps the add-on small.
- **Three recovery attempts** means three automatic cycles after the original validation, matching the V0 suggested default. Original chain is attempt 1. Each cycle increments attempt. Limit reached → `BLOCKED` at attempt 4. The limit is not operator-configurable in this phase.
- **Classification signals** reuse the existing structured result: questions list, validation status (pass / fail / blocked), status, and next action. Declared checks that cannot start are `NON_RETRYABLE` (not transient). `next_action` of `retry` with blocked validation is the transient signal only when the checks are not a cannot-start. Checks inject those fields via the stand-in. No new result shape is required for V0.
- **Diagnosis reuses the validation agent; debug reuses implementation.** Defaults: diagnosis runs the agent already mapped to validation, as a non-validation-role run (so it does not re-execute project checks as its success criterion). Debug is an implementation-role run with the diagnostic report in context. Operators may remap agents in configuration. This phase does not add folders to methodology. Diagnosis shares the validation model assignment; debug shares the implementation assignment.
- **Phases on the record** add `diagnosis` and `debug` alongside `discovery`, `planning`, `implementation`, `validation`.
- **`RETRYABLE_FAILURE` is history, not a wait-return.** Start/resume still block until completed, failed, parked, or blocked. History must show `RETRYABLE_FAILURE` so a reviewer can see that recovery started.
- **`BLOCKED` occupies the slot.** Same reason parked occupies it: V0 is one-at-a-time. Escalation is useless if the next task has already started.
- **Blocked options are fixed `A`/`B`.** Do not ask the diagnosis agent to invent abandon/retry options. Planning-style questions remain the agent’s questions list. One resume call handles both.
- **Operator `B` is a single grant**, not a budget reset. Shape follows last class: full recovery cycle when retryable; validate-only when transient or non-retryable. Non-retryable `B` exists so the operator can retry after fixing the environment without a pointless debug edit.
- **Existing task board.** This feature reads tasks from it (or a fixture board in checks). Native board fields for retries and circuit breaker (`consecutive_failures`, `max_retries`, `last_failure_error`, `block_kind`) exist on the installed control plane but are **not written in this phase**. `ponytail:` ceiling — in-memory operational overlay (as the previous phase already used); upgrade path — map attempt / blocked onto those native fields without a second task table.
- **No second database.** Execution-state fields the host can already represent SHOULD fill those host fields when a later phase maps them. Until then the overlay record is enough. No new task table.
- **Parked occupies the slot.** `HUMAN_DECISION_REQUIRED` still counts as active. Resume of a parked diagnosis/debug/validation step does not increment attempt (same attempt, with an answer).
- **Empty questions means continue.** Only a non-empty questions list is a consequential pause during recovery. Validation questions park (replacing the previous phase’s `FAILED` for that case). Original implementation questions still `FAILED`.
- **Start and resume wait.** No background worker. How the record is stored on the host (native fields vs overlay) is a planning choice; there is still no second task table.
- **Local commit, no remote publish.** Debug may leave a local commit on the work branch, as implementation already allows. This phase still publishes 0 times.
- **PIV-complete ≠ pull request.** Hosting is the next phase. `COMPLETED` here is validation passed, including after recovery.
- **Stand-in model service and fixture board for checks.** Contract checks MUST NOT require a live model account, a live production project, a live board file, a live hosting account, or a live messaging bot.
- **Reuse existing operations.** The orchestrator MUST call existing eligible-project resolve, context load, prepare/inspect workspace, board reads, and role/agent execute. It MUST NOT duplicate Git safety, methodology loading, or model assignment.
- **Trust boundary**: `run_workflow`, `run_next_workflow`, and `resume_workflow`. Invalid input fails there.
- **No new third-party libraries** without an explicit owner request.
- **Checks** live with the existing control-plane package. One contract-check file must fail if the seven behaviors in SC-007 break.
- **Public operation names** stay `run_workflow`, `run_next_workflow`, `resume_workflow`. Exact module layout inside the existing control-plane package is an implementation choice. Recovery is added to the existing orchestrator, not a second orchestrator.
- **Implementation follows this spec**, then code; Git hosting and messaging do not start until this feature’s checks pass and a later spec/plan asks for them.
- **Disposable fixture only.** Checks MUST NOT enroll a production repository.
- **Constitution invariants hold:** methodology is read-only; project knowledge stays in the project; the control plane owns operational state; the existing board is task source of truth; no merge/deploy; no silent production repo.

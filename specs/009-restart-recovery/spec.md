# Feature Specification: Restart Recovery

**Feature Branch**: `009-restart-recovery`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "capture phase 7 in the scratch/implimentation.md" (Phase 7 — Persistence / Restart Recovery: verify container restart, worker interruption, task recovery, workspace recovery, duplicate prevention)

## Clarifications

### Session 2026-09-02

- Q: If two copies of the control plane are running at the same time (for example two containers), who is allowed to continue the interrupted task? → A: Only one copy may work. The second copy must refuse to take over.
- Q: When work was cut off mid-run, what should count as one “step” that we either skip (already done) or run again once? → A: A whole phase (plan, implement, check, debug, or publish).
- Q: How should the system tell a still-running first copy from a crashed one, so a second copy does not take over by mistake? → A: Heartbeat: still-alive signal means refuse; silence means reclaim.
- Q: If GitHub or the network is unreachable when the service comes back, should reclaim still continue? → A: Yes, continue on the local working copy and local branch; do not wait on the network.
- Q: After a restart, when does reclaim happen, and does a person have to press Resume? → A: Automatically during start-up, before any new start is accepted; no Resume press.

## User Scenarios & Testing *(mandatory)*

Phases 0–6 already deliver enrollment, isolated working copies, chained discovery → planning → implementation → validation, bounded **validation** recovery (diagnose / debug / re-check), GitHub publish, and operator messaging. Execution state lives on the control plane. V0 still runs **one** in-progress workflow at a time.

That is enough while the service stays up. It is **not** enough when the control plane process stops in the middle of work (operator restart, crash, container stop/start). Today an interrupted run can leave a worker that never finishes, a second start that looks like a new job, or a working copy that nobody can find.

This feature is Phase 7: **persistence across process / container restart** and **no duplicate workers after interruption**. After the control plane comes back, an interrupted task’s state is still readable, its working copy and work branch are still findable, the same run continues or safely restarts that interrupted phase, and a second worker MUST NOT appear for the same task.

This is **not** Phase 4 (PIV recovery): that feature retries **failed project checks** with diagnosis and debug. This feature recovers from a **dead or restarted process**. It does not add check-failure classification, extra retry budget, Telegram events, GitHub publish rules, or a full end-to-end fixture parade (Phase 8).

The people who benefit are operators: they can stop and start the service without losing the board’s operational truth, without two workers rewriting the same task, and without a second task store. Methodology stays read-only. Project knowledge stays in the project. The existing task board stays the source of truth for *what* the work is. Hermes owns operational state.

### User Story 1 - Restart does not lose or corrupt the active run (Priority: P1)

An operator starts a normal workflow for a fixture task. While a phase is in progress (discovery, planning, implementation, validation, recovery cycle, or publish), the control plane is stopped and started again — including a full container restart.

After start-up, the same execution record is still there: same task identity, same execution identity, same project identity, same workspace identity, last recorded state and phase, attempt count, and correlation fields. Terminal runs (`COMPLETED`, `FAILED`, `PR_CREATED`) are unchanged. Parked and blocked runs stay parked or blocked. An in-progress run is still the one occupying the single V0 slot.

The human-readable task body on the board is not rewritten into a different task. Nothing is invented to “fill gaps.” If a write was cut off, the record MUST remain readable as one consistent snapshot (the last complete write), not a mix of two versions.

**Why this priority**: If restart corrupts or drops the run, every later recovery behavior is guessing. Persistence is the foundation of this phase.

**Independent Test**: Start a fixture workflow, stop the control plane during an in-progress phase, start it again. Confirm the execution record still exists with the same identities and a coherent state. Repeat with a finished run and a parked run and confirm those records are unchanged.

**Acceptance Scenarios**:

1. **Given** a fixture workflow whose state is `RUNNING`, `VALIDATING`, or `RETRYABLE_FAILURE`, **When** the control plane is stopped and started (including a full container restart), **Then** the same execution identity is still present with the same task, project, and workspace identities, and the last fully written state is readable (not a mixed or empty record).
2. **Given** a run already in `COMPLETED`, `FAILED`, or `PR_CREATED`, **When** the control plane restarts, **Then** that terminal state is unchanged and no automatic work starts for that task.
3. **Given** a run already in `HUMAN_DECISION_REQUIRED` or `BLOCKED`, **When** the control plane restarts, **Then** it stays in that state, still occupies the single V0 slot, and does not spawn a worker until the existing resume / blocked-choice path is used.
4. **Given** a successful restart, **When** the caller reads the task on the existing board, **Then** owner, reviewer, priority, and the problem / expected-result / acceptance-criteria body are unchanged; execution details were not copied into that body to “repair” them.

---

### User Story 2 - Interrupted work resumes or safely restarts without a second worker (Priority: P1)

After restart, the control plane **reclaims** the interrupted run. It does not allocate a new execution identity. It does not start a second worker for the same task.

A **step** in this spec is a **whole workflow phase**: discovery, planning, implementation, validation, a Phase 4 recovery action (diagnose, debug, or re-check), or publish — not a single model call or tool use.

Reclaim rule (documented default):

- If the last recorded **phase completed** and the next phase had not started, **resume** from that next phase on the same working copy and branch.
- If the last recorded **phase was in progress** when the process died, **safely restart that same phase once** on the same working copy, same branch, same execution identity. Do not treat this as a new attempt budget for Phase 4 check-retries unless that phase actually finished as a classified validation failure (unchanged from Phase 4).
- If the run was already terminal, parked, or blocked, do nothing automatic.

A second `run_workflow` / `run_next_workflow` while that slot is still occupied MUST still be refused. Coming back as a new process MUST NOT count as a free slot.

Worker interruption (the in-flight agent dies with the process) is the same case: reclaim the execution; do not launch a parallel worker “to catch up.”

**Why this priority**: Duplicate execution is the failure this phase exists to prevent. Resume-or-safe-restart is how V0 stays one active task after a crash.

**Independent Test**: Interrupt during implementation. After restart, confirm one worker continues (or that same phase re-runs once), `execution_id` is unchanged, and a second start is refused until the slot is free. Confirm no second working copy was prepared for the same task as a “new” run.

**Acceptance Scenarios**:

1. **Given** an in-progress fixture run interrupted by process stop, **When** the control plane starts again, **Then** at most one worker proceeds for that task, using the existing execution identity (not a newly allocated one).
2. **Given** that reclaimed run, **When** an operator (or scheduler) tries to start another workflow before the slot is released, **Then** the start is refused with the same occupied-slot failure as before this phase.
3. **Given** interruption after a **phase** result was fully recorded and before the next phase started, **When** reclaim runs, **Then** work continues from that next phase (resume), not from the beginning of the whole workflow and not as a second execution.
4. **Given** interruption while a phase is in progress (no completed result for that phase), **When** reclaim runs, **Then** that same phase is run again once on the same working copy (“safe restart” of the interrupted phase), and a second parallel worker is not started.
5. **Given** two control-plane start-ups in a row with no operator start call, **When** the slot is already reclaimed, **Then** start-up MUST NOT create a second in-progress execution for the same task.
6. **Given** a first copy that is still sending its alive signal, **When** a second copy starts, **Then** the second copy MUST refuse the slot and MUST NOT start a worker.
7. **Given** a first copy whose alive signal has been silent for **60 seconds**, **When** another copy starts, **Then** that copy MAY reclaim (treat the first as dead).
8. **Given** start-up of the only copy after a crash, **When** reclaim is due, **Then** it runs automatically as part of becoming ready, **before** any new `run_workflow` / `run_next_workflow` is accepted, with no operator Resume press.

---

### User Story 3 - Working copy and work branch are discoverable after restart (Priority: P1)

The isolated working copy for the interrupted task is still findable: same workspace identity, same location when the files are still there, same task feature branch. Unrelated tasks’ copies stay isolated. The enrolled project location is not used as a substitute work directory.

If the copy still exists, reclaim uses **that** copy — including when it has uncommitted changes from the killed worker. The existing “never reuse a dirty copy” rule still applies to **preparing a new run**; it MUST NOT force a second copy or delete the interrupted task’s files in order to continue.

If the copy directory is gone but the task feature branch still exists, reclaim MAY recreate the isolated copy for the **same** workspace identity onto that same branch (not a new task, not the protected default branch). If neither the copy nor the branch can be found, the run goes `BLOCKED` with a visible reason; it MUST NOT silently start a different task or share another task’s copy.

Inspect after recovery still reports current branch, whether files changed, and (when changed) a summary — same Git-safety inspect as workspace management.

**Why this priority**: A recovered record pointing at a missing or shared directory is how work gets duplicated or overwritten. Workspace recovery is the physical half of restart safety.

**Independent Test**: Interrupt with files present in the task copy. Restart. Confirm the same path and branch are used and another task’s copy is untouched. Repeat with the copy removed but the feature branch still present, and with both missing.

**Acceptance Scenarios**:

1. **Given** an interrupted run whose isolated copy still exists, **When** the control plane restarts, **Then** reclaim uses that same copy and workspace identity; the current branch is the task feature branch (recoverable); the enrolled project location’s current branch is unchanged.
2. **Given** that copy has uncommitted changes from the interrupted worker, **When** reclaim continues or safely restarts the interrupted phase, **Then** those files are not discarded to “clean” the copy, a second copy is not prepared for the same task, and no other task’s files are removed or overwritten.
3. **Given** two task copies under the workspace root, **When** one task is reclaimed after restart, **Then** the other task’s copy remains isolated (not shared, not checked out as the reclaimed run’s mutable directory).
4. **Given** the copy directory is missing and the task feature branch still exists, **When** reclaim needs a working copy, **Then** it recreates an isolated copy for the same workspace identity on that same feature branch — never on `main`, `master`, or the project’s default branch.
5. **Given** both the copy and the task feature branch are missing or invalid, **When** reclaim runs, **Then** the execution becomes `BLOCKED` with a visible error, no second unrelated workspace is taken, and the slot stays occupied until a human acts on the existing blocked path.
6. **Given** GitHub or the network is unreachable at start-up and the isolated copy still exists locally, **When** reclaim runs, **Then** work continues on that local copy and local feature branch (no wait for the remote).
7. **Given** the copy is missing and the feature branch is only knowable via a remote that is unreachable, **When** reclaim cannot find a local copy or local branch, **Then** the run is `BLOCKED` with a visible reason (MUST NOT hang waiting for the network).

---

### Edge Cases

- **Restart during publish**: Reclaim the same execution. Do not open a second pull request. Follow the already-specified publish rules (same work branch; rewrite title/body if that run publishes again; never merge). This phase does not redefine GitHub.
- **Restart during a Phase 4 recovery cycle**: Reclaim the same attempt and cycle in progress. Do not increment the check-retry budget solely because the process died. Safe-restart the interrupted diagnosis, debug, or re-check **phase**.
- **Restart while `QUEUED` (accepted, phase not started)**: Resume by starting the first (or next) phase on the existing identity; do not enqueue a second run.
- **Dirty copy belonging to a different task than the record names**: Fail as invalid workspace and `BLOCKED`; MUST NOT adopt that directory.
- **Control plane starts with no in-progress run**: Idle. Do not invent a task. Existing terminal history remains readable.
- **Operator start of the same task after a terminal success**: Unchanged from prior phases (slot free). MUST NOT look like “duplicate recovery” of the finished execution identity.
- **Partial last write of operational state**: Use the last complete snapshot. NEVER leave two in-progress executions for one task. NEVER create a second task store to “repair” the record.
- **Two live control-plane copies**: Only one copy may reclaim or run workers. If a second copy starts while another copy still holds the slot (two containers, two processes), the second MUST refuse to take over and MUST NOT start a worker for that task. V0 does not “steal” the run from a still-living first copy.
- **Alive vs crashed**: A still-living copy keeps an **alive signal** (heartbeat). While that signal is fresh, other copies MUST refuse. If the signal has been silent for **60 seconds**, treat the holder as dead and allow reclaim. Crash of the only copy MUST NOT require a person to delete a lock file or press Resume.
- **Network / GitHub down at reclaim**: Continue on the local working copy and local feature branch. Do not wait for the remote. Recreate-from-branch is allowed only when that branch is already available locally. If neither local copy nor local branch exists, `BLOCKED` — do not hang.
- **When reclaim runs**: Automatically during start-up, as part of becoming ready, before any new start is accepted. No Resume press. Parked and blocked runs still get no automatic worker.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operational execution state MUST survive a full control-plane stop and start (including container restart) without corruption: identities, explicit state, current phase, attempt count, workspace location and branch, and last fully written snapshot remain readable.
- **FR-002**: Hermes MUST remain the owner of operational state. This phase MUST NOT introduce a second task store. The existing board remains the source of truth for the human-readable task body.
- **FR-003**: On start-up, the control plane MUST reclaim at most one in-progress V0 execution (`QUEUED`, `RUNNING`, `VALIDATING`, `RETRYABLE_FAILURE`). Parked (`HUMAN_DECISION_REQUIRED`) and `BLOCKED` runs occupy the slot without automatic workers. Terminal runs MUST NOT be reclaimed as new work.
- **FR-004**: Reclaim MUST keep the existing `task_id`, `execution_id`, `project_id`, and `workspace_id`. A new process MUST NOT allocate a new execution identity for the interrupted task. `worker_id` MAY reflect the agent that runs after reclaim.
- **FR-005**: After interruption, the control plane MUST either resume the next unstarted **phase** or safely restart the interrupted **phase** once (discovery, planning, implementation, validation, diagnose, debug, re-check, or publish — not a single model call). It MUST NOT run two workers for the same execution or the same task at the same time.
- **FR-006**: A second workflow start MUST be refused while the reclaimed or parked/blocked slot is occupied — same single-active-task rule as prior phases.
- **FR-007**: After restart, the isolated working copy MUST be discoverable for the reclaimed task (existing path, or recreated onto the existing task feature branch with the same workspace identity). Unrelated copies MUST stay isolated. Dirty copies MUST NOT be reused to prepare a **new** run; the interrupted run MAY continue on its own dirty copy.
- **FR-008**: The task feature branch MUST be recoverable as the work branch. Reclaim MUST NEVER use a protected default branch (`main`, `master`, or the project’s default) as the mutable work branch.
- **FR-009**: If workspace or branch recovery is impossible (missing copy and missing/invalid branch, or the path belongs to another task), the run MUST enter `BLOCKED` with a visible reason and MUST NOT take another task’s copy.
- **FR-010**: Restart MUST NOT by itself increment Phase 4 validation-recovery attempt count, open a second pull request, send a substitute “new task started” as if it were a distinct execution, or copy methodology / project knowledge into the control plane.
- **FR-011**: Duplicate prevention MUST hold across start-up and operator start: one task MUST NOT have two in-progress execution records; start-up twice MUST NOT create two reclamations that both run.
- **FR-012**: Inspect after recovery MUST still report current branch, whether files changed, and a change summary when files changed (existing Git-safety inspect).
- **FR-013**: This phase MUST NOT implement Phase 8 full end-to-end certification, MUST NOT respecify Telegram transport or event catalogs, MUST NOT respecify GitHub merge/push policy, and MUST NOT replace Phase 4 check-failure recovery.
- **FR-014**: At most one live control-plane copy MAY reclaim or run workers for the in-progress slot. A second copy that starts while another copy still holds that slot MUST refuse to take over and MUST NOT start a worker. It MUST NOT steal the run from a still-living first copy.
- **FR-015**: Liveness MUST be an **alive signal** that a running copy keeps fresh. Other copies MUST refuse while that signal is fresh. After **60 seconds** of silence, the holder is dead and reclaim is allowed. A crash MUST NOT require a person to delete a lock or press Resume.
- **FR-016**: Reclaim MUST proceed using the local working copy and local feature branch even when GitHub or the network is unreachable. It MUST NOT wait on the remote. Recreate-from-branch MUST use a locally available branch. If neither local copy nor local branch exists, the run MUST be `BLOCKED`.
- **FR-017**: Reclaim MUST run automatically during start-up, before the process accepts a new workflow start. Operators MUST NOT be required to press Resume for process-death recovery.

### Key Entities

- **Execution record**: Control-plane owned snapshot of one workflow run: identities (`task_id`, `execution_id`, `project_id`, `workspace_id`, `worker_id` when assigned), explicit state, phase, attempt, workspace location and branch, validation status, blockers, next action, pull-request slot when present.
- **In-progress slot**: The single V0 occupancy. After restart it is the reclaimed run, a parked decision, or a blocked run — never two of these at once. Held by at most one live control-plane copy; a second live copy MUST refuse that slot.
- **Isolated working copy**: Per-task directory and feature branch prepared by workspace management. Recovery finds or recreates it; it is never shared across tasks.
- **Reclaim**: Start-up action that continues or safely restarts an interrupted execution without a new identity and without a second worker. It runs automatically before new starts are accepted.
- **Phase (step)**: One of discovery, planning, implementation, validation, diagnose, debug, re-check, or publish. Resume and safe-restart operate at this grain, not per model call.
- **Alive signal**: Proof that a control-plane copy still holds the slot. Fresh signal → other copies refuse. **60 seconds** of silence → holder is dead; reclaim is allowed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In **100%** of fixture restarts during an in-progress run, the execution record is still readable afterward with the same execution identity (no empty or mixed snapshot).
- **SC-002**: After an interrupted in-progress fixture run and one control-plane restart, **exactly one** worker proceeds for that task (**0** duplicate in-progress executions, **0** second start accepted while the slot is occupied). When a second live copy is started while the first still holds the slot, **0** second copies take over or start a worker.
- **SC-003**: After restart, operators can locate the task’s working copy and work branch in **100%** of fixtures where either the copy or the feature branch still exists; **0** reclamations attach to another task’s copy.
- **SC-004**: In **100%** of restarts of already-finished, parked, or blocked fixture runs, that recorded state is unchanged (no automatic re-run of a finished task; no unsolicited worker on parked/blocked).
- **SC-005**: **0** second pull requests and **0** extra Phase 4 retry-budget increments occur **solely** because the process restarted.
- **SC-006**: Operators can complete the interrupted-execution test (stop during an active task, start again, confirm recoverability and no duplicate worker) in a single restart cycle without rebuilding enrollment, publish, or messaging.
- **SC-007**: After start-up, reclaim of an in-progress fixture run begins automatically **before** a new start is accepted (**0** Resume presses required for process-death recovery).
- **SC-008**: In **100%** of fixtures where GitHub/network is unreachable but the local copy still exists, reclaim continues locally (**0** waits for the remote; **0** new working copies invented).

## Assumptions

- Source of this spec is Phase 7 plus the Interrupted Execution Test and Reliability Definition of Done in `scratch/implimentation.md`. Surrounding phases are in-scope only as dependencies, not as new work.
- **Resume vs safe restart**: a step is a whole workflow phase. Resume the next phase when the last phase was fully recorded; otherwise re-run the interrupted phase once on the same identity and copy.
- **Alive signal**: 60-second silence means dead; otherwise refuse. Prefer the platform’s existing heartbeat if it already exists.
- **Offline reclaim**: local copy/branch only; no wait on GitHub.
- **Automatic reclaim**: start-up, before accepting new work; no Resume press.
- **One active task** remains V0 law (`max_concurrent_tasks: 1`). Concurrent workers stay out of scope.
- **Dirty copy on reclaim** is the interrupted task’s own files, not a violation of “never reuse dirty worktrees” for a *new* prepare.
- Missing copy + existing feature branch → recreate same workspace identity on that branch. Missing both → `BLOCKED`.
- Process death is not a Phase 4 `TRANSIENT` check failure and does not consume the three recovery attempts by itself.
- Publish-in-progress follows existing GitHub rules; this spec only forbids a second execution / second PR as a restart side effect.
- Messaging may emit events the existing catalog already defines when a reclaimed run later starts a phase or blocks; this spec does not add a dedicated “restarted” event.
- Prior specs remain in force: `001-ainative-adapter`, `002-project-registry`, `003-workspace-manager`, `004-agent-execution`, `005-piv-orchestrator`, `006-piv-recovery` (validation/debug retry — different from this feature), `007-github-integration`, `008-telegram`.
- No second database, queue, or dashboard. Native control-plane persistence is reused.
- Target projects remain disposable fixtures until the owner names otherwise.
- Clarification (if any) happens in the parent; this spec records defaults instead of `[NEEDS CLARIFICATION]` markers.

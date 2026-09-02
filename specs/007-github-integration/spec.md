# Feature Specification: GitHub Integration

**Feature Branch**: `007-github-integration`

**Created**: 2026-09-01

**Status**: Draft

**Input**: User description: "go for Phase 5 — GitHub is next." (Phase 5 — GitHub: branch → commit → push → PR, plus SSH from inside the runtime container. Orchestrator owns the GitHub boundary. Builder must not push. Merge stays forbidden.)

## Clarifications

### Session 2026-09-01

- Q: When a pull request for the same work branch already exists and the orchestrator publishes more commits, must it also rewrite that pull request’s title and body (summary, changes, validation, limitations, task reference), or is pushing the new commits onto the existing branch enough? → A: Rewrite title and body on each publish (plus push commits to the same branch). No second PR.
- Q: When the orchestrator must put a commit on the work branch before publishing, may it rewrite existing Git history (amend or force-push), or must it only add a new commit? → A: Never amend or force-push. Only create a new commit when there is no publishable commit yet.
- Q: Who is responsible for making GitHub SSH work inside the control-plane container: this phase may change the shipped runtime, or operators must wire SSH with no runtime change? → A: This phase may change the shipped runtime (compose/mounts/docs) for SSH forwarding; no keys in the image.
- Q: What must a successful `PR_CREATED` wait-return include as pull-request identity? → A: Hosting pull-request number and HTML URL.
- Q: Which Git hosting endpoints are in scope for V0 publish? → A: github.com only (SSH `git@github.com`). GitHub Enterprise Server and other Git hosts are out of scope.

## User Scenarios & Testing *(mandatory)*

Phases 0–4 already deliver a disposable fixture project, an isolated working copy on a task feature branch, a chained discovery → planning → implementation → validation run, bounded recovery when project checks fail, and a parked/blocked human off-ramp. After validation passes, the run is **PIV-complete**: work exists only in the isolated copy, a local commit may already exist, and **nothing has been published**. That is enough to prove the chain. It is not enough to hand a human a reviewable change on the hosting service.

This feature is Phase 5: when a run becomes PIV-complete, the **orchestrator** (not the builder, not the isolated worker) takes the GitHub boundary: ensure the work branch has a commit, **publish that feature branch**, and **open or update a pull request** targeting the project’s default branch. Authentication to GitHub is **SSH from the same container runtime** that runs the control plane. Private keys are never copied into images. Merge, approval-as-human, deploy, and any push to a protected or default branch remain **impossible** through this workflow.

The people who benefit are operators: a finished task leaves a pull request they can review, not an unpublished local branch. Methodology stays read-only. Project knowledge stays in the project. The existing task board stays the source of truth for *what* the work is. Execution state, including the new `PR_CREATED` outcome and pull-request identity, belongs to the control plane.

This feature **adds** publish-after-PIV-complete on top of the existing chain. It does not respecify enrollment, workspace prepare, agent runs, recovery, Telegram, or container-restart persistence.

### User Story 1 - Publish a validated feature branch as a pull request (Priority: P1)

An operator starts the standard workflow for a fixture task. The chain reaches PIV-complete: validation passed (on the first try or after recovery). The orchestrator then, in order: confirms the work is on the task feature branch (never the default or protected branch), ensures a commit exists on that branch, publishes the feature branch to the project’s remote, and opens a pull request against the project’s default branch.

The pull request includes a summary, what changed, what validation ran, known limitations, and a reference to the task. The start call waits until that published outcome is recorded. Success is **`PR_CREATED`**, not a silent local `COMPLETED`.

If a pull request for this work branch already exists, the orchestrator publishes any new feature-branch commits and **rewrites that pull request’s title and body** so the five required sections and the task reference stay current. Pushing commits alone is not enough. A second pull request MUST NOT be opened.

**Why this priority**: Phase 5 exists so a human can review a real pull request. Without publish, the previous phases still leave work stranded on an isolated copy.

**Independent Test**: Drive an eligible fixture to validation pass. Confirm the orchestrator (not the builder) published the feature branch, a pull request exists against the default branch with the required body sections and task reference, the enrolled project location is unchanged, methodology is unchanged, and the wait-return is `PR_CREATED`. Confirm a second publish of additional feature-branch commits updates the same pull request **and** that the title and body were rewritten (not left stale).

**Acceptance Scenarios**:

1. **Given** an eligible fixture project and a fixture task that reaches PIV-complete (validation pass, isolated copy, task feature branch, local commit present or creatable), **When** the caller starts the workflow, **Then** the start call waits through publish and returns `PR_CREATED` with a pull-request identity that includes the hosting pull-request number and HTML URL, the published branch is the task feature branch, and the pull request targets the project’s default branch.
2. **Given** PIV-complete with no commit yet on the work branch but with reviewable changes in the isolated copy, **When** publish runs, **Then** the orchestrator creates **one new commit** on the task feature branch (does not amend, does not force-push) before publishing; the builder is not invoked to publish.
3. **Given** a pull request already open for this work branch, **When** publish runs again with additional feature-branch commits, **Then** those commits are published to the same branch, the existing pull request’s title and body are rewritten with the five required sections and task reference, and a second pull request for the same branch is not opened.
4. **Given** a successful publish, **When** the caller inspects the enrolled project location, **Then** it is unchanged; methodology is unchanged; 0 merges occurred; 0 pushes targeted a protected or default branch.
5. **Given** a successful publish, **When** the caller reads the pull request, **Then** it contains summary, changes, validation performed, known limitations, and a task reference.

---

### User Story 2 - Orchestrator owns GitHub; builder never publishes; merge stays impossible (Priority: P1)

Implementation and debug may still leave a **local** commit on the work branch, as earlier phases already allow. They MUST NOT publish, open a pull request, update a remote, merge, or deploy. Only the orchestrator’s post-validation GitHub step may publish a feature branch or open/update a pull request.

The workflow MUST NOT merge a pull request, MUST NOT approve a pull request as if it were a human, MUST NOT deploy, MUST NOT push to a protected or default branch, MUST NOT amend existing commits, and MUST NOT force-push — even if the operator or a stand-in worker tries to do so through this workflow. Updating an existing feature-branch pull request with more feature-branch commits is allowed (history-preserving push only). Targeting a protected branch for direct push is never allowed.

GitHub policy for this phase: push of feature branches is allowed; pull requests are allowed; merge is forbidden.

**Why this priority**: The constitution and V0 plan put merge and protected-branch writes on the human side of the boundary. If the builder can push, that boundary is gone.

**Independent Test**: Run an implementation-role step that produces a local commit and confirm 0 remotes were updated. After PIV-complete, confirm only the orchestrator’s publish step updated the remote. Attempt merge (or a merge-equivalent) through the workflow and confirm it is refused. Attempt a push to the default/protected branch through the workflow and confirm it is refused.

**Acceptance Scenarios**:

1. **Given** an implementation or debug step that creates a local commit, **When** that step finishes, **Then** the remote is unchanged: 0 branches published, 0 pull requests opened.
2. **Given** PIV-complete, **When** publish runs, **Then** the actor that publishes is the orchestrator’s GitHub step, not the builder, not diagnosis, and not validation.
3. **Given** any workflow state, **When** the caller (or a worker) requests merge, approve-as-human, deploy, or a push to a protected/default branch through this workflow, **Then** the request fails at the boundary; execution state is not `PR_CREATED` as a result of that request.
4. **Given** configuration for this phase, **When** a reviewer inspects allowed GitHub actions, **Then** feature-branch push and pull-request create/update are permitted and merge is not.

---

### User Story 3 - Authenticate from the container runtime without baking secrets (Priority: P2)

GitHub access is SSH-based to **github.com**. The same container runtime that runs the control plane MUST be able to prove authentication to GitHub (identity handshake), fetch from the project remote, and publish a feature branch — without private keys copied into images and without secrets written into execution records or pull-request bodies.

This phase MAY change the shipped control-plane runtime (compose, mounts, operator docs) so host SSH agent forwarding or an equivalent runtime secret is available. Credentials MUST NOT be baked into the image. Git integration is not complete until this works from that container, not only from a developer laptop.

Contract checks MAY simulate publish against a disposable fixture so they do not require a live hosting account. A live authentication check from the container is still required before this phase is declared done against a real remote; that live check uses a disposable or operator-named non-critical repository, never a silently chosen production repository.

**Why this priority**: A pull request opened only from the host, while the runtime cannot authenticate, is a false complete. Keys in images violate the security boundary.

**Independent Test**: From the control-plane container, confirm the GitHub SSH handshake succeeds, fetch succeeds, and a feature-branch publish succeeds, with 0 private keys in the image and 0 secrets in execution records. Confirm contract checks still pass without a live hosting account by using a simulated remote.

**Acceptance Scenarios**:

1. **Given** the control-plane container with runtime SSH forwarding configured, **When** an operator (or the done-check) authenticates to GitHub, **Then** the handshake succeeds from inside that container.
2. **Given** that same environment, **When** publish runs for a disposable/non-critical remote, **Then** fetch and feature-branch publish succeed.
3. **Given** the runtime image, **When** a reviewer inspects it, **Then** it does not contain copied SSH private keys; execution state and pull-request bodies do not contain secrets.
4. **Given** contract checks for this phase, **When** they run without live hosting credentials, **Then** they still prove orchestrator-owned publish, builder-never-publish, and merge-forbidden using a simulated remote; they MUST NOT enroll a production repository.
5. **Given** the shipped control-plane runtime after this phase, **When** a reviewer inspects it, **Then** SSH agent forwarding or an equivalent runtime secret mount is defined there (or documented as the supported equivalent), and the image still has 0 copied private keys.

---

### User Story 4 - Fail publish without merging it into validation recovery (Priority: P2)

Publish happens only after validation has already passed. A GitHub failure is not a project-check failure. The orchestrator MUST NOT start diagnosis/debug because a push or pull-request open failed.

Authentication or permission failures are **non-retryable**: the workflow goes `BLOCKED` with an escalation brief the operator can abandon (`A`) or retry-once (`B`, re-run publish only). Transient network failures MAY be retried a bounded number of times (same three-cycle budget as recovery, applied to publish attempts only), then `BLOCKED`. Discovery, planning, implementation, and validation behavior is unchanged.

Parked (`HUMAN_DECISION_REQUIRED`), `FAILED`, and `BLOCKED` runs that never reached PIV-complete MUST NOT publish. `COMPLETED` as a wait-return is replaced on the success path by `PR_CREATED`. A recorded PIV-complete moment MAY appear in history immediately before publish; the start/resume wait-return on success is `PR_CREATED`.

**Why this priority**: Retrying a missing SSH agent by editing the workspace would waste recovery budget and hide a human-owned credential problem.

**Independent Test**: After validation pass, inject an authentication failure and confirm `BLOCKED` with zero diagnosis and zero debug. Inject a transient publish failure twice then success and confirm publish retried without diagnosis. Confirm a parked or failed run never published.

**Acceptance Scenarios**:

1. **Given** PIV-complete and a GitHub authentication or permission failure on publish, **When** publish finishes, **Then** execution state is `BLOCKED`, diagnosis and debug did not run, and the isolated copy was not merged.
2. **Given** PIV-complete and a transient network failure on publish, **When** fewer than 3 publish retries have been used, **Then** the orchestrator retries publish only (no diagnosis, no debug, no second validation).
3. **Given** three failed publish attempts that are retryable/transient, **When** the third still fails that way, **Then** execution state is `BLOCKED` and a fourth automatic publish does not start.
4. **Given** a workflow in `HUMAN_DECISION_REQUIRED`, `FAILED`, or `BLOCKED` that never reached validation pass, **When** the caller inspects the remote, **Then** 0 branches were published and 0 pull requests were opened for that run.
5. **Given** a blocked publish, **When** the operator resumes with `B`, **Then** publish is retried once (not diagnosis/debug); resume `A` still fails the run and releases the slot.

---

### Edge Cases

- **Publish only after validation pass**: Discovery, planning, implementation, or validation failure MUST NOT publish. Recovery that later passes MAY then publish.
- **No changes to publish**: If the work branch has no commit ahead of the default branch and a clean tree, publish MUST fail visibly (not open an empty pull request). Dirty tree with no commit: orchestrator creates **one new commit** first if there are reviewable changes; if a publishable commit already exists, it MUST NOT add another empty ensure-commit. If the tree is dirty with no reviewable intent, fail visibly — MUST NOT discard a dirty copy. MUST NOT amend or force-push.
- **Protected / default branch**: The work branch MUST remain the task feature branch. Direct push to `main`/`master`/configured protected branches is forbidden. Pull request target is the default branch; that is not a push to that branch.
- **Idempotent PR**: Same work branch → same pull request. Do not open duplicates. Each publish MUST rewrite title and body; a push that leaves a stale description is a failed update.
- **PR body**: Missing sections fail the publish step (retryable only if the hosting service was unavailable; incomplete body is a control-plane bug and MUST fail the check, not ship).
- **Working tree**: Before `PR_CREATED`, the isolated copy MUST be clean except intentional artifacts already allowed by workspace rules.
- **Slot occupancy**: `PR_CREATED` releases the single V0 slot (terminal success), same as `COMPLETED` did after PIV-complete in the previous phase. `FAILED` still releases. Parked and blocked still occupy. A second start is refused while a run is active.
- **Wait-return**: Start/resume wait until `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. Intermediate PIV-complete is not a wait-return once this phase is in effect.
- **Live vs simulated remote**: Contract checks use a simulated or disposable fixture remote. A live GitHub proof uses only a disposable fixture or an operator-named non-critical repository. MUST NOT silently enroll a production repository.
- **Host-only success is not enough**: Authentication that works only on the developer laptop and not in the container MUST NOT count as phase-complete. The shipped runtime MAY be changed so the container can use host SSH agent forwarding.
- **github.com only**: Publish and live SSH proof target github.com. GitHub Enterprise Server, GitLab, and other hosts MUST NOT be required or silently selected. An enrolled remote that is not github.com MUST fail at the trust boundary.
- **Pull-request identity**: On `PR_CREATED`, the operational record MUST include the hosting pull-request number and the HTML URL. Either field missing is an incomplete success record.
- **Secrets**: MUST NOT appear on execution state, pull-request bodies, escalation briefs, or summaries.
- **Methodology writes**: Still forbidden.
- **Telegram**: PR-created notification is out of scope (next phase). `PR_CREATED` is recorded; no message is sent.
- **Restart persistence**: Still out of scope. This phase MUST NOT claim interrupted-run recovery.
- **Concurrent workers**: Still one-at-a-time.
- **Editor absence**: MUST NOT fail publish.
- **Stand-in vs live model**: Unchanged from previous phases.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After a workflow reaches PIV-complete (discovery and planning succeeded, implementation and any debug ran in the isolated copy, validation passed using the project’s declared checks, work branch is the task feature branch), the orchestrator MUST run the GitHub sequence: ensure a commit on that feature branch → publish that feature branch → create or update a pull request targeting the project’s default branch. The start/resume wait-return on that success path MUST be `PR_CREATED`.
- **FR-002**: The GitHub sequence MUST be owned by the orchestrator. Implementation, debug, diagnosis, validation, and any builder-role run MUST NOT publish a branch, update a remote, open or update a pull request, merge, or deploy. Local commits on the task feature branch remain allowed for implementation/debug as in previous phases.
- **FR-003**: The workflow MUST NOT merge a pull request, MUST NOT approve a pull request as a human, MUST NOT deploy, MUST NOT push to a protected or default branch, MUST NOT amend existing commits, and MUST NOT force-push any branch. Feature-branch push (history-preserving) and pull-request create/update MUST be allowed. Merge MUST remain impossible through the autonomous V0 workflow.
- **FR-004**: A newly created pull request MUST target the project’s default branch and MUST include summary, changes, validation performed, known limitations, and a task reference. An existing pull request for the same work branch MUST be reused (no duplicate). On every successful publish, including updates, the orchestrator MUST rewrite that pull request’s title and body so those five sections and the task reference match the current run. Pushing commits without rewriting title and body MUST NOT count as a successful update.
- **FR-005**: Authentication to GitHub MUST be SSH from the control-plane container runtime to **github.com**. The phase MUST NOT be considered complete until handshake, fetch, and feature-branch publish succeed from that container. Private SSH keys MUST NOT be copied into images. Credentials MUST come from runtime forwarding (host SSH agent or equivalent), environment, or mounted runtime secrets — not from git. This phase MAY update the shipped control-plane runtime (compose, mounts, operator docs) to provide that forwarding. GitHub Enterprise Server and non-github.com remotes are out of scope and MUST fail at the trust boundary if selected.
- **FR-006**: Publish MUST NOT run unless validation has passed for this run. Parked, failed, and blocked runs that never reached validation pass MUST leave the remote unchanged (0 publishes, 0 pull requests for that run).
- **FR-007**: GitHub authentication or permission failures MUST be `NON_RETRYABLE` for publish: `BLOCKED`, no diagnosis, no debug. Transient publish failures (network timeout, unavailable hosting) MAY retry publish only, at most 3 automatic publish attempts, then `BLOCKED`. Publish failure MUST NOT enter the validation recovery loop (no diagnosis/debug because of a push failure).
- **FR-008**: Every workflow record MUST use an explicit state of `QUEUED`, `RUNNING`, `VALIDATING`, `COMPLETED` (history-only PIV-complete, not a success wait-return), `FAILED`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, `BLOCKED`, or `PR_CREATED`. The record MUST include the previous phase’s fields plus a pull-request identity when `PR_CREATED` (or empty until then). Pull-request identity MUST include the hosting pull-request **number** and the **HTML URL**. Status MUST NOT be determined only by reading summary prose.
- **FR-009**: `PR_CREATED` MUST release the single V0 slot. `FAILED` still releases. `QUEUED`, `RUNNING`, `VALIDATING`, `HUMAN_DECISION_REQUIRED`, `RETRYABLE_FAILURE`, and `BLOCKED` still occupy it. A second start MUST be refused while the slot is occupied.
- **FR-010**: `run_workflow` / `run_next_workflow` / `resume_workflow` MUST wait until `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. They MUST NOT start a background worker. Blocked-publish resume `A` abandons (`FAILED`, release slot). Blocked-publish resume `B` retries publish once (not diagnosis/debug). Invalid letters fail at the boundary.
- **FR-011**: If the work branch has no commit ahead of the default branch and no reviewable changes, publish MUST fail visibly and MUST NOT open an empty pull request. If reviewable changes exist without a publishable commit, the orchestrator MUST create exactly one new commit on the task feature branch before publishing. If a commit already exists ahead of the default branch, the orchestrator MUST NOT invent another commit solely to “ensure” publish. Amend, rebase-onto-rewrite, and force-push MUST NOT be used.
- **FR-012**: Before `PR_CREATED`, the isolated copy’s working tree MUST be clean except intentional artifacts. Unrelated dirty trees MUST NOT be published or discarded.
- **FR-013**: Execution state, pull-request identity, and publish errors MUST live in the control plane’s operational record, not in the human-readable task body. Secrets MUST NOT appear there or in pull-request bodies.
- **FR-014**: This feature MUST reuse existing eligible-project resolve, context load, workspace prepare/inspect, Git safety (never work on default/protected, never share dirty copies), board reads, and the PIV/recovery chain. It MUST NOT duplicate Git safety in a second workspace manager, MUST NOT create a second task board, MUST NOT write methodology, and MUST NOT change the enrolled project location.
- **FR-015**: Contract checks MAY inject a stand-in model service, a fixture task board, and a **simulated remote** so a live hosting account is not required to prove FR-001–FR-004 and FR-006–FR-014. A live container SSH/fetch/push proof is still required for FR-005 against a disposable or operator-named non-critical repository. A live model service, live messaging bot, and production repository MUST NOT be required for contract checks. The system MUST NOT silently choose a production repository.
- **FR-016**: `run_workflow` / `run_next_workflow` / `resume_workflow` remain the trust boundary. Invalid project, task, workspace, mapping, active-slot conflict, no-ready-task, invalid resume, or a merge/protected-push request MUST fail there with a visible error.

### Key Entities

- **Task (board record)**: Unchanged. Source of truth for *what* to do. Not overwritten with pull-request churn.
- **Workflow run**: One plan → implement → validate (with recovery) → GitHub publish execution. Occupies the V0 slot until `PR_CREATED`, `FAILED`, parked, or blocked.
- **Execution state**: Operational record, extended with `PR_CREATED` as the success wait-return and a pull-request identity. Control-plane owned.
- **PIV-complete**: Validation has passed for this run. Necessary but no longer sufficient for the success wait-return. May appear in history immediately before publish.
- **Feature branch**: The task work branch created earlier. The only branch this workflow may publish.
- **Pull request**: Hosting-service review request on github.com targeting the project’s default branch, created or updated by the orchestrator after PIV-complete. Never merged by this workflow. Identity on the operational record is number plus HTML URL.
- **Publish attempt**: One try of commit-ensure → push feature branch → create/update pull request. Separate from validation recovery cycles.

### Out of Scope

This specification covers orchestrator-owned GitHub publish after PIV-complete, SSH from the container runtime, pull-request create/update, and a forbidden merge/protected-push boundary. Explicitly deferred:

- Telegram / notifications (including PR-created messages)
- Container restart / interrupted-run persistence
- Concurrent execution of more than one workflow
- Automatic merge, human-equivalent approval, production deploy
- Push to protected or default branches
- Amend, rebase-rewrite, or force-push of any branch through this workflow
- Copying SSH private keys into images
- Silently selecting a production repository
- GitHub Enterprise Server, GitLab, Bitbucket, or any remote that is not github.com
- Learning / retrospectives / methodology-change proposals
- Recovering discovery, planning, or original implementation failures (unchanged)
- Installing an external planning framework
- Editor-specific command files
- A second task database or a second task board
- Obsidian
- Operator-configurable publish-retry limit (V0 default is 3 publish retries)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an eligible fixture whose checks pass, a caller can finish the workflow on the start call: the returned record is `PR_CREATED` with a pull-request number and HTML URL, a pull request exists against the default branch with the five required sections and a task reference, and the published branch is the task feature branch — in one wait, not a follow-up command.
- **SC-002**: 100% of implementation/debug local commits leave the remote unchanged; 100% of feature-branch publishes and pull-request opens/updates are performed by the orchestrator after validation pass; 0% of runs merge, approve-as-human, deploy, push a protected/default branch, amend, or force-push through this workflow.
- **SC-003**: 100% of authentication/permission publish failures go `BLOCKED` with 0 diagnosis and 0 debug; 100% of transient publish failures retry publish only and stop after 3 automatic attempts; 0% of publish failures start validation recovery.
- **SC-004**: 100% of parked, failed, or blocked runs that never reached validation pass publish 0 branches and open 0 pull requests; 100% of republishes for the same work branch update one pull request (rewrite title and body, plus new commits) rather than opening a second.
- **SC-005**: Operators can prove authentication, fetch, and feature-branch publish from the same runtime environment that executes the workflow, without private credentials stored in that environment’s image; 0 secrets appear in execution records or pull-request bodies.
- **SC-006**: 100% of overlapping starts are refused while a workflow is active; `PR_CREATED` and `FAILED` release the slot; 100% of published file changes originated in the isolated copy; 0% of runs modify methodology or rewrite the human-readable task body with publish churn.
- **SC-007**: A reviewer can complete seven contract checks — PIV-complete then `PR_CREATED` with required pull-request body, builder-never-publish, merge and protected-push refused, idempotent pull-request update, no publish before validation pass, auth-fail → `BLOCKED` without diagnosis, simulated-remote checks without a live hosting account — and each check fails if that behavior breaks. A separate live-container authentication proof is required for phase-complete against a real remote and MUST use a disposable or operator-named non-critical repository.

## Assumptions

- **This phase is GitHub on top of recovery.** Methodology adapter, project registry, workspace manager, agent execution, PIV chain, and recovery already exist. This feature adds orchestrator-owned publish, `PR_CREATED`, SSH-from-container, and a hard merge/protected-push ban. It does not start messaging or restart persistence.
- **Success wait-return is `PR_CREATED`.** Previous phases returned `COMPLETED` at PIV-complete. That is no longer sufficient. History MAY still record a PIV-complete/`COMPLETED` moment immediately before publish so reviewers can see validation passed before hosting ran.
- **Task-complete (V0 GitHub checklist) means**: implementation exists, validation passed, working tree clean except intentional artifacts, feature branch exists, commit exists, branch is published, pull request exists. Only then `PR_CREATED`.
- **Builder must not push.** The executor already forbids publish in the implementation role. This phase adds a positive orchestrator publish step and keeps that forbid.
- **PR update is in scope; merge is not.** The V0 plan allows creating and updating pull requests and pushing additional feature commits. It forbids merge, human-equivalent approval, and deploy. Update means: push feature-branch commits **and** rewrite title and body on every publish.
- **SSH, not baked keys.** Prefer host SSH agent forwarding into the container. Equivalent runtime secret mounts are acceptable. Copying private keys into images is forbidden. The shipped control-plane runtime MAY be updated in this phase to mount/forward that agent. The previous phase’s compose freeze does not apply to this SSH-forwarding change.
- **github.com only.** Live remotes and live SSH proofs use github.com. Other Git hosts are out of scope.
- **Pull-request identity** is the hosting PR number plus HTML URL on the existing operational record. No new table.
- **Three publish retries** for transient hosting/network failures only. Auth/permission failures do not consume that budget as “try diagnosis”; they block immediately. The limit is not operator-configurable in this phase.
- **Blocked publish options stay `A`/`B`.** Same letter protocol. `B` retries publish only.
- **Simulated remote for contract checks.** “PR simulation where possible” means checks MUST prove the boundary without a live GitHub account. Live SSH/fetch/push from the container is a separate done-gate for FR-005.
- **Disposable / named non-critical only.** When a live remote is used, the operator must name it or checks use a disposable fixture. Never silently pick a production repository.
- **Telegram is the next phase.** Recording `PR_CREATED` does not send a message.
- **No second database.** Pull-request identity lives on the existing operational record / overlay. No new task table.
- **Reuse Git safety.** Workspace manager already forbids working on default/protected branches. This phase MUST call that, not reimplement it.
- **Conventional commit messages** for any orchestrator-created commit follow existing commit-style rules; exact wording is an implementation choice. Orchestrator-created commits are always **new** commits: never amend, never force-push.
- **Feature branch naming** already exists (task feature branch). This phase does not invent a second branch.
- **Default branch** is the project’s configured default (typically `main`). Pull requests target it; pushes do not.
- **No new third-party libraries** without an explicit owner request.
- **Checks** live with the existing control-plane package. One contract-check file must fail if the seven behaviors in SC-007 break. The live-container SSH proof may be a documented operator/done-check rather than the same contract file.
- **Public operation names** stay `run_workflow`, `run_next_workflow`, `resume_workflow`. GitHub is added to the existing orchestrator, not a second orchestrator that builders call.
- **Constitution invariants hold:** methodology is read-only; project knowledge stays in the project; the control plane owns operational state and GitHub workflow orchestration; the existing board is task source of truth; no merge/deploy; no silent production repo; no private keys in images.

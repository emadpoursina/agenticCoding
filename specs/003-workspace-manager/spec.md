# Feature Specification: Workspace Manager

**Feature Branch**: `003-workspace-manager`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "specify the next Phase 1 step and finish Phase 1: workspace manager, Git safety, and execution identity (isolated working copies per task, never work on protected branches, never share or reuse dirty copies, correlation identity for each run)"

## User Scenarios & Testing *(mandatory)*

Hermes is the operational control plane. A later worker must be able to change a project for one task without touching another task’s files, without editing the project’s protected default branch, and without guessing which run produced a result.

This feature finishes Phase 1 of the control plane. It prepares an isolated working copy for a single task, enforces Git safety before and after that copy is used, and stamps a correlation identity so a reviewer can later answer: which task, which project, which workspace, which run.

The people who benefit are operators of the control plane and later workflow phases that will plan, implement, and validate inside that copy. This phase does not run agents, call models, push branches, open pull requests, or send messages.

It depends on the existing project registry: only an eligible enrolled project may receive a workspace. It does not replace that registry, and it does not copy project knowledge into the control plane.

### User Story 1 - Prepare an isolated working copy for one task (Priority: P1)

An operator (or a later worker) asks: “give me a place to work on task 123 for project A.” The workspace manager resolves that project as eligible, then prepares a dedicated working copy for that task under the configured workspace root.

The copy is tied to exactly one project identity, one task identity, one feature branch, and one workspace identity. The feature branch is created from the project’s default branch and is never the protected default branch itself. Unrelated tasks do not share a mutable working copy. The enrolled project location is not used as the place where task edits happen.

**Why this priority**: Without an isolated copy and a safe feature branch, later phases cannot implement or validate without risking the default branch or another task’s work. This is the remaining foundation of Phase 1.

**Independent Test**: Point the manager at operational configuration whose workspace root is a temporary directory, and at a disposable enrolled fixture project that is a versioned repository. Prepare a workspace for a known task id. Confirm a working copy exists only for that task, on a deterministic feature branch that is not `main`, `master`, or the project’s default branch. Prepare a second task for the same project and confirm it receives a different working copy. Confirm the enrolled project location’s current branch is unchanged.

**Acceptance Scenarios**:

1. **Given** an eligible enrolled fixture project that is a versioned repository and a configured workspace root, **When** the caller prepares a workspace for task identity `123`, **Then** the result includes a working-copy location under the configured workspace root, a feature branch derived from that task identity, the project identity, and the task identity.
2. **Given** the same setup, **When** the caller prepares a workspace, **Then** the working copy’s current branch is not `main`, not `master`, and not the project’s default branch, and that feature branch was created from the project’s default branch.
3. **Given** two different task identities for the same eligible project, **When** the caller prepares a workspace for each, **Then** each task receives its own working-copy location and the two copies are not the same mutable directory.
4. **Given** a successful prepare, **When** the caller inspects the enrolled project location, **Then** that location’s current branch is unchanged and task edits are not required to happen there.
5. **Given** configuration whose workspace root is missing, empty, or not a directory, **When** the caller prepares a workspace, **Then** the call fails at the trust boundary with a visible error and does not substitute a hardcoded workstation path.

---

### User Story 2 - Refuse unsafe Git situations (Priority: P1)

The workspace manager is the Git safety boundary. It must never let a task work directly on a protected branch, never share a working copy across tasks, never reuse a dirty working copy, and never overwrite another task’s changes in order to proceed.

Before a working copy is considered ready, the manager confirms: current branch, whether files are changed, remote identity when one exists, refresh from the project’s default branch when a remote exists, and that the base branch is an allowed default (not a protected branch used as the work branch). After work (or when asked to inspect), it reports current branch, whether files are changed, and what changed.

A request to publish a protected branch must be refused even though this phase does not publish. Later Git-hosting work must not be able to skip this refusal.

**Why this priority**: A workspace that can be prepared onto `main`, reused while dirty, or shared between tasks is a data-loss failure. Safety is not optional polish on top of prepare.

**Independent Test**: Prepare a valid fixture workspace. Attempt to prepare with the work branch forced onto the default branch and confirm failure. Create uncommitted edits in an existing task workspace, ask to prepare that same task again, and confirm failure without deleting those edits and without touching a different task’s copy. Confirm two tasks never receive the same path. Ask whether publishing the default branch would be allowed and confirm it is refused.

**Acceptance Scenarios**:

1. **Given** an eligible project whose default branch is `main` (or `master`, or another declared default), **When** prepare would make the task’s work branch that protected branch, **Then** prepare fails with a distinct protected-branch error and no task edits are made on that branch.
2. **Given** an existing working copy for task `123` that has uncommitted changes, **When** the caller prepares a workspace for the same project and task again, **Then** the call fails with a visible dirty-workspace error, the uncommitted changes remain, and no other task’s files are removed or overwritten.
3. **Given** a working copy already in use for task `123`, **When** the caller prepares a workspace for a different task, **Then** the new task does not receive task `123`’s working-copy path and does not check out task `123`’s feature branch as its mutable copy.
4. **Given** any workspace whose current branch is protected (`main`, `master`, or the project’s default branch), **When** the caller asks whether that branch may be published, **Then** the answer is a refusal. This phase MUST NOT publish.
5. **Given** a valid clean workspace for task `123` on the expected feature branch, **When** the caller inspects it before or after a local file change, **Then** the inspection reports the current branch, whether files are changed, and (when files are changed) a summary of what changed.
6. **Given** a workspace path that is missing, not a versioned working copy, or belongs to a different task than the caller named, **When** the caller inspects or prepares, **Then** the call fails with a visible invalid-workspace error and MUST NOT delete or overwrite an unrelated task’s files in order to continue.

---

### User Story 3 - Stamp a correlation identity on every prepare (Priority: P1)

Every successful prepare must return a correlation identity so later logs and reviews can reconstruct what ran. The identity includes: task identity, execution identity, project identity, workspace identity, and worker identity when a worker has been assigned.

This phase does not assign workers, so worker identity may be omitted. It does not record private reasoning. It does not create a second task store or a second workspace store. It reuses the control plane’s existing workspace fields when they already exist (location, branch, project identity) and only adds identity fields the host does not already represent.

A later reviewer, given the identity, must be able to answer: which task, which project, which working copy, which run. Re-preparing a valid clean workspace for the same task keeps the workspace identity stable and allocates a new execution identity so runs remain distinguishable.

**Why this priority**: Phase 1 is incomplete if a workspace exists but a failure cannot be tied to a run. Identity is the last foundation piece before agent execution.

**Independent Test**: Prepare a fixture workspace and confirm the identity fields for task, execution, project, and workspace are present and non-empty. Prepare a second task and confirm workspace identities differ. Prepare the same task again on a valid clean copy and confirm the workspace identity is unchanged while the execution identity is new. Confirm the identity record does not include model reasoning text.

**Acceptance Scenarios**:

1. **Given** a successful prepare, **When** the caller reads the returned record, **Then** it includes non-empty task identity, execution identity, project identity, and workspace identity, and includes worker identity only if a worker was supplied.
2. **Given** two successful prepares for different tasks, **When** the caller compares identities, **Then** workspace identities differ and execution identities differ.
3. **Given** a valid clean workspace for task `123` on the expected feature branch, **When** the caller prepares that same task again, **Then** the workspace identity is the same and the execution identity is new.
4. **Given** a successful prepare, **When** the caller inspects the identity record, **Then** it does not contain private reasoning, chain-of-thought, or model transcript text.
5. **Given** the control plane already stores workspace location, branch name, and project identity for a task, **When** this feature records a workspace, **Then** it MUST reuse those fields rather than creating a second workspace or task store.

---

### Edge Cases

- **Unknown or ineligible project**: Prepare fails with the same distinct errors the project registry already uses (unknown, disabled, invalid location). This feature MUST NOT invent a project path.
- **Path-like task identity**: Identities containing `/`, `\`, `..`, or extra path segments fail at the trust boundary. The manager MUST NOT join a caller-supplied identity onto a filesystem path.
- **Empty or missing task identity**: Fail at the trust boundary. Do not invent a task id.
- **Workspace root**: Missing, empty, file-instead-of-directory, or unreadable root fails at the trust boundary. No silent substitute, including the developer’s home directory.
- **Enrolled location is not a versioned repository**: Prepare fails clearly. This phase does not create a repository from unversioned files and does not clone from a network remote.
- **Default branch missing**: Prepare fails. It MUST NOT guess a base other than the project’s declared default (with the registry’s existing `main` fallback when the project never declared one).
- **Protected work branch**: `main`, `master`, and the project’s default branch are always protected. The task’s feature branch MUST NOT be one of those names.
- **Feature branch already exists, clean, expected path**: Reuse that working copy; new execution identity; same workspace identity.
- **Feature branch already exists and is dirty**: Refuse reuse. Do not reset, clean, or discard changes automatically.
- **Feature branch already checked out in another working copy**: Fail. Do not share that mutable copy with a second task.
- **Dirty enrolled project location**: Preparing a new task working copy MUST still succeed if safety otherwise holds. Task work MUST NOT be performed in the enrolled location.
- **Unrelated existing files under the workspace root**: Prepare MUST NOT delete another task’s directory in order to create this task’s copy.
- **Inspect of a clean copy**: Reports current branch and that files are unchanged; change summary is empty or omitted.
- **No remote**: Refresh from remote is skipped; prepare may still succeed for a local fixture. Remote identity may be omitted.
- **Remote exists and refresh fails**: Prepare fails with a visible error. It MUST NOT silently continue as if the default branch were up to date.
- **Publish query on a feature branch**: This phase does not publish. The safety answer for a non-protected feature branch is “allowed later”; the safety answer for a protected branch is always refuse.
- **Worker identity omitted**: Valid in this phase. Later execution may fill it; this feature MUST NOT invent a worker name.
- **Host-specific paths**: Application behavior must not depend on a developer’s home directory layout. Mapping a host folder to the configured workspace root is an environment concern.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The manager MUST load the workspace root from operational configuration. It MUST NOT hardcode a workstation path.
- **FR-002**: The manager MUST validate the workspace root at the trust boundary (construction or first use). Missing, empty, or non-directory values MUST fail. The manager MUST NOT silently default to another path.
- **FR-003**: The manager MUST expose `prepare_workspace(project_id, task_id)` that succeeds only for an eligible project (existing `resolve_eligible_project`) and a valid task identity. The result MUST include: working-copy location, feature branch, project identity, task identity, and the correlation identity in FR-012.
- **FR-004**: `task_id` MUST be an exact non-empty identity that is not path-like (`/`, `\`, `..`, extra segments). Invalid identities MUST fail with a visible error. The manager MUST NOT join a caller-supplied identity onto a filesystem path.
- **FR-005**: Each successful prepare MUST produce (or reuse per FR-010) an isolated working copy whose location is under the configured workspace root, partitioned by project identity and task identity. Unrelated tasks MUST NOT share a mutable working copy.
- **FR-006**: The working copy MUST be a versioned checkout of the enrolled project, created from the project’s local location. Task edits MUST happen in that isolated copy, not in the enrolled location. This phase MUST NOT clone from a network remote and MUST NOT initialize a repository where none exists.
- **FR-007**: The work branch MUST be a deterministic feature branch derived from the task identity (form: `feature/task-<task_id>`). It MUST be created from the project’s default branch. It MUST NOT be `main`, `master`, or the project’s default branch.
- **FR-008**: `main`, `master`, and the project’s default branch are protected. The manager MUST refuse to use a protected branch as the task’s work branch. It MUST expose `assert_publish_allowed(branch)` that refuses those protected names. This phase MUST NOT publish any branch.
- **FR-009**: Before a working copy is returned as ready, the manager MUST confirm: current branch, whether files are changed, remote identity when a remote exists, refresh from the default branch when a remote exists, and that the work branch is not protected. A failed refresh when a remote exists MUST fail prepare.
- **FR-010**: If a working copy for the same project and task already exists, is a valid versioned copy, is on the expected feature branch, and has no uncommitted changes, prepare MUST reuse it (same workspace identity, new execution identity). If it has uncommitted changes, prepare MUST fail with a dirty-workspace error and MUST NOT discard, reset, or overwrite those changes. If it is invalid or belongs to a different task, prepare MUST fail and MUST NOT overwrite the unrelated copy.
- **FR-011**: The manager MUST expose `inspect_workspace(project_id, task_id)` returning: current branch, whether files are changed, and a change summary when files are changed. Inspect MUST fail for a missing, invalid, or mismatched working copy. It MUST NOT repair or delete that copy as a side effect.
- **FR-012**: Every successful prepare MUST return a correlation identity with: `task_id`, `execution_id`, `project_id`, `workspace_id`, and `worker_id` when supplied. `execution_id` MUST be unique per successful prepare. `workspace_id` MUST be stable for the same project+task working copy. `worker_id` MUST be omitted when no worker was supplied. The identity MUST NOT include private reasoning or model transcript text.
- **FR-013**: The manager MUST reuse the control plane’s existing workspace fields when they already exist (working-copy location, branch name, project identity). It MUST NOT introduce a second task store or a second workspace store.
- **FR-014**: Prepare MUST NOT delete or overwrite another task’s working copy in order to succeed.
- **FR-015**: The manager MUST NOT execute agents, call models, load methodology, orchestrate plan/implement/validate, push, open pull requests, merge, deploy, or send notifications.
- **FR-016**: Operational configuration other than the workspace root and the project-registry fields needed to resolve an eligible project MAY be ignored in this phase.

### Key Entities

- **Workspace root**: Configured directory under which all task working copies live. Never inferred from the developer’s machine layout.
- **Isolated working copy**: The versioned checkout for exactly one project identity and one task identity. Owner of that task’s file edits. Not the enrolled project location. Not shared with another task.
- **Feature branch**: Deterministic branch `feature/task-<task_id>`, created from the project’s default branch. Never a protected branch.
- **Protected branch**: `main`, `master`, and the project’s default branch. Must not be the work branch and must not be publishable through this feature.
- **Correlation identity**: Bundle of `task_id`, `execution_id`, `project_id`, `workspace_id`, and optional `worker_id` returned from prepare. Used later to reconstruct which run happened where. Not a second database.
- **Workspace inspection**: Point-in-time report of current branch, whether files are changed, and what changed.

### Out of Scope

This specification covers isolated working copies, Git safety, and correlation identity. Explicitly deferred:

- Agent execution, model calls, and methodology loading (already specified separately)
- Project registry and project context loading (already specified separately)
- Plan → implement → validate orchestration
- Network clone, fetch credentials, SSH, push, pull requests, merge
- Automatic cleanup or reset of dirty working copies
- Concurrent execution of more than one task at a time (isolation still required; scheduling is later)
- Container restart / interrupted-run recovery beyond reuse of a valid clean copy
- Telegram / notifications
- Learning / retrospectives
- Obsidian
- Automatic merge, production deploy, or protected-branch writes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an eligible fixture project and a valid task identity, a caller can prepare an isolated working copy on a non-protected feature branch on the first attempt without using the enrolled location as the edit directory.
- **SC-002**: 100% of attempts to use `main`, `master`, or the project’s default branch as the task work branch fail with a visible error (never a silent checkout onto a protected branch).
- **SC-003**: 100% of prepares for two different tasks receive different mutable working-copy locations (never a shared directory).
- **SC-004**: 100% of prepares that find uncommitted changes in that task’s existing copy fail without discarding those changes and without deleting another task’s files.
- **SC-005**: 100% of successful prepares return non-empty task, execution, project, and workspace identities; a second prepare of a valid clean copy keeps workspace identity stable and issues a new execution identity.
- **SC-006**: A reviewer can complete six contract checks — prepare fixture workspace, refuse protected work branch, refuse dirty reuse, refuse shared copy, inspect reports branch and change status, identity fields present — and each check fails if that behavior breaks.
- **SC-007**: 100% of publish-allowed checks for a protected branch return refuse; this phase performs 0 publishes.

## Assumptions

- **This phase finishes Phase 1.** Configuration, methodology mount, methodology adapter, and project registry already exist. This feature adds workspace manager, Git safety, and execution identity only.
- **Eligible project required.** Prepare uses the existing project registry. It does not enroll projects, load project knowledge into the control plane, or pick a production repository.
- **Local fixture, not GitHub.** Checks use a disposable versioned fixture repository. Prepare uses the enrolled local location. Network clone, SSH, and push wait for the Git-hosting phase.
- **Feature branch name** is `feature/task-<task_id>` with no extra slug. Task identities in checks are simple tokens such as `123`.
- **Layout** is under the configured workspace root, partitioned by project identity then task identity. The exact folder names inside that partition are an implementation choice as long as copies are isolated and deterministic.
- **Reuse rule**: A valid, clean, expected-branch copy for the same project+task is reused. Dirty copies are never auto-repaired. Invalid or mismatched copies are never overwritten.
- **Protected set** is always `main`, `master`, and the project’s default branch, even when the default is already `main` or `master`.
- **No remote on fixtures** is valid. Refresh is required only when a remote exists.
- **One active task later, isolated copies now.** V0 scheduling will run one task at a time. This feature still isolates copies so a second prepare cannot clobber the first.
- **Host workspace fields.** The control plane already has a place to record workspace location, branch, and project identity. This feature fills those rather than adding a second store. Correlation fields the host cannot already represent are returned on the prepare record.
- **Worker identity** is optional until a later executor assigns a worker. This phase does not invent workers.
- **No private reasoning** in identity or inspection records. This phase does not call models; the constraint exists so later logging cannot treat this record as a transcript dump.
- **Trust boundary**: Construction (or first load of workspace root) validates the root. `prepare_workspace` is the boundary for project eligibility, task identity, Git safety, and identity stamping. Invalid input fails there.
- **No new third-party libraries** without an explicit owner request. Version-control operations must use capabilities already present on the platform.
- **Checks** live with the existing control-plane package. One set of checks must fail if the six contract behaviors in SC-006 break. Tests MUST NOT depend on a live production checkout or a live Git-hosting account.
- **Public operation names** (`prepare_workspace`, `inspect_workspace`, `assert_publish_allowed`) are the agreed contract for this phase. Exact module layout inside the existing control-plane package is an implementation choice.
- **Implementation follows this spec**, then code; agent execution, PIV, Git hosting, and messaging do not start until this feature’s checks pass and a later spec/plan asks for them.

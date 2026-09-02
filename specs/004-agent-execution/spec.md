# Feature Specification: Agent Execution

**Feature Branch**: `004-agent-execution`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "specify the next step of the scratch/implimentation.md plan"

## Clarifications

### Session 2026-08-30

- Q: How should callers supply optional task fields (title, description, acceptance criteria, priority) and previous-step outputs (plan, validation) when invoking execute? → A: Optional structured payload on the same execute call (task fields + previous outputs). Identity remains name or role plus project_id and task_id. This phase does not load tasks from the host task store.
- Q: Must a discovery-role run produce the eight-section plan artifact? → A: No. Only the planning role. Discovery gathers context; planning writes the plan.
- Q: Where does a successful planning run put the plan artifact? → A: A Markdown file inside the prepared isolated working copy; its path is listed on the result's artifacts list.
- Q: How does a validation-role run obtain pass, fail, or blocked? → A: The executor runs the project's declared validation commands and sets status from those command outcomes, not from model prose.
- Q: May an implementation-role run create a git commit? → A: Yes, a local commit on the task work branch only. It must not push, open a pull request, or commit in the enrolled project location.

## User Scenarios & Testing *(mandatory)*

Hermes is the operational control plane. Phase 1 can already discover methodology, enroll a project, load that project’s instructions, and prepare an isolated working copy. Nothing yet *runs* an agent.

This feature is Phase 2: a caller can execute a named methodology agent (or a named role that maps to one) against one prepared task workspace. The executor assembles a complete context, asks the configured model service for that role, and returns a structured result. Planning writes a Markdown plan artifact in the isolated working copy. Implementation may change that copy and may create a local commit on the work branch. Validation runs the project’s own declared checks and sets status from those command outcomes.

The people who benefit are operators of the control plane and the later plan → implement → validate phase that will call this executor once per step. This phase does not chain those steps, does not retry failures, does not publish branches, does not open pull requests, and does not send messages.

Methodology remains read-only documents, not programs. The executor translates those documents plus task, project, and workspace context into one run. It does not depend on a specific editor being present. It does not install a planning framework into the control plane. It does not add agents to methodology.

### User Story 1 - Execute a named agent with a complete context (Priority: P1)

An operator (or a later workflow step) asks: “run scout on task 123 for project A.” The executor resolves that agent from methodology, confirms the project is eligible, confirms a prepared isolated working copy exists for that task, and runs once.

The agent receives a predictable context: the task (identity, title, description, acceptance criteria, priority), the project (identity, name, repository, default branch, and the already-loaded project context), the workspace (location and feature branch), the methodology location and revision, the workflow name and current phase, previous-step outputs when the caller supplied them on the execute payload (plan, validation), and supporting rules and skills for that agent. Optional task fields and previous outputs come from that payload — not from the host task store.

The returned record includes the correlation identity from prepare, with worker identity set to the agent that ran. Private reasoning is not stored on the result.

**Why this priority**: Without a single execute call that carries task, project, workspace, and methodology revision, later workflow steps cannot run. This is the remaining gap after Phase 1.

**Independent Test**: Prepare a fixture workspace for an eligible project and a known task. Point the executor at a fixture methodology that lists `scout`. Execute `scout` with a fixture task payload. Confirm the assembled context includes non-empty task, project, workspace, methodology revision (including commit identity), and agent definition. Confirm worker identity is `scout`. Omit previous-step outputs from the payload and confirm those slots are empty rather than invented. Supply a plan on the payload and confirm it is present unchanged.

**Acceptance Scenarios**:

1. **Given** an eligible fixture project, a prepared workspace for task `123`, and a fixture methodology that lists `scout`, **When** the caller executes agent `scout` for that project and task, **Then** the run proceeds and the assembled context includes task identity, project identity, workspace location, feature branch, methodology path, a non-empty methodology commit identity, and the `scout` definition.
2. **Given** the same setup, **When** the caller omits previous-step outputs from the execute payload, **Then** plan and validation slots on the context are absent (not guessed).
3. **Given** the same setup plus an explicit previous plan on the execute payload, **When** the caller executes, **Then** that plan is present on the context unchanged.
4. **Given** a successful execute, **When** the caller reads the result’s identity, **Then** it includes the prepare correlation fields and a worker identity equal to the agent that ran, and it does not include private reasoning or model transcript text.
5. **Given** a listed agent whose how-to references supporting skills, **When** the caller executes that agent, **Then** those supporting rules and skills are part of the assembled context (same contents the methodology adapter already resolves).

---

### User Story 2 - Return a structured result for planning, implementation, and validation (Priority: P1)

Every execute returns a machine-readable result. Free-form notes may exist as artifacts; execution status must not be inferred from prose alone.

The result includes: status (`success`, `failure`, or `blocked`), a short summary, any artifact locations, a next action when one is known, and a questions list (empty when none). Validation status is present when the run was a validation role.

Role outcomes on a fixture:

- **Discovery**: context gathering for a later planning run. No eight-section plan artifact is required.
- **Planning**: a Markdown plan artifact in the isolated working copy with problem understanding, scope, likely affected parts, implementation approach, acceptance-criteria mapping, validation strategy, risks, and open questions. The result lists that file path in `artifacts`.
- **Implementation**: the isolated working copy may gain file changes and may receive a local commit on the work branch. The enrolled project location is unchanged. The executor does not publish.
- **Validation**: the executor runs the project’s own declared validation commands. The result reports pass, fail, or blocked from those command outcomes, not from model prose. The executor MUST NOT invent generic checks when the project declared its own.

Roles map to methodology agents through operational configuration. Defaults: discovery → `scout`, planning → `specs-planner`, implementation → `builder`, validation → `tester`. Checks use a fixture methodology that includes those names. This phase does not add those folders to the live methodology tree. An unknown mapped name fails with the same unknown-agent error the methodology adapter already uses.

**Why this priority**: A later workflow cannot decide “plan is done, implement next” from a paragraph of text. Planning, implementation, and validation must each be independently runnable and independently checkable.

**Independent Test**: On a fixture project with declared validation checks, execute planning, then implementation with that plan on the execute payload, then validation. Confirm the plan Markdown file is in the isolated copy with the required sections, implementation changed only that copy (local commit allowed), validation status comes from the project’s own commands, and every result has an explicit status. Execute discovery and confirm no eight-section plan is required. Map planning to a name that is not in the fixture roster and confirm unknown-agent failure.

**Acceptance Scenarios**:

1. **Given** a successful execute, **When** the caller reads the result, **Then** it includes an explicit status of `success`, `failure`, or `blocked`, a summary, an artifacts list (empty if none), a next-action field (empty if none), and a questions list (empty if none). Status MUST NOT be determined only by reading summary prose.
2. **Given** a fixture methodology that lists `specs-planner` and a prepared workspace, **When** the caller executes the planning role, **Then** a Markdown plan artifact exists inside that isolated working copy, is listed on the result’s artifacts list, and includes problem understanding, scope, likely affected parts, implementation approach, acceptance-criteria mapping, validation strategy, risks, and open questions.
3. **Given** a fixture methodology that lists `builder`, a prepared workspace, and a previous plan on the execute payload, **When** the caller executes the implementation role, **Then** any file changes (and any local commit) occur only in that isolated working copy on the work branch; the enrolled project location is unchanged; no branch is published.
4. **Given** an eligible fixture project that declares its own validation checks and a fixture methodology that lists `tester`, **When** the caller executes the validation role, **Then** the executor runs those declared commands, and the result’s validation status is pass, fail, or blocked from those command outcomes. The executor MUST NOT substitute invented generic checks or infer status from model prose.
5. **Given** operational configuration that maps a role to an agent name not in the methodology roster, **When** the caller executes that role, **Then** the call fails with the same visible unknown-agent error as loading an unknown agent, and the workspace is not published.
6. **Given** a fixture methodology that lists `scout` and a prepared workspace, **When** the caller executes the discovery role, **Then** a structured result is returned and an eight-section plan artifact is not required for success.

---

### User Story 3 - Assign models by role and refuse unsafe or incomplete runs (Priority: P1)

Agent instruction documents do not name a model. Each role (planning, implementation, validation; discovery uses the planning assignment) uses the model assignment from operational configuration. Provider, location, and secrets come from configuration and the environment — never from the project repository, never from agent documents, never hardcoded.

Execute is a trust boundary. It must fail visibly when: the project is ineligible, the workspace is missing or invalid, the agent is unknown or has unresolved dependencies, required context slots the caller claimed to provide are missing, the methodology would be written, or the model assignment for that role is missing. It must not work on a protected branch, must not publish, must not merge, must not deploy, and must not depend on a specific editor.

A stand-in model service is valid for checks. A live model service is not required to prove this phase. When a real run is requested and the configured secret or location is missing, execute fails at the boundary rather than silently skipping the model.

**Why this priority**: Hardcoding a model into an agent, writing methodology, or running without a workspace would violate the constitution and make later debugging lie about what ran.

**Independent Test**: Execute planning and implementation with different configured model assignments and confirm each run is tagged with its role’s assignment (not a name copied from the agent documents). Remove the assignment and confirm failure. Attempt a methodology write through the executor and confirm failure. Execute without a prepared workspace and confirm failure. Confirm the enrolled default branch was never checked out as the work branch and that no publish occurred.

**Acceptance Scenarios**:

1. **Given** configuration that assigns different models to planning and implementation, **When** the caller executes each role, **Then** each run uses that role’s assignment. Agent instruction documents are not the source of the model name.
2. **Given** configuration that omits the model assignment for the requested role, **When** the caller executes, **Then** the call fails at the trust boundary with a visible error and does not invent a model.
3. **Given** a valid execute setup, **When** a caller attempts to create, modify, delete, or copy files under the methodology location through the executor, **Then** the executor refuses and methodology is unchanged.
4. **Given** an eligible project but no prepared workspace for the named task, **When** the caller executes, **Then** the call fails with a visible missing-workspace error and MUST NOT create a working copy as a side effect.
5. **Given** any execute, **When** the run finishes, **Then** the task’s work branch is not `main`, not `master`, and not the project’s default branch, and the executor has published 0 branches.

---

### Edge Cases

- **Unknown or reserved agent name**: Same unknown-agent failure as the methodology adapter (`template`, `_skills`, nested paths, `../`). Execute MUST NOT join a caller-supplied name onto a filesystem path.
- **Unresolved agent dependencies**: If resolving supporting skills would fail, execute fails with that same visible error and does not run a partial context.
- **Ineligible project**: Unknown, disabled, or invalid-location project fails with the project registry’s existing distinct errors. Execute MUST NOT invent a project path.
- **Missing or invalid workspace**: Missing copy, not a versioned working copy, wrong task, or protected work branch fails. Execute MUST NOT repair, reset, or overwrite an unrelated task’s copy.
- **Dirty isolated copy**: Allowed for execute (implementation is expected to leave changes). Re-prepare remains the workspace manager’s dirty-reuse refusal; this feature does not call prepare.
- **Empty previous outputs**: Valid. When the execute payload omits them, plan and validation slots stay empty.
- **Questions on the result**: Recorded on the structured result. This phase does not pause for a human and does not send a message.
- **Validation checks missing on the project**: Fail with the existing missing-project-configuration error rather than inventing checks. (Context load already requires declared validation commands.)
- **Validation checks fail**: Result status is `failure` (or `blocked` if the check cannot run). Status comes from the command outcomes. This phase does not diagnose, retry, or open a human-decision path.
- **Stand-in vs live model service**: Checks inject a stand-in that returns predetermined structured results. A live service is optional. Missing live credentials MUST fail a real configured run; they MUST NOT fail checks that injected a stand-in.
- **Live methodology lacks `specs-planner` or `builder`**: Default mapping still names them. Execute against that live tree fails unknown-agent unless the operator remaps the role in configuration to a listed agent. This phase MUST NOT add agents to methodology.
- **Planning-framework instructions**: If a planner’s how-to mentions an external planning framework, those instructions are passed through as document text. The control plane MUST NOT install that framework into itself and MUST NOT rewrite it into a control-plane-specific procedure.
- **Editor commands**: Not a runtime dependency. Absence of any particular editor MUST NOT fail execute.
- **Secrets in results or logs**: Model secrets and environment secrets MUST NOT appear in the structured result, identity record, or operational summary.
- **Host-specific paths**: Application behavior must not depend on a developer’s home directory layout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The executor MUST expose `execute_agent(name, project_id, task_id)` that runs one named methodology agent against one eligible project and one prepared workspace. It MUST NOT create the workspace; the caller MUST have already prepared it. Optional task fields (title, description, acceptance criteria, priority) and previous-step outputs (plan, validation) MUST be accepted on the same call as a structured payload. This phase MUST NOT load those fields from the host task store.
- **FR-002**: The executor MUST expose `execute_role(role, project_id, task_id)` for roles `discovery`, `planning`, `implementation`, and `validation`. Each role MUST map to an agent name from operational configuration. Defaults: `discovery` → `scout`, `planning` → `specs-planner`, `implementation` → `builder`, `validation` → `tester`. An operator MAY remap a role to any listed agent name. An unmapped or unknown mapped name MUST fail before the model is asked. The same optional structured payload as `execute_agent` MUST be accepted.
- **FR-003**: `name` MUST follow the methodology adapter’s identity rules (exact listed folder name). Unknown, reserved, and path-like names MUST fail with the same unknown-agent error. The executor MUST NOT join a caller-supplied name onto a filesystem path.
- **FR-004**: Before running, the executor MUST resolve an eligible project (existing `resolve_eligible_project`), load project context (existing `load_project_context`), inspect a prepared workspace for that project and task (existing `inspect_workspace`), load the agent, resolve its dependencies, and capture methodology revision. Any of those failures MUST fail execute with that visible error.
- **FR-005**: The assembled context MUST include: task (id, title, description, acceptance criteria, priority), project (id, name, repository, default branch), project context already loaded from the project, workspace (path, branch), methodology (path, revision), workflow name and phase, agent definition, resolved dependencies, and previous-step outputs only when the caller supplied them on the execute payload. The executor MUST NOT invent task, project, workspace, or previous-output values, and MUST NOT read them from the host task store.
- **FR-006**: Task fields the caller does not supply on the payload MAY be empty except `id`, which is required and MUST be the same identity used to prepare the workspace. Empty optional task fields MUST NOT be invented.
- **FR-007**: Every execute result MUST include explicit `status` (`success` | `failure` | `blocked`), `summary`, `artifacts` (list, possibly empty), `next_action` (possibly empty), `questions` (list, possibly empty), and the correlation identity with `worker_id` set to the agent that ran. The result MUST NOT include private reasoning, chain-of-thought, model transcript text, or secrets.
- **FR-008**: A successful planning-role run MUST write a Markdown plan artifact inside the prepared isolated working copy and list that path on the result’s `artifacts`. The file MUST contain: problem understanding, scope, likely affected parts, implementation approach, acceptance-criteria mapping, validation strategy, risks, and open questions. Missing required sections on a claimed-success planning run MUST NOT be treated as success. A discovery-role run MUST NOT be required to produce this artifact.
- **FR-009**: An implementation-role run MAY change files and MAY create a local commit only inside the prepared isolated working copy on the task work branch. It MUST NOT change the enrolled project location, MUST NOT change methodology, MUST NOT publish (push, open a pull request, or update a remote), MUST NOT merge, and MUST NOT deploy. Creating a published commit on a remote is out of scope; this phase does not own the hosting boundary.
- **FR-010**: A validation-role run MUST invoke the project’s own declared validation commands from project context. It MUST NOT invent generic checks. The result MUST include a validation status of pass, fail, or blocked derived from those command outcomes, not from model summary prose.
- **FR-011**: Model assignment MUST come from operational configuration per role (planning, implementation, validation). Discovery MUST use the planning assignment. Agent documents MUST NOT be the source of provider or model identity. Secrets MUST come from the environment or equivalent runtime configuration, never from the project repository.
- **FR-012**: Missing or empty model assignment for the requested role MUST fail at the trust boundary. The executor MUST NOT invent a model or silently skip asking the model service.
- **FR-013**: Checks MAY inject a stand-in model service that returns predetermined structured results. A live model service is not required for this phase’s contract checks.
- **FR-014**: Any executor operation that would create, modify, delete, or copy files under the methodology location MUST fail. Methodology MUST be read in place, not copied into the workspace or into the control-plane repository.
- **FR-015**: The executor MUST NOT depend on a specific editor being present. It MUST NOT “run” instruction documents as programs. It MUST NOT install an external planning framework into the control plane. Planner how-to text that refers to such a framework MUST be passed through unchanged as instructions.
- **FR-016**: The executor MUST NOT introduce a second task store, orchestrate plan → implement → validate as a chain, retry failures, classify retries, send notifications, push branches, or open pull requests.
- **FR-017**: `execute_agent` / `execute_role` is the trust boundary for this feature. Invalid project, workspace, agent, mapping, context, or model assignment MUST fail there.

### Key Entities

- **Execute payload**: Optional structured input on `execute_agent` / `execute_role`: task fields beyond `id`, plus previous-step `plan` and `validation`. Omitted slots stay empty. Not loaded from the host task store in this phase.
- **Role**: One of `discovery`, `planning`, `implementation`, `validation`. Maps to a methodology agent name through operational configuration.
- **Agent run**: A single execute of one agent against one project and one prepared workspace. Not a workflow. Not a retry loop.
- **Assembled context**: The predictable bundle given to the model service: task, project, project context, workspace, methodology revision, workflow phase, agent definition, dependencies, optional previous outputs.
- **Model assignment**: Per-role choice of which configured model to ask. Stored in operational configuration, not in agent documents.
- **Structured result**: Machine-readable outcome of one run: status, summary, artifacts, next action, questions, identity. Human-readable artifacts may exist as files; status is explicit.
- **Plan artifact**: Planning-role Markdown file in the isolated working copy with the required understanding / scope / approach / validation / risk sections. Listed on `result.artifacts`.
- **Stand-in model service**: Predetermined responder used by contract checks so this phase does not require a live model account.

### Out of Scope

This specification covers agent execution, model assignment by role, complete context, and the structured result for discovery, planning, implementation, and validation. Explicitly deferred:

- Plan → implement → validate orchestration and state transitions (next phase)
- Failure classification, bounded retry, debug loop, human-decision pause
- Git hosting: commit-to-remote, push, pull requests, merge
- SSH / credential forwarding for hosting
- Telegram / notifications
- Container restart / interrupted-run recovery
- Concurrent execution of more than one task
- Learning / retrospectives / methodology-change proposals
- Adding `builder`, `specs-planner`, or `debugger` folders to live methodology
- Installing an external planning framework into this control plane
- Editor-specific command files
- Critic / plan-reviewer as a required extra step (optional later)
- `pr-reviewer`, `task-groomer`, `project-bootstrapper` (not standard V0 execution)
- Debugger role (recovery phase)
- Obsidian
- Automatic merge, production deploy, or protected-branch writes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given an eligible fixture project, a prepared workspace, and a listed fixture agent, a caller can complete one execute on the first attempt and receive a structured result with an explicit status.
- **SC-002**: 100% of successful executes include non-empty task, project, workspace, and methodology-revision identities on the assembled context; 0% invent previous-step outputs that were not supplied.
- **SC-003**: 100% of planning-role successes write a Markdown plan artifact in the isolated working copy that contains all eight required sections and is listed on `artifacts`; a result that claims success without those sections does not count as success. Discovery-role success MUST NOT require that artifact.
- **SC-004**: 100% of implementation-role file changes and local commits are confined to the isolated working copy’s work branch; 0% of executes publish a branch or modify methodology or the enrolled project location.
- **SC-005**: 100% of validation-role runs invoke the project’s declared commands and derive validation status from those outcomes; 0% invent generic checks or infer status from model prose.
- **SC-006**: 100% of executes with unknown agent, ineligible project, missing workspace, or missing role model assignment fail with a visible error (never a guessed agent, project, workspace, or model).
- **SC-007**: A reviewer can complete seven contract checks — execute listed agent with full context from the execute payload, structured result shape, planning artifact in the isolated copy, implementation changes only the isolated copy, validation status from project commands, refuse unknown/missing inputs, refuse methodology write / publish — and each check fails if that behavior breaks.

## Assumptions

- **This phase is agent execution only.** Phase 1 (methodology adapter, project registry, workspace manager, Git safety, execution identity) already exists. This feature adds execute, role mapping, model assignment, full context, and structured results. It does not start the plan → implement → validate chain.
- **Caller prepares first.** `prepare_workspace` remains a separate call. Execute inspects the existing copy and fails if it is missing or invalid.
- **One run per call.** Chaining discovery → plan → implement → validate is the next phase. The caller MAY pass a previous plan or validation result on the execute payload; this feature does not do that automatically.
- **Dirty copies are valid for execute.** Implementation is expected to change files. Dirty-reuse rules continue to belong to prepare, not execute.
- **Local commit, no remote publish.** Implementation may leave local file changes and may create a local commit on the work branch. Hosting (push/PR) is a later phase. The builder must not publish; the executor enforces that here by never publishing.
- **Role mapping defaults** are `scout` / `specs-planner` / `builder` / `tester`. Live methodology currently lists scout and tester but may omit `specs-planner` and `builder`. Checks use a fixture tree that includes all four. Operators remap in configuration rather than this phase adding agents to methodology. Discovery gathers context; only planning writes the eight-section plan.
- **Planning-framework compatibility** means: pass the planner’s instruction documents through. Do not install that framework into the control plane. Do not rewrite it.
- **No dedicated builder in live methodology** is expected. The builder profile is a role plus a fixture agent for checks, not a new methodology owned by the control plane.
- **Model assignment** is four configuration slots conceptually (planning, implementation, validation, and later debugging). This phase uses the first three; discovery shares planning; debugging waits for recovery. Names of providers and models are configuration values, never literals in agent documents or in this spec’s required behavior.
- **Stand-in model service for checks.** Contract checks MUST NOT require a live model account or a production project. A real run without configured location/secret fails at the boundary.
- **Task payload** for checks is a small fixture description supplied on the execute call (identity, title, expected result, and acceptance criteria). This phase does not read the host task store or parse human task documents beyond those fields the context requires.
- **Workflow name** defaults to the configured default workflow (plan → implement → validate). Phase on context is the role being executed (`discovery`, `planning`, `implementation`, `validation`).
- **Reuse existing adapters.** Execute MUST call the existing methodology, registry, and workspace operations rather than duplicating discovery, context load, or Git safety.
- **No second database.** Identity and workspace fields remain the host’s existing records plus the result of this run. Execute does not read or write the host task store.
- **Trust boundary**: `execute_agent` / `execute_role`. Construction may also validate that role mapping keys and model-assignment slots are present in configuration even before a run.
- **No new third-party libraries** without an explicit owner request. Asking a model service MUST use capabilities already present on the platform.
- **Checks** live with the existing control-plane package. One set of checks must fail if the seven contract behaviors in SC-007 break. Tests MUST NOT depend on a live production checkout, a live model account, or a live Git-hosting account.
- **Public operation names** (`execute_agent`, `execute_role`) are the agreed contract for this phase. Exact module layout inside the existing control-plane package is an implementation choice.
- **Implementation follows this spec**, then code; orchestration, recovery, Git hosting, and messaging do not start until this feature’s checks pass and a later spec/plan asks for them.

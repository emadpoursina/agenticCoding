# Feature Specification: External Framework Planning Adapter

**Feature Branch**: `011-external-framework-planning`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Fill the live gap where AiNative does not contain the required planning or builder agents. Hermes must run external planning frameworks through adapters instead of copying framework agents into the read-only AiNative methodology. V0 selects one pinned external framework, initially GitHub Spec Kit, and uses it to generate the implementation plan and task list inside the isolated task worktree. Building remains a later slice. The existing Hermes model service performs the work, native framework artifacts remain the source of truth, and control-plane safety, worktree isolation, retries, GitHub, and existing PIV rules remain in force."

## Clarifications

### Session 2026-09-07

- Q: When Hermes bootstraps Spec Kit inside the isolated worktree, should those setup files stay there for later steps? → A: Keep them in the worktree with the plan and tasks.
- Q: When a live task runs the usual plan-then-build workflow, should planning use Spec Kit instead of looking for a planner agent in AiNative? → A: Yes: Spec Kit does planning and the task list; AiNative is not required to have a planner.
- Q: After Spec Kit finishes the plan and task list, what should the live workflow do next in this first slice? → A: Stop after the plan and task list; do not start building in this feature.
- Q: When planning stops after the plan and task list, how should Hermes record that outcome? → A: Show “planning complete”; free the slot so another task can run.
- Q: Before Spec Kit writes the plan and task list, should Hermes still run your AiNative discovery agent (scout) first? → A: Yes: run scout first, then Spec Kit plan and tasks.

## User Scenarios & Testing *(mandatory)*

The live AiNative methodology intentionally does not contain `specs-planner` or `builder`. This feature fills the planning gap without changing that methodology: Hermes selects one external framework, invokes it through an adapter, and keeps its native artifacts in the task’s isolated worktree. AiNative remains available for the operator’s own agents, while the control plane remains responsible for workflow, safety, state, workspaces, GitHub, and retries.

### User Story 1 - Generate a plan and task list through Spec Kit (Priority: P1)

An operator starts planning for an eligible task. Hermes first runs the operator’s AiNative discovery agent (`scout`), then uses its configured external-framework adapter to run GitHub Spec Kit’s planning and task-generation steps with the task, project, and discovery context. The Spec Kit work happens in the isolated task worktree, using Hermes’s existing configured model service. The operator does not paste framework instructions or copy framework agents into AiNative.

For V0, Spec Kit is the only selectable external framework. A planning result contains an explicit status, the native plan and task artifact paths, any questions, the next action, the provider name and pinned version, and the framework revision used. The result is usable by later Hermes steps without replacing the native files with `PLAN.md` or `TASKS.md`.

**Why this priority**: This directly removes the live planning gap while preserving the operator’s chosen methodology and the existing control plane.

**Independent Test**: Use an isolated disposable worktree and a fixture Spec Kit runtime/model service. Start planning and task generation, then confirm both native artifacts exist inside that worktree, their paths are returned, the enrolled project root and AiNative are unchanged, and no builder or implementation step runs.

**Acceptance Scenarios**:

1. **Given** an eligible task, project context, isolated task worktree, and the active Spec Kit provider, **When** Hermes runs the V0 planning slice, **Then** Spec Kit produces its native implementation plan and task list, and the normalized result lists their paths and identifies the provider, pinned version, and framework revision.
2. **Given** the same setup, **When** the operator does not paste framework agents or planning artifacts, **Then** Hermes supplies the existing task/project/workspace context through the adapter and planning proceeds without reading `specs-planner` from live AiNative.
3. **Given** a successful planning result, **When** a later step reads its artifacts, **Then** it receives the native framework paths and contents unchanged; Hermes does not create a second canonical plan or task list.
4. **Given** a planning run, **When** it finishes, **Then** no framework implementation/build step, builder agent, publish, merge, or deployment runs as part of this feature.
5. **Given** a live plan-then-build workflow with Spec Kit selected as the active framework, **When** Hermes reaches planning, **Then** it uses the Spec Kit adapter for plan and task-list generation and MUST NOT fail because live AiNative lacks `specs-planner`.
6. **Given** a successful Spec Kit plan and task list in a live workflow, **When** that slice returns, **Then** Hermes records a visible “planning complete” outcome, MUST NOT start implementation, validation, or GitHub publish, MUST NOT treat the run as a finished build-and-check workflow, and MUST free the single-task slot so another task can start.
7. **Given** an eligible live workflow with Spec Kit selected, **When** the operator starts the task, **Then** Hermes runs AiNative discovery (`scout`) first and only then Spec Kit plan and task generation.

---

### User Story 2 - Bootstrap Spec Kit only inside the task worktree (Priority: P1)

An enrolled project may not already be enabled for Spec Kit. Hermes makes the project ready automatically as part of the same isolated task worktree, then runs the requested planning slice. The enrolled project root is never used for bootstrap or planning, and Hermes does not create a second planning workspace.

**Why this priority**: Automatic bootstrap makes the adapter usable across enrolled projects without asking operators to install or copy framework files manually, while preserving workspace safety.

**Independent Test**: Run against a disposable project worktree with no Spec Kit setup. Confirm setup and native planning files appear only in the isolated worktree. Repeat with a project that is already enabled and confirm Hermes reuses the existing setup rather than creating another workspace.

**Acceptance Scenarios**:

1. **Given** an isolated task worktree that is not Spec Kit-enabled, **When** Hermes starts the planning slice, **Then** it bootstraps Spec Kit in that worktree and continues to native planning/task generation.
2. **Given** an enrolled project root and its isolated task worktree, **When** bootstrap or planning writes files, **Then** all writes are confined to the isolated worktree; the enrolled root, AiNative methodology, and control-plane task store are unchanged.
3. **Given** a project already enabled for Spec Kit, **When** Hermes starts planning, **Then** it uses that worktree’s native setup with the pinned runtime and does not create a second planning workspace or a second task store.
4. **Given** a successful bootstrap, **When** planning and task generation finish, **Then** the Spec Kit setup files remain in that isolated worktree together with the native plan and task artifacts; Hermes MUST NOT delete them as a cleanup step.
5. **Given** bootstrap or planning cannot complete, **When** the adapter returns, **Then** the result is a visible failure or blocked outcome with no fabricated artifact paths and no later implementation step.

---

### User Story 3 - Select one provider while preserving a future lifecycle (Priority: P1)

An operator configures one active external framework identity and pinned version for Hermes. The same provider selection applies to all external-framework steps in V0; the operator cannot select one framework for planning and another for tasks. AiNative remains the separate provider for the operator’s own agents. The adapter contract carries a stable role/context in and normalized result out so the full selected framework lifecycle can be added later without copying its agents into AiNative.

**Why this priority**: A single active provider keeps V0 understandable and safe, while the stable boundary prevents this first planning slice from becoming a one-off integration that must be replaced later.

**Independent Test**: Load valid configuration with Spec Kit selected and confirm a planning request uses that provider for every external-framework step. Load configuration with two active frameworks, a missing pin, or a different unsupported active provider and confirm rejection before any model or framework work starts.

**Acceptance Scenarios**:

1. **Given** configuration with exactly one active framework id and pinned version, **When** Hermes builds a workflow, **Then** external-framework steps use that provider and the normalized result carries provider name, version, and framework revision.
2. **Given** configuration naming two active external frameworks, **When** Hermes loads configuration, **Then** it fails visibly at the trust boundary and starts zero framework or model runs.
3. **Given** an active framework plus AiNative roles, **When** a workflow is assembled, **Then** its steps may identify the active framework, AiNative, or project validation, while AiNative remains read-only and is not treated as the generic external-framework adapter.
4. **Given** a later lifecycle request such as specify, clarify, or implement, **When** the provider boundary receives that request, **Then** the contract has a place for the lifecycle step, but this feature executes only planning and task generation; later lifecycle behavior is not silently substituted or run early.

---

### User Story 4 - Operate safely with fixtures and existing PIV controls (Priority: P1)

An operator or maintainer can verify the adapter without a live GitHub account, live model, production repository, or live AiNative mount. The adapter uses Hermes’s existing model service and control-plane safety rules. It does not add a second task store, fork Hermes, install a framework into the control plane’s Python environment, or publish work.

**Why this priority**: Framework execution touches files and model services. Fixture-based checks must prove the boundary before any real project or external credential is used.

**Independent Test**: Run focused contract checks with temporary disposable worktrees, a pinned-runtime fixture, and a stand-in model service. Confirm no live network or production repository is needed, then run the existing checks and style checks without changing AiNative.

**Acceptance Scenarios**:

1. **Given** fixture task, project, worktree, runtime, and model inputs, **When** adapter checks run, **Then** they prove planning, task artifacts, bootstrap isolation, normalized results, and safety without contacting GitHub, a live model, or a production repository.
2. **Given** a valid planning run, **When** the adapter requests changes, **Then** all changes remain in the isolated task worktree and the existing builder-never-publish, protected-branch, retry, state, and PIV rules remain authoritative.
3. **Given** the live AiNative tree, **When** the feature is implemented or exercised, **Then** no `specs-planner`, `builder`, or other framework agent folder is added, copied, or modified there.
4. **Given** a completed delivery, **When** an operator reads the documentation and version history, **Then** they can find how the active provider is configured, how fixture checks run, which native artifacts are produced, and which credentials remain outside the repository.

### Edge Cases

- **No active framework**: Configuration fails before any planning or model run. Hermes does not fall back to an AiNative planner or manual paste path in V0.
- **Live workflow planning**: With Spec Kit selected, planning and task-list generation MUST go through the adapter. Missing live AiNative `specs-planner` is expected and MUST NOT fail the planning slice. Discovery still requires the AiNative `scout` agent; a missing or failing scout MUST follow existing Hermes errors and MUST NOT start Spec Kit.
- **Two active frameworks**: Configuration is rejected before execution. Multiple adapter implementations may exist in code, but runtime selection has exactly one active external framework.
- **Unsupported provider or missing pinned version**: The workflow fails visibly at the trust boundary; it does not download a replacement or silently use another provider.
- **Pinned runtime unavailable or version-mismatched**: The adapter fails before model work and reports the provider/runtime problem without installing into the project or control plane.
- **Project is not enabled**: Bootstrap occurs in the existing isolated task worktree only. Missing or invalid worktree fails; Hermes does not bootstrap in the enrolled root or create a second planning workspace. After a successful planning slice, bootstrap/setup files MUST remain in that worktree with the native plan and task files; they MUST NOT be stripped as temporary scaffolding.
- **Framework output path escapes the isolated worktree**: Treat the result as unsafe and fail without passing the path onward.
- **Native plan or task artifact is missing, unreadable, or not returned**: Do not claim success; return a visible failure or blocked result with no guessed replacement path.
- **Framework asks a consequential question**: Preserve the questions and next action in the normalized result and let existing Hermes decision/state rules handle it. Do not invent an answer.
- **Framework runtime or model fails**: Return a visible failure; existing Hermes retry and recovery rules decide whether and how to retry. The adapter does not add a second recovery machine.
- **Framework attempts to write AiNative, the enrolled project root, control-plane state, or another task’s worktree**: Refuse the operation and leave those locations unchanged.
- **Task or project context is incomplete**: Fail at the existing trust boundary rather than inventing requirements, project instructions, or output artifacts.
- **Secrets appear in framework output or result metadata**: Remove or reject the unsafe result; secrets, tokens, and private keys must not enter artifacts, state, notices, or logs.
- **Builder role is requested during this slice**: Do not invoke a builder or framework implementation lifecycle. Building remains a later feature and no publish occurs.
- **Live network is unavailable during fixture checks**: Checks continue with fixtures and stand-ins; they do not require GitHub, live model service, or production repositories.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hermes MUST support one active external-framework selection consisting of a framework id and pinned version. V0 MUST support GitHub Spec Kit (`https://github.com/github/spec-kit`) as the only active external framework.
- **FR-002**: Configuration MUST reject zero active external frameworks, two or more active external frameworks, an unsupported active framework, or a missing/empty version pin before any framework or model work starts. V0 MUST NOT select a different external provider per role.
- **FR-003**: The external-framework boundary MUST accept stable workflow context including the requested lifecycle step, task context, project context, isolated worktree, active provider identity, and configured model assignment, and MUST return a normalized result containing status, artifact paths, questions, next action, provider name, provider version, and framework revision.
- **FR-004**: Hermes MUST support workflow steps identified as the active external framework, AiNative, or project validation. The control plane MUST retain ownership of workflow sequencing, safety, workspaces, operational state, GitHub, retries, and human-decision handling. For V0 live runs with Spec Kit selected, sequencing MUST be AiNative discovery (`scout`), then Spec Kit plan generation, then Spec Kit task-list generation, then stop at “planning complete”.
- **FR-005**: V0 MUST execute only Spec Kit implementation-plan generation and task-list generation through the active external-framework adapter. When the active framework is configured, the live plan-then-build workflow MUST use that adapter for those steps and MUST NOT require a planner agent in live AiNative. After a successful plan and task list, the workflow MUST stop with a visible “planning complete” outcome, MUST free the single-task slot, and MUST NOT start implementation, validation, or GitHub publish. That outcome MUST NOT be the same as a finished build-and-check workflow (including PIV-complete or pull-request-created). Building, framework implementation, publishing, merging, deployment, and later Spec Kit lifecycle steps MUST remain out of scope for this feature.
- **FR-006**: Spec Kit planning MUST run with Hermes’s existing configured model service. It MUST NOT launch Cursor or Claude Code as a separate agent runtime, use a framework-owned model runtime, hardcode a provider/model, or require a manual paste path.
- **FR-007**: The Spec Kit runtime MUST be preinstalled and version-pinned in the Hermes execution environment. Hermes MUST NOT install it per project, download it per run, or call an external planning API. This feature MUST NOT add Spec Kit as a personalAgent control-plane Python dependency when the pinned runtime is provided by the Hermes environment.
- **FR-008**: Every framework operation MUST run only inside the already prepared isolated task worktree. The enrolled project root, a second planning workspace, another task’s worktree, and the control-plane repository MUST NOT be used as framework working locations.
- **FR-009**: If the target project is not Spec Kit-enabled, Hermes MUST bootstrap Spec Kit automatically inside the isolated task worktree before planning. Bootstrap MUST not modify the enrolled root, AiNative, the control-plane task store, or another worktree. After planning and task generation, those setup files MUST remain in the same worktree with the native plan and task artifacts so later steps can reuse them. This feature MUST NOT remove them as a cleanup step and MUST NOT copy them into the enrolled project root.
- **FR-010**: Hermes MUST preserve Spec Kit’s native plan and task files as the source of truth and pass their paths to later steps. It MUST NOT convert them into `PLAN.md` or `TASKS.md` as a second canonical artifact and MUST NOT introduce a second task store or write `kanban.db` for this feature.
- **FR-011**: A successful V0 planning result MUST include usable paths for the native implementation plan and native task list, and those paths MUST resolve inside the isolated worktree. Missing, unreadable, fabricated, or escaping paths MUST prevent a success result.
- **FR-012**: The normalized result MUST use the existing explicit outcome shape (`success`, `failure`, or `blocked`) and MUST contain artifact paths, questions (possibly empty), next action (possibly empty), provider name/version, and framework revision. It MUST NOT contain private reasoning, model transcript text, or secrets.
- **FR-013**: Framework revision MUST identify the exact pinned framework/runtime snapshot used for the operation. A result MUST NOT claim a revision that was not available from the configured runtime.
- **FR-014**: The adapter MUST use the existing AiNative adapter only for AiNative methodology roles. AiNative MUST remain read-only. This feature MUST NOT add, copy, or modify `specs-planner`, `builder`, or any external-framework agent folder in live AiNative.
- **FR-015**: Builder-never-publish, isolated-worktree, protected-branch, no-merge, no-deploy, no-secrets, and existing PIV safety rules MUST remain enforced. This feature MUST NOT create a second orchestrator, recovery machine, task database, queue, or control plane.
- **FR-016**: Adapter failures, framework questions, and missing inputs MUST flow through existing Hermes workflow state and retry/decision rules. The adapter MUST NOT silently retry, invent defaults, bypass a human decision, or mark a run successful after a partial framework operation.
- **FR-017**: Focused automated checks MUST use temporary disposable worktree/project fixtures, a pinned-runtime fixture, and a stand-in model service. They MUST NOT require github.com, a live model, a production repository, a live Kanban board, or a writable live AiNative tree. Existing checks and style checks MUST remain passing.
- **FR-018**: Delivery MUST land in `personalAgent/` and its existing test/documentation surfaces, and MUST update operator documentation and `CHANGELOG.md` with the real change, usage/configuration guidance, native artifact behavior, fixture check commands, and external credentials that remain outside git.
- **FR-019**: The adapter contract MUST allow the full selected framework lifecycle to be added later (including specify, clarify, plan, tasks, and implement) without changing the stable context/result boundary. This feature MUST implement only plan and tasks.

### Key Entities *(include if feature involves data)*

- **Active external framework**: The single runtime-selected framework identity and pinned version used for all external-framework steps in V0.
- **External-framework adapter**: Hermes’s provider boundary that receives stable workflow context, invokes the active framework in the isolated worktree, and returns a normalized result. It is not the AiNative adapter.
- **Framework runtime**: The preinstalled, version-pinned Spec Kit capability available in the Hermes environment. It is not installed into a project or the control plane per run.
- **Native framework artifacts**: The active framework’s plan and task-list files in the isolated worktree. Their paths and contents remain the source of truth for later steps.
- **Normalized framework result**: The explicit status, artifact paths, questions, next action, provider name/version, and framework revision returned to Hermes without private reasoning or secrets.
- **Workflow provider step**: One workflow step delegated to the active framework, AiNative, or project validation while Hermes retains control of sequencing and safety.
- **Isolated task worktree**: The only location where bootstrap and framework planning may read or write for a task. It is distinct from the enrolled project root and every other task worktree.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful V0 planning fixtures, Hermes produces both a native implementation plan and a native task list inside the isolated task worktree, returns both paths, and identifies the exact provider version and framework revision used.
- **SC-002**: In 100% of fixture runs, framework bootstrap and planning write zero files to the enrolled project root, live AiNative, the control-plane repository, another task worktree, or a second planning workspace.
- **SC-003**: In 100% of configurations with zero or multiple active external frameworks, missing pins, unsupported providers, or unavailable pinned runtimes, Hermes starts zero framework and model runs and reports a visible boundary failure.
- **SC-004**: 100% of native framework artifacts passed to later steps remain the framework-owned files; zero runs create a competing canonical plan, task list, task database, or `kanban.db` write for this feature.
- **SC-005**: 100% of V0 requests use Hermes’s existing configured model service; zero requests launch a separate Cursor/Claude Code runtime, use a framework-owned model runtime, or download a framework at run time.
- **SC-006**: 100% of builder, publish, merge, deploy, protected-branch, AiNative-write, and secret-leak safety checks remain blocked by the existing Hermes controls; this feature adds zero successful operations in those forbidden categories.
- **SC-007**: All focused fixture checks pass without github.com, live model credentials, production repositories, live Kanban data, or a writable live AiNative mount, and all existing checks and style checks remain passing.
- **SC-008**: An operator can follow the delivered documentation to configure the single active provider, run the fixture checks, locate native plan/task artifacts, and identify all credentials that must remain outside the repository.
- **SC-009**: In 100% of live-style fixture workflows with Spec Kit selected, planning and task-list generation succeed without a `specs-planner` folder in the methodology tree; 0% of those runs look up or require that agent.
- **SC-010**: In 100% of successful V0 live-style planning fixtures, the recorded outcome is “planning complete”, the slot is free for another task, and 0 implementation, validation, or publish steps run; 0% of those runs are recorded as a finished build-and-check workflow.
- **SC-011**: In 100% of successful V0 live-style fixtures, AiNative discovery runs before any Spec Kit plan or task generation; 0% of those runs start Spec Kit first or skip discovery.

## Assumptions

- **Spec Kit is the only V0 external provider.** The adapter boundary is provider-neutral for future lifecycle expansion, but runtime configuration cannot select another provider or more than one provider in this slice.
- **Discovery still uses AiNative.** Before Spec Kit plan and task generation, the live workflow MUST run the existing discovery agent (`scout`). Spec Kit does not replace discovery in this slice. If discovery parks on questions or fails, existing Hermes decision and failure rules apply and Spec Kit MUST NOT start.
- **The isolated worktree already exists or is prepared by existing workspace controls.** This feature may bootstrap Spec Kit within that worktree but does not replace workspace management.
- **Bootstrap means the normal Spec Kit project setup in the target worktree.** Setup files remain in that worktree with the native plan and task artifacts for later steps. They are not temporary scaffolding, not AiNative methodology, and not control-plane state. This feature does not copy them to the enrolled project root and does not publish them by itself.
- **Native output names and locations belong to Spec Kit.** The adapter records and passes the paths it receives rather than imposing `PLAN.md`, `TASKS.md`, or another Hermes naming convention.
- **Planning/task generation can consume the current task’s structured goal and available project context.** If the active Spec Kit runtime requires an input that Hermes cannot provide, the adapter fails visibly rather than inventing it.
- **Framework questions are existing Hermes questions.** They become normalized questions and next action; existing human-decision and retry behavior determines what happens next.
- **The configured Hermes model service is the only model executor.** Model names, provider names, locations, and secrets come from runtime configuration and environment, never from AiNative documents or project artifacts.
- **The pinned runtime is supplied by the Hermes image/environment.** No per-project package install, per-run download, external API, or personalAgent dependency is needed.
- **AiNative remains read-only methodology.** Missing live `specs-planner` and `builder` folders are expected and are not repaired by copying framework agents into AiNative. With the active framework configured, live planning and task-list generation use that adapter, not an AiNative planner. `AiNativeAdapter` remains one provider, not the generic external-framework adapter.
- **Building is a later slice.** After successful plan and task-list generation, this feature records “planning complete”, frees the slot, and stops. It does not start implementation, validation, or GitHub publish, and it does not treat the run as a finished build-and-check workflow.
- **Hermes remains the control plane.** Existing PIV, isolated worktree, GitHub, retry, state, safety, and human-authority rules remain in force; no fork, second task store, or `kanban.db` write is introduced.
- **Fixtures are disposable and offline-capable.** Contract checks use temporary worktrees and stand-ins. They never require live github.com, a live model, a production repository, a live Kanban file, or production credentials.
- **Credentials remain outside git.** Any model, GitHub, or messaging credentials needed by later live operation are supplied through existing runtime configuration and documented without being stored in artifacts, operational records, notices, or the repository.

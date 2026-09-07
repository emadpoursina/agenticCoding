---

description: "Task list for the External Framework Planning Adapter"
---

# Tasks: External Framework Planning Adapter

**Input**: Design documents from `/specs/011-external-framework-planning/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Tests**: Focused fixture tests are required by FR-017 and the implementation plan. They must remain offline and use disposable worktrees, a pinned-runtime fixture, and a stand-in model service.

**Organization**: Tasks are grouped by user story so each increment can be implemented and tested independently after the shared foundation is complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the disposable framework and methodology fixtures used by the focused checks.

- [X] T001 [P] Create the scout-only AiNative fixture in `personalAgent/tests/fixtures/ainative/manifest.yaml` and `personalAgent/tests/fixtures/ainative/agents/scout.md`; omit `specs-planner`, `builder`, and all external-framework agent folders.
- [X] T002 [P] Create the pinned Spec Kit runtime fixture in `personalAgent/tests/fixtures/speckit-runtime/manifest.json` and `personalAgent/tests/fixtures/speckit-runtime/setup/.specify/integrations/speckit.manifest.json`, including provider id, version, revision, and the setup marker copied into disposable task worktrees.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the provider-neutral contract, trust-boundary validation, model seam, and durable record support required by every user story.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [X] T003 Define `FrameworkIdentity`, lifecycle-step validation, `ExternalFrameworkContext`, `ExternalFrameworkResult`, and the `ExternalFrameworkAdapter` protocol in `personalAgent/src/hermes_kanban/external_framework.py`.
- [X] T004 Implement active-provider configuration parsing, exactly-one-provider validation, V0 `github-spec-kit` selection, runtime path-environment validation, and manifest identity/revision matching in `personalAgent/src/hermes_kanban/external_framework.py`.
- [X] T005 Implement normalized-result validation in `personalAgent/src/hermes_kanban/external_framework.py`, rejecting missing, unreadable, non-regular, escaping, or secret-bearing artifact paths and preventing fabricated success results.
- [X] T006 Extend the model-service context seam and add the validated external-framework execution context types in `personalAgent/src/hermes_kanban/executor.py`, while preserving the configured model assignment and avoiding any AiNative planner/builder lookup for framework steps.
- [X] T007 Extend `WorkflowRecord` and terminal-state handling in `personalAgent/src/hermes_kanban/orchestrator.py`, and add backward-compatible `external_result` overlay serialization/deserialization in `personalAgent/src/hermes_kanban/persist.py`.
- [X] T008 Export the provider contract, adapter, result, and new workflow symbols from `personalAgent/src/hermes_kanban/__init__.py` without adding a second task store or control-plane dependency.

**Checkpoint**: The provider identity, runtime manifest, result safety, model seam, and overlay schema are ready for story-specific execution.

---

## Phase 3: User Story 1 - Generate a plan and task list through Spec Kit (Priority: P1) 🎯 MVP

**Goal**: Run AiNative discovery first, then use the active Spec Kit adapter and Hermes model service to produce native plan and task artifacts without requiring `specs-planner` or starting implementation.

**Independent Test**: In a disposable worktree with the scout-only methodology fixture and a matching pre-enabled Spec Kit fixture, run the planning slice and verify model-call order `discovery → plan → tasks`, native artifact paths, unchanged AiNative/project root, and zero builder/implementation/validation/publish calls.

### Tests for User Story 1

- [X] T009 [US1] Add focused failing fixture checks in `personalAgent/tests/test_external_framework_planning.py` for scout-before-framework ordering, absence of live `specs-planner`/`builder` lookup, native plan/task paths, provider metadata, unchanged source locations, and the absence of implementation or publish calls.

### Implementation for User Story 1

- [X] T010 [US1] Implement `SpecKitAdapter` in `personalAgent/src/hermes_kanban/speckit.py` to execute only `plan` and `tasks` through the existing `ModelService`, materialize Spec Kit-owned native outputs, preserve questions and next actions, and return normalized provider/version/revision metadata.
- [X] T011 [US1] Implement `AgentExecutor.execute_framework` in `personalAgent/src/hermes_kanban/executor.py`, validating task/project/worktree/branch/model inputs and constructing external context without calling `AiNativeAdapter.get_agent` for framework lifecycle steps.
- [X] T012 [US1] Integrate the live planning branch in `personalAgent/src/hermes_kanban/orchestrator.py` as `scout → external plan → external tasks → PLANNING_COMPLETE`, storing both native paths, leaving validation pending, freeing the slot, and skipping implementation, validation, GitHub, merge, and deployment.
- [X] T013 [US1] Connect the validated provider adapter to live construction and print the operator-visible `planning complete` outcome in `personalAgent/src/hermes_kanban/runtime.py`; ensure the live path uses the native Kanban board and does not fall back to an AiNative planner.

**Checkpoint**: User Story 1 is independently testable with a pre-enabled worktree and stops at a distinct, free-slot planning outcome.

---

## Phase 4: User Story 2 - Bootstrap Spec Kit only inside the task worktree (Priority: P1)

**Goal**: Bootstrap or reuse matching Spec Kit setup in the already prepared task worktree, retain it with native artifacts, and fail closed on mismatch or unsafe locations.

**Independent Test**: Run the adapter against an unconfigured disposable worktree and an already configured worktree; verify setup appears or is reused only below the task worktree, remains after success, and never changes the enrolled root, runtime source, AiNative fixture, overlay, or sibling worktree.

### Tests for User Story 2

- [X] T014 [US2] Extend `personalAgent/tests/test_external_framework_planning.py` with bootstrap-isolation, matching-setup reuse, mismatched-setup rejection, setup-retention, invalid-worktree, and partial-failure checks using disposable directories and byte-for-byte source snapshots.

### Implementation for User Story 2

- [X] T015 [US2] Implement Spec Kit runtime bootstrap and reuse in `personalAgent/src/hermes_kanban/speckit.py`, copying only the pinned setup bundle below the prepared worktree, rejecting mismatched markers, retaining setup files after plan/tasks, and performing no per-run install, download, or second workspace creation.
- [X] T016 [US2] Enforce resolved worktree containment and write restrictions for bootstrap, native inputs, and returned artifacts in `personalAgent/src/hermes_kanban/external_framework.py` and `personalAgent/src/hermes_kanban/speckit.py`, including refusal of enrolled-root, control-plane, AiNative, runtime-source, sibling-worktree, and path-escape writes.

**Checkpoint**: User Stories 1 and 2 work with both pre-enabled and unconfigured task worktrees, while native setup remains available for later lifecycle steps.

---

## Phase 5: User Story 3 - Select one provider while preserving a future lifecycle (Priority: P1)

**Goal**: Enforce one active pinned provider for every external-framework step, retain provider-neutral lifecycle names, and keep AiNative as a separate read-only provider.

**Independent Test**: Load valid Spec Kit configuration and verify plan/tasks share one identity; load zero-active, multiple-active, unsupported, missing-pin, missing-runtime, and mismatched-revision configurations and verify rejection before any model or framework call.

### Tests for User Story 3

- [X] T017 [US3] Add provider-selection and lifecycle-boundary checks to `personalAgent/tests/test_external_framework_planning.py` for valid identity reuse, zero/multiple active providers, unsupported ids, empty pins, unavailable or mismatched runtimes, and rejection of `specify`, `clarify`, and `implement` execution in V0.

### Implementation for User Story 3

- [X] T018 [US3] Wire active-provider and pinned-runtime validation into `AgentExecutor.from_config` and `PivOrchestrator.from_config` in `personalAgent/src/hermes_kanban/executor.py` and `personalAgent/src/hermes_kanban/orchestrator.py`, and ensure `personalAgent/src/hermes_kanban/runtime.py` performs all checks before creating a model request.
- [X] T019 [US3] Preserve the stable lifecycle boundary and one provider identity across both plan and tasks in `personalAgent/src/hermes_kanban/external_framework.py` and `personalAgent/src/hermes_kanban/speckit.py`, returning visible unsupported-step results without silently substituting or running later lifecycle behavior.

**Checkpoint**: Configuration is fail-closed at the trust boundary, and the same provider identity governs every V0 external-framework operation.

---

## Phase 6: User Story 4 - Operate safely with fixtures and existing PIV controls (Priority: P1)

**Goal**: Prove the adapter preserves Hermes safety, retry, state, PIV, GitHub, no-secret, and read-only AiNative controls without live credentials or repositories.

**Independent Test**: Run the focused offline checks with fixtures and stand-ins, then inspect the resulting worktree and overlay to confirm only native planning artifacts and retained setup exist and no forbidden operation was called.

### Tests for User Story 4

- [X] T020 [US4] Complete safety assertions in `personalAgent/tests/test_external_framework_planning.py` for secret redaction/rejection, unsafe result paths, no `PLAN.md`/`TASKS.md` aliases, no `kanban.db` writes, no live-network requirement, preserved questions/failures, free-slot reuse, and zero implementation/validation/GitHub operations.

### Implementation for User Story 4

- [X] T021 [P] [US4] Provision the pinned Spec Kit `v1.0.1` runtime and its exact revision manifest at build time in `personalAgent/docker/Dockerfile`, exposing the configured runtime directory without installing Spec Kit into the Python package or project worktrees.
- [X] T022 [US4] Update operator configuration and delivery documentation in `personalAgent/config/default.yaml` and `personalAgent/README.md` with the single-provider setup, runtime environment variable, fixture commands, native artifact locations, planning-only behavior, and credentials that remain outside git.
- [X] T023 [US4] Record the delivered feature version and changes in `personalAgent/CHANGELOG.md`, and update the package version in `personalAgent/src/hermes_kanban/__init__.py` and `personalAgent/pyproject.toml` according to the existing semantic-versioning scheme.

**Checkpoint**: Fixture checks demonstrate that external planning stays inside Hermes’s existing control-plane safety boundaries.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature against the documented offline workflow and existing quality gates.

- [X] T024 [P] Run the focused and full test suites from `personalAgent/` with `uv run pytest tests/test_external_framework_planning.py` and `uv run pytest`, fixing any regressions in the touched implementation or fixture files.
- [X] T025 [P] Run `uv run ruff check src tests` from `personalAgent/`, resolving lint or import issues without adding dependencies or unrelated refactors.
- [X] T026 Validate every command and expected outcome in `specs/011-external-framework-planning/quickstart.md` against the implemented fixture/runtime behavior, including offline execution, native artifact paths, retained setup, planning-complete output, and no forbidden writes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; fixture files can be created in parallel.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user-story work because every story uses the provider contract, runtime identity, result validation, model seam, and durable record shape.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP planning path using a pre-enabled worktree.
- **User Story 2 (Phase 4)**: Depends on the adapter from User Story 1; adds automatic bootstrap, reuse, retention, and stricter isolation for unconfigured worktrees.
- **User Story 3 (Phase 5)**: Depends on Foundational and the live construction path from User Story 1; makes provider selection and lifecycle boundaries fail-closed.
- **User Story 4 (Phase 6)**: Depends on the completed adapter, orchestration, bootstrap, and provider-selection behavior; adds production runtime provisioning, safety coverage, and operator documentation.
- **Polish (Phase 7)**: Depends on all desired user stories and runs the complete documented verification.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependency on another user story when the worktree already contains matching Spec Kit setup.
- **User Story 2 (P1)**: Depends on the Spec Kit adapter created for User Story 1, but is independently testable with an unconfigured worktree.
- **User Story 3 (P1)**: Depends on the live adapter construction from User Story 1; it validates that one provider identity is shared by all external steps.
- **User Story 4 (P1)**: Depends on User Stories 1–3 so its safety checks cover the complete planning-only path.

### Within Each User Story

- Tests are written before the implementation tasks for that story and must initially fail for the new behavior.
- Contract and runtime validation precede model calls.
- The adapter precedes executor integration; executor integration precedes orchestration and CLI behavior.
- Bootstrap and path-safety checks must pass before the story is considered complete.
- A story checkpoint must be independently verified before moving to the next story.

### Parallel Opportunities

- Setup tasks T001 and T002 can run in parallel.
- After Foundational completes, User Story 1 and the provider-selection test design for User Story 3 can be prepared independently, but implementation must respect shared-file ordering.
- T021 and T022 can run in parallel after the safety contract is stable because they touch separate Docker/documentation surfaces.
- T024 and T025 can run in parallel after implementation is complete.

## Parallel Example: User Story 1

```text
# After Phase 2, prepare the story test and fixture inputs:
Task: "Add focused planning-order and native-artifact checks in personalAgent/tests/test_external_framework_planning.py"

# Then execute in dependency order:
Task: "Implement SpecKitAdapter in personalAgent/src/hermes_kanban/speckit.py"
Task: "Implement AgentExecutor.execute_framework in personalAgent/src/hermes_kanban/executor.py"
Task: "Integrate discovery → external plan → external tasks → PLANNING_COMPLETE in personalAgent/src/hermes_kanban/orchestrator.py"
```

## Parallel Example: User Story 2

```text
# Prepare the isolation assertions first:
Task: "Extend personalAgent/tests/test_external_framework_planning.py with bootstrap/reuse/retention checks"

# After those checks fail, implement the two related safety pieces:
Task: "Implement Spec Kit bootstrap/reuse in personalAgent/src/hermes_kanban/speckit.py"
Task: "Enforce worktree containment in personalAgent/src/hermes_kanban/external_framework.py and personalAgent/src/hermes_kanban/speckit.py"
```

## Parallel Example: User Story 3

```text
# Provider boundary checks must be completed before wiring the live constructor:
Task: "Add provider-selection and lifecycle-boundary checks in personalAgent/tests/test_external_framework_planning.py"
Task: "Wire active-provider validation into personalAgent/src/hermes_kanban/executor.py, personalAgent/src/hermes_kanban/orchestrator.py, and personalAgent/src/hermes_kanban/runtime.py"
```

## Parallel Example: User Story 4

```text
# These independent delivery surfaces can proceed after the safety tests are defined:
Task: "Provision the pinned runtime in personalAgent/docker/Dockerfile"
Task: "Document provider configuration and native artifacts in personalAgent/config/default.yaml and personalAgent/README.md"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases.
2. Complete User Story 1 with a matching pre-enabled Spec Kit fixture.
3. Stop and validate discovery order, native plan/task paths, provider metadata, and the distinct `PLANNING_COMPLETE` free-slot outcome.
4. Confirm no builder, implementation, validation, GitHub, merge, deployment, or live AiNative planner lookup occurs.

### Incremental Delivery

1. Add User Story 2 for automatic isolated bootstrap and retained setup.
2. Add User Story 3 for strict single-provider selection and future lifecycle reservation.
3. Add User Story 4 for offline safety coverage, image provisioning, documentation, and version history.
4. Run the complete pytest, ruff, and quickstart checks after each logical increment.

### Parallel Team Strategy

1. Complete Setup and Foundational together because all stories share the contract and record seams.
2. Assign the User Story 1 adapter/orchestration path to one implementer.
3. Assign User Story 2 isolation/bootstrap checks and User Story 3 provider-boundary checks to separate implementers after the shared adapter contract is stable.
4. Assign User Story 4 runtime provisioning and documentation to separate implementers, then run the final quality gates together.

## Notes

- Every task uses the required `- [ ] T###` checklist format; `[P]` appears only for tasks with independent files and no incomplete dependency.
- User-story tasks carry exactly one `[US#]` label for traceability.
- Native Spec Kit plan/task files remain the source of truth; no Hermes `PLAN.md`, `TASKS.md`, second task store, or `kanban.db` write is introduced.
- The adapter owns no retry loop and never answers framework questions; existing Hermes state, retry, and human-decision handling remains authoritative.

## Phase 8: Convergence

- [X] T027 Make `build_live_orchestrator` require and validate exactly one active pinned provider (and matching runtime) before any model or framework work, with no AiNative planner fallback when the block is missing or inactive per FR-002 (contradicts)
- [X] T028 Run the live-style planning fixtures against `personalAgent/tests/fixtures/ainative/` with no `specs-planner` or `builder` folders, and assert those agents are never looked up per SC-009 (partial)
- [X] T029 Extend `personalAgent/tests/test_external_framework_planning.py` so two-active, unsupported-id, empty-pin, missing-runtime, and mismatched-revision configs fail before any stand-in model call per SC-003 (partial)
- [X] T030 Assert enrolled project root, AiNative fixture, overlay, runtime source, and sibling worktrees remain byte-for-byte unchanged across bootstrap and planning per SC-002 (partial)

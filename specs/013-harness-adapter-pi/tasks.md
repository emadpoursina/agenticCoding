---

description: "Task list for the Pi Harness Adapter feature"
---

# Tasks: Pi Harness Adapter

**Input**: Design documents from `/specs/013-harness-adapter-pi/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and `contracts/harness-execution.md`

**Tests**: Test tasks are included because the specification requires focused offline fixture checks for the contract, playbook, human decisions, isolation, retries, validation, and publication gating.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as an independently verifiable increment.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the existing Python package, configuration, and disposable fixture surfaces needed by every story.

- [X] T001 [P] Establish Python 3.12 package metadata, test dependencies, and the feature version in `personalAgent/pyproject.toml` and `personalAgent/src/hermes_kanban/__init__.py`
- [X] T002 [P] Add the named Pi harness, `speckit-orchestrate` playbook, runtime marker, and model-profile configuration shape in `personalAgent/config/default.yaml`
- [X] T003 [P] Create the injected Pi runtime fixture and disposable managed-project fixture directories in `personalAgent/tests/fixtures/pi-runtime/` and `personalAgent/tests/fixtures/projects/standard/`
- [X] T004 [P] Add disposable worktree, in-memory messaging, simulated GitHub, and forbidden-write snapshot helpers in `personalAgent/tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the provider-neutral boundary, safety checks, configuration validation, and persistence primitives that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Define the provider-neutral `HarnessStartRequest`, `HarnessResult`, `HarnessArtifact`, `ResumeContext`, safety records, context projections, and `HarnessAdapter` protocol in `personalAgent/src/hermes_kanban/external_framework.py`
- [X] T006 Implement request/result validation for required identity, accepted playbook, positive finite timeout, protected-branch/worktree rules, bounded safe text, relative artifact/change/output paths, and secret rejection in `personalAgent/src/hermes_kanban/external_framework.py` (depends on T005)
- [X] T007 Replace the stage-oriented external-framework configuration loader with a single active Pi adapter, runtime marker, accepted-playbook, and named-model-profile loader in `personalAgent/src/hermes_kanban/external_framework.py` (depends on T005)
- [X] T008 Extend atomic overlay serialization and deserialization for `HarnessResult`, `ResumeContext`, harness attempts, and safe relative artifacts in `personalAgent/src/hermes_kanban/persist.py` (depends on T005 and T006)
- [X] T009 Add foundational contract checks for closed statuses, required timeout, accepted playbook, path containment, secret-free metadata, and absence of Pi/SDK/model leakage in `personalAgent/tests/test_harness_adapter.py` (depends on T005 through T008)

**Checkpoint**: The generic request/result boundary, configuration checks, and existing-record persistence are ready for independent harness and Hermes workflow work.

---

## Phase 3: User Story 1 - Run the full Spec Kit playbook in Pi (Priority: P1) 🎯 MVP

**Goal**: Run the complete Spec Kit playbook inside Pi, write native artifacts in the task worktree, stop safely for questions or limits, and return one normalized result without publication access.

**Independent Test**: Start the injected Pi fixture through the harness boundary and verify the recorded order is specify, clarify/continue when needed, plan, tasks, optional analyze, and implement/converge; verify native files stay in the disposable task worktree and forbidden-write snapshots remain unchanged.

### Tests for User Story 1

- [X] T010 [P] [US1] Implement the stand-in Pi SDK/runtime and native artifact writer that records playbook order, questions, timeout, stuck, and forbidden-operation cases in `personalAgent/tests/fixtures/pi-runtime/runtime.py`
- [X] T011 [US1] Add adapter fixture tests for full playbook order, conditional analyze, repeated implement/converge, native artifact paths, timeout-to-failed mapping, unavailable runtime, malformed output, and no-forbidden-write behavior in `personalAgent/tests/test_harness_adapter.py` (depends on T009 and T010)

### Implementation for User Story 1

- [X] T012 [US1] Implement the private `PiSdkPort`, named-profile translation, worktree safety policy, deadline handling, playbook invocation, and normalized status/artifact mapping in `personalAgent/src/hermes_kanban/pi.py` (depends on T011)

**Checkpoint**: A Pi adapter run can execute and test the full playbook independently of Hermes stage orchestration or publication.

---

## Phase 4: User Story 2 - Start one generic harness run and receive one result (Priority: P1)

**Goal**: Make Hermes assemble one framework-neutral request, invoke one selected adapter exactly once, reject direct stage requests, and expose one normalized result.

**Independent Test**: Start a disposable task through the Hermes executor and verify exactly one `HarnessStartRequest` and one `HarnessResult`, with no individual Spec Kit lifecycle call or Pi-specific value crossing the boundary.

### Tests for User Story 2

- [X] T013 [P] [US2] Add executor/orchestrator fixture checks for one request per attempt, one result per run, direct-stage rejection, model-profile reference mapping, and fail-closed adapter startup errors in `personalAgent/tests/test_piv_orchestrator.py`

### Implementation for User Story 2

- [X] T014 [US2] Add `start_harness` request assembly, task/project/worktree validation, named harness selection, and exactly-once adapter invocation to `personalAgent/src/hermes_kanban/executor.py` (depends on T012 and T013)
- [X] T015 [US2] Replace live stage dispatch with one-run result handling for execution started/running/finished, failed, needs-human, and stuck outcomes in `personalAgent/src/hermes_kanban/orchestrator.py` (depends on T014)

**Checkpoint**: Hermes starts a generic Pi-backed work attempt without knowing or invoking Spec Kit stages.

---

## Phase 5: User Story 3 - Park and resume human decisions through Hermes (Priority: P1)

**Goal**: Keep questions, skip assumptions, one continue confirmation, resume context, diagnostics, and bounded stuck retries on the Hermes task record while Pi remains operator-chat-free.

**Independent Test**: Pause fixtures during clarify and implementation, verify Hermes parks the task, verify no later playbook work starts while parked, then verify answer/skip/continue context resumes through another whole-run request; verify the third same-point failure parks with no fourth attempt.

### Tests for User Story 3

- [X] T016 [US3] Add clarify, skip choice-report, single continue confirmation, implementation-question, and second-question-batch parking/resume checks in `personalAgent/tests/test_piv_orchestrator.py` (depends on T015)
- [X] T017 [P] [US3] Add overlay restart/reclaim checks for parked answers, assumptions, resume context, prior diagnostics, partial native artifacts, and whole-run attempt counts in `personalAgent/tests/test_restart_recovery.py` (depends on T008)

### Implementation for User Story 3

- [X] T018 [US3] Persist validated parked questions, skip/continue decisions, diagnostic context, retry guidance, and native artifact references on the existing workflow record in `personalAgent/src/hermes_kanban/persist.py` (depends on T016 and T017)
- [X] T019 [US3] Implement Hermes human parking, choice-report messaging, resume request construction, whole-run retry context, and the three-attempt stuck escalation in `personalAgent/src/hermes_kanban/orchestrator.py` (depends on T016 and T018)

**Checkpoint**: Human decisions and recoverable stuck points use the same whole-run harness boundary and never become Hermes-owned Spec Kit stages.

---

## Phase 6: User Story 4 - Validate and publish only after the harness completes (Priority: P1)

**Goal**: Treat `completed` as playbook completion only, run the existing validation path, recover workspace changes with another whole harness run, and publish through the existing GitHub path only after validation passes.

**Independent Test**: Drive completed, failed, human, stuck, validation-failure, recovery, and validation-pass fixtures and verify GitHub remains untouched until a validation pass.

### Tests for User Story 4

- [X] T020 [P] [US4] Add validation-before-publish and no-prevalidation-GitHub-operation checks for completed, failed, needs-human, and stuck results in `personalAgent/tests/test_live_piv_bridge.py`
- [X] T021 [US4] Add validation failure, whole-run recovery, retry-budget, commit/push, and create-or-update pull-request checks in `personalAgent/tests/test_piv_orchestrator.py` (depends on T019 and T020)

### Implementation for User Story 4

- [X] T022 [US4] Connect completed-result handling to the existing project validation, validation recovery, feature-branch commit/push, and pull-request workflow without giving the harness publication access in `personalAgent/src/hermes_kanban/orchestrator.py` (depends on T021)

**Checkpoint**: Only a validated completed playbook can reach the existing Hermes publication workflow.

---

## Phase 7: User Story 5 - Remove the old Hermes Spec Kit stage machine (Priority: P1)

**Goal**: Remove every live stage, fallback, and recovery route, park historical short-path records for human review, and preserve existing workspace, validation, Kanban, messaging, and GitHub behavior.

**Independent Test**: Inspect and run the live-style fixture path to verify no command or fallback can call the removed stage machine, while a completed generic harness result still reaches existing validation and publication.

### Tests for User Story 5

- [X] T023 [P] [US5] Add regression checks proving no live path invokes `scout`, individual Spec Kit stages, `PLANNING_COMPLETE`, or an AiNative planner fallback, and proving historical records are parked without auto-starting Pi in `personalAgent/tests/test_legacy_stage_removal.py`

### Implementation for User Story 5

- [X] T024 [US5] Remove lifecycle-stage methods, stage names, and direct-stage compatibility behavior from `personalAgent/src/hermes_kanban/external_framework.py` while retaining only generic boundary validation (depends on T023)
- [X] T025 [US5] Remove legacy framework execution entry points and stage-to-model assignment routing from `personalAgent/src/hermes_kanban/executor.py` (depends on T023 and T024)
- [X] T026 [US5] Delete `_run_external_planning`, `_run_external_implementation`, `PLANNING_COMPLETE`, and all stage fallback/recovery branches from `personalAgent/src/hermes_kanban/orchestrator.py` (depends on T023 and T025)
- [X] T027 [US5] Detect and park historical short-path and `PLANNING_COMPLETE` records with a clear migration reason during load, startup, or reclaim in `personalAgent/src/hermes_kanban/persist.py` and `personalAgent/src/hermes_kanban/runtime.py` (depends on T023 and T026)
- [X] T028 [US5] Delete the obsolete stage adapter and fixture implementation from `personalAgent/src/hermes_kanban/speckit.py` and `personalAgent/tests/fixtures/speckit-runtime/`, then remove all remaining references in `personalAgent/tests/` (depends on T024 through T027)

**Checkpoint**: The removed Hermes stage machine cannot run beside or instead of the generic Pi harness path.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finish operator-facing behavior, deployment wiring, version history, and all required quality gates.

- [X] T029 [P] Update terminal/CLI outcome reporting and public exports for generic execution, human parking, validation, failure, stuck, and pull-request outcomes in `personalAgent/src/hermes_kanban/runtime.py`, `personalAgent/src/hermes_kanban/__main__.py`, and `personalAgent/src/hermes_kanban/__init__.py`
- [X] T030 [P] Update operator documentation for the harness boundary, Pi model-profile configuration, human question/skip/continue behavior, native artifact locations, validation/publication ownership, offline fixtures, and external credentials in `personalAgent/README.md`
- [X] T031 [P] Update runtime provisioning and environment wiring for the preinstalled/injected Pi runtime without adding a Python dependency in `personalAgent/docker/Dockerfile` and `personalAgent/docker-compose.yml`
- [X] T032 [P] Update the repository and package changelogs with the delivered semantic-versioned harness adapter feature in `CHANGELOG.md` and `personalAgent/CHANGELOG.md`
- [X] T033 [P] Update import, version, and package-surface checks for the delivered adapter boundary in `personalAgent/tests/test_import.py`
- [X] T034 Run the focused fixture commands and Ruff checks from `specs/013-harness-adapter-pi/quickstart.md`, including `personalAgent/tests/test_harness_adapter.py`, `personalAgent/tests/test_piv_orchestrator.py`, `personalAgent/tests/test_restart_recovery.py`, and `personalAgent/tests/test_live_piv_bridge.py`
- [X] T035 Run the complete `uv run pytest` and `uv run ruff check src tests` quality gates from `personalAgent/`, then verify every command and disposable-artifact assertion in `specs/013-harness-adapter-pi/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T004 can start in parallel.
- **Foundational (Phase 2)**: Depends on Setup; T005-T009 establish the shared contract, safety, configuration, persistence, and baseline checks.
- **User Story 1 (Phase 3)**: Depends on Foundation; the Pi fixture and adapter tests can proceed in parallel after T009, then T012 implements the adapter.
- **User Story 2 (Phase 4)**: Depends on the completed Pi adapter from US1; T013 precedes T014-T015.
- **User Story 3 (Phase 5)**: Depends on the one-run executor/orchestrator path from US2; persistence tests may run alongside the story tests, then T018-T019 implement parking and resume.
- **User Story 4 (Phase 6)**: Depends on result handling and human/recovery behavior from US2-US3; validation/publication tests precede T022.
- **User Story 5 (Phase 7)**: Depends on the new path being covered by US1-US4 tests; removal tasks are serialized because they touch the shared dispatch and orchestrator seams.
- **Polish (Phase 8)**: Depends on all required stories; T029-T033 can proceed in parallel, followed by T034-T035 as final gates.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only; no other story dependency.
- **US2 (P1)**: Depends on US1 because Hermes must select and invoke the first adapter.
- **US3 (P1)**: Depends on US2 because parking/resume is implemented around the one-run boundary.
- **US4 (P1)**: Depends on US2 and US3 so validation recovery can start whole harness attempts with persisted diagnostics.
- **US5 (P1)**: Depends on US2-US4 so removal checks cover every new execution, recovery, and publication route.

### Within Each User Story

- Tests are written before the matching implementation tasks.
- Shared typed records and validators precede adapter and orchestration work.
- The Pi adapter is implemented before executor request assembly.
- Executor request assembly precedes orchestrator result handling.
- Human persistence precedes resume/retry orchestration.
- Validation precedes publication.
- Legacy deletion happens only after regression checks prove the replacement path.

### Parallel Opportunities

- **Setup**: T001, T002, T003, and T004 are independent.
- **Foundation**: T005 and T006 are serialized in one module; T008 can be prepared after the record definitions, while T009 is the contract gate.
- **US1**: T010 can start after T009; T011 follows the fixture and contract setup, then T012 implements the adapter.
- **US3**: T016 and T017 cover separate test files and can be prepared in parallel once US2 is available.
- **US4**: T020 can start after US3; T021 follows the live-bridge checks, and T022 is serialized in the orchestrator.
- **Polish**: T029-T033 touch separate delivery surfaces and can run in parallel; quality gates T034-T035 run after them.

## Parallel Example: User Story 1

```text
After T009:
Task T010: Build the stand-in Pi runtime in personalAgent/tests/fixtures/pi-runtime/runtime.py

After T010:
Task T011: Add adapter fixture tests in personalAgent/tests/test_harness_adapter.py

After T011:
Task T012: Implement personalAgent/src/hermes_kanban/pi.py
```

## Parallel Example: User Story 3

```text
After US2:
Task T016: Add human parking/resume checks in personalAgent/tests/test_piv_orchestrator.py
Task T017: Add restart persistence checks in personalAgent/tests/test_restart_recovery.py

After T016 and T017:
Task T018: Implement resume persistence in personalAgent/src/hermes_kanban/persist.py

After T018:
Task T019: Implement parking and bounded whole-run retry in personalAgent/src/hermes_kanban/orchestrator.py
```

## Implementation Strategy

### MVP First (US1 plus the required generic boundary)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1 so Pi can run the full playbook in a disposable worktree.
3. Complete User Story 2 so Hermes starts exactly one generic harness run and receives one normalized result.
4. Validate the end-to-end fixture path before adding human recovery or publication behavior.

### Incremental Delivery

1. Add User Story 3 for human parking, skip/continue, resume, and bounded retry.
2. Add User Story 4 for validation-gated recovery and existing pull-request publication.
3. Add User Story 5 to remove and park every legacy short-path route.
4. Complete Polish and run the focused and full quality gates.

### Parallel Team Strategy

1. Complete Setup and Foundation together.
2. Assign the Pi fixture/adapter work to one implementer and the generic contract checks to another.
3. After the one-run boundary is stable, split human persistence/recovery from validation/publication tests.
4. Keep changes to `executor.py`, `orchestrator.py`, and shared persistence serialized when they touch the same state transitions.

## Notes

- Every task uses the required `- [ ] T###` checklist format.
- `[P]` marks work that can proceed in parallel without editing an unfinished dependency.
- `[US#]` labels map tasks to the corresponding specification story.
- Native `spec.md`, `plan.md`, and `tasks.md` are Pi artifacts in the task worktree, not Hermes aliases.
- No task adds an AiNative planner, a Hermes Spec Kit command, a second database, a live event stream, a new Python dependency, or harness publication access.

## Phase 9: Convergence

- [X] T036 When skip is active, self-answer queued specify/clarify questions from recorded assumptions, show the choice report, and require only one continuation confirmation before plan per FR-008
- [X] T037 Add parking/resume fixture checks for an implementation question and a second human-question batch so no later playbook work starts while parked per US3/Independent Test
- [X] T038 Use the existing snapshot helper to prove focused fixtures do not write the enrolled project root, AiNative fixture, Hermes control-plane overlay, or a sibling worktree per SC-003
- [X] T039 Delete the leftover empty `personalAgent/tests/fixtures/speckit-runtime/` tree so the removed stage fixture cannot remain beside the Pi runtime stand-in per plan: fixtures

## Phase 10: Convergence

- [X] T040 Add a focused playbook fixture that skips analyze and proceeds to implement when analysis is not required per US1/AC2
- [X] T041 Record a second implement/converge cycle in the Pi stand-in when implementation and convergence do not yet agree, then finish only after they converge per US1/AC3

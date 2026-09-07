---

description: "Task list for Spec Kit implementation and publish"
---

# Tasks: Spec Kit Implementation and Publish

**Input**: Design documents from `/specs/012-speckit-implementation-publish/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/external-framework-implementation.md`, and `quickstart.md`

**Tests**: Required. FR-017 and the success criteria require focused offline checks for provider validation, native handoff consumption, isolation, recovery, checkpoint semantics, and publish gating. Tests use disposable worktrees, the pinned runtime fixture, stand-in model/hosting/messaging seams, and no live credentials.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses different files and has no dependency on incomplete work.
- **[Story]**: Maps the task to a user story (`US1`–`US4`).
- Every task names the exact file path or command location it changes or verifies.

## Path Conventions

- Source: `personalAgent/src/hermes_kanban/`
- Tests: `personalAgent/tests/`
- Fixtures: `personalAgent/tests/fixtures/`
- Runtime and operator surfaces: `personalAgent/config/`, `personalAgent/docker/`, `personalAgent/README.md`, and `personalAgent/CHANGELOG.md`
- Feature documentation: `specs/012-speckit-implementation-publish/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the hermetic methodology and pinned-runtime fixtures needed by implementation and recovery checks.

- [X] T001 [P] Extend `personalAgent/tests/fixtures/ainative/manifest.yaml`, `personalAgent/tests/fixtures/ainative/agents/scout.md`, and `personalAgent/tests/fixtures/ainative/agents/tester.md` with the existing read-only `scout` plus validation/diagnostic role needed by recovery fixtures; keep `specs-planner` and `builder` absent.
- [X] T002 [P] Update `personalAgent/tests/fixtures/speckit-runtime/manifest.json` and `personalAgent/tests/fixtures/speckit-runtime/setup/.specify/integrations/speckit.manifest.json` so the disposable runtime fixture has one matching `github-spec-kit` `1.0.1` identity and revision for `plan`, `tasks`, and `implement`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the provider-neutral contract, trust checks, model seam, and durable record support before any story-specific workflow changes.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Define the implementation lifecycle contract in `personalAgent/src/hermes_kanban/external_framework.py`: make `implement` executable while keeping `specify` and `clarify` visibly unsupported, add validated native-handoff, validation-summary, and diagnostic-summary fields to `ExternalFrameworkContext`, and preserve provider-neutral `ExternalFrameworkResult` status/artifact rules.
- [X] T004 Add strict native handoff and implementation-result validation in `personalAgent/src/hermes_kanban/external_framework.py`: require readable regular `plan` and `tasks` files inside the current task worktree, matching provider/version/revision and setup marker, secret-free metadata, safe implementation artifacts, and explicit provider success before any model call or validation.
- [X] T005 Extend `personalAgent/src/hermes_kanban/executor.py` so `execute_framework` validates the task/project/worktree/branch boundary, selects the configured `planning` assignment for plan/tasks and `implementation` for implement/fixes, carries native paths plus validation/diagnostic context, and never performs an AiNative planner/builder lookup.
- [X] T006 Extend `personalAgent/src/hermes_kanban/persist.py` to round-trip the combined native handoff and implementation result through `overlay.json`, remain backward-compatible with old snapshots, and reject malformed, secret-bearing, escaping, or identity-drifted saved framework state instead of guessing replacement artifacts.
- [X] T007 Update `personalAgent/src/hermes_kanban/__init__.py` exports for the lifecycle/context/result and handoff-validation symbols introduced in T003–T006 without adding a second task store or control-plane dependency.

**Checkpoint**: The implementation lifecycle, safe native paths, configured model assignments, and durable handoff schema are ready for story work.

---

## Phase 3: User Story 1 - Implement from native Spec Kit artifacts (Priority: P1) 🎯 MVP

**Goal**: Run `scout → plan → tasks → PLANNING_COMPLETE → implement` in one isolated task worktree, consuming the exact native plan/task paths through the active pinned Spec Kit provider.

**Independent Test**: Use a disposable project, scout-plus-validation AiNative fixture, matching Spec Kit runtime fixture, and stand-in model. Verify the call order, exact native paths in the implement context, worktree-only writes, no aliases, no planner/builder lookup, and no publish before implementation and validation.

### Tests for User Story 1

- [X] T008 [US1] Add focused implement fixtures in `personalAgent/tests/test_external_framework_planning.py` that assert `scout → plan → tasks → implement`, exact same-worktree `specs/<feature>/plan.md` and `tasks.md` handoff paths, implementation file isolation, retained native setup, no `PLAN.md`/`TASKS.md` aliases, no planner/builder lookup, explicit model failure handling, partial-file retention, and implementation-question parking.

### Implementation for User Story 1

- [X] T009 [US1] Extend `personalAgent/src/hermes_kanban/speckit.py` so `PinnedSpecKitRuntime.execute_step` and `SpecKitAdapter.execute` support `implement`, pass the validated native plan/tasks and safe context to the configured `ModelService`, materialize only relative worktree files, preserve optional local commits, retain partial files on failure, and return normalized provider metadata without publishing.
- [X] T010 [US1] Replace the planning-only branch in `personalAgent/src/hermes_kanban/orchestrator.py` with the full external sequence: append a distinct `PLANNING_COMPLETE` checkpoint after native plan/tasks, keep the new-run slot occupied, invoke implement without routine approval, preserve the combined handoff, and enter existing validation only after explicit implementation success.
- [X] T011 [US1] Update `personalAgent/src/hermes_kanban/runtime.py` and `personalAgent/src/hermes_kanban/__main__.py` so the live dispatcher reports terminal implementation/validation/publish outcomes, does not treat `PLANNING_COMPLETE` as final success, and continues using the native board and existing single start surface.

**Checkpoint**: User Story 1 is independently testable: implementation consumes native artifacts in the prepared worktree and reaches validation without copying agents, aliases, or publishing.

---

## Phase 4: User Story 2 - Validate and recover safely (Priority: P1)

**Goal**: Reuse the existing validation and bounded recovery machine after Spec Kit implementation, routing only workspace-fixing recovery through Spec Kit `implement`.

**Independent Test**: Run pass, retryable, transient, non-retryable, model-failure, and question fixtures. Confirm existing pass/retry/blocked/decision outcomes, native handoff preservation, Spec Kit implementation for retryable fixes, no AiNative builder lookup, and zero publish before validation pass.

### Tests for User Story 2

- [X] T012 [US2] Extend `personalAgent/tests/test_piv_orchestrator.py` and `personalAgent/tests/test_external_framework_planning.py` with validation/recovery assertions for native handoff propagation, retryable `diagnosis → implement fix → re-validation`, transient validation-only retry, non-retryable blocking, implementation/validation questions, bounded attempts, partial worktree preservation, and zero GitHub calls before a validation pass.

### Implementation for User Story 2

- [X] T013 [US2] Update `personalAgent/src/hermes_kanban/orchestrator.py` recovery paths so diagnosis remains on the existing validation role, retryable debug/worktree fixes call external `implement` with the same provider/worktree/native paths plus diagnostic and last-validation summaries, and transient/non-retryable classifications do not invoke unauthorized implementation.
- [X] T014 [US2] Extend the validation/tester context assembly in `personalAgent/src/hermes_kanban/executor.py` and the validation handoff calls in `personalAgent/src/hermes_kanban/orchestrator.py` to expose the native plan/tasks and implementation context without reading or creating Hermes `PLAN.md`/`TASKS.md` aliases.

**Checkpoint**: User Stories 1 and 2 are independently testable: validation gates publish, recovery remains bounded, and only the active Spec Kit implement lifecycle can change the task worktree during recovery.

---

## Phase 5: User Story 3 - Publish only after validation (Priority: P1)

**Goal**: After validation passes, reuse the orchestrator-owned commit, feature-branch push, create/update pull request, and existing notice path for both new runs and continued planning handoffs.

**Independent Test**: Drive a live-style disposable run through implementation and passing checks with `MemoryGitHost` and in-memory messaging. Verify one feature-branch publish, one PR identity with number and URL, existing `pr_created` notice, update-not-duplicate behavior, protected-branch safety, and zero publish on every pre-pass outcome.

### Tests for User Story 3

- [X] T015 [US3] Extend `personalAgent/tests/test_live_piv_bridge.py` and `personalAgent/tests/test_piv_orchestrator.py` with publish-gating fixtures for a validation-pass PR, continued valid `PLANNING_COMPLETE` handoff, existing-PR update, publish failure classification, no pre-validation push/PR, no merge/deploy/protected-branch write, and the existing `pr_created` notice payload.

### Implementation for User Story 3

- [X] T016 [US3] Integrate the successful external validation result with `_begin_github` and `_run_github` in `personalAgent/src/hermes_kanban/orchestrator.py`, preserving history-safe commit, feature-branch-only push, configured default base branch, one create-or-update PR, required number/HTML URL, existing retry/block behavior, and no adapter-owned GitHub calls.
- [X] T017 [US3] Update `personalAgent/src/hermes_kanban/runtime.py` live result handling and `personalAgent/README.md` operator examples so a successful full run ends at `PR_CREATED`, while implementation/recovery/validation failures and questions remain visible without a publish or a misleading planning-only success message.

**Checkpoint**: User Story 3 is independently testable: a validation pass is the only route to the existing reviewable pull request and notice.

---

## Phase 6: User Story 4 - Preserve handoff and control-plane safety (Priority: P1)

**Goal**: Resume valid historical planning checkpoints in place, distinguish planning from PIV completion, and fail closed on malformed or drifting handoffs.

**Independent Test**: Seed a valid free-slot `PLANNING_COMPLETE` overlay and resume by task name or next-ready; verify plan/tasks are not rerun, the same worktree and provider are used, implementation continues through validation and publish, and corrupted paths/identity fail before any model, validation, or GitHub call.

### Tests for User Story 4

- [X] T018 [US4] Extend `personalAgent/tests/test_restart_recovery.py` and `personalAgent/tests/test_external_framework_planning.py` with valid legacy-handoff resume, named and next-ready selection, slot reclaim/protection, skipped plan/tasks calls, same-worktree identity, provider/runtime drift rejection, missing/unreadable/non-regular/secret/escaping path rejection, no-forbidden-write snapshots, and overlay redaction checks.

### Implementation for User Story 4

- [X] T019 [US4] Implement strict historical handoff continuation in `personalAgent/src/hermes_kanban/orchestrator.py`: validate the saved provider/runtime/worktree/branch/setup/native paths, reclaim the slot when a valid planning-only record is selected, skip completed plan/tasks, continue at Spec Kit implement, and preserve `PLANNING_COMPLETE` as neither PIV-complete nor terminal success.
- [X] T020 [US4] Harden `personalAgent/src/hermes_kanban/persist.py` and `personalAgent/src/hermes_kanban/external_framework.py` at the overlay trust boundary so invalid or incomplete handoffs become visible failed/blocked outcomes before implementation, validation, or publish and records contain no transcripts, private reasoning, tokens, or secrets.

**Checkpoint**: All four user stories preserve one provider, one worktree, one native handoff, one control-plane record, and the existing human decision and publish boundaries.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Deliver operator documentation/version history and run the complete offline quality gates.

- [X] T021 [P] Update `personalAgent/config/default.yaml`, `personalAgent/README.md`, and `specs/012-speckit-implementation-publish/quickstart.md` with the active pinned provider, native implement handoff, validation/recovery behavior, checkpoint/PIV distinction, fixture commands, live command shape, and credentials that remain outside git.
- [X] T022 [P] Update `personalAgent/docker/Dockerfile`, `personalAgent/docker/speckit-runtime/manifest.json`, and `personalAgent/docker/speckit-runtime/setup/.specify/integrations/speckit.manifest.json` to document and verify build-time Spec Kit provisioning, exact revision matching, read-only runtime use, and no per-run installation/download.
- [X] T023 Record the delivered implementation/publish version in `personalAgent/CHANGELOG.md` and `/Users/emad/Projects/playground/agenticCoding/CHANGELOG.md`, and bump `personalAgent/src/hermes_kanban/__init__.py` plus `personalAgent/pyproject.toml` according to the existing semantic-versioning scheme.
- [X] T024 [P] Run the focused offline suites from `personalAgent/`: `uv run pytest tests/test_external_framework_planning.py`, `uv run pytest tests/test_live_piv_bridge.py`, and `uv run pytest tests/test_restart_recovery.py`; fix regressions in the touched implementation and fixtures.
- [X] T025 [P] Run `uv run pytest` and `uv run ruff check src tests` from `personalAgent/`, then resolve failures without adding dependencies or unrelated refactors.
- [X] T026 Validate every command and expected result in `specs/012-speckit-implementation-publish/quickstart.md`, including offline fixture execution, native artifact locations, valid/invalid handoff resume, retained setup, recovery routing, PR gating, and the absence of forbidden writes or live credentials.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; the two fixture updates can run in parallel.
- **Foundational (Phase 2)**: Depends on Setup and blocks every user story.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP implementation path.
- **User Story 2 (Phase 4)**: Depends on User Story 1's implement path and extends the existing validation/recovery seams.
- **User Story 3 (Phase 5)**: Depends on successful implementation and validation integration from User Stories 1–2; it reuses the existing GitHub path.
- **User Story 4 (Phase 6)**: Depends on the handoff/result contract and implementation path from User Story 1; its resume checks also cover validation/publish continuation from User Stories 2–3.
- **Polish (Phase 7)**: Depends on all desired stories being complete; documentation can be prepared while final tests run, but version updates follow the delivered implementation.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependency on another user story.
- **User Story 2 (P1)**: Requires US1's external implement lifecycle; uses existing validation and recovery state transitions.
- **User Story 3 (P1)**: Requires US1 implementation and US2 validation pass; does not create a second publisher.
- **User Story 4 (P1)**: Requires US1's native handoff and US2/US3 continuation behavior; independently proves restart and trust-boundary safety.

### Within Each User Story

- Tests are written before the matching implementation tasks and initially fail for the new behavior.
- Contract and path validation precede model/framework calls.
- Native plan/tasks must exist before implement; implement must succeed before validation; validation must pass before GitHub.
- Diagnosis precedes retryable implement fixes; transient and non-retryable classifications keep their existing paths.
- A story checkpoint must pass before moving to the next dependent story.

### Parallel Opportunities

- T001 and T002 can run in parallel.
- After T003, T004 and T007 can be prepared in separate files, but T007 must land after the exported symbols exist.
- Once Foundational is complete, US1 test preparation (T008) and documentation/runtime preparation in T021–T022 can proceed on separate files; do not edit the shared orchestrator concurrently.
- T024 and T025 can run in parallel after implementation is complete.
- T021 and T022 can run in parallel with final test preparation; T023 follows the actual delivered version.
- Do not parallelize tasks that edit `personalAgent/src/hermes_kanban/orchestrator.py`, `personalAgent/src/hermes_kanban/executor.py`, or the same test module.

---

## Parallel Example: User Story 1

```text
# After the foundational contract is ready:
Task: "Add implement-order and isolation fixtures in personalAgent/tests/test_external_framework_planning.py"

# After the tests are prepared, execute the provider and workflow work in order:
Task: "Extend SpecKitAdapter and PinnedSpecKitRuntime for implement in personalAgent/src/hermes_kanban/speckit.py"
Task: "Replace the planning-only branch with checkpoint → implement → validation in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Update terminal result handling in personalAgent/src/hermes_kanban/runtime.py"
```

## Parallel Example: User Story 2

```text
# Tests first:
Task: "Add validation/recovery fixtures in personalAgent/tests/test_piv_orchestrator.py and personalAgent/tests/test_external_framework_planning.py"

# Then route the existing recovery state machine through the external implement step:
Task: "Update recovery routing in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Expose native handoff to validation context in personalAgent/src/hermes_kanban/executor.py"
```

## Parallel Example: User Story 3

```text
# Tests first:
Task: "Add validation-pass, PR identity, existing-PR, notice, and no-prepass-publish checks in personalAgent/tests/test_live_piv_bridge.py and personalAgent/tests/test_piv_orchestrator.py"

# Then keep publication in the existing orchestrator path:
Task: "Gate _begin_github/_run_github behind external validation pass in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Update PR_CREATED and failure output in personalAgent/src/hermes_kanban/runtime.py"
```

## Parallel Example: User Story 4

```text
# Tests first:
Task: "Add valid and invalid PLANNING_COMPLETE resume checks in personalAgent/tests/test_restart_recovery.py and personalAgent/tests/test_external_framework_planning.py"

# Then enforce the saved handoff at both orchestration and persistence boundaries:
Task: "Implement legacy handoff continuation in personalAgent/src/hermes_kanban/orchestrator.py"
Task: "Harden overlay handoff deserialization and validation in personalAgent/src/hermes_kanban/persist.py and personalAgent/src/hermes_kanban/external_framework.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational; the contract and trust boundary must be ready before model work.
2. Complete User Story 1: `scout → plan → tasks → PLANNING_COMPLETE → implement`.
3. **STOP and VALIDATE**: confirm exact native paths, worktree-only writes, no aliases, no planner/builder lookup, and no pre-validation publish.
4. Continue to User Story 2 only after the MVP implementation result is explicit and safely handed to validation.

### Incremental Delivery

1. Add User Story 2 → validate pass, bounded retryable recovery, transient/non-retryable behavior, and question parking.
2. Add User Story 3 → validate existing feature-branch publish, one PR identity, notice, and no forbidden GitHub actions.
3. Add User Story 4 → validate legacy planning-handoff continuation, slot semantics, overlay safety, and fail-closed corruption handling.
4. Update runtime/docs/version history, then run focused tests, the full pytest suite, ruff, and the quickstart commands.

### Parallel Team Strategy

1. Complete Setup and Foundational together.
2. Assign the US1 provider implementation and US1 orchestration work sequentially because both depend on the same handoff contract.
3. After US1, assign US2 recovery routing and US4 handoff test design to separate workers only when they are not editing the same source/test files.
4. Assign US3 publish-gate verification after validation behavior is stable.
5. Run documentation/runtime packaging and quality checks in parallel at the end, with one owner for version history.

---

## Notes

- Every task uses the required `- [ ] T###` checklist format; `[P]` appears only where file and dependency boundaries permit parallel work.
- User-story tasks carry exactly one `[US#]` label.
- Native Spec Kit `specs/<feature>/plan.md` and `tasks.md` remain canonical; no Hermes `PLAN.md`, `TASKS.md`, second task store, second workspace, or copied AiNative builder/planner is introduced.
- The adapter has no retry loop and never answers consequential questions; existing Hermes state, recovery budget, human-decision, validation, GitHub, and notice seams remain authoritative.
- Focused checks remain hermetic: no GitHub, Telegram, live model credentials, production repositories, or writable live AiNative.

---

description: "Implementation task list for Hermes Startup Context Files"
---

# Tasks: Hermes Startup Context Files

**Input**: Design documents from `/specs/016-hermes-startup-context/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/startup-context.md`, and `quickstart.md`

**Tests**: Test tasks are included because FR-011 and SC-001–SC-006 require focused startup, failure, precedence, revision, isolation, and diagnostic checks. Write the focused checks before the matching implementation in each user-story phase.

**Organization**: Tasks are grouped by user story so each slice can be implemented and verified independently.

**Scope boundary**: Keep `AGENTS.md` versioned, keep actual `SYSTEM.md` and `USER.md` outside Git in persistent Hermes data, and leave project-bootstrapper wiring and the existing `ich-mag-dich` validation command unchanged.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other marked tasks after listed dependencies
- **[Story]**: Maps a task to US1–US3; setup, foundational, and polish tasks have no story label
- Every task names the exact file or command surface it changes or verifies

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the existing Hermes package surfaces, exact configuration, and safe first-delivery instruction files.

- [X] T001 [P] Confirm the Python 3.12/uv package, pytest, Ruff, live CLI, orchestrator, configuration, and test surfaces in `personalAgent/pyproject.toml`, `personalAgent/src/hermes_kanban/runtime.py`, `personalAgent/src/hermes_kanban/orchestrator.py`, `personalAgent/config/default.yaml`, and `personalAgent/tests/`; preserve the existing dependency set.
- [X] T002 [P] Add the required `context` mapping with exactly `hermes_instructions`, `system`, and `user` registrations and the exact container paths in `personalAgent/config/default.yaml`.
- [X] T003 [P] Add short, safe starter instructions to `personalAgent/AGENTS.md`, `personalAgent/docs/context/SYSTEM.example.md`, and `personalAgent/docs/context/USER.example.md`; preserve existing AGENTS safety guidance, tell the operator to complete the placeholders later, and include no secrets.
- [X] T004 [P] Document manual template copying, persistent-file boundaries, exact container paths, `--doctor`, and the no-auto-create rule in `personalAgent/README.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the typed startup-context contract and fail-closed loader before live startup or story-specific behavior is added.

**⚠️ CRITICAL**: No user-story implementation should begin until this phase is complete.

- [X] T005 Define the fixed role order, typed `StartupContextRegistration`, `StartupContextSnapshot`, safe startup error, precedence-layer, and diagnostic metadata records in `personalAgent/src/hermes_kanban/startup_context.py`.
- [X] T006 Implement configuration parsing through the existing `_parse_document`, exact container-path validation, regular readable non-empty UTF-8 file checks, duplicate-resolution rejection, SHA-256 revision hashing, and no-fallback/no-auto-create behavior in `personalAgent/src/hermes_kanban/startup_context.py`.
- [X] T007 Keep full file text only in the process-local snapshot and expose a separate role/path/revision metadata view in `personalAgent/src/hermes_kanban/startup_context.py`; do not add a database, overlay field, task field, worktree file, or project copy.

**Checkpoint**: The loader contract is typed, exact-path, fail-closed, revision-aware, and safe to attach to live Hermes without persisting file bodies.

## Phase 3: User Story 1 - Load the three context files at startup (Priority: P1) 🎯 MVP

**Goal**: Validate and load all three exact container files before Hermes accepts or handles a command.

**Independent Test**: Start Hermes with readable temporary fixtures at the three configured paths and verify registration order, exact-path loading, and clear fail-closed errors for every invalid fixture.

### Tests for User Story 1

- [X] T008 [US1] Add startup-context checks in `personalAgent/tests/test_startup_context.py` for the three-role registration order, successful byte/text loading, exact configured paths, and rejection of host-only paths or fallback lookup.
- [X] T009 [US1] Add startup-context failure checks in `personalAgent/tests/test_startup_context.py` for missing, unreadable, directory, empty, invalid-UTF-8, and duplicate files; assert each error names the role and exact path and that missing files are never created.

### Implementation for User Story 1

- [X] T010 [US1] Load and validate the startup snapshot at the beginning of `build_live_orchestrator()` in `personalAgent/src/hermes_kanban/runtime.py`, before board selection, orchestrator readiness, or command dispatch.
- [X] T011 [US1] Add an optional process-local startup snapshot reference to `PivOrchestrator` construction in `personalAgent/src/hermes_kanban/orchestrator.py` while keeping `WorkflowRecord`, overlay serialization, and existing fixture construction unchanged.
- [X] T012 [US1] Extend `personalAgent/tests/test_live_piv_bridge.py` to prove live startup validates all three files before selecting a task or board and stops with a safe role/path error when a configured file is invalid.

**Checkpoint**: A valid startup fixture loads all three files before dispatch, and every missing, unreadable, directory, empty, invalid-UTF-8, duplicate, or host-path fixture stops startup without creating or exposing a file.

## Phase 4: User Story 2 - Preserve one source of truth (Priority: P1)

**Goal**: Record only exact source paths and revisions while preventing registered file bodies from entering operational records or coding-job payloads.

**Independent Test**: Load sentinel-bearing fixtures, inspect registrations, diagnostics, job requests, and overlay records, and verify only role/path/revision metadata is exposed outside Hermes startup/planning/health code.

### Tests for User Story 2

- [X] T013 [P] [US2] Add revision-only checks in `personalAgent/tests/test_startup_context.py` for stable SHA-256 revisions, changed revisions at the same source path, registration role/path values, and absence of full file text from metadata.
- [X] T014 [P] [US2] Add sentinel-isolation checks in `personalAgent/tests/test_live_piv_bridge.py`, `personalAgent/tests/test_piv_orchestrator.py`, and the existing persistence test surface for absence of registered file bodies from `ExecutePayload`, `AssembledContext`, `HarnessStartRequest`, model messages, `WorkflowRecord`, overlay JSON, worktrees, and managed project files.

### Implementation for User Story 2

- [X] T015 [US2] Keep the startup snapshot out of `WorkflowRecord`, persistence serializers, task/Kanban records, worktrees, and project repositories in `personalAgent/src/hermes_kanban/orchestrator.py`, `personalAgent/src/hermes_kanban/persist.py`, and `personalAgent/src/hermes_kanban/executor.py`; retain `_read_workspace_files()` as the project-local coding-job projection.
- [X] T016 [US2] Build the secret-safe `StartupDiagnostic` from the existing AiNative adapter, project registry, workspace manager, harness configuration, and overlay directory in `personalAgent/src/hermes_kanban/runtime.py` and `personalAgent/src/hermes_kanban/startup_context.py`; include only required runtime locations, agent/project identities, and context revisions.
- [X] T017 [US2] Add `--doctor` parsing and execution to `personalAgent/src/hermes_kanban/runtime.py` so it performs the same startup validation, prints the safe diagnostic, exits before task selection, and never prints registered file bodies or secret values.
- [X] T018 [US2] Add diagnostic and isolation checks in `personalAgent/tests/test_live_piv_bridge.py` and `personalAgent/tests/test_startup_context.py` for required location fields, role/path/revision metadata, secret-safe output, no auto-create behavior, and no sentinel text in coding-job or operational-record payloads.

**Checkpoint**: A changed source file produces a new revision for the same path, diagnostics remain metadata-only, and coding jobs continue to receive project-local context only.

## Phase 5: User Story 3 - Apply predictable context precedence (Priority: P2)

**Goal**: Resolve conflicting instructions in the documented order while keeping platform, safety, project-validation, and protected-operation rules authoritative.

**Independent Test**: Supply conflicting candidates for every precedence layer and verify the resolver chooses platform/safety, Hermes, live runtime, SYSTEM, project, USER, and task in that order.

### Tests for User Story 3

- [X] T019 [US3] Add conflicting-layer checks in `personalAgent/tests/test_startup_context.py` for every documented precedence rank, runtime configuration over `SYSTEM.md`, and rejection of USER/task attempts to weaken safety, project validation, or protected-branch rules.

### Implementation for User Story 3

- [X] T020 [US3] Implement the pure ordered precedence resolver in `personalAgent/src/hermes_kanban/startup_context.py` with layers for platform/safety, Hermes instructions, live runtime configuration, SYSTEM, project instructions, USER, and current task.
- [X] T021 [US3] Expose the resolver to Hermes startup/planning/health diagnostics in `personalAgent/src/hermes_kanban/runtime.py` and `personalAgent/src/hermes_kanban/startup_context.py` without adding registered file text to `ExecutePayload`, harness requests, model messages, or persistence schemas.

**Checkpoint**: All precedence fixtures resolve deterministically, with lower-priority preferences and task requests unable to override higher-priority safety or protected-operation rules.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete feature, preserve out-of-scope boundaries, and record the delivered implementation.

- [X] T022 [P] Run the focused startup-context checks and Ruff command documented in `specs/016-hermes-startup-context/quickstart.md` from `personalAgent/`; confirm success, exact-path failures, revision changes, precedence, isolation, and secret-safe diagnostics.
- [X] T023 [P] Run the complete `uv run pytest` and `uv run ruff check src tests` quality gates from `personalAgent/`; preserve the existing harness, orchestrator, project, workspace, and AiNative checks.
- [X] T024 [P] Run the optional Docker doctor and missing-file checks from `specs/016-hermes-startup-context/quickstart.md` against the available Hermes container and disposable home; verify the persistent files are manually provisioned, never auto-created, and never printed.
- [X] T025 Update `CHANGELOG.md` and `personalAgent/CHANGELOG.md` with the semantic-version entries for startup registration, exact-path loading, revision-only diagnostics, precedence, safe placeholders, tests, and CLI doctor verification; do not add persistent `SYSTEM.md` or `USER.md` to Git.
- [X] T026 Re-read `specs/016-hermes-startup-context/spec.md`, `specs/016-hermes-startup-context/plan.md`, and `specs/016-hermes-startup-context/quickstart.md` against the implementation; confirm project-bootstrapper wiring and the existing `ich-mag-dich` validation command remain unchanged.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No implementation dependency. T001–T004 can run in parallel because they inspect or edit separate surfaces.
- **Foundational (Phase 2)**: Depends on the setup baseline. T005 must precede T006, and T006 must precede T007 because all three extend `startup_context.py`.
- **User Story 1 (Phase 3)**: Depends on T007. T008 and T009 are separate checks in the same test file and should be written before T010–T011; T012 follows the live startup integration.
- **User Story 2 (Phase 4)**: Depends on the live snapshot seam from US1. T013 and T014 can be prepared in parallel; T015–T017 are serialized around the existing runtime/orchestrator boundaries; T018 follows the diagnostic path.
- **User Story 3 (Phase 5)**: Depends on T007 and the snapshot contract. T019 must precede T020–T021; coordinate edits because the resolver and its tests share `startup_context.py` and `test_startup_context.py`.
- **Polish (Phase 6)**: Depends on all desired stories. T022–T024 are verification gates, T025 records the delivered change, and T026 is the final scope audit.

### User Story Dependencies

- **US1 (P1)**: Depends only on the foundational loader contract and is the MVP.
- **US2 (P1)**: Depends on US1's process-local snapshot attachment and proves the operational-record and coding-job boundaries independently.
- **US3 (P2)**: Depends on the foundational snapshot contract; it may be implemented after the loader is stable, with shared-file edits coordinated with US2.

### Parallel Opportunities

- **Setup**: T001, T002, T003, and T004 use separate package, config, context-file, and guidance surfaces.
- **US1**: T008 and T009 are logically independent test cases but touch one test file, so keep them in one worker or serialize their edits; T012 can follow T010–T011 in a separate live-test pass.
- **US2**: T013 and T014 touch separate test surfaces and can proceed in parallel after T012; diagnostic source work and persistence-boundary work should remain serialized where they share runtime/orchestrator code.
- **US3**: T019 is the contract test gate; T020 and T021 must follow it and share the startup-context implementation boundary.
- **Polish**: T022, T023, and T024 are separate verification commands and can run in parallel when the environment supports it; T025–T026 are final delivery checks.

### Execution Assignments

- **T005–T007, T010–T011, T015–T017, T020–T021**: `implementation-worker` / `po-normal-grok46` / Medium effort.
- **T002–T004, T025–T026**: `documentation-worker` / `po-normal-grok46` / Medium effort.
- **T008–T009, T012–T014, T018–T019**: `test-worker` / `po-normal-grok46` / Medium effort.
- **T022–T024**: `validation-worker` / `po-normal-grok46` / Medium effort.
- Do not substitute a different model, effort, default agent, or new dependency for these assignments.

## Parallel Example: User Story 1

```text
After T007:
T008  personalAgent/tests/test_startup_context.py — successful loading and exact paths
T009  personalAgent/tests/test_startup_context.py — fail-closed fixtures

After the tests are ready:
T010  personalAgent/src/hermes_kanban/runtime.py — live startup gate
T011  personalAgent/src/hermes_kanban/orchestrator.py — optional process-local snapshot
T012  personalAgent/tests/test_live_piv_bridge.py — live boundary verification
```

## Parallel Example: User Story 2

```text
After T012:
T013  personalAgent/tests/test_startup_context.py — revisions and metadata-only records
T014  personalAgent/tests/test_live_piv_bridge.py, test_piv_orchestrator.py — sentinel isolation

After T013 and T014:
T015  personalAgent/src/hermes_kanban/orchestrator.py, persist.py, executor.py — boundary preservation
T016  personalAgent/src/hermes_kanban/runtime.py, startup_context.py — diagnostic construction
T017  personalAgent/src/hermes_kanban/runtime.py — --doctor mode
T018  personalAgent/tests/test_live_piv_bridge.py, test_startup_context.py — diagnostic verification
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1 tests and live startup gating.
3. Run the focused startup-context checks and Ruff.
4. Stop and validate that all three exact files load before command handling and all invalid fixtures fail closed.

### Incremental Delivery

1. Add User Story 2 for revision-only diagnostics and coding-job/record isolation.
2. Add User Story 3 for deterministic precedence.
3. Run the complete pytest/Ruff suite and the available Docker doctor proof.
4. Update both changelogs and complete the out-of-scope boundary audit.

### Constraints During Implementation

- Do not commit actual persistent `SYSTEM.md` or `USER.md`; only safe examples belong in the repository.
- Do not translate `/Users/...` host paths, search fallback locations, or auto-create missing registered files.
- Do not print registered file contents, secrets, tokens, passwords, or private keys.
- Do not add the startup snapshot to coding-job payloads, model messages, Kanban/task records, worktrees, project repositories, overlays, or a new database.
- Do not change project-bootstrapper wiring or the existing `ich-mag-dich` validation behavior.

## Notes

- Every task uses the required `- [ ] T###` checklist format.
- `[P]` marks only tasks that can safely proceed in parallel without editing an unfinished dependency.
- `[US#]` labels map story tasks to the three prioritized user stories.
- The first-delivery instruction content is intentionally short and safe; the operator completes the real `SYSTEM.md` and `USER.md` instructions later.

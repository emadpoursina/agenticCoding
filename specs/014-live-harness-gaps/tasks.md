---

description: "Task list for the Live Harness Adapter Gaps feature"
---

# Tasks: Live Harness Adapter Gaps

**Input**: Design documents from `/specs/014-live-harness-gaps/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/harness-execution.md`, and `quickstart.md`

**Tests**: Test tasks are included because FR-015 and SC-001–SC-008 require focused process, configuration, restart, offline-boundary, and Docker-live checks. Tests MUST be written to fail before the matching implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as an independently verifiable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other marked tasks after their listed dependencies
- **[Story]**: Maps a task to US1–US4; setup, foundational, and polish tasks have no story label
- Every task names the exact file or command surface it changes or verifies

## Path Conventions

The Python package lives under `personalAgent/`. Source is in `personalAgent/src/hermes_kanban/`; tests are in `personalAgent/tests/`; configuration is in `personalAgent/config/`; container files are in `personalAgent/docker/` and `personalAgent/docker-compose.yml`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the existing Python package, runtime fixtures, and isolated test surfaces used by every story.

- [X] T001 [P] Align the existing Python 3.12 package metadata, pytest/ruff development tools, and feature version surface in `personalAgent/pyproject.toml` and `personalAgent/src/hermes_kanban/__init__.py` without adding a Pi or TypeScript SDK dependency
- [X] T002 [P] Define the active Pi runtime, `speckit-orchestrate` playbook, positive timeout, and provider-neutral model-profile configuration shape in `personalAgent/config/default.yaml`, and keep the fixture marker/executable layout in `personalAgent/tests/fixtures/pi-runtime/manifest.json` and `personalAgent/tests/fixtures/pi-runtime/runtime.py`
- [X] T003 [P] Extend disposable worktree, fake-runtime injection, child-process cleanup, protected-path snapshot, and no-secret helpers in `personalAgent/tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared trust-boundary validation and persistence primitives that all four stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Foundational checks first

- [X] T004 Add failing baseline checks for executable runtime validation, strict timeout inputs, legacy acknowledgement round-trip, provider-neutral result statuses, safe worktree-relative paths, and forbidden Pi/SDK/model leakage in `personalAgent/tests/test_harness_adapter.py` and `personalAgent/tests/test_restart_recovery.py`

### Foundational implementation

- [X] T005 Implement container-visible executable resolution and marker validation in `personalAgent/src/hermes_kanban/external_framework.py`: require adapter `pi`, revision/version marker fields, and a runnable executable; treat marker-only `manifest.json` directories as unavailable before a task starts
- [X] T006 Add one strict positive-finite timeout coercion helper in `personalAgent/src/hermes_kanban/external_framework.py` that accepts numeric values and numeric strings, rejects booleans/blank/missing/zero/negative/non-numeric/non-finite values, and introduces no upper bound
- [X] T007 Extend `WorkflowRecord` serialization with `legacy_acknowledged: bool = False` in `personalAgent/src/hermes_kanban/persist.py`, default old overlays to false, and preserve task/worktree/history/decision fields during atomic round-trip

**Checkpoint**: Runtime availability, timeout normalization, and durable legacy state are ready before adapter and restart behavior are implemented.

---

## Phase 3: User Story 1 - Start a real Pi process for one task (Priority: P1) 🎯 MVP

**Goal**: Hermes starts one container-runnable `pi --mode rpc` child in the task worktree, sends one JSON `prompt` command, consumes Pi's private JSONL run to settlement, extracts one structured result, maps it through `HarnessResult`, and always stops the child after settlement or timeout.

**Independent Test**: Run the process-backed adapter with a disposable task worktree and a container-visible Pi launcher; verify exact arguments, `cwd`, one request, one result, normalized statuses, cleanup, safe paths, and marker-only startup failure. The Docker proof must use the real project Pi program.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T008 [P] [US1] Extend the controlled Pi fixture in `personalAgent/tests/fixtures/pi-runtime/runtime.py` to record argv/cwd/input count and support completed, failed, needs-human, stuck, malformed, extra-output, timeout, early-exit, and still-running-after-result cases without requiring live credentials
- [X] T009 [US1] Add failing adapter checks in `personalAgent/tests/test_harness_adapter.py` for one `pi --mode rpc` child, task-worktree `cwd`, exactly one JSON `prompt` command/result extraction, all four status mappings, marker-only/missing/non-executable startup failure, malformed/extra/unknown/unsafe output rejection, timeout failure, and leftover-process termination

### Implementation for User Story 1

- [X] T010 [US1] Implement the private one-shot subprocess transport behind `PiHarnessAdapter` in `personalAgent/src/hermes_kanban/pi.py`: start the configured executable as `[pi, "--mode", "rpc"]` with `cwd=request.workspace_path`, send one JSON `prompt` command, consume JSONL responses/events until settlement, extract one structured result, and terminate/kill/wait after settlement or timeout
- [X] T011 [US1] Build the bounded provider-neutral job and structured-result prompt from `HarnessStartRequest`, then route startup/transport/result validation failures to one normalized `HarnessResult` without exposing Pi SDK types, transcripts, secrets, stage scripts, or a legacy fallback in `personalAgent/src/hermes_kanban/pi.py` and `personalAgent/src/hermes_kanban/executor.py`
- [X] T012 [US1] Provision a container-runnable real project Pi executable beside its matching marker, with a read-only runtime mount or image installation and no host-only assumption, in `personalAgent/docker/Dockerfile`, `personalAgent/docker-compose.yml`, and `personalAgent/config/default.yaml`

**Checkpoint**: A disposable task can reach a real container-visible Pi process through the existing generic adapter boundary and leaves no running child.

---

## Phase 4: User Story 2 - Load the checked-in timeout and start Pi (Priority: P1)

**Goal**: The checked-in `timeout_seconds: 1800` and valid numeric strings load as finite numeric timeouts, invalid values fail before Pi starts, and the accepted timeout bounds the live child.

**Independent Test**: Load the checked-in default configuration and focused numeric, numeric-string, missing, blank, boolean, zero, negative, non-numeric, and non-finite fixtures; verify valid live-style startup reaches Pi while invalid configuration starts no child.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T013 [US2] Add failing timeout/configuration checks in `personalAgent/tests/test_harness_adapter.py` and `personalAgent/tests/test_live_piv_bridge.py` for checked-in `1800`, positive numeric strings, valid finite numbers, every specified invalid form, and the guarantee that invalid values are rejected before process start

### Implementation for User Story 2

- [X] T014 [US2] Use the shared coercion helper from `personalAgent/src/hermes_kanban/external_framework.py` in `load_harness_config` and `ExecutionSettings.from_config` in `personalAgent/src/hermes_kanban/external_framework.py` and `personalAgent/src/hermes_kanban/executor.py`, exposing accepted values as numeric timeouts before Pi starts
- [X] T015 [US2] Apply the normalized timeout to the one-shot child deadline and cleanup path in `personalAgent/src/hermes_kanban/pi.py`, mapping timeout/termination to `failed` while retaining inspectable worktree artifacts

**Checkpoint**: The checked-in default configuration reaches Pi startup, and all invalid timeout forms fail closed before execution.

---

## Phase 5: User Story 3 - Resume acknowledged leftover work after restart (Priority: P1)

**Goal**: Historical short-path records remain parked until human acknowledgement; acknowledgement clears the old-path marker without starting Pi; a later Hermes process starts one fresh generic harness run.

**Independent Test**: Persist an unacknowledged legacy record, verify startup parks without Pi, acknowledge it, verify marker/history/worktree preservation and no same-call start, then construct a new Hermes process and verify one generic harness start. Replayed acknowledgement remains safe.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T016 [US3] Add failing park/acknowledgement/restart checks in `personalAgent/tests/test_piv_orchestrator.py`, `personalAgent/tests/test_restart_recovery.py`, and `personalAgent/tests/test_legacy_stage_removal.py` for unacknowledged parking, no Pi start before acknowledgement, marker clearing, retained worktree/history/decision context, no same-call start, one generic start after restart, and idempotent acknowledgement replay

### Implementation for User Story 3

- [X] T017 [US3] Implement the existing human-decision acknowledgement transition in `personalAgent/src/hermes_kanban/orchestrator.py`: clear `legacy_migration_reason`, set `legacy_acknowledged`, clear the pending decision, preserve task/worktree/history, leave the record queued, and never invoke Pi in the acknowledgement call
- [X] T018 [US3] Make legacy detection and startup reclaim honor `legacy_acknowledged` while retaining historical legacy steps, so unacknowledged records remain parked and acknowledged records enter the generic `start_harness` path once in `personalAgent/src/hermes_kanban/orchestrator.py` and `personalAgent/src/hermes_kanban/runtime.py`

**Checkpoint**: Restart behavior distinguishes human-authorized generic reclaim from unacknowledged historical work without reviving the removed stage machine.

---

## Phase 6: User Story 4 - Keep offline proof on the fake Pi boundary (Priority: P1)

**Goal**: Offline tests remain deterministic and fake-Pi based, while generic request/result data stays free of Pi SDK types, Cursor slugs, secrets, private reasoning, stage scripts, and unsafe writes.

**Independent Test**: Run focused pytest and Ruff checks without credentials or a TypeScript SDK; inspect imports and serialized request/result data; verify a completed harness result only enters the existing validation path.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T019 [US4] Add failing offline-boundary and leakage checks in `personalAgent/tests/test_harness_adapter.py`, `personalAgent/tests/test_live_piv_bridge.py`, `personalAgent/tests/test_legacy_stage_removal.py`, and `personalAgent/tests/test_import.py` for fake-Pi execution, no TypeScript/Pi SDK imports, no Cursor model slugs/provider secrets/tokens/private reasoning/stage scripts, worktree-only writes, and no legacy fallback
- [X] T020 [US4] Add failing validation-gating checks in `personalAgent/tests/test_live_piv_bridge.py` for completed/failed/needs-human/stuck results, proving only a valid completed result reaches existing project validation and no harness result directly publishes

### Implementation for User Story 4

- [X] T021 [US4] Preserve fake runtime injection for offline tests while selecting the private subprocess only for the configured live runtime in `personalAgent/src/hermes_kanban/pi.py`, `personalAgent/src/hermes_kanban/executor.py`, and `personalAgent/tests/conftest.py`
- [X] T022 [US4] Enforce provider-neutral request/result leakage and worktree-safety rejection at the existing boundary in `personalAgent/src/hermes_kanban/external_framework.py`, retaining the four closed statuses and existing `HarnessStartRequest`, `HarnessResult`, and `PiHarnessAdapter` interfaces
- [X] T023 [US4] Keep completed harness handling as playbook completion only, preserving existing validation and later Git/PR ownership in `personalAgent/src/hermes_kanban/orchestrator.py`; do not add publication access to Pi

**Checkpoint**: Offline fake-Pi checks are credential-free and the live adapter remains a thin generic boundary with Hermes-owned validation and publication.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Document the delivered runtime contract, update version history, and run all focused, full, and disposable Docker checks.

- [X] T024 [P] Update operator and manual verification documentation for runtime availability, `pi --mode rpc`, timeout forms, legacy acknowledgement/restart, fake-Pi offline checks, and the real-project Docker proof in `personalAgent/README.md` and `specs/014-live-harness-gaps/quickstart.md`
- [X] T025 [P] Update semantic-versioned feature history for the live process adapter, timeout loading, acknowledgement transition, fake-Pi boundary, and Docker provisioning in `CHANGELOG.md` and `personalAgent/CHANGELOG.md`
- [X] T026 Run the focused checks from `specs/014-live-harness-gaps/quickstart.md` in `personalAgent/`: adapter/process, orchestrator/restart, live bridge, legacy removal, and Ruff checks; confirm tests use the fake Pi and no live credentials
- [ ] T027 Run the complete `uv run pytest` and `uv run ruff check src tests` quality gates in `personalAgent/`, then execute the disposable Docker live proof from `specs/014-live-harness-gaps/quickstart.md` using the real project `pi --mode rpc`; verify one job/result, task-worktree `cwd`, child cleanup, marker-only failure, and no protected/sibling/control-plane writes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001–T003 can run in parallel.
- **Foundational (Phase 2)**: Depends on Setup; T004 must be written first, then T005–T007 establish runtime, timeout, and persistence prerequisites.
- **User Story 1 (Phase 3)**: Depends on Foundational; T008–T009 establish failing process checks before T010–T012 implement the live path.
- **User Story 2 (Phase 4)**: Depends on Foundational and the process boundary from US1; T013 precedes T014–T015.
- **User Story 3 (Phase 5)**: Depends on Foundational persistence and the generic start path from US1; T016 precedes T017–T018.
- **User Story 4 (Phase 6)**: Depends on the live/fake adapter and timeout behavior from US1–US2; T019–T020 precede T021–T023.
- **Polish (Phase 7)**: Depends on all required stories; T024–T025 can run in parallel, and T026–T027 are final verification gates.

### User Story Dependencies

- **US1 (P1)**: After Phase 2; independently proves executable runtime validation and one-shot process execution.
- **US2 (P1)**: After Phase 2 and the US1 process seam; independently proves configuration acceptance/rejection and deadline application.
- **US3 (P1)**: After Phase 2 and the generic start/reclaim seam from US1; does not depend on live credentials or Docker.
- **US4 (P1)**: After US1–US2 so its offline checks cover both injected fake and process-backed adapter selection; validation/publication checks remain Hermes-owned.

### Within Each User Story

- Tests and fixture checks MUST be written before their matching implementation.
- Runtime/contract validation precedes process execution.
- Timeout normalization precedes child deadline use.
- Durable acknowledgement state precedes legacy detector bypass and restart reclaim.
- Fake-boundary/leakage checks precede final adapter and orchestrator gating changes.
- A story is independently testable at its checkpoint before moving to the next dependent story.

### Parallel Opportunities

- **Setup**: T001, T002, and T003 touch separate package/config/test-support surfaces.
- **Foundation**: T007 can proceed separately from the two `external_framework.py` changes after T004; T005 and T006 must be serialized because they edit the same module.
- **US1**: T008 can proceed in the fixture file while the generic boundary tests in T004 are reviewed; T010–T011 must be serialized because both define the adapter transport/request path. T012 is serialized after the transport contract and before Docker proof.
- **US2**: T013 is one test group and must remain ordered before T014–T015; T014 and T015 share the timeout flow and should be serialized.
- **US3**: T016 spans several test files but represents one lifecycle contract; T017 and T018 must be serialized because both change legacy orchestration state.
- **US4**: T019 and T020 touch separate test modules and can be prepared in parallel; T021–T023 should be serialized around the shared adapter/orchestrator boundary.
- **Polish**: T024 and T025 can run in parallel; T026 and T027 run after documentation and implementation are complete.

## Parallel Example: User Story 1

```text
After Phase 2:
Task T008: Extend the controlled Pi fixture in personalAgent/tests/fixtures/pi-runtime/runtime.py
Task T009: Add failing process-contract checks in personalAgent/tests/test_harness_adapter.py

After T008 and T009:
Task T010: Implement the private transport in personalAgent/src/hermes_kanban/pi.py

After T010:
Task T011: Build the generic job/result mapping in personalAgent/src/hermes_kanban/pi.py and personalAgent/src/hermes_kanban/executor.py
Task T012: Provision the container runtime in personalAgent/docker/Dockerfile and personalAgent/docker-compose.yml
```

## Parallel Example: User Story 3

```text
After the foundational persistence field and US1 generic start path:
Task T016: Add park/ack/restart checks in personalAgent/tests/test_piv_orchestrator.py, personalAgent/tests/test_restart_recovery.py, and personalAgent/tests/test_legacy_stage_removal.py

After T016:
Task T017: Implement acknowledgement state transition in personalAgent/src/hermes_kanban/orchestrator.py

After T017:
Task T018: Implement acknowledged-record startup reclaim in personalAgent/src/hermes_kanban/orchestrator.py and personalAgent/src/hermes_kanban/runtime.py
```

## Implementation Strategy

### MVP First (Foundation + User Stories 1–2)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1 so Hermes can start and safely finish one real Pi process attempt.
3. Complete User Story 2 because the checked-in timeout is required for the live process to start.
4. **STOP and VALIDATE**: run the focused adapter/configuration checks and the disposable real-project Docker proof.
5. Do not claim live readiness until the marker-only and leftover-process checks pass.

### Incremental Delivery

1. Add User Story 3 → test legacy park, acknowledgement, and restart reclaim independently.
2. Add User Story 4 → test fake-Pi offline execution, leakage restrictions, and validation gating independently.
3. Complete Polish → update operator guidance/changelogs and run focused plus full quality gates.

### Parallel Team Strategy

1. Complete Setup and Foundational together, serializing edits to `external_framework.py`.
2. After the foundation:
   - Developer A: US1 fixture and `pi.py` transport.
   - Developer B: US3 restart tests and acknowledgement state, after the generic start seam exists.
   - Developer C: US4 fake-boundary/leakage tests, without changing the shared adapter until US1 is stable.
3. Keep edits to `executor.py`, `orchestrator.py`, `persist.py`, and shared test files serialized when they touch the same lifecycle state.

## Notes

- Every task uses the required `- [ ] T###` checklist format.
- `[P]` marks work that can proceed in parallel without editing an unfinished dependency.
- `[US#]` labels map tasks to the corresponding specification story.
- The existing generic harness boundary remains canonical; Pi's private RPC event stream does not become a Hermes event channel, and no second harness, queue, task database, SDK import, or Hermes stage machine is added.
- The Docker proof must execute the real project Pi program; a protocol-only stub is valid only for isolated offline transport tests.
- No task authorizes GitHub publication, protected-branch writes, AiNative writes, production access, or live credentials.

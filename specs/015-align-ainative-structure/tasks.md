---

description: "Implementation task list for AiNative Structure Alignment"
---

# Tasks: AiNative Structure Alignment

**Input**: Design documents from `/specs/015-align-ainative-structure/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/structure-alignment.md`, and `quickstart.md`

**Organization**: Tasks are grouped by user story so each slice can be implemented and verified independently.

**Scope boundary**: The nested `AiNative/` checkout is the read-only source of truth. Do not copy, reorganize, or modify its methodology content.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the current source-of-truth layout, consumer baseline, and versioning targets before changing the adapter.

- [X] T001 [P] Verify the four-layer reference tree and existing migration validators in `AiNative/docs/`, `AiNative/scripts/setup-project.sh`, `AiNative/scripts/check-ainative-link.sh`, `AiNative/scripts/check-agent-commands.sh`, and `AiNative/scripts/check-doc-links.mjs`; record any intentional old-path negative assertions without changing the read-only checkout.
- [X] T002 [P] Inspect the consumer baseline in `personalAgent/src/hermes_kanban/ainative.py`, `personalAgent/tests/test_ainative_adapter.py`, `personalAgent/tests/test_agent_executor.py`, `personalAgent/docker-compose.yml`, `personalAgent/config/default.yaml`, `personalAgent/AGENTS.md`, and `personalAgent/docs/v0-implementation-plan.md` to identify active versus historical old-path references.
- [X] T003 [P] Confirm the existing version-history targets in `CHANGELOG.md`, `personalAgent/CHANGELOG.md`, and `personalAgent/src/hermes_kanban/__init__.py` before recording the delivered alignment.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Prepare the shared fixture and preserve the trust-boundary/runtime invariants required by every story.

**⚠️ CRITICAL**: No user-story implementation should begin until this phase is complete.

- [X] T004 [P] Preserve the read-only methodology boundary by keeping `${AINATIVE_PATH}:/ainative:ro` in `personalAgent/docker-compose.yml` and `ainative.read_only: true` with `/ainative` in `personalAgent/config/default.yaml`; do not introduce a copied or writable AiNative tree.
- [X] T005 Move `personalAgent/tests/fixtures/ainative-full/docs/8-agents/` to `personalAgent/tests/fixtures/ainative-full/docs/agents/` with `git mv`, and remove the obsolete fallback-only `personalAgent/tests/fixtures/ainative-full/agents/scout.md` and `personalAgent/tests/fixtures/ainative-full/manifest.yaml`.
- [X] T006 [P] Establish the baseline commands and disposable-only execution boundary for `AiNative/scripts/check-ainative-link.sh`, `AiNative/scripts/check-agent-commands.sh`, `AiNative/scripts/check-doc-links.mjs`, and the fixture-copy helpers in `personalAgent/tests/test_ainative_adapter.py` and `personalAgent/tests/test_agent_executor.py`.

**Checkpoint**: The shared fixture is rooted at `docs/agents/`, the live mount remains read-only, and the canonical validators are available before story work starts.

---

## Phase 3: User Story 1 - Read agents from the current AiNative layer (Priority: P1) 🎯 MVP

**Goal**: Make the adapter accept only `docs/agents/`, preserve existing agent/dependency/revision/read-only behavior, and reject the retired numbered root.

**Independent Test**: Copy `personalAgent/tests/fixtures/ainative-full/` into a temporary Git repository, list and load a known agent, resolve its rule and shared skill, assert every returned path is under `docs/agents/`, and assert a checkout containing only `docs/8-agents/` raises `InvalidMethodologyError`.

### Tests for User Story 1

- [X] T007 [US1] Update `personalAgent/tests/test_ainative_adapter.py` first to assert `docs/agents/` construction, sorted discovery, raw instruction/dependency paths, revision and dirty-state behavior, invalid-path rejection, and rejection of a methodology containing only `docs/8-agents/` or a top-level `agents/` roster.
- [X] T008 [P] [US1] Update `personalAgent/tests/test_agent_executor.py` first so executor integration and refused-write assertions target `docs/agents/`, prove the fixture remains unchanged, and preserve existing unsafe-write behavior.

### Implementation for User Story 1

- [X] T009 [US1] Change `personalAgent/src/hermes_kanban/ainative.py` to require `settings.path / "docs" / "agents"` as a directory, remove manifest/simple-roster and top-level `agents/` fallbacks, and keep reserved-folder filtering, dependency resolution, revision capture, and write refusal unchanged.
- [X] T010 [US1] Run the focused adapter and executor checks in `personalAgent/tests/test_ainative_adapter.py` and `personalAgent/tests/test_agent_executor.py`, then run `uv run ruff check src tests` from `personalAgent/`; fix only regressions caused by the path cutover.

**Checkpoint**: The adapter has one strict current root, all returned paths use it, and the old root cannot satisfy construction or execution.

---

## Phase 4: User Story 2 - Keep the consumer's tests, fixtures, and guidance aligned (Priority: P1)

**Goal**: Ensure all consumer-facing fixtures, integration checks, and maintainer guidance use the same current `docs/agents/` contract without weakening read-only or dependency behavior.

**Independent Test**: Run the adapter, executor, import, and focused integration checks against the migrated fixture, inspect consumer guidance links, and audit active consumer files for retired operational paths.

### Tests for User Story 2

- [X] T011 [P] [US2] Audit and update any current-layout assumptions in `personalAgent/tests/test_live_piv_bridge.py` and `personalAgent/tests/test_harness_adapter.py` so their methodology fixture setup and assertions remain hermetic and do not require a live mount.
- [X] T012 [P] [US2] Audit `personalAgent/tests/fixtures/ainative/` and its consumers; remove the unused simple-roster `agents/*.md` and `manifest.yaml` fallback fixture or migrate it to `docs/agents/` if a current test still requires that fixture.

### Implementation for User Story 2

- [X] T013 [US2] Update `personalAgent/AGENTS.md` and the active AiNative layout guidance in `personalAgent/docs/v0-implementation-plan.md` to link critic/tester references through `docs/agents/`, describe the four semantic layers, and label any retained old-path text as historical or negative-test context.
- [X] T014 [US2] Run the focused consumer checks in `personalAgent/tests/test_ainative_adapter.py`, `personalAgent/tests/test_agent_executor.py`, `personalAgent/tests/test_import.py`, `personalAgent/tests/test_live_piv_bridge.py`, and `personalAgent/tests/test_harness_adapter.py`; verify existing revision, incomplete-agent, broken-dependency, read-only, and unsafe-write behavior remains covered.

**Checkpoint**: Consumer fixtures, tests, and guidance no longer depend operationally on numbered agent paths and remain usable without credentials, network access, or writes to AiNative.

---

## Phase 5: User Story 3 - Verify the complete four-layer migration (Priority: P2)

**Goal**: Migrate the live Hermes projection, align active specifications, and prove setup, parity, documentation links, and clean-break behavior agree on `systems`, `agents`, `knowledge`, and `records`.

**Independent Test**: Re-run setup against `personalAgent/`, inspect the resulting links and ignore block, run the setup self-check, agent-command parity check, and documentation-link check, then audit active consumer source/specs for retired-path dependencies.

### Implementation for User Story 3

- [X] T015 [US3] Re-run `AiNative/scripts/setup-project.sh` for `/Users/emad/Projects/playground/agenticCoding/personalAgent` with `--ainative-home /Users/emad/Projects/playground/agenticCoding/AiNative`; verify `.cursor/rules/personal`, `docs/agents`, and `docs/systems` point to AiNative, stale `docs/8-agents` and `docs/2-ai-workflows` symlinks are removed, and a real local `docs/systems/` directory remains protected without force.
- [X] T016 [P] [US3] Verify the managed ignore migration in `personalAgent/.gitignore` contains only `.cursor/rules/personal`, `docs/agents`, and `docs/systems` for the setup projection, with no retired numbered entries.
- [X] T017 [P] [US3] Update active adapter contract and design artifacts in `specs/001-ainative-adapter/spec.md`, `specs/001-ainative-adapter/checklists/requirements.md`, `specs/001-ainative-adapter/research.md`, `specs/001-ainative-adapter/contracts/ainative-adapter.md`, `specs/001-ainative-adapter/data-model.md`, `specs/001-ainative-adapter/plan.md`, and `specs/001-ainative-adapter/quickstart.md` to use `docs/agents/` and the current four-layer vocabulary.
- [X] T018 [P] [US3] Update stale active fixture/contract prescriptions in `specs/004-agent-execution/plan.md`, `specs/004-agent-execution/research.md`, `specs/004-agent-execution/tasks.md`, `specs/005-piv-orchestrator/tasks.md`, and `specs/006-piv-recovery/tasks.md`; preserve old paths only where the text explicitly records migration history or tests stale-link removal.
- [X] T019 [P] [US3] Run `AiNative/scripts/check-agent-commands.sh` against the current `AiNative/docs/agents/` roster and `.cursor/commands/`, confirming reserved folders, shared skills, `AGENTS.md`/`SKILL.md`/`rule.md`, and command parity.
- [X] T020 [P] [US3] Run `node AiNative/scripts/check-doc-links.mjs AiNative` and `node AiNative/scripts/check-doc-links.mjs personalAgent`; repair consumer-side relative links whose depth changed under `docs/records/{debugging,decisions,postmortems,evaluations}/` without editing the read-only AiNative checkout.
- [X] T021 [US3] Run `AiNative/scripts/check-ainative-link.sh` and confirm its temporary-project coverage proves new/existing setup, stale symlink removal, ignore migration, real `docs/systems/` protection, and refusal to treat AiNative itself as a consumer.
- [X] T022 [US3] Run a final stale-path audit across `personalAgent/src/`, `personalAgent/tests/`, `personalAgent/AGENTS.md`, `personalAgent/docs/`, and the active specification files; classify only deliberate historical/negative-test mentions and leave zero operational, test, setup, or guidance dependency on retired numbered paths.
- [X] T023 [US3] Verify `/ainative:ro` in `personalAgent/docker-compose.yml`, the read-only settings in `personalAgent/config/default.yaml`, and the fixture write-refusal assertions in `personalAgent/tests/test_ainative_adapter.py` and `personalAgent/tests/test_agent_executor.py`; confirm no check writes to the real AiNative checkout.
- [X] T024 [US3] Run the complete Hermes verification from `personalAgent/`: `uv run pytest` and `uv run ruff check src tests`; report failures instead of masking them.

**Checkpoint**: Setup, parity, link, stale-path, read-only, full-test, and lint gates all pass for the live consumer and current four-layer contract.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Record the delivered planning/implementation work without adding compatibility behavior.

- [X] T025 [P] Update `CHANGELOG.md` and `personalAgent/CHANGELOG.md` with the next semantic-version entries for the adapter, fixture, setup, guidance, specification, and verification alignment; update `personalAgent/src/hermes_kanban/__init__.py` only if its existing version source requires the delivered version.
- [X] T026 [P] Re-read `specs/015-align-ainative-structure/quickstart.md` and confirm every documented command and expected result matches the completed paths in `personalAgent/` and `AiNative/`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No implementation dependency; T001, T002, and T003 can run in parallel.
- **Foundational (Phase 2)**: Depends on the baseline inspection; T004 and T006 can run in parallel, while T005 must finish before path-sensitive tests.
- **User Story 1 (Phase 3)**: Depends on T005; T007 and T008 can be written in parallel, then T009, then T010.
- **User Story 2 (Phase 4)**: Depends on T005 and the current adapter contract from T009; T011 and T012 can run in parallel, then T013 and T014.
- **User Story 3 (Phase 5)**: T015 can begin after T005 and the current AiNative checkout is verified; T016–T020 can proceed in parallel after setup where their files do not overlap; T021–T024 are the release gates after consumer/spec edits.
- **Polish (Phase 6)**: Depends on all desired stories and verification gates completing.

### User Story Dependencies

- **US1 (P1)**: Depends only on the foundational fixture and mount boundary; it is the MVP.
- **US2 (P1)**: Depends on the migrated fixture and strict adapter contract, but its guidance and integration checks are independently testable.
- **US3 (P2)**: Depends on the consumer cutover being complete enough for setup, link, parity, and stale-path gates; it must not add runtime readers for `knowledge` or `records`.

### Parallel Opportunities

- Setup inventory (T001–T003) is parallel-safe.
- Foundation verification (T004 and T006) is parallel-safe; fixture movement (T005) is the shared prerequisite.
- US1 test updates T007 and T008 are parallel-safe because they touch different test files; adapter implementation waits for both.
- US2 fixture audit (T011 and T012) is parallel-safe; guidance update T013 follows the audit.
- US3 specification updates T017 and T018, parity T019, and documentation-link validation T020 are parallel-safe when the setup projection is not being edited concurrently.

---

## Parallel Example: User Story 1

```text
T007  personalAgent/tests/test_ainative_adapter.py
T008  personalAgent/tests/test_agent_executor.py
```

After both test updates are ready:

```text
T009  personalAgent/src/hermes_kanban/ainative.py
T010  focused pytest and ruff verification
```

## Parallel Example: User Story 2

```text
T011  personalAgent/tests/test_live_piv_bridge.py and personalAgent/tests/test_harness_adapter.py
T012  personalAgent/tests/fixtures/ainative/
```

Then update and verify:

```text
T013  personalAgent/AGENTS.md and personalAgent/docs/v0-implementation-plan.md
T014  focused consumer test suite
```

## Parallel Example: User Story 3

```text
T017  specs/001-ainative-adapter/*
T018  specs/004-agent-execution/*, specs/005-piv-orchestrator/tasks.md, specs/006-piv-recovery/tasks.md
T019  AiNative/scripts/check-agent-commands.sh
T020  AiNative/scripts/check-doc-links.mjs
```

Run setup and the final gates after overlapping consumer projection edits are complete:

```text
T015  AiNative/scripts/setup-project.sh -> personalAgent/
T021  AiNative/scripts/check-ainative-link.sh
T022  stale-path audit
T023  read-only/write-refusal audit
T024  full pytest and ruff
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 test updates and strict adapter cutover.
3. Run the focused adapter/executor checks and Ruff.
4. Stop and validate that only `docs/agents/` is accepted before expanding scope.

### Incremental Delivery

1. Add US2 fixture, integration, and guidance alignment; run focused consumer checks.
2. Add US3 setup projection and active specification updates.
3. Run parity, documentation-link, setup self-check, stale-path, read-only, full pytest, and Ruff gates.
4. Record the delivered change in both changelogs.

### Constraints During Implementation

- Do not modify or copy the nested `AiNative/` checkout.
- Do not add `docs/8-agents` aliases, duplicate folders, manifest fallback, or top-level `agents/` lookup.
- Do not add a Hermes runtime reader for `knowledge` or `records`.
- Do not require network access, credentials, or writes to the real AiNative mount for fixture verification.

## Notes

- Every task has a checkbox, sequential ID, required story label for story phases, and concrete file path(s).
- `[P]` is used only where tasks touch different files and have no incomplete dependency.
- Existing historical migration records and negative setup assertions may retain retired path names when they explicitly explain or verify the clean break.
- Tests are required here because the feature specification makes adapter, setup, parity, link, read-only, and hermetic verification part of acceptance.

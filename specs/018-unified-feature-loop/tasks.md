# Tasks: 018-unified-feature-loop — Unified feature loop (Hermes stages + Pi per step)

**Input**: Design documents from `/specs/018-unified-feature-loop/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Tests ARE requested by the spec (apply checklist §2 "Tests" bullet and SC-004). Contract-style pytest tasks are included per user story using the fixture Pi runtime (no network, no real Pi process).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Methodology SoT is `AiNative/docs/systems/feature-loop.md` (linked, never copied — FR-010).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Code: `personalAgent/src/hermes_kanban/` (existing package, extended in place)
- Tests: `personalAgent/tests/` (hermetic, fixture Pi runtime)
- Docs: `personalAgent/AGENTS.md`, `personalAgent/README.md`, `personalAgent/docs/context/SYSTEM.md`; AiNative dev-time edits; banner specs `specs/011…014/`
- Cursor `/speckit-orchestrate` and `/pi-harness`: **out of scope, never edited (FR-013)**

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing project shape and add the state-graph data that all stories depend on

- [x] T001 Verify personalAgent hermetic baseline: `uv run pytest` and `uv run ruff check .` pass in `personalAgent/` before any change (SC-004 guard)
- [x] T002 [P] Define the canonical `LoopState` enum + state-kind table (agent/human/parent) in `personalAgent/src/hermes_kanban/orchestrator.py` as plain data, ids exactly: ready, specify, clarify, confirm, plan, tasks, analyze, implement, converge, critic, tester, uat, pr-review, publish (data-model.md §1)
- [x] T003 [P] Add the per-step model-profile mapping schema (ready/specify/…/pr-review) to `personalAgent/config.yaml` handling; unknown step in map fails closed at startup; remove `harness.playbook` (research.md R9)

**Checkpoint**: State ids exist as data; no behavior change yet

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Per-step request contract and strict report parsing — required by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Replace `HarnessStartRequest` with `StepStartRequest` in `personalAgent/src/hermes_kanban/external_framework.py`: fields `step_id`, `flow_id`, `skill_path`, `workspace_path`, `workspace_branch`, `model_profile`, `timeout_seconds`, `inputs`, `operator_flags`, `resume_context` (contracts/harness-request.md); drop `playbook_id`
- [x] T005 Implement request validation in `personalAgent/src/hermes_kanban/external_framework.py`: `step_id` must be agent-kind on the graph; refuse (raise `HarnessValidationError`) any request carrying playbook id `speckit-orchestrate` or non-agent states `confirm`/`uat`/`publish`; do NOT translate (FR-005, FR-006, FR-014, SC-002)
- [x] T006 Implement per-state compact-report parsing (strict, extends `_coerce_response`) in `personalAgent/src/hermes_kanban/external_framework.py` per contracts/compact-reports.md: ready (`READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES`), spec-kit steps (`STATUS`, `ARTIFACTS`, `SUMMARY`; plan adds `ANALYZE: yes|no`), implement (`IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`), converge (`CONVERGE_OUTCOME`, `FINDINGS`, `FINGERPRINT`, `TASKS_APPENDED`), critic/tester/pr-reviewer (parseable PASS/FAIL mandatory); unknown/missing fields ⇒ step failure, no lenient defaults (FR-008 boundary)
- [x] T007 Update Pi adapter in `personalAgent/src/hermes_kanban/pi.py`: one RPC run per step start, prompt names ONLY that step + its skill path; per-step resume context only; safety constraints carried unchanged (write root = worktree, feature branch only, no publish/push/merge) (FR-002, FR-004)
- [x] T008 Extend `AiNativeAdapter` in `personalAgent/src/hermes_kanban/ainative.py` to resolve live agent set `ready` (promoted `docs/agents/ready/`), `critic`, `tester`, `pr-reviewer` from `/ainative/docs/agents/<name>/`; remove the global `speckit-ready` map-only option (FR-011, research.md R5)

**Checkpoint**: Boundary contracts done — request in, report out, per step. User stories can now proceed.

---

## Phase 3: User Story 1 — Hermes dispatches one Pi session per state (Priority: P1) 🎯 MVP

**Goal**: Live execution is the Hermes-owned state machine over the canonical graph; every agent state starts a new Pi session; no whole-playbook dispatch.

**Independent Test**: Fixture Pi records each start (step id + session handle). Drive one fake successful run: assert N starts, N distinct sessions, order matches the graph, and no prompt includes a later step name as an instruction (spec.md US1).

### Tests for User Story 1

- [x] T009 [P] [US1] Create `personalAgent/tests/test_feature_loop_states.py`: fixture Pi records starts; full successful run yields one start per agent state (ready, specify, clarify, plan, tasks, [analyze], implement, converge, critic, tester, pr-review) with DISTINCT session handles, zero starts for confirm/uat/publish, order matches graph; `analyze` runs only when plan says `ANALYZE: yes` (SC-001)
- [x] T010 [P] [US1] Create `personalAgent/tests/test_prompt_isolation.py`: inspect each recorded prompt — names only that step + skill path; no prompt instructs a later state; any `speckit-orchestrate` or non-agent `step_id` request is refused (FR-004, SC-002)

### Implementation for User Story 1

- [x] T011 [US1] Implement the overlay state machine in `personalAgent/src/hermes_kanban/orchestrator.py`: generalize `current_phase` to `LoopState` ids; transition table per contracts/state-graph.md (advance edges); malformed report or exhausted retries ⇒ park (depends on T002, T004–T007)
- [x] T012 [US1] Implement per-step dispatch in `personalAgent/src/hermes_kanban/executor.py`: remove role map (discovery/planning/implementation/validation), playbook config, and `_run_validation`-as-gate; step-id dispatch via `StepStartRequest`; each agent state = one new Pi session (FR-002, FR-005)
- [x] T013 [US1] Implement implement↔converge loop in `personalAgent/src/hermes_kanban/orchestrator.py`: `CONVERGE_OUTCOME: tasks_appended` ⇒ new implement session (never instructing the converge session to implement); unchanged `FINGERPRINT` ⇒ stuck ⇒ park; `blocked` ⇒ park (FR-004, R7)
- [x] T014 [US1] Implement per-state stuck policy in `personalAgent/src/hermes_kanban/orchestrator.py`: 3 attempts per state then park; stable `READY: blocked` never retried; missing spec/plan/tasks artifacts never retried (contracts/state-graph.md Guarantee 5)
- [x] T015 [US1] Remove `speckit-orchestrate` whole-playbook path from all live dispatch, fallback, resume/recovery, and prompt text in `personalAgent/src/hermes_kanban/executor.py` and `pi.py` (same removal posture as 013; FR-005, FR-014)

**Checkpoint**: User Story 1 independently functional — a fake full run walks the graph, one fresh session per state.

---

## Phase 4: User Story 2 — Human gates stay in Hermes (Priority: P1)

**Goal**: Clarify, confirm, and uat park as `needs_human` via existing Telegram park/resume; Pi never owns skip/confirm/UAT policy; confirm/uat never start Pi.

**Independent Test**: Fixture clarify returns a question queue; assert park, recorded answers, then a new Pi start for encode-answers or plan after confirm — never Pi chatting with the operator (spec.md US2).

### Tests for User Story 2

- [x] T016 [P] [US2] Create `personalAgent/tests/test_human_gates.py`: clarify `STATUS: blocked` + questions ⇒ park `HUMAN_DECISION_REQUIRED` with 0 further stages; after recorded answers a NEW Pi session encodes them; `confirm` always precedes `plan` (including under operator `skip`); UAT starts no Pi session and presents a feature-derived QA checklist; after pr-review the record parks — never auto-loops (FR-006, FR-015, FR-016)

### Implementation for User Story 2

- [x] T017 [US2] Implement clarify question park/relay in `personalAgent/src/hermes_kanban/orchestrator.py`: blocked clarify ⇒ park with `question_queue`, relay one question at a time over existing Telegram path, answers resume into a second **clarify** Pi session (encode-answers carries the answers in the resume context; same `clarify` step id — not a new LoopState, no new graph state) (R6)
- [x] T018 [US2] Implement `confirm` as a human continuation in `personalAgent/src/hermes_kanban/orchestrator.py`: operator continuation advances to `plan`; `skip` self-answers clarify but confirm still runs; no Pi (FR-006)
- [x] T019 [US2] Implement `uat` as simple human QA in `personalAgent/src/hermes_kanban/orchestrator.py`: derive QA checklist from converge report / quickstart into `uat_checklist`, present to operator, record pass; no Pi, no failure-state machine, no auto-loop (FR-015, R6)
- [x] T020 [US2] Implement post-pr-review parking in `personalAgent/src/hermes_kanban/orchestrator.py`: after pr-review completes (PASS or FAIL) record parks `HUMAN_DECISION_REQUIRED`; operator approval after PASS unlocks `publish` only (FR-016, contracts/state-graph.md)

**Checkpoint**: Stories 1 AND 2 work independently — the graph walks with human gates as parks.

---

## Phase 5: User Story 3 — Validation is critic then tester then UAT (Priority: P1)

**Goal**: After converge: Pi(critic) → Pi(tester) → UAT (human) → Pi(pr-review) → Hermes publish. No shell validation phase. Publish only after all gates PASS.

**Independent Test**: Fixture converge `converged`; assert next starts are critic, tester, (no Pi), pr-review, then GitHub path; `validation_commands` never run by Hermes as a substitute (spec.md US3).

### Tests for User Story 3

- [x] T021 [P] [US3] Create `personalAgent/tests/test_publish_gate.py`: converge `converged` ⇒ critic starts before tester before UAT before pr-review; tester request `inputs` carries declared `validation_commands` and Hermes never executes them in-process; publish (commit/push/PR) attempted only after critic PASS ∧ tester PASS ∧ uat pass ∧ pr-review PASS, feature branch only, never main/master; critic retryable FAIL follows bounded retries without skipping to publish (FR-007, FR-008, FR-009)

### Implementation for User Story 3

- [x] T022 [US3] Move validation into the tester step in `personalAgent/src/hermes_kanban/executor.py`: delete `_run_validation` shell gate; pass `ProjectContext.validation_commands` as tester request `inputs`; Hermes does not execute them (FR-008, R4)
- [x] T023 [US3] Wire critic → tester → uat → pr-review transitions in `personalAgent/src/hermes_kanban/orchestrator.py`: critic FAIL retryable ⇒ bounded retries; tester pass ⇒ uat; uat operator pass ⇒ pr-review; pr-review PASS ⇒ publish park decision (FR-007)
- [x] T024 [US3] Restrict the GitHub unlock in `personalAgent/src/hermes_kanban/github.py` to: critic PASS ∧ tester PASS ∧ uat pass ∧ pr-review PASS recorded in `steps`; commit/push/PR on feature branch only; no Pi for publish (FR-009)

**Checkpoint**: Stories 1–3 work independently — publish is gated end-to-end.

---

## Phase 6: User Story 4 — Hermes docs match the loop (Priority: P1)

**Goal**: AiNative `feature-loop.md` is the SoT; personalAgent docs link to it and describe one Pi session per agent state; supersede banners on specs 011–014; Cursor untouched.

**Independent Test**: Grep live path docs for "one Pi playbook" / "forbid Hermes-owned stages" / "PIV before multi-file" as live contract — those claims must be gone or marked historical (spec.md US4).

### Implementation for User Story 4

- [x] T025 [P] [US4] Rewrite `personalAgent/AGENTS.md`: one Pi session per agent state; Hermes never runs skills in-process; LINK `/ainative/docs/systems/feature-loop.md` (no pasted graph); delete "do not restore Hermes-owned stages" and "one speckit-orchestrate playbook" lines (FR-010, SC-003)
- [x] T026 [P] [US4] Rewrite `personalAgent/README.md` with the same posture as T025 (FR-010, SC-003)
- [x] T027 [P] [US4] Align reference copy `personalAgent/docs/context/SYSTEM.md` with the new `AGENTS.md` text (plan.md Project Structure)
- [x] T028 [P] [US4] Add supersede banners on live-path sections of `specs/011-*/spec.md`, `specs/012-*/spec.md`, `specs/013-*/spec.md`, `specs/014-*/spec.md`: "superseded by 018 for execution shape"; no scenario rewrites (spec.md §4)
- [x] T029 [P] [US4] AiNative dev-time edits per apply checklist §1: point `docs/systems/agentic-coding.md`, `docs/systems/README.md`, `docs/README.md`, `ENGINEERING-OS.md`, `.cursor/rules/piv-gate.mdc`, `.cursor/rules/ai-rules.mdc`, `docs/systems/cursor-rules.md`, `docs/systems/ai-rules-template.md` at the feature loop as live; mark old PIV historical; update `docs/agents/README.md` (Ready promoted, critic/tester/pr-reviewer live; scout/plan-reviewer optional off-graph) (FR-011, R10)
- [x] T030 [P] [US4] Promote the Ready agent as `AiNative/docs/agents/ready/` (modeled on `~/.cursor/skills/speckit-ready`, folder contract `AGENTS.md`/`SKILL.md`/`rule.md`); document the single Ready agent in `AiNative/docs/systems/feature-loop.md` (one-line edit of the ready row's global-speckit-ready mention) (FR-011, R5)
- [x] T031 [US4] Verify no contradictory live loop remains: run quickstart V6 greps (`grep -rn "speckit-orchestrate" personalAgent/AGENTS.md personalAgent/README.md` must be empty; feature-loop link present); confirm `git status` shows zero Cursor changes (FR-013, SC-003)

**Checkpoint**: All user stories independently functional; docs agree with the runtime.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Legacy parking, migration safety, and full-suite validation

- [x] T032 Extend `personalAgent/tests/test_legacy_stage_removal.py`: every live dispatch path refuses a whole-playbook job (SC-002: 100% refusal); config no longer defines `harness.playbook`; `_run_validation` no longer unlocks GitHub (quickstart V5)
- [x] T033 Implement legacy-record parking in `personalAgent/src/hermes_kanban/orchestrator.py`: at startup detect `013` records (`current_phase` ∈ {execution, validation, github} or playbook id present) and park `HUMAN_DECISION_REQUIRED` with diagnostic "superseded by 018 — whole-playbook run"; never auto-migrate (FR-012, Edge Case 1)
- [x] T034 Run full quickstart validation V1–V6 in `specs/018-unified-feature-loop/quickstart.md`; verify all expectations per scenario
- [x] T035 Final gate: `uv run pytest && uv run ruff check .` passes in `personalAgent/`; existing hermetic tests still pass (SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (state ids) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — the runtime contract, first MVP increment
- **US2 (Phase 4)**: Depends on US1 (state machine exists to park/resume within)
- **US3 (Phase 5)**: Depends on US1 (converge→graph) and US2 (uat human gate exists)
- **US4 (Phase 6)**: Docs can be drafted in parallel with stories but verification (T031) needs the runtime claims settled; banner tasks T028–T030 have no code dependencies
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — no other story dependencies
- **US2 (P1)**: Uses the US1 state machine; independently testable after US1
- **US3 (P1)**: Tail of the same graph; independently testable after US1 (+US2 for uat)
- **US4 (P1)**: Independent file set (docs); verify last

### Within Each User Story

- Tests (fixture Pi) written to fail first, then implementation
- Data/contracts (Phase 2) before state machine before dispatch
- Core implementation before integration (github unlock, legacy parking)

### Parallel Opportunities

- Phase 1: T002, T003 in parallel
- Phase 2: T005/T006/T007/T008 after T004 (different files, contract-driven)
- Test files T009/T010 (US1), T016 (US2), T021 (US3) each in parallel
- US4: T025–T030 all in parallel (disjoint files)
- T001, T028, T029, T030 have no code dependencies — start anytime

---

## Parallel Example: User Story 1

```bash
# Launch test-writing tasks together:
Task: "tests/test_feature_loop_states.py (T009)"
Task: "tests/test_prompt_isolation.py (T010)"

# Then implementation in dependency order:
Task: "orchestrator.py state machine (T011)"  →  Task: "executor.py step dispatch (T012)"
→ Task: "converge loop (T013)" → Task: "stuck policy (T014)" → Task: "playbook removal (T015)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: fixture full run shows one new session per agent state (V1, V2)
5. The runtime contract exists — demo if ready

### Incremental Delivery

1. Setup + Foundational → boundary contracts done
2. US1 → per-state starts proven (MVP)
3. US2 → human gates park/resume (V3)
4. US3 → critic→tester→UAT→pr-review→publish gate (V4)
5. US4 → docs agree (V6); Polish → legacy parking + full gate (V5, SC-004)

### Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All tests are hermetic: fixture Pi runtime, no network, no real Pi process, no Telegram
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Never edit Cursor `/speckit-orchestrate` or `/pi-harness` (FR-013)
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence

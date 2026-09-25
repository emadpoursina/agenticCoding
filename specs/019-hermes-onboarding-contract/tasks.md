# Tasks: Hermes onboarding contract (Kanban as the user-facing work queue)

**Feature Branch**: `hermes-onboarding-contract`
**Input**: Design documents from `specs/019-hermes-onboarding-contract/`
(plan.md, spec.md, research.md D1–D9, data-model.md, contracts/,
quickstart.md scenarios A–G)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/card-body.md, contracts/orchestrator.md, contracts/onboarding.md

**Tests**: Explicitly requested — spec SC-005/quickstart cross-checks require
one hermetic automated check per FR-021..FR-029, plus the preserved baseline
(`tests/test_onboarding.py`: 17 guarantees, 11 behaviors) that must keep
passing unchanged. All tests are hermetic: pytest + fake seams — no live
GitHub, Telegram, model, or operator board.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story. All changes land in the existing
`personalAgent/src/hermes_kanban/` package in place (no new modules, no
second task database) per plan.md structure decision.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5 from spec.md)
- Include exact file paths in descriptions

## Path Conventions

- Single existing package: `personalAgent/src/hermes_kanban/` (source),
  `personalAgent/tests/` (tests) at workspace root
- Run pytest via: `cd personalAgent && uv run pytest tests/<file> -q`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding and the preserved-baseline gate

- [X] T001 [P] Create `personalAgent/tests/test_onboarding_contract.py` with hermetic scaffolding: fixture `kanban.db` board, `write_projects_db`/`write_config`/`fake_cloner` helpers mirroring `personalAgent/tests/test_onboarding.py` patterns
- [X] T002 [P] Create `personalAgent/tests/test_feature_parent_completion.py` with fake-harness scaffolding: `MemoryTaskBoard`, injectable `CardCreateFn`/`live_create_card`/`live_add_card_note` seams and fake Pi harness mirroring `personalAgent/tests/test_piv_orchestrator.py` patterns
- [X] T003 Run baseline gate: `cd personalAgent && uv run pytest tests/test_onboarding.py -q` — all 17 guarantees / 11 established behaviors pass UNCHANGED before any source edit (FR-020, SC-005)

**Checkpoint**: Test files exist (empty or placeholder), baseline recorded green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared read-side and durability surfaces that US1–US5 all extend

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Extend `BoardTask` in `personalAgent/src/hermes_kanban/board.py`: add `parent_id: str = ""` and `profile: str = ""` parsed read-only from `## Parent` / `## Profile` body sections via the existing `_sections` helper; absent sections default to "" (research D1, D9; contracts/card-body.md)
- [X] T005 [P] Extend `WorkflowRecord` in `personalAgent/src/hermes_kanban/orchestrator.py`: add `parent_task_id: str | None`, `children: tuple[str, ...]`, and `AWAITING_CHILDREN` to the active-state machinery (research D4, D7; data-model.md Workflow Record)
- [X] T006 [P] Extend `personalAgent/src/hermes_kanban/persist.py`: round-trip `parent_task_id`/`children` through the existing `_jsonable`/`_record_from_dict` path, add `awaiting_children` to `_canonical_phase` allowlist, and add `append_decision(directory, entry)` — fsync'd append-only JSONL to `<overlay_dir>/decisions.jsonl` (research D2, D7; contracts/orchestrator.md "Durability rules")
- [X] T007 [P] Add `live_add_card_note(card_id: str, text: str) -> None` seam in `personalAgent/src/hermes_kanban/onboard.py` beside `live_create_card`/`_run_hermes` — native `hermes kanban` CLI note write, fail-closed, seam-injectable for tests (research D5; contracts/orchestrator.md "Board seams")

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel (US1 → US2 are independent of each other; US3–US5 note their deps below).

---

## Phase 3: User Story 1 — Operator submits a desired outcome and the system completes it (Priority: P1) 🎯 MVP

**Goal**: Feature Card on the primary board → task-generator decomposition into child Task Cards → independent child execution → automated feature validation → parent completes with zero operator knowledge of the internal workflow.

**Independent Test**: Enrolled fixture project + one Feature Card; drive the loop with the fake harness (`tests/test_feature_parent_completion.py`): `tasks` completes → child cards appear with `## Parent` → complete all children (simulated executors) → validator PASS → parent card `done` with zero operator actions (FR-011, FR-012, FR-016, FR-028; quickstart Scenario B).

### Tests for User Story 1 (hermetic, written first) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Contract test FR-022: a Feature Card created on the primary board belongs to the enrolled project and its primary board (`project_id` filter) — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T009 [P] [US1] Test FR-023: child Task Cards reference their parent Feature Card (body `## Parent` ∪ native `task_links`), parent identifiable from any child; dangling/self parent fails card creation — in `personalAgent/tests/test_feature_parent_completion.py`
- [X] T010 [P] [US1] Lifecycle test FR-011/FR-016: at `tasks` completion with `specs/<feature-id>/tasks.md`, child Task Cards appear on the same board (never workflow-state cards), each independently claimable (FR-025) — in `personalAgent/tests/test_feature_parent_completion.py`
- [X] T011 [P] [US1] Parent-completion rule test FR-012: parent completes only when ALL task-generator children are complete (none optional) + validation passes; a partial child set never completes the parent — in `personalAgent/tests/test_feature_parent_completion.py`
- [X] T012 [P] [US1] Automated-validator test FR-026/FR-028: validator (critic → tester) is associated with the Feature Card, not children; PASS + no raised gate ⇒ parent completes with zero additional operator actions — in `personalAgent/tests/test_feature_parent_completion.py`
- [X] T013 [P] [US1] Human-gate test FR-017 / SC-006: a raised clarify/confirm/uat/blocked gate parks durably, posts a visible gate marker (decision brief + resume hint) on the parked card, resolves via `resume_workflow` with a closing note, zero silent bypasses; a gate-marker CLI failure surfaces but leaves park state unchanged — in `personalAgent/tests/test_feature_parent_completion.py`
- [X] T014 [P] [US1] Edge-case tests: (a) decomposition produces zero children ⇒ parent stays open with durable surfaced failure (no empty completion); (b) a child failure parks/retries the child only, parent stays open — in `personalAgent/tests/test_feature_parent_completion.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement `decompose_children(record)` in `personalAgent/src/hermes_kanban/orchestrator.py`: parse `specs/<feature-id>/tasks.md` artifact via existing `_artifact_for_step` seam, create child Task Cards through the existing `CardCreateFn`/`live_create_card` seam with `## Parent` + `## Profile: executor` bodies and idempotency keys, capture `record.children`, park record in `AWAITING_CHILDREN` (research D4; depends T004, T005)
- [X] T016 [US1] Implement `evaluate_parent(parent_id)` in `personalAgent/src/hermes_kanban/orchestrator.py`: re-read the board, re-derive children truth from the board (never stored snapshots), move the parent record to the validator step when no incomplete children remain (research D2, D7; depends T015)
- [X] T017 [US1] Wire manual-edit re-evaluation into `resume_workflow` and `run_next_workflow` in `personalAgent/src/hermes_kanban/orchestrator.py`: manually completed child (column `done`/`archived`) counts toward parent; deleted child is dropped from the requirement set; orchestrator never restores deleted / demotes completed children (FR-029; contracts/orchestrator.md "Manual-edit rule"; depends T016)
- [X] T018 [US1] Journal integration in `personalAgent/src/hermes_kanban/orchestrator.py`: append `child-completed`/`child-deleted`/`parent-completed`/`gate-raised`/`gate-resolved` entries via `persist.append_decision` with board evidence; write failure surfaced fail-closed, never gated on silently (FR-029; depends T006, T016)
- [X] T019 [US1] Implement `run_validator(record)` in `personalAgent/src/hermes_kanban/orchestrator.py`: run existing `critic` → `tester` verdict states against the parent worktree (feature-level, not per-child); PASS + no raised gate → `_complete` with zero human actions; raised gate → park per existing path (FR-026, FR-028; research D4; depends T016)
- [X] T020 [US1] Gate markers: on every park (`_park_step_human`, clarify, confirm, uat, pr-review, generic) call `live_add_card_note` with the flat-rendered `DecisionBrief` (gate kind, decision, options, `--resume project task option` hint); on resume/complete post the closing note so no stale open gate remains (FR-017; research D5; depends T007, T019)
- [X] T021 [US1] Narrow `confirm`/`uat` park triggers in `personalAgent/src/hermes_kanban/orchestrator.py` per recorded collision: park only when the step report / verdict flags unresolved questions or acceptance items or a blocked dependency; absent a raise, no human wait; existing `skip` flag behavior unchanged; validate with a dedicated hermetic check inside `personalAgent/tests/test_feature_parent_completion.py` (plan Complexity Tracking; research D4; depends T019)

**Checkpoint**: User Story 1 (MVP) fully functional and testable independently — end-to-end card-to-completion flow runs hermetically.

---

## Phase 4: User Story 2 — Onboarding guarantees a complete, inspectable project contract (Priority: P1)

**Goal**: Identity + board discoverability recorded at onboarding; idempotent, fail-closed behavior preserved and now includes the primary board.

**Independent Test**: Fixture onboarding run returns `OnboardResult.board_path`; re-run is identical with zero writes/zero diffs; missing board fails closed (FR-001–FR-007, FR-020 preservation, FR-021; quickstart Scenario A).

### Tests for User Story 2 (hermetic, written first) ⚠️

- [X] T022 [P] [US2] Contract test FR-021: fixture onboarding yields `OnboardResult.board_path` pointing at a readable fixture board; a missing/unreadable native board fails closed with `OnboardError` and no partial enrollment — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T023 [P] [US2] Idempotency test SC-003: re-running onboarding on an enrolled fixture returns the same `board_path` with zero diffs (config bytes, board rows, scaffold files) and zero writes — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T024 [P] [US2] Dry-run test: the board-discoverability check is read-only, the printed plan includes the projected primary-board result (board path, native id, would-be cards), and nothing is written anywhere (preserved guarantee 13) — in `personalAgent/tests/test_onboarding_contract.py`

### Implementation for User Story 2

- [X] T025 [US2] Add `board_path: Path` field to `OnboardResult` and a read-only native-board present/readable check in `run_onboard` in `personalAgent/src/hermes_kanban/onboard.py`; fail closed before any scaffold work (FR-008, FR-021; contracts/onboarding.md; research D6)
- [X] T026 [US2] Print `board: <path>` line on the enroll/import reports in `personalAgent/src/hermes_kanban/runtime.py` (FR-021; contracts/onboarding.md CLI section; depends T025)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (and the full preserved baseline still passes).

---

## Phase 5: User Story 3 — The board shows work, not workflow (Priority: P2)

**Goal**: Zero cards encode internal workflow states; internal states stay orchestrator-owned, durable, invisible; restarts resume from board + overlay.

**Independent Test**: Mid-feature, list every card on the fixture board and assert only Feature/Task Cards exist with no workflow-state Path/Profile values; restart the orchestrator mid-feature and assert resume with no conversation reconstruction and no workflow-state card (FR-009, FR-010, FR-027, FR-018; quickstart Scenario C).

**Dependencies**: US3 implementation needs the US1 orchestrator machinery (`AWAITING_CHILDREN`, decomposition) but its tests are written against that same hermetic scaffold; do not start before T015–T016.

### Tests for User Story 3 (hermetic, written first) ⚠️

- [X] T027 [P] [US3] Contract tests FR-027/SC-002: (a) card-draft validation rejects a workflow-state name (`ready, specify, clarify, confirm, plan, tasks, implement, converge, critic, tester, uat, pr-review, publish`) as `## Path` or `## Profile` for every card path (feature/change/job); (b) mid-feature board inspection shows only Feature/Task Cards — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T028 [P] [US3] Restart matrix (FR-018, SC-004): force interruptions at decomposition, child execution, validator, and park points; re-instantiate the orchestrator on the same fixture overlay dir and assert resume from board + overlay, children re-derived from the board (never a stored snapshot), no conversation reconstruction, no new workflow-state card — in `personalAgent/tests/test_feature_parent_completion.py`

### Implementation for User Story 3

- [X] T029 [US3] Extend `validate_card_draft` in `personalAgent/src/hermes_kanban/onboard.py` (and the shared composition used by PRD import/guide) to reject workflow-state names as Path/Profile values, fail-closed at the trust boundary (FR-027; research D9; depends T004)
- [X] T030 [US3] Restart re-derivation in `personalAgent/src/hermes_kanban/orchestrator.py`: on `become_ready`/`_board_record`, rebuild child completion sets from a fresh board read (missing children journaled per T018), never from persisted status snapshots; `AWAITING_CHILDREN` records resume correctly via `persist` round-trip (FR-018, FR-010; research D7; depends T005, T006, T016)

**Checkpoint**: All three board-truth guarantees hold: work-only board, durable invisible states, full restart recovery.

---

## Phase 6: User Story 4 — Profiles describe execution strategy, never a provider (Priority: P2)

**Goal**: task-generator / executor / validator roles as profile semantics with provider/vendor rejection; Path-selected default auto-applied at creation, operator-overridable.

**Independent Test**: Card bodies with `## Profile: openai`/`gpt-4`/`some/provider` are rejected; role values (with optional named strategy) accepted; a Feature Card without `## Profile` receives the Path-selected default; overrides pass the same validation (FR-013, FR-014, FR-014a, FR-024; quickstart Scenario D).

### Tests for User Story 4 (hermetic, written first) ⚠️

- [X] T031 [P] [US4] Contract test FR-014/FR-013: profile values `openai`, `gpt-4`, provider-style refs (`/`, `\`) are rejected with allowed-roles message; `task-generator`, `executor`, `validator` and `role:named-strategy` accepted; the task-generator role is a profile/role, never a workflow state or board card (FR-024) — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T032 [P] [US4] Contract test FR-014a: a Feature Card created without `## Profile` gets the Path-selected project default (`feature` → task-generator; `change`/`job` → their defaults from `profiles.defaults` config/overlay, fallback = role name); operator overrides later are honored and validated; legacy cards without the section are NOT rewritten (idempotency) — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T033 [P] [US4] Test FR-025: a child Task Card assigned an executor profile is claimable/completable by a single executor independently of its siblings (one card, one executor at a time, single workflow slot) — in `personalAgent/tests/test_feature_parent_completion.py`

### Implementation for User Story 4

- [X] T034 [US4] Role allowlist + provider-leak shared helper in `personalAgent/src/hermes_kanban/external_framework.py`: reuse the existing named-reference rule and `_PROVIDER_LEAK` regex; expose for `validate_card_draft` and card composition (contracts/card-body.md Profile rules 1–3; research D3; depends T004)
- [X] T035 [US4] Profile-for-role resolution in `personalAgent/src/hermes_kanban/executor.py` + `personalAgent/src/hermes_kanban/orchestrator.py`: read card `## Profile` (named strategy ref, no provider), else apply the Path default at claim time without mutating the card body; runtime/model selection stays in Hermes config (FR-013, FR-014; contracts/card-body.md rule 5; depends T004, T034)

**Checkpoint**: All user stories so far independently functional; provider name can never appear as a profile.

---

## Phase 7: User Story 5 — PRD import lands on the new hierarchy (Priority: P3)

**Goal**: Optional PRD import preserved; each section becomes a top-level Feature Card on the primary board; draft-only and dry-run stay write-free.

**Independent Test**: Import a 2-section PRD with card creation (fake card creator): 2 top-level Feature Cards, `## Path: feature`, default task-generator profile, none encoding a workflow state; draft-only mode produces only files (FR-019; quickstart Scenario G).

**Dependencies**: depends on T034 (profile composition helper) and the foundational card-body machinery.

### Tests for User Story 5 (hermetic, written first) ⚠️

- [X] T036 [P] [US5] Contract test FR-019: N-section PRD import with card creation (fake creator) yields N top-level Feature Cards on the native project, each with `## Path: feature` and the default task-generator profile, none encoding a workflow state — in `personalAgent/tests/test_onboarding_contract.py`
- [X] T037 [P] [US5] Preserved-behavior test: same import in draft-only mode produces drafts as files with nothing written to the board; `--dry-run` writes nothing anywhere (existing guarantees 12/13) — in `personalAgent/tests/test_onboarding_contract.py`

### Implementation for User Story 5

- [X] T038 [US5] Compose `## Path: feature` + default `## Profile: task-generator` into PRD-import card drafts in `personalAgent/src/hermes_kanban/onboard.py` (`create_cards_from_drafts`) and `personalAgent/src/hermes_kanban/guide.py` (`card_text`), passing the same validation; draft-only/dry-run untouched (research D8; contracts/onboarding.md "Card-creation composition"; depends T034)

**Checkpoint**: All user stories independently functional; the full lifecycle and hierarchy hold end to end.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, trust-boundary hardening, and regression proof

- [X] T039 [P] Malformed-body trust-boundary tests (research D9, constitution IV): malformed `## Parent` (dangling id, self-reference, top-level card carrying `## Parent`) and malformed `## Profile` values are rejected fail-closed at creation in `personalAgent/tests/test_onboarding_contract.py`
- [X] T040 [P] Run `ruff` and the full suite `cd personalAgent && uv run pytest tests/ -q`: `tests/test_onboarding.py` passes UNCHANGED (17 guarantees, 11 behaviors) plus all new files green — record output
- [X] T041 Run `specs/019-hermes-onboarding-contract/quickstart.md` Scenarios A–G end to end as the validation record; fix any gap found and re-run
- [X] T042 SC-005 completeness check: confirm every FR-021..FR-029 maps to ≥1 automated hermetic check across `personalAgent/tests/test_onboarding_contract.py` and `personalAgent/tests/test_feature_parent_completion.py`, and SC-003 zero-diff idempotency + SC-004 restart matrix pass — annotate any gap and close it

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately; T003 baseline gate MUST be green before any source edit (FR-020 preservation proof)
- **Foundational (Phase 2)**: depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: depends on Phase 2 only
- **US2 (Phase 4)**: depends on Phase 2 only — independent of US1 (may run in parallel)
- **US3 (Phase 5)**: tests T027–T028 can be drafted early, but implementation T029–T030 depends on T015–T016 (US1 decomposition + record machinery)
- **US4 (Phase 6)**: depends on Phase 2 (T034 also reused by US5)
- **US5 (Phase 7)**: depends on T034 (profile composition) — allocated to US4's helper
- **Polish (Phase 8)**: depends on all user stories complete

### User Story Dependencies

- **US1 (P1, MVP)**: Foundational → fully independent
- **US2 (P1)**: Foundational → independent of US1
- **US3 (P2)**: builds on US1 orchestrator machinery; independently verifiable via board inspection + restart matrix
- **US4 (P2)**: independent of US1/US3 (profile validation path); FR-025 test uses US1 child-claim machinery
- **US5 (P3)**: independent journey; implementation rides US4's profile helper

### Within Each User Story

- Tests written first and FAILING before implementation (hermetic, no live services)
- Board/persist read-side (T004–T007 style) before orchestrator logic
- Core implementation before integration wiring
- Story complete before next priority

### Parallel Opportunities

- Phase 1: T001, T002 together; T003 after (gate)
- Phase 2: T004–T007 all parallel (different files)
- US1 tests T008–T014 all parallel; US2 tests T022–T024 all parallel; US3 tests T027–T028; US4 tests T031–T033; US5 tests T036–T037
- Entire US2 phase can run in parallel with US1 phase
- Cross-story: US2 can proceed while US1 implementation lands (different modules: onboard.py/runtime.py vs orchestrator.py)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (hermetic, different concerns):
Task: "Contract test FR-022 in personalAgent/tests/test_onboarding_contract.py"
Task: "Parent-link test FR-023 in personalAgent/tests/test_feature_parent_completion.py"
Task: "Lifecycle test FR-011/016 in personalAgent/tests/test_feature_parent_completion.py"
Task: "Automated-validator test FR-026/028 in personalAgent/tests/test_feature_parent_completion.py"
# Then implementation in dependency order:
Task: decompose_children (T015) → evaluate_parent (T016) → manual-edit wiring (T017)
      → journal (T018) → run_validator (T019) → gate markers (T020) → trigger narrowing (T021)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (incl. baseline gate T003)
2. Complete Phase 2: Foundational (blocks all stories)
3. Complete Phase 3: US1 — decomposition → children → validation → completion
4. **STOP and VALIDATE**: US1 tests + preserved baseline green
5. Demo: an enrolled fixture project completes one Feature Card end to end

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test independently → deploy/demo (MVP!)
3. US2 (+ board_path discoverability) → test independently
4. US3 (board shows work, not workflow) → independent board-inspection check
5. US4 (profiles, not providers) → provider-leak rejection proven
6. US5 (PRD import on the new hierarchy) → optional capability aligned
7. Each story adds value without breaking the 17 guarantees / 11 behaviors

### Preservation Guarantee (FR-020)

`personalAgent/tests/test_onboarding.py` is NEVER edited. It is the
regression proof surface: green at T003 (pre-change) and again at T040
(post-change). Any test change there is a contract violation.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps the task to a spec.md user story for traceability
- Every task is hermetic — no live GitHub, Telegram, model, or operator board (package rule)
- Verify each new test FAILS before implementing its behavior (TDD for the FR-021..FR-029 checks per SC-005)
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, second task databases, provider names in profiles, workflow-state cards

---

## Implementation validation record (T041/T042)

All scenarios validated hermetically via the automated checks; baseline
preserved (`tests/test_onboarding.py` untouched, green pre- and post-change).

| Quickstart scenario | Automated check(s) |
|---------------------|--------------------|
| A — onboarding guarantees preserved | `tests/test_onboarding.py` (unchanged baseline) + `test_onboarding_contract.py::test_onboarding_records_a_readable_primary_board` / `test_onboard_fails_closed_without_a_native_board` |
| B — Feature Card end-to-end | `test_feature_parent_completion.py::test_children_reference_their_parent_feature_card` … `test_validator_belongs_to_the_feature_card_not_children` (zero operator actions) |
| C — board shows work, not workflow | `test_mid_feature_board_shows_only_work_cards` + restart matrix `test_restart_resumes_*` |
| D — profiles, not providers | `test_profile_rejects_provider_and_vendor_names`, `test_profile_accepts_execution_roles_and_named_strategies`, `test_feature_card_without_profile_gets_the_path_default`, `test_operator_profile_override_is_honored_and_validated` |
| E — human gates on the board | `test_raised_gate_parks_with_a_visible_board_marker`, `test_gate_marker_failure_surfaces_and_leaves_the_park_unchanged`, `test_blocked_gate_parks_durably_with_a_marker`, `test_skip_flag_still_confirms_before_plan` |
| F — manual board edits | `test_manual_edits_are_journaled_with_board_evidence`, `test_deleted_children_are_never_restored_or_demoted`, `test_journal_failure_halts_evaluation_fail_closed` |
| G — PRD import | `test_prd_import_lands_top_level_feature_cards`, `test_prd_draft_only_import_writes_nothing_to_the_board` |

SC-005 completeness (FR-021..FR-029 → automated hermetic check):
FR-021 (board discoverable/fail-closed/dry-run plan) · FR-022 (project
membership) · FR-023 (parent links, dangling/self rejected) · FR-024
(task-generator role never a card/state) · FR-025 (single-slot claim) ·
FR-026 (feature-level validator) · FR-027 (no workflow-state cards, all
paths) · FR-028 (automated completion absent a raised gate; confirm/uat
narrowed; skip unchanged) · FR-029 (board-authoritative manual edits +
fail-closed journal). SC-003 zero-diff idempotency and the SC-004 restart
matrix (decomposition, child execution, validator, park) pass.

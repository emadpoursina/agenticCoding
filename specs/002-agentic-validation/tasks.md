---

description: "Task list for Agentic validation loop"
---

# Tasks: Agentic validation loop

**Input**: Design documents from `/specs/002-agentic-validation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Spec Independent Tests are tabletop + ripgrep (`quickstart.md`). No TDD/unit-test tasks. Polish runs those CLI/job and logic proofs.

**Organization**: Tasks are grouped by user story so each story can be implemented, tabletop-tested, and delivered as an increment. Documentation-only product surface (AiNative skills/docs); no application runtime.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Canonical edits: `AiNative/docs/…` and `AiNative/CHANGELOG.md`
- Contracts (already written; do not rewrite unless a task says to cite them): `specs/002-agentic-validation/contracts/`
- Host Cursor/OpenCode skills that symlink/mount AiNative change with the canonical files — do not maintain a second copy
- Spec directory: `FEATURE_DIR` / `.specify/feature.json` (`002-agentic-validation`), never git `BRANCH` (`agentic-validation`)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bound the documentation deliverable; no new packages, agents, or changelogs

- [X] T001 Lock the implement file list to the In Scope paths in `specs/002-agentic-validation/spec.md` plus `AiNative/docs/agents/critic/AGENTS.md` and `AiNative/docs/agents/tester/AGENTS.md` (they already restate compact reports). Do not edit leftover on-demand wording in `AiNative/docs/systems/agentic-coding.md`, `AiNative/docs/systems/agentic-system.md`, `AiNative/docs/agents/README.md`, `AiNative/docs/agents/prd-writer/SKILL.md`, or `AiNative/docs/agents/pr-reviewer/AGENTS.md`. Do not add Hermes/`agy-spawn.py` edits, a playground-root changelog, or a new converge skill.
- [X] T002 Treat `specs/002-agentic-validation/contracts/compact-reports.md`, `specs/002-agentic-validation/contracts/parent-routing.md`, and `specs/002-agentic-validation/contracts/same-pr-ship.md` as the field-name source of truth for all later AiNative edits (FR-022: smallest diff that satisfies the spec, not a smaller product that leaves pr-review on-demand).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared dispatcher constraints that MUST land before story-specific graph/routing text so parsers do not drift

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Document that downstream stages MUST use `FEATURE_DIR` / `.specify/feature.json` and MUST NOT infer the spec directory from git `BRANCH` in `AiNative/docs/systems/feature-loop.md` (FR-024; data-model: basename e.g. `002-agentic-validation`).
- [X] T004 [P] Encode parent dispatcher-only bans in `AiNative/docs/agents/speckit-orchestrate/rule.md`: parent never implements; never writes `spec.md` / `plan.md` / `tasks.md`; never ships from a worker session; validators never write `tasks.md`; auto-merge MUST NOT be introduced (FR-004, FR-015, FR-017).
- [X] T005 Document `FEATURE_DIR` / `feature.json` (never `BRANCH`) and add pr-reviewer to the Validation profile (fresh session, same as critic/tester) in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` matching the Profiles table in `specs/002-agentic-validation/contracts/parent-routing.md` (FR-017, FR-024).

**Checkpoint**: Foundation ready — user story documentation can begin

---

## Phase 3: User Story 1 - Feature path runs Validation then automatic PR review (Priority: P1) 🎯 MVP

**Goal**: After `CONVERGE_OUTCOME: converged`, the documented feature graph and parent steps are critic → tester → ship → pr-review → uat with no operator prompt except existing UAT.

**Independent Test**: Tabletop a happy path after `converged`; recite `converge(converged) → critic → tester → ship → pr-review → uat`. Feature-loop and orchestrate must not describe pr-reviewer as on-demand-only for this path (SC-001, SC-002).

### Implementation for User Story 1

- [X] T006 [P] [US1] Rewrite the live graph and PIVS mapping in `AiNative/docs/systems/feature-loop.md` to `converge(converged) → critic → tester → ship → pr-review → uat` (docs MUST show `ready → route → specify → clarify → plan → tasks → [analyze] → implement ↔ converge → critic → tester → ship → pr-review → uat`). Remove “on-demand tool after Ship, not a loop state” / on-demand-only for the feature path (FR-001, FR-003, SC-001).
- [X] T007 [P] [US1] Update the feature-path mermaid in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` so after `converged` the next nodes are critic → tester → ship → pr-review → uat (not ship immediately after `converged`) (FR-001, FR-002).
- [X] T008 [US1] Replace the “Ship / UAT after `CONVERGE_OUTCOME: converged`” numbered procedure in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` with: launch critic (Validation, fresh session); launch tester only after critic PASS; ship only after tester PASS unless `keep-local` (FR-002).
- [X] T009 [US1] After feature-path `SHIP: ok`, launch pr-reviewer automatically as a loop state in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`; pr-reviewer MUST NOT remain on-demand-only on this path (FR-003).
- [X] T010 [US1] Mirror critic → tester → ship → pr-review → uat sequencing and worker stage-dumbness (report compact verdict; do not dispatch next stage, write `tasks.md`, ship, or implement) in `AiNative/docs/agents/speckit-orchestrate/rule.md` (FR-002, FR-003, FR-017).

**Checkpoint**: User Story 1 graph and parent launch order are independently tabletop-testable

---

## Phase 4: User Story 2 - PR review verdicts route without a new fix loop (Priority: P1)

**Goal**: Parent routes APPROVE / REQUEST CHANGES / BLOCKED using Critical count; Criticals enter existing converge; same-PR ship then re-review `--extra`; zero-Critical REQUEST CHANGES is APPROVE for the loop.

**Independent Test**: Tabletop three verdicts after `SHIP: ok`. Criticals never go straight to implement. Same PR URL. Zero Criticals parks for UAT with no converge (SC-003).

### Implementation for User Story 2

- [X] T011 [US2] Add the feature-path pr-review routing table to `AiNative/docs/agents/speckit-orchestrate/SKILL.md` matching `specs/002-agentic-validation/contracts/parent-routing.md`: `APPROVE` → existing operator UAT pass/fail (does not complete the run; merge stays human); `REQUEST CHANGES` with `CRITICAL_COUNT ≥ 1` → converge (`$ARGUMENTS` = Criticals) then implement ↔ converge then critic → tester then same-PR ship then re-review; `REQUEST CHANGES` with `CRITICAL_COUNT = 0` → route as APPROVE (UAT park; no converge); `BLOCKED` (Phase 1.5) → park, not a REQUEST CHANGES retry (FR-004, FR-005, FR-006, FR-019).
- [X] T012 [US2] Document same-PR ship in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` per `specs/002-agentic-validation/contracts/same-pr-ship.md`: first ship may `gh pr create`; later passes commit, push `BRANCH` (no force-push unless existing ship policy already requires it), refresh `## Walkthrough` and `## Evidence`, keep the same `PR:` URL, MUST NOT open a second PR; workers never ship (FR-020).
- [X] T013 [P] [US2] Add the parseable compact header (`FLOW_ID`, `VERDICT: APPROVE | REQUEST CHANGES | BLOCKED`, `CRITICAL_COUNT: <integer>`, `CRITICALS`, `REPORT`, `SUMMARY`) to `AiNative/docs/agents/pr-reviewer/SKILL.md` matching `specs/002-agentic-validation/contracts/compact-reports.md`; worker MUST NOT ship, merge, write `tasks.md`, or dispatch converge/implement (FR-003, FR-015).
- [X] T014 [P] [US2] Mirror the compact header, Critical-only merge gate (Warning/Suggestion never change `VERDICT`), and re-review `--extra @<previous-review>.md` in `AiNative/docs/agents/pr-reviewer/rule.md` (FR-019, FR-020).
- [X] T015 [US2] State in `AiNative/docs/systems/pr-review-system.md` that pr-review is a loop state after Ship (not on-demand-only on feature/change after `SHIP: ok`) and that the merge gate remains Critical-only (FR-003, FR-016, FR-019). Do not sweep `AiNative/docs/agents/pr-reviewer/AGENTS.md` (out of In Scope).
- [X] T016 [US2] Document re-review in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`: parent saves the previous `REPORT` artifact and relaunches pr-reviewer with `--extra` (existing Re-review path; no new protocol) (FR-020).
- [X] T017 [US2] Add hard ban in `AiNative/docs/agents/speckit-orchestrate/rule.md`: parent MUST NOT feed validator Criticals directly to implement; Implement-target failures MUST enter converge first (FR-007).
- [X] T018 [US2] Document `SHIP: blocked` in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`: do not launch pr-reviewer; report the blocker and stop; MUST NOT infer `keep-local` from blocked ship (parent-routing hard bans).

**Checkpoint**: User Stories 1 and 2 — automatic review plus exclusive routing — are independently tabletop-testable

---

## Phase 5: User Story 3 - Critic and tester compact reports name a loop-back target (Priority: P1)

**Goal**: Critic and PIVS tester keep PASS/FAIL and add `LOOP_BACK: implement | plan | none`. Parent routes implement-target FAIL through converge; plan-target or mixed parks.

**Independent Test**: Compact contracts include `LOOP_BACK`; implement-target FAIL next worker is converge; plan-target and mixed park; validators never write `tasks.md` (SC-004, SC-005).

### Implementation for User Story 3

- [X] T019 [P] [US3] Add critic compact report `LOOP_BACK: implement | plan | none` (keep `CRITIC: PASS | FAIL` and severity-grouped `FINDINGS` with IDs `C1`, …) to `AiNative/docs/agents/critic/SKILL.md`, `AiNative/docs/agents/critic/rule.md`, and `AiNative/docs/agents/critic/AGENTS.md`. PASS ⇒ `LOOP_BACK: none`. FAIL mixed implement+plan ⇒ emit `plan`. Worker MUST NOT write `tasks.md` or launch tester/ship (FR-010, FR-015).
- [X] T020 [P] [US3] Add PIVS tester compact report `LOOP_BACK: implement | plan | none` (keep `TESTER: PASS | FAIL` and `EVIDENCE: specs/<flow>/evidence.md`, `<flow>` from `feature.json` not `BRANCH`) to `AiNative/docs/agents/tester/SKILL.md`, `AiNative/docs/agents/tester/rule.md`, and `AiNative/docs/agents/tester/AGENTS.md`. PASS ⇒ `none`. Assertion/code failures default to `implement` when the field is omitted (FR-010, FR-024).
- [X] T021 [US3] Document parent LOOP_BACK routing in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` and `AiNative/docs/agents/speckit-orchestrate/rule.md`: `implement` FAIL → converge (`$ARGUMENTS`) then implement ↔ converge then critic → tester; `plan` or mixed FAIL → park; missing `LOOP_BACK` on FAIL → tester assertion/code as `implement`, explicit spec/plan contradiction as `plan`, else park; `CONVERGE_OUTCOME: converged` while a validator FAIL is still open → park, do not re-run critic/tester/pr-review (FR-011, FR-012).
- [X] T022 [US3] List the same critic/tester compact fields including `LOOP_BACK` in `AiNative/docs/systems/feature-loop.md` so they match `specs/002-agentic-validation/contracts/compact-reports.md` (FR-010).

**Checkpoint**: User Story 3 compact reports and FAIL routing are independently inspectable

---

## Phase 6: User Story 4 - Change path retries without converge; job path skips PR review (Priority: P1)

**Goal**: Change stays tester-only (no critic, no `LOOP_BACK`, FINDINGS retries, three-attempt stuck). Job never runs pr-review or UAT.

**Independent Test**: Tabletop change REQUEST CHANGES never creates/edits `tasks.md` and never launches critic; job `SHIP: ok` never launches pr-reviewer (SC-007).

### Implementation for User Story 4

- [X] T023 [P] [US4] Update `AiNative/docs/agents/change/SKILL.md`: validation remains `STEP: tester` only (no critic, no `LOOP_BACK`); compact report stays `FLOW_ID` / `TESTER: PASS | FAIL` / `TESTS` / `FINDINGS` / `SUMMARY`; FAIL retries the change worker with FINDINGS (three attempts then park); MUST NOT write `tasks.md` or run converge (FR-008, FR-025).
- [X] T024 [US4] Document change-path parent routing in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`: change worker → tester (no critic); tester FAIL → change + FINDINGS; `SHIP: ok` → pr-review; REQUEST CHANGES with Criticals → change + FINDINGS then tester then same-PR ship then re-review; zero Criticals → UAT as APPROVE; BLOCKED → park (FR-008, FR-025).
- [X] T025 [US4] Document job path in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`, `AiNative/docs/agents/speckit-orchestrate/rule.md`, and `AiNative/docs/systems/feature-loop.md`: after named skill `STATUS: ok` → ship (or declined); MUST NOT run pr-reviewer; UAT is not a job-path stage (FR-009).

**Checkpoint**: Path isolation for change and job is independently tabletop-testable

---

## Phase 7: User Story 5 - Converge treats repeated validator findings as the same stuck point (Priority: P2)

**Goal**: `FINGERPRINT` includes sorted validator IDs; source-refs stay spec/plan/constitution; validator IDs only in task descriptions; three unchanged attempts park.

**Independent Test**: Two converge passes with the same `[tester: flow-2]` / `[critic: C1]` / `[pr-review: C1]` share a fingerprint component; third unchanged attempt parks (SC-006).

### Implementation for User Story 5

- [X] T026 [US5] Extend converge compact `FINGERPRINT` in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` to `<sorted source-refs> | <sorted validator-ids or "none">` (ids like `critic:C1`, `tester:flow-2`, `pr-review:C1`) matching `specs/002-agentic-validation/contracts/compact-reports.md` (FR-013).
- [X] T027 [US5] Document source-ref vs description split in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` and `AiNative/docs/systems/feature-loop.md`: source-refs remain spec/plan/constitution only (`FR-###`, `US1/AC2`, `plan: …`, `Constitution …`); validator IDs appear in the task description only (`[tester: flow-2]`, `[critic: C1]`, `[pr-review: C1]`); MUST NOT invent PR-review source-refs (FR-014).
- [X] T028 [US5] Document parent `$ARGUMENTS` `VALIDATOR_CRITICALS` list (`source: critic|tester|pr-review`, `id`, `summary`, `suggested_source_ref`) in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` (FR-005, FR-021).
- [X] T029 [P] [US5] If `.pi/prompts/speckit.converge.md` exists in the worktree, add at most a short paragraph: when `$ARGUMENTS` lists validator Criticals, append remaining work, map to spec/plan/constitution source-refs, put validator ids in the description, include those ids in `FINGERPRINT`. This worktree currently has no converge prompt — do not create one or a second converge skill (FR-021).
- [X] T030 [US5] Document stuck policy in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`: unchanged fingerprint across original + two resumes → park; `CONVERGE_OUTCOME: blocked` → park immediately; do not continue critic/tester/pr-review (FR-013).

**Checkpoint**: Fingerprint + source-ref convention is independently checkable with rg

---

## Phase 8: User Story 6 - Critic and PR review stay distinct gates (Priority: P2)

**Goal**: Critic implementation review remains required before tester; pr-reviewer is architecture, risk, and evidence after the PR opens.

**Independent Test**: Critic docs still require implementation review before tests; pr-reviewer docs still describe architecture, risk, and evidence after Ship (SC-008).

### Implementation for User Story 6

- [X] T031 [P] [US6] Keep (do not drop) critic implementation review after Implementation and before tester in `AiNative/docs/agents/critic/SKILL.md`, `AiNative/docs/agents/critic/rule.md`, and `AiNative/docs/agents/critic/AGENTS.md`; FAIL on spec/plan mismatch remains (FR-016).
- [X] T032 [P] [US6] State in `AiNative/docs/agents/pr-reviewer/SKILL.md` and `AiNative/docs/agents/pr-reviewer/rule.md` that the job is architecture, risk, and evidence on the opened PR — not a second spec/plan implementation critique that replaces critic (FR-016).
- [X] T033 [US6] Update `AiNative/docs/systems/validation-layer.md`: critic → tester is required on the feature path; pr-review is a loop state after Ship (remove on-demand-only); keep the critic vs pr-review split (FR-001, FR-016, FR-018).

**Checkpoint**: An operator can distinguish the two reviews in one sitting

---

## Phase 9: User Story 7 - keep-local skips ship and automatic PR review (Priority: P2)

**Goal**: `keep-local` still runs path validation, then `SHIP: declined`, no pr-review, no UAT.

**Independent Test**: Tabletop feature `keep-local` after tester PASS: no commit/push/PR, no pr-reviewer, finish includes `SHIP: declined`. Change: tester only, no critic (SC-002 keep-local branch).

### Implementation for User Story 7

- [X] T034 [US7] Document feature `keep-local` in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` and `AiNative/docs/agents/speckit-orchestrate/rule.md`: critic and tester still run; skip ship, automatic pr-review, and UAT; emit `SHIP: declined` (FR-018).
- [X] T035 [US7] Document change `keep-local` in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` and `AiNative/docs/agents/change/SKILL.md`: tester still runs; critic MUST NOT run; skip ship and pr-review; emit `SHIP: declined` (FR-018, FR-025).

**Checkpoint**: keep-local opt-out is independently tabletop-testable

---

## Phase 10: User Story 8 - Operator docs and changelog describe the new Validation graph (Priority: P2)

**Goal**: Canonical in-scope files tell one graph; methodology changelog is 0.4.0.

**Independent Test**: Listed canonical files describe graph, routing, compact fields, fingerprint, source-ref, critic vs pr-review, keep-local, change/job exceptions. `AiNative/CHANGELOG.md` has `## [0.4.0]` (SC-009).

### Implementation for User Story 8

- [X] T036 [P] [US8] Add Keep a Changelog + SemVer entry `## [0.4.0] - 2026-10-26` to `AiNative/CHANGELOG.md` for this agentic Validation graph (critic → tester → ship → pr-review → uat, LOOP_BACK, same-PR ship, change/job exceptions). No playground-root changelog (FR-023).
- [X] T037 [US8] Consistency sweep of in-scope files only (`AiNative/docs/systems/feature-loop.md`, `validation-layer.md`, `pr-review-system.md`, `AiNative/docs/agents/speckit-orchestrate/SKILL.md` and `rule.md`, critic/, tester/, pr-reviewer `SKILL.md`/`rule.md`, `change/SKILL.md`) so they share the same routing rules and have no contradictory on-demand-only leftover on the feature path (SC-009).

**Checkpoint**: Operator docs and changelog match the spec file list

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Prove the documentation deliverable with quickstart CLI/job and logic checks

- [X] T038 [P] Run `specs/002-agentic-validation/quickstart.md` ripgrep checks 2–8 from repository root (graph, LOOP_BACK, routing/same-PR, fingerprint/source-ref, path isolation, critic vs pr-review, changelog 0.4.0).
- [X] T039 [P] Walk `specs/002-agentic-validation/contracts/parent-routing.md` tabletop against SC-002–SC-007 (quickstart section 9).
- [X] T040 Confirm `git diff --name-only` stays within the In Scope list (quickstart section 1); no Hermes runtime files; `.pi/prompts/speckit.converge.md` only if a tiny `$ARGUMENTS` paragraph was required.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational
  - Sequential in priority order is recommended because many stories edit `AiNative/docs/agents/speckit-orchestrate/SKILL.md`
  - Stories that only touch distinct files (critic vs tester vs changelog) can proceed in parallel after Foundational
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — graph + parent launch order (MVP)
- **User Story 2 (P1)**: After US1 mermaid/steps exist — routing table, same-PR, pr-reviewer header
- **User Story 3 (P1)**: After Foundational — critic/tester `LOOP_BACK` can proceed in parallel with US1 file work on different files; parent LOOP_BACK routing should follow US1 launch text
- **User Story 4 (P1)**: After US1/US2 ship/pr-review text exists so change/job exceptions are deltas, not a second graph
- **User Story 5 (P2)**: After US2/US3 so fingerprints attach to the same Criticals/`LOOP_BACK` FINDINGS
- **User Story 6 (P2)**: After US1 graph + US3 critic compact fields
- **User Story 7 (P2)**: After US1/US4 path validation exists
- **User Story 8 (P2)**: After in-scope files are updated — changelog + consistency sweep

### Within Each User Story

- Cite contract field names verbatim (do not invent a fourth source-ref kind)
- Parent routing before worker compact headers when the same behavior is described in both
- Story complete (tabletop or rg) before moving to next priority when files overlap

### Parallel Opportunities

- T003 (feature-loop FEATURE_DIR) ∥ T004 (orchestrate rule bans)
- T006 (feature-loop graph) ∥ T007 (orchestrate mermaid) ∥ T010 (orchestrate rule sequence)
- T013 (pr-reviewer SKILL header) ∥ T014 (pr-reviewer rule)
- T019 (critic LOOP_BACK) ∥ T020 (tester LOOP_BACK)
- T023 (change SKILL) ∥ later T025 job docs after T024 starts
- T031 (critic implementation review) ∥ T032 (pr-reviewer architecture/risk/evidence)
- T036 (changelog) ∥ T037 only after files exist; T038 ∥ T039 in polish

**Do not parallelize** tasks that both edit `AiNative/docs/agents/speckit-orchestrate/SKILL.md` (T005, T007–T009, T011–T012, T016, T018, T021, T024–T028, T030, T034–T035).

---

## Parallel Example: User Story 1

```bash
# Different files after Foundational:
Task: "Rewrite live graph in AiNative/docs/systems/feature-loop.md"
Task: "Update mermaid in AiNative/docs/agents/speckit-orchestrate/SKILL.md"
Task: "Mirror sequence in AiNative/docs/agents/speckit-orchestrate/rule.md"
```

## Parallel Example: User Story 3

```bash
Task: "Add LOOP_BACK to AiNative/docs/agents/critic/SKILL.md, rule.md, AGENTS.md"
Task: "Add LOOP_BACK to AiNative/docs/agents/tester/SKILL.md, rule.md, AGENTS.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (graph + automatic critic → tester → ship → pr-review)
4. **STOP and VALIDATE**: Tabletop happy path (SC-001, SC-002)
5. Continue US2–US4 before calling Validation agentic (verdicts, LOOP_BACK, path isolation)

### Incremental Delivery

1. Setup + Foundational → dispatcher bans and FEATURE_DIR ready
2. US1 → automatic Validation+PR-review graph (MVP)
3. US2 → verdict routing + same-PR (review is useful)
4. US3 → LOOP_BACK (FAIL loops through converge)
5. US4 → change/job isolation
6. US5–US8 → fingerprint, review split, keep-local, changelog 0.4.0
7. Polish → `quickstart.md` rg + tabletop

### Parallel Team Strategy

With multiple writers (after Foundational):

1. Writer A: orchestrate SKILL.md sequence (US1 then US2/US4/US5/US7 — single-file owner)
2. Writer B: critic + tester compact reports (US3, US6)
3. Writer C: feature-loop.md + validation-layer.md + changelog (US1 graph copy, US8)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec user stories US1–US8
- Proof types for this feature: CLI/job (ripgrep) and logic (tabletop) — not a browser app
- ANALYZE: yes (plan.md) — compact-report names cut across eight surfaces; field-name drift is the main risk
- Avoid: feeding Criticals to implement; new fix loop; critic on change; job pr-review; auto-merge; second PR; inventing PR-review source-refs


---

## Phase 12: Convergence

- [X] T041 Fix stuck-policy closer in AiNative/docs/agents/speckit-orchestrate/SKILL.md to launch critic after converge, ship only after tester PASS, and UAT only after pr-review APPROVE or zero Criticals [critic: C1] per FR-002 (contradicts)
- [X] T042 Drop UAT from change-path excluded-stage list in AiNative/docs/systems/feature-loop.md so change is tester -> ship -> pr-review -> uat [critic: C2] per FR-004 (contradicts)
- [X] T043 Reconcile all-paths UAT prose in AiNative/docs/systems/feature-loop.md with job-path ban on pr-review and UAT [critic: C3] per FR-009 (contradicts)
- [X] T044 Add critic and pr-reviewer to parent dispatcher execution bans and worker launch skill list in AiNative/docs/agents/speckit-orchestrate/SKILL.md [critic: C4] per FR-017 (partial)
- [X] T045 Update keep-local keyword blurb in AiNative/docs/agents/speckit-orchestrate/SKILL.md to explicitly mention skipping automatic pr-review [critic: C5] per FR-018 (partial)

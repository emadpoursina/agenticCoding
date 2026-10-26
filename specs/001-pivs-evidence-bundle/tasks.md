# Tasks: PIVS evidence bundle

**Input**: Design documents from `specs/001-pivs-evidence-bundle/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md — all present from plan stage.

**Tests**: Spec and plan request **no** application TDD files. Post-implement validation is `quickstart.md` (CLI/job QF-1–QF-5) plus tabletop logic reads (TF-2–TF-5) in Polish. Do not add unit-test tasks.

**Organization**: Tasks grouped by user story (US1–US7). Documentation-only in the spec **In Scope** list (FR-011). No new dependencies (FR-012). Workers never commit, push, or open PRs (FR-013). Do not modify `AiNative/docs/agents/antigravity-harness/agy-spawn.py` (FR-015). Changelog only in `AiNative/CHANGELOG.md` (FR-014). Plan recommends **speckit.analyze** before large edits.

**Constitution**: `.specify/memory/constitution.md` is an unfilled template — spec FRs are binding.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US7) on story-phase tasks only
- Every task includes exact file path(s)

## Path conventions

- `<flow>` = Spec Kit feature directory basename from `.specify/feature.json` (example `001-pivs-evidence-bundle`), not `FLOW_ID` and not the git branch when they differ
- Manifest: `specs/<flow>/evidence.md` (feature-root sibling; no YAML front matter; no JSON)
- Captures: `specs/<flow>/evidence/`
- Implement targets live under `AiNative/` in this worktree

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Lock scope and contract baselines before editing agent docs.

- [X] T001 Confirm implementation stays on the spec **In Scope** list (`AiNative/docs/systems/feature-loop.md`, `AiNative/docs/systems/validation-layer.md`, `AiNative/docs/systems/pr-review-system.md`, `AiNative/docs/agents/tester/SKILL.md`, `AiNative/docs/agents/tester/rule.md`, `AiNative/docs/agents/tester/AGENTS.md`, `AiNative/docs/agents/_skills/test-execution/SKILL.md`, `AiNative/docs/agents/critic/` proof-type plan check, `AiNative/docs/agents/speckit-orchestrate/SKILL.md`, `AiNative/docs/agents/pr-reviewer/` prompts, `AiNative/CHANGELOG.md`); no new loop states, agents, Hermes runtime, or third-party evidence products (FR-011, FR-012); never edit `AiNative/docs/agents/antigravity-harness/agy-spawn.py` (FR-015)
- [X] T002 [P] Desk-check `specs/001-pivs-evidence-bundle/contracts/evidence-manifest.md`, `specs/001-pivs-evidence-bundle/contracts/compact-reports.md`, `specs/001-pivs-evidence-bundle/contracts/plan-test-flow-proof.md`, and `specs/001-pivs-evidence-bundle/contracts/evidence-audit.md` against FR-003 column order (`Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA`), FR-003a FAIL persistence, FR-003b full replace, FR-013a `Authorization` redaction, and compact-report `EVIDENCE` semantics

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Canonical compact-report field names in the feature-loop graph before skills and Ship docs diverge (plan W1; FR-010).

**⚠️ CRITICAL**: Complete T003 before tester/Ship compact-report wording in later phases.

- [X] T003 Update the compact-report section in `AiNative/docs/systems/feature-loop.md` so tester **adds** `EVIDENCE: specs/<flow>/evidence.md` (or the resolved manifest path) without dropping existing PASS/FAIL verdict fields, and Ship **adds** `EVIDENCE: included | none` alongside existing `SHIP`, `PR`, `WALKTHROUGH`, and `SUMMARY` per `specs/001-pivs-evidence-bundle/contracts/compact-reports.md` (FR-005, FR-008, FR-010)

**Checkpoint**: Feature-loop documents canonical `EVIDENCE` fields — user story phases can proceed.

---

## Phase 3: User Story 1 — Planner names how each criterion is proven (Priority: P1) 🎯 MVP

**Goal**: Plan-stage critic guidance requires every listed acceptance criterion to map to ≥1 test flow with exactly one proof type: UI (Playwright **trace and video and screenshot(s)**; Playwright commands only), API (HTTP request/response capture), CLI/job (terminal transcript + exit code), or logic (test name + JUnit-style report) (FR-001, FR-002, FR-012).

**Independent Test**: Tabletop — (a) Plan missing proof type on one AC → blocking finding names the orphan criterion; (b) UI label with non-Playwright commands → critic fails and Plan must use CLI/job or logic (spec US1; plan TF-3; AC-3, AC-4). Same fail on a change-path Plan for every criterion that Plan lists.

### Implementation for User Story 1

- [X] T004 [P] [US1] Document the four proof types, artifact shapes, and Plan test-flow template (Maps to / Proof type / Role / Steps / Command(s) / Expected artifacts) in `AiNative/docs/agents/critic/SKILL.md`, citing `specs/001-pivs-evidence-bundle/contracts/plan-test-flow-proof.md`; Plans MUST NOT assign UI unless validation commands are Playwright (FR-001, FR-012)
- [X] T005 [P] [US1] Add **blocking** plan-review checks in `AiNative/docs/agents/critic/rule.md`: orphan acceptance criterion (zero linked flows), missing proof type, or UI proof whose commands are not Playwright; finding MUST name the orphan criterion id or quote; applies to change-path Plans for every listed criterion (FR-002)
- [X] T006 [P] [US1] Mirror the same blocking plan-review checks and proof-type enum in `AiNative/docs/agents/critic/AGENTS.md` (FR-001, FR-002)

**Checkpoint**: Critic docs fail plans that lack provable flows or misuse UI without Playwright.

---

## Phase 4: User Story 2 — Tester persists evidence on disk (Priority: P1)

**Goal**: Tester and test-execution skills require command-produced captures under `specs/<flow>/evidence/` and a single Markdown table at `specs/<flow>/evidence.md`; compact report adds `EVIDENCE: <path>` (FR-003–FR-005, FR-003a–b, FR-004, FR-013a).

**Independent Test**: Read updated tester + test-execution skills — table columns match FR-003; FAIL still writes rows for every executed flow including non-zero exit codes (FR-003a); each run **replaces** the prior `evidence.md` and reconciles artifacts (FR-003b); `Commit SHA` is full 40-char worktree `HEAD` at tester completion; API dumps redact credentials and `Authorization`; compact report keeps PASS/FAIL and adds `EVIDENCE:` (AC-1, AC-2, AC-10; plan TF-2).

### Implementation for User Story 2

- [X] T007 [P] [US2] Wire the evidence bundle into `AiNative/docs/agents/tester/SKILL.md` per `specs/001-pivs-evidence-bundle/contracts/evidence-manifest.md` and `specs/001-pivs-evidence-bundle/data-model.md`: captures under `specs/<flow>/evidence/`; manifest `specs/<flow>/evidence.md` as **one** Markdown table with columns `Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA` (no YAML front matter, no JSON); paths MUST reference files the command created, not chat prose (FR-004); on FAIL still write rows for every executed flow (FR-003a); each validation run **replaces** the prior bundle including Implement loop-back full regeneration (FR-003b); SHA = 40-char `HEAD` immediately before the compact report; API captures MUST redact credentials and `Authorization` tokens; warn that UI traces and screenshots can contain secrets; evidence MUST remain uncommitted (FR-013a); emit `EVIDENCE: specs/<flow>/evidence.md` without removing PASS/FAIL (FR-005); keep failed-flow-first **execution** if useful but written bundle must represent the full run (research R-003)
- [X] T008 [P] [US2] Mirror the same manifest, artifact-directory, full-replace, FAIL-persistence, SHA, secrets-redaction, and `EVIDENCE:` compact-report requirements in `AiNative/docs/agents/_skills/test-execution/SKILL.md` (FR-003–FR-005, FR-003a–b, FR-004, FR-013a)
- [X] T009 [US2] Update `AiNative/docs/agents/tester/rule.md` and `AiNative/docs/agents/tester/AGENTS.md` for on-disk artifacts only (no chat-prose evidence), worktree `HEAD` SHA per row, FAIL still records executed flows, and tester compact report `EVIDENCE: specs/<flow>/evidence.md` without dropping existing verdict fields (FR-004, FR-005, FR-003a)

**Checkpoint**: Validation workers have a complete evidence persistence contract independent of Ship/pr-reviewer.

---

## Phase 5: User Story 3 — CI independently re-proves validation (Priority: P1)

**Goal**: Enrolled-project guidance requires PR CI to re-run Plan `validation_commands` (or documented equivalent), enable Playwright trace/video/screenshot for UI flows, and upload bulky captures as workflow artifacts — never git history (FR-006, FR-006a).

**Independent Test**: `rg` quickstart §7 in `AiNative/docs/systems/validation-layer.md` (and feature-loop if cross-linked): vendor-neutral re-run requirement; one GitHub Actions example snippet only; recommended ignore of `specs/*/evidence/` **and** `specs/*/evidence.md`; no committed enrolled-repo workflow files (AC-5; SC-006).

### Implementation for User Story 3

- [X] T010 [US3] Document in `AiNative/docs/systems/validation-layer.md` a **vendor-neutral** requirement that PR CI re-executes `validation_commands` (or documented equivalent), enables Playwright capture (trace, video, and screenshots) where UI proof types apply, and publishes bulky files as workflow artifacts; include **one GitHub Actions example snippet only**; do not add workflow files to enrolled repos and do not require GitHub Actions as the only allowed CI (FR-006, research R-010)
- [X] T011 [US3] Add recommended gitignore patterns `specs/*/evidence/` **and** `specs/*/evidence.md` in `AiNative/docs/systems/validation-layer.md`; state bulky traces/videos belong in CI artifacts or local `evidence/` directories, never git history; CI artifact URLs or named artifacts satisfy PR `## Evidence` links for bulky files (FR-006a, research R-004)
- [X] T012 [P] [US3] Add a short cross-link from `AiNative/docs/systems/feature-loop.md` to the validation-layer CI re-proof / gitignore guidance without changing the T003 compact-report field names (FR-006)

**Checkpoint**: Operators see independent re-proof and git hygiene without this worktree committing workflows.

---

## Phase 6: User Story 4 — Ship surfaces evidence beside walkthrough (Priority: P2)

**Goal**: Parent Ship keeps mandatory `## Walkthrough` and adds mandatory `## Evidence` sourced from the tester manifest; Ship compact report adds `EVIDENCE: included|none` (FR-007, FR-008, FR-013).

**Independent Test**: Read Ship / UAT in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` — both headings required; walkthrough purpose unchanged; compact `EVIDENCE: included | none`; PR open does **not** wait for CI; missing usable manifest → `EVIDENCE: none` with walkthrough still present (AC-6; plan TF-4; SC-005).

### Implementation for User Story 4

- [X] T013 [US4] Require PR body `## Evidence` alongside mandatory `## Walkthrough` in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`: copy the acceptance-criterion table from `specs/<flow>/evidence.md`; inline small PNG/JPEG screenshots when they exist locally; reference bulky captures by documented workflow artifact name (or URL if already known); do not wait for CI; if no usable manifest, still include `## Walkthrough` (FR-007, FR-013; contracts/compact-reports.md **PR body**)
- [X] T014 [US4] Extend the Ship compact report template in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` with `EVIDENCE: included | none` (`included` even if tester verdict was FAIL when a usable manifest exists; `none` when missing/empty/invalid) while preserving `SHIP`, `PR`, `WALKTHROUGH`, and `SUMMARY` (FR-008)

**Checkpoint**: Parent Ship docs describe evidence on the PR without demoting UAT walkthrough.

---

## Phase 7: User Story 5 — pr-reviewer audits evidence across fix pushes (Priority: P2)

**Goal**: On-demand pr-reviewer gains an evidence audit: completeness, manifest SHA vs current PR head (stale), CI job success on this head (bytes need not match), blocking “claimed but unproven”; re-runnable after every fix push (FR-009).

**Independent Test**: Tabletop — manifest SHA `S_old` vs PR head `S_new` → stale blocking; tester PASS with CI failed/skipped/unfinished or missing artifact → claimed but unproven; second pass after a fix push re-applies the same rules (AC-8; plan TF-5; SC-002).

### Implementation for User Story 5

- [X] T015 [P] [US5] Add an evidence-audit step to the staged review in `AiNative/docs/agents/pr-reviewer/prompts.md` covering completeness (every AC has a row and required artifact shape), SHA freshness vs PR head, and CI agreement as job success on this head for the re-run of `validation_commands` (or documented equivalent) — not byte-identical artifacts — per `specs/001-pivs-evidence-bundle/contracts/evidence-audit.md` (FR-009)
- [X] T016 [P] [US5] Document blocking findings **stale** (manifest SHA ≠ PR head until tester re-runs) and **claimed but unproven** (tester PASS with missing manifest/artifact, stale SHA, or CI failed/skipped/unfinished) in `AiNative/docs/agents/pr-reviewer/SKILL.md`, `AiNative/docs/agents/pr-reviewer/rules.md`, `AiNative/docs/agents/pr-reviewer/rule.md`, and `AiNative/docs/agents/pr-reviewer/AGENTS.md`; audit is not a loop gate; prior-pass PASS does not waive a newly stale bundle (FR-009)
- [X] T017 [P] [US5] Summarize the same evidence-audit expectations for operators in `AiNative/docs/systems/pr-review-system.md` (FR-009, SC-002)

**Checkpoint**: On-demand pr-reviewer can flag stale or unproven evidence after fix pushes.

---

## Phase 8: User Story 7 — Compact-report contracts stay aligned (Priority: P2)

**Goal**: `feature-loop.md` tester and Ship compact-report definitions match the updated agent skills: tester `EVIDENCE: <path>`; Ship `EVIDENCE: included|none`; existing PASS/FAIL and walkthrough fields stay (FR-010).

**Independent Test**: Grep `EVIDENCE:` in `AiNative/docs/systems/feature-loop.md`, `AiNative/docs/agents/tester/`, `AiNative/docs/agents/_skills/test-execution/`, and `AiNative/docs/agents/speckit-orchestrate/SKILL.md`; field names and allowed values match (spec US7; SC-004; quickstart §2).

### Implementation for User Story 7

- [X] T018 [US7] Reconcile compact-report `EVIDENCE` field names and allowed values across `AiNative/docs/systems/feature-loop.md`, `AiNative/docs/agents/tester/SKILL.md`, `AiNative/docs/agents/tester/rule.md`, `AiNative/docs/agents/tester/AGENTS.md`, `AiNative/docs/agents/_skills/test-execution/SKILL.md`, and `AiNative/docs/agents/speckit-orchestrate/SKILL.md` so they match `specs/001-pivs-evidence-bundle/contracts/compact-reports.md` (tester path form; Ship `included|none`; no dropped PASS/FAIL/`WALKTHROUGH` fields) (FR-010)

**Checkpoint**: Parent parsers will see the same `EVIDENCE` contract in the graph and the skills.

---

## Phase 9: User Story 6 — Optional fail-before / pass-after discipline (Priority: P3)

**Goal**: Document an optional check: new tests should fail on the merge-base commit before implementation and pass after, when practical — not a gate for every project or flow (FR-016).

**Independent Test**: Paragraph present in validation-layer and/or tester docs; wording is optional, not required for every flow (spec US6; AC-11; quickstart §9).

### Implementation for User Story 6

- [X] T019 [US6] Add optional fail-before / pass-after guidance (run the new test against merge-base, observe failure, then confirm pass on the feature branch) to `AiNative/docs/systems/validation-layer.md` and a short pointer in `AiNative/docs/agents/tester/SKILL.md` and `AiNative/docs/agents/_skills/test-execution/SKILL.md` per `specs/001-pivs-evidence-bundle/contracts/plan-test-flow-proof.md`; do not make it mandatory (FR-016)

**Checkpoint**: Optional discipline documented without blocking adoption.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Changelog, secrets grep coverage, quickstart gate, scope guards.

- [X] T020 [P] Add a Keep a Changelog + SemVer entry (recommend **0.3.0**) describing the evidence-bundle methodology in `AiNative/CHANGELOG.md`; do not add a playground-root changelog (FR-014, research R-012, AC-9)
- [X] T021 Confirm secrets wording (API redaction of credentials and `Authorization`; UI traces/screenshots warning; evidence uncommitted) is present in `AiNative/docs/agents/tester/SKILL.md`, `AiNative/docs/agents/_skills/test-execution/SKILL.md`, and `AiNative/docs/systems/validation-layer.md` (FR-013a; quickstart §8)
- [X] T022 Run all checks in `specs/001-pivs-evidence-bundle/quickstart.md` §§1–10 and complete the tabletop end-to-end story (AC-12, SC-001–SC-006)
- [X] T023 Confirm `AiNative/docs/agents/antigravity-harness/agy-spawn.py` has no diff and `git diff --name-only` against base shows only in-scope `AiNative/` paths plus `specs/001-pivs-evidence-bundle/` (FR-011, FR-015; plan TF-6)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks** compact-report wording in US2, US4, US7
- **US1 (Phase 3)**: After Phase 2; independent files from US2–US7
- **US2 (Phase 4)**: After T003
- **US3 (Phase 5)**: After Setup; T012 after T003 (same `feature-loop.md`); T010 then T011 (same `validation-layer.md`)
- **US4 (Phase 6)**: After T003; logically after US2 manifest contract (T007–T009)
- **US5 (Phase 7)**: After US2 and US4 docs describe manifest and PR `## Evidence`
- **US7 (Phase 8)**: After US2 and US4 (and T003) so grep has both skill and graph text
- **US6 (Phase 9)**: After T010–T011 (same `validation-layer.md`); after T007–T008 if adding tester pointers
- **Polish (Phase 10)**: After all story phases

### User story dependencies

| Story | Priority | Depends on |
|-------|----------|------------|
| US1 | P1 | Phase 2 recommended; no other stories |
| US2 | P1 | T003 (feature-loop `EVIDENCE` baseline) |
| US3 | P1 | Setup; T012 after T003 |
| US4 | P2 | T003; US2 manifest contract (content reference) |
| US5 | P2 | US2 + US4 documented |
| US7 | P2 | T003 + US2 + US4 |
| US6 | P3 | US3 tasks in `validation-layer.md` (serialize T019 after T010–T011) |

### Parallel opportunities

- T001 ∥ T002
- T004 ∥ T005 ∥ T006 (distinct critic files)
- T007 ∥ T008 (tester SKILL vs test-execution SKILL)
- T010 then T011 (same file — **do not** parallelize)
- T013 then T014 (same `speckit-orchestrate/SKILL.md` — **do not** parallelize)
- T015 ∥ T016 ∥ T017 (prompts vs pr-reviewer agent files vs system overview) — only one editor on each file
- After T003: US1 critic edits ∥ US2 tester SKILL ∥ US3 validation-layer (different owners/files)

### Parallel example: User Story 1

```bash
# After Phase 2:
# T004 — AiNative/docs/agents/critic/SKILL.md
# T005 — AiNative/docs/agents/critic/rule.md
# T006 — AiNative/docs/agents/critic/AGENTS.md
```

### Parallel example: User Story 2

```bash
# After T003:
# T007 — AiNative/docs/agents/tester/SKILL.md
# T008 — AiNative/docs/agents/_skills/test-execution/SKILL.md
# Then sequential: T009 — tester/rule.md + tester/AGENTS.md
```

### Parallel example: User Story 5

```bash
# After US2 + US4:
# T015 — AiNative/docs/agents/pr-reviewer/prompts.md
# T016 — pr-reviewer SKILL.md / rules.md / rule.md / AGENTS.md (single owner)
# T017 — AiNative/docs/systems/pr-review-system.md
```

---

## Implementation strategy

### MVP first (User Story 1 + core US2)

1. Complete Phase 1–2 (scope + feature-loop `EVIDENCE` baseline)
2. Complete Phase 3 (US1) — plan/critic proof-type gate
3. Complete Phase 4 (US2) — tester persistence contract
4. **Stop and validate** with tabletop TF-3 and read-through TF-2 before Ship/pr-reviewer phases

### Incremental delivery

1. Foundation (Phases 1–2) → compact-report anchor
2. US1 + US2 → validation can persist evidence (P1 value)
3. US3 → CI/gitignore guidance
4. US4 + US5 + US7 → PR, review audit, grep parity
5. US6 + Polish → optional discipline, changelog, quickstart gate

### Suggested commit split (implement worker; parent Ship may squash)

Align with plan.md **Commit plan** (implement worker does not commit unless the operator later asks the parent):

| Commit | Tasks | Contents |
|--------|-------|----------|
| 1 `docs(loop): evidence compact-report fields` | T003, T012 | W1 |
| 2 `docs(tester): evidence bundle and secrets` | T007–T009 | W2 |
| 3 `docs(critic): proof-type plan gate` | T004–T006 | W3 |
| 4 `docs(validation): CI re-proof and gitignore` | T010–T011, T019 | W4 + US6 |
| 5 `docs(orchestrate): ship evidence section` | T013–T014 | W5 |
| 6 `docs(pr-reviewer): evidence audit` | T015–T017 | W6 |
| 7 `docs(ainative): changelog for evidence bundle` | T018, T020–T023 | W7 + parity/polish |

### Analyze gate (recommended)

Before starting T003–T019, run **speckit.analyze** on compact-report and evidence contracts across `feature-loop.md`, tester, test-execution, speckit-orchestrate, critic, and pr-reviewer (plan.md `ANALYZE: yes`).

---

## Notes

- Manifest table columns (fixed order): Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA
- Re-validation after Implement loop-back: **replace** entire `evidence.md` and refresh artifacts (FR-003b)
- Tester FAIL: still write rows for executed flows (FR-003a)
- Gitignore both `specs/*/evidence/` and `specs/*/evidence.md`
- Cursor skill promotion / `~/.cursor/skills` mirrors are out of scope (research R-006)
- [P] = different files; avoid concurrent edits to the same markdown file
- Do not add `agentic-coding.md` or other files outside the spec **In Scope** list

---

## Task summary

| Phase | Task IDs | Count |
|-------|----------|-------|
| Setup | T001–T002 | 2 |
| Foundational | T003 | 1 |
| US1 | T004–T006 | 3 |
| US2 | T007–T009 | 3 |
| US3 | T010–T012 | 3 |
| US4 | T013–T014 | 2 |
| US5 | T015–T017 | 3 |
| US7 | T018 | 1 |
| US6 | T019 | 1 |
| Polish | T020–T023 | 4 |
| **Total** | **T001–T023** | **23** |

**MVP scope**: Phases 1–4 (T001–T009) — proof types at plan time plus tester evidence persistence and feature-loop compact-report baseline.

**Format validation**: All tasks use `- [ ]`, sequential IDs `T001`–`T023`, story labels on US phases only, and explicit file paths.

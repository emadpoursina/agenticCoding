---

description: "Task list for the Adjust stage (PIVS → PIVSA)"
---

# Tasks: Adjust stage (PIVS → PIVSA)

**Input**: Design documents from `/specs/004-adjust-stage/` — [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Prerequisites**: plan.md, spec.md (both present), research.md, data-model.md, contracts/ (all present)

**Deliverable root**: every implementation path below is relative to the repo root and lives under `AiNative/`. This feature ships **documents only** — no scripts, no parsers, no `.ainative/` file is pre-created, no symlink is installed, `personalAgent/`, `.specify/`, and `.pi/` are untouched.

**Tests**: No unit/integration tests are requested — the deliverable is prose. The executable checks are the doc-review suite **TF-1 … TF-12** plus tabletop scenarios **A–E** in [quickstart.md](./quickstart.md); they are run as tasks in Phase 9, and their commands and outputs must be pasted into the PR-body evidence sheet (plan W10).

**Organization**: tasks are grouped by user story so each story can be reviewed (its independent test) without the next one landing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: the user story from spec.md (US1 … US6); setup, foundational, and polish tasks carry no story label
- Every task names the file it edits and the section/heading it edits, so no design is re-derived at implementation time

## Path Conventions

- Methodology docs: `AiNative/docs/systems/*.md`, `AiNative/docs/knowledge/setup/*.md`
- Agent docs: `AiNative/docs/agents/<name>/{SKILL.md,AGENTS.md,rule.md}`, harness prompt contracts at `AiNative/docs/agents/<name>/worker-contract.md`
- Registry/changelog: `AiNative/docs/agents/README.md`, `AiNative/CHANGELOG.md`
- The new stage lives in `AiNative/docs/agents/adjust/`
- Line numbers below are hints taken from the current tree; match on the quoted heading or text, because earlier tasks shift lines in the same file

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: create the `adjust` agent folder at the documented file-contract shape and register it, so every later story writes into an existing, discoverable skill.

- [X] T001 Create `AiNative/docs/agents/adjust/` with the three files, copied in **shape** from `AiNative/docs/agents/template/` and `AiNative/docs/agents/critic/`: `SKILL.md` frontmatter `name: adjust` (must equal the folder name), a third-person WHAT+WHEN `description` naming the trigger ("after a feature or change card reaches a terminal state — merged or closed without a merge" — and the weekly roll-up card) plus `disable-model-invocation: true`, and body headings `## Inputs`, `## Procedure`, `## Output`, `## Compact report`; `AGENTS.md` headings `Purpose`, `## When to use`, `## Inputs`, `## Outputs`, `## Supporting files`; `rule.md` headings `## Must`, `## Must not`, `## Stop conditions`. Leave the section bodies empty for the story tasks; create no other file in the folder
- [X] T002 [P] Register the stage in `AiNative/docs/agents/README.md` § Agents: add the row `| [adjust](./adjust/) | Feature-loop Adjust (after UAT + merge, and on non-merging terminal states) | Turns a finished card's numbers, reports, and `FRICTION` lines into learnings entries and evidence-backed proposals; proposes only |` immediately after the `tester` row, and add one clause to § Add a new agent step 7 noting that the loop's numbered states are `ready … uat` plus `adjust` (state #5), so a new agent that is a loop stage is wired as a state rather than a job skill

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the two facts every later story depends on — the loop is PIVSA everywhere, and the `FRICTION` grammar is stated exactly once.

**⚠️ CRITICAL**: no user-story work should land before this phase, or two documents will define the loop's phase count and the friction line differently.

- [X] T003 Rename and rewrite the mapping in `AiNative/docs/systems/feature-loop.md` (heading at ~line 254 `## PIVS mapping`; the file's opening paragraph at ~line 4 also says "PIVS agent definitions are stages on"; and line ~256 reads "The loop above is the detailed form of PIVS:" — those three lines are the entire `PIVS\b` residue in the file, proved with `rg -n 'PIVS\b' AiNative/docs/systems/feature-loop.md`): heading becomes exactly `## PIVSA mapping` — **no** `(PIVS)` suffix and **no** `<a id="pivs-mapping">` shim, because a retained `PIVS` literal is itself a TF-1 match while a shim anchor would need TF-1 to tolerate it; the heading's GitHub slug therefore moves to `#pivsa-mapping`, and T004 retargets every inbound link (8 files, 11 links — proved with `rg -n '#pivs-mapping' AiNative/`). The bullet list becomes five phases — **Plan** = `ready → route → specify → clarify → plan → tasks → [analyze]`, **Implementation** = `implement ↔ converge`, **Validation** = `critic → tester`, **Ship** = `ship → pr-review → uat` → merge, **Adjust** = `adjust`, stated as running **after** the merge and on cards that never merge, and as never gating the merge or the card. Rewrite the opening paragraph to "PIVSA agent definitions" and line ~256 to "The loop above is the detailed form of PIVSA:"; leave no sentence in the file claiming the loop has four phases (FR-038, FR-039)
- [X] T004 [P] Propagate PIVSA to the linked documents, one line each, changing the phase name only (never the surrounding body): `AiNative/docs/systems/agentic-system.md:239` ("PIVS in its detailed form is …" → PIVSA); `AiNative/docs/systems/validation-layer.md:3` ("Technical guide for the PIVS **Validation** phase" → PIVSA) and `:127`, where the live graph string must gain `→ adjust` (`critic → tester → ship → pr-review → uat → adjust`); `AiNative/docs/systems/jev/README.md:3`; `AiNative/docs/systems/README.md:20` (feature-loop row text mentions Adjust — the only change in that file, which contains no PIVS text); `AiNative/docs/agents/README.md:105` ("Methodology: PIVS …" → "Methodology: PIVSA …"); and the `description:` frontmatter of `AiNative/.cursor/commands/critic.md` and `AiNative/.cursor/commands/tester.md` ("during PIVS Validation" → "during PIVSA Validation"). Frontmatter/description only — the `.cursor` command bodies are thin wrappers and must not be forked. Then **retarget the anchor**: replace `#pivs-mapping` with `#pivsa-mapping` in all 11 inbound links, which live in exactly 8 files — `docs/systems/agentic-system.md:239`, `docs/systems/validation-layer.md:3`, `docs/systems/agentic-coding.md:3,6,87`, `docs/agents/README.md:105`, `docs/agents/critic/AGENTS.md:5`, `docs/agents/tester/AGENTS.md:5`, `docs/agents/pr-reviewer/AGENTS.md:9`, `docs/agents/prd-writer/SKILL.md:467,473` (link target only in `agentic-coding.md` — its historical PIVS prose and the `PIVS` link text stay). Done when `rg -n '#pivs-mapping' AiNative/` returns nothing, `rg -n '#pivsa-mapping' AiNative/` returns those 11, and `rg -l 'PIVS\b' AiNative/docs AiNative/CHANGELOG.md` returns only `docs/systems/agentic-coding.md` and `CHANGELOG.md` (FR-038, SC-010)
- [X] T005 State the friction grammar **once** in `AiNative/docs/systems/feature-loop.md` § Compact reports (~line 274), as a short subsection before the per-worker field lists: `FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>`, where `<target-class>` is one of exactly four values — `project-rules` (project `AGENTS.md`), `project-config` (`.ainative/project.yaml`), `ainative` (an AiNative skill or system doc), `harness` (a harness adapter); the clean-run form is exactly `FRICTION: none` (no pipes, no trailing text) and omitting the line is a report defect; a missing line on an older or partial artifact means **unknown**, never "no friction"; the observation is one sentence with no `|`; the evidence reference is something the parent can open (card id, artifact path, report id, metric). State that the line never changes a verdict, loop-back, gate, or merge; that the `ready` report contract **subsumes** `docs/agents/speckit-ready/SKILL.md` (its step 3 returns the script stdout as the ready report) and that contract item 12 — the job-skills line — covers job skills that document their own report (`server-setup`, `prd-writer`, `project-bootstrapper`, `proposal-writer`, `learn`), so no worker document is left without a home in the list. State that the `ship` line is emitted by the **parent** (ship is a parent step), and do not restate this grammar anywhere else in the tree (FR-011, FR-040)

**Checkpoint**: the loop reads PIVSA in every document it is named in, and the friction line has exactly one definition to point at.

---

## Phase 3: User Story 1 — Every finished card produces evidence-backed proposals (Priority: P1) 🎯 MVP

**Goal**: `adjust` is the loop's fifth state on the feature and change paths, it runs as its own fresh worker on the card's terminal state (merged, or closed without a merge), and it emits proposals — evidence + exactly one target — that the parent turns into Change cards, without ever editing anything or holding the merge.

**Independent Test**: read `AiNative/docs/agents/adjust/` and `AiNative/docs/systems/feature-loop.md` alone and answer: where Adjust runs on each path, what it may read, what it may write, whether it can block merge, how a proposal is filed. Then tabletop a merged card whose tester FAILed twice with a `FRICTION` line and confirm the documented outcome is one proposal with an evidence reference, one named target, and a Change card filed by the parent (quickstart TF-2, TF-5; scenarios A, C, E).

### Implementation for User Story 1

- [X] T006 [P] [US1] Fill `AiNative/docs/agents/adjust/AGENTS.md`: purpose paragraph (one stage, one job: turn a finished card's evidence into learnings and proposals, never edits rules); `## When to use` = the card reached a terminal state (merged after a UAT pass on feature/change, or blocked, parked, killed, abandoned) or the card is the weekly roll-up (`STEP: rollup`), and explicitly **not** on the `job` path per card; `## Inputs` in priority order (1 card numbers incl. the `## Metrics` block, 2 compact reports and their `FRICTION` lines, 3 a session bundle through the harness adapter, for anomalies only); `## Outputs` (two writes — `.ainative/learnings.md` and `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md`; the **parent** files the Change cards); `## Supporting files` table pointing at `SKILL.md` and `rule.md` (FR-002, FR-009, FR-010, FR-015)
- [X] T007 [US1] Write `AiNative/docs/agents/adjust/SKILL.md` § Inputs and § Procedure steps 1–3: the three input classes in the stated priority order with the sentence "Adjust runs from (1) and (2) alone. Transcript access is an optional drill-down, never a prerequisite."; step 1 confirm the trigger (terminal state or rollup; a still-active card ⇒ `STATUS: blocked`, do not invent a run); step 2 read the `## Metrics` block and dispatch history and note which fields are `unknown`/`n/a`; step 3 read every report named on the card, extracting verdicts, findings, and `FRICTION` lines, and record the count of reports seen vs reports carrying a line (FR-009, FR-010, FR-011)
- [X] T008 [US1] Write `AiNative/docs/agents/adjust/SKILL.md` § Procedure steps 4–8 and § Output: build one-line candidate observations keyed `<target-class>/<normalized-target-ref>/<slug>`; read `.ainative/learnings.md` (create on first write) and count **distinct cards** per key; decide per finding by consulting `rule.md`; write learnings first, then the artifact, nothing else; report. § Output states the two writes and their paths, the artifact header fields (`flow`, `path`, `terminal` + `closed_at`, `evidence`, `reports seen (with FRICTION: m)`, `learnings appended`), the per-proposal block (finding key, exactly one target class from the closed four, target file, merge target, existing rule quote, intended edit, ≥1 evidence item, cards, `status: pending-change-card`), the verbatim prohibitions (must not edit project rules/config/AiNative skills or system docs/harness adapters; must not write to the board; must not apply, stage, commit, or ship its own proposals; must not gate, delay, or hold the card or its merge), the rule that a target inside the read-only AiNative tree is filed as a card against the AiNative repo (never an in-place edit), and `ADJUST: no-findings` as the explicit empty outcome with the evidence actually checked listed (FR-012, FR-013, FR-014, FR-015, FR-017, FR-018)
- [X] T009 [US1] Add the stage to `AiNative/docs/systems/feature-loop.md` § Canonical state graph (~line 205): append `→ adjust` to the graph block (after `→ uat`) and to the one-line graph string (`… → pr-review → uat → adjust`); add the state-table row `| adjust | AiNative docs/agents/adjust/ | yes | …|` recording — one step, fresh worker session under the Validation profile on the same executor rule as every other state (link `validation-layer.md#model-selection`), runs after `uat`/merge **and** on blocked/parked/killed/abandoned cards, output is proposals only, **never gates or delays merge or card completion**, three attempts then park with the park recorded as a follow-up item on a completed card; extend § End-of-path rule with the sentence that Adjust's trigger is the card reaching a terminal state — merged, or closed without a merge — so no new card state is required (FR-004, FR-005, FR-006, FR-007, FR-008, FR-037)
- [X] T010 [US1] Update the card-path table in `AiNative/docs/systems/feature-loop.md` § Card paths (~line 117): the `feature` row's graph ends `… → ship → pr-review → uat → adjust`; the `change` row's graph ends `… → ship → pr-review → uat → adjust`; the `job` row (or the paragraph after the table) states in one sentence that the job path has **no per-card Adjust** — one worker, a ship, and a human merge give no spec/plan/critic/tester evidence — while job cards still emit `FRICTION` and still carry a `## Metrics` block so the weekly roll-up sees them. Do not add a card state or a card field for Adjust (FR-004, FR-005, FR-037)

**Checkpoint**: an operator can read the loop doc plus the skill folder and answer all five questions; nothing in either place makes Adjust a gate.

---

## Phase 4: User Story 2 — Every worker reports friction in its compact report (Priority: P1)

**Goal**: the `FRICTION:` line is in every documented report contract and in every worker's own report section — as a one-line pointer to the single grammar, never a restatement.

**Independent Test**: `rg -n 'FRICTION' AiNative/docs/systems/feature-loop.md` shows one definition paragraph plus one mention inside each documented report contract, and `rg -c 'FRICTION' AiNative/docs/agents/*/{SKILL,AGENTS}.md AiNative/docs/agents/*/worker-contract.md` shows a hit for every worker that describes a report (quickstart TF-3).

### Implementation for User Story 2

- [X] T011 [P] [US2] Append the `FRICTION:` line to each documented report contract in `AiNative/docs/systems/feature-loop.md` § Compact reports (~line 274) — exactly **twelve** contracts, counting the job-skills line as the twelfth: (1) ready, (2) route, (3) specify/clarify/plan/tasks/analyze, (4) implement, (5) converge, (6) critic, (7) tester (feature), (8) tester (change path), (9) pr-reviewer, (10) ship, (11) adjust, (12) job skills — one short clause each (`and a FRICTION line — grammar above`), no field-by-field restatement. Eleven are worker-emitted; **`ship`'s line is emitted by the parent** (ship is a parent step), which the block must say; **ready's line is emitted by the ready worker, appended as the last line after the unwrapped `ready-check.sh` stdout** (that stdout *is* the report, and no script changes), which that block must say too. Done when the file holds **13** `FRICTION` occurrences: the single grammar statement from T005 plus the twelve blocks. Where the contract lists its fields inline (critic, tester, pr-reviewer, ship), add `FRICTION` to that field list so the report reads complete (FR-040)
- [X] T012 [P] [US2] Add the pointer line to the setup workers: `AiNative/docs/agents/ready/AGENTS.md` § Output (~line 26) and `AiNative/docs/agents/route-work/AGENTS.md` § Outputs (~line 22) — one sentence, "every report ends with a `FRICTION:` line; grammar in `docs/systems/feature-loop.md` § Compact reports — emit exactly `FRICTION: none` when nothing slowed the step down" (FR-041). In the same `ready/AGENTS.md` § Output paragraph, name the **emitter** so nothing is implicit: ready's report is the unwrapped `ready-check.sh` stdout (`speckit-ready/SKILL.md` step 3 — "Do not wrap it"), so the ready worker appends the `FRICTION:` line after that stdout as its last line — harness-neutral, with **no** `AiNative/scripts/**` or `ready-check.sh` change (FR-040, FR-041)
- [X] T013 [P] [US2] Add the pointer line to the validation-stage folders: `AiNative/docs/agents/critic/AGENTS.md` § Outputs, `critic/SKILL.md` § Compact report (~line 120 — also rename that heading "Compact report (PIVS, feature path)" → "(PIVSA, feature path)"), `critic/rule.md` § Must; `AiNative/docs/agents/tester/AGENTS.md` § Outputs, `tester/SKILL.md` § Compact report (~line 67), `tester/rule.md` § Must. Same task, same files — complete the PIVSA rename in these four documents, which TF-1 otherwise fails: `critic/AGENTS.md:3` ("Adversarial reviewer for the PIVS Validation phase" → PIVSA) and `:5` ("Methodology: PIVS Validation phase" → PIVSA); `tester/AGENTS.md:3` ("Runs the test flows defined in the PIVS Plan phase" → PIVSA) and `:5` (same methodology line); and the `description:` frontmatter at `critic/SKILL.md:3` ("during PIVS Validation") and `tester/SKILL.md:3` ("Use during PIVS Validation"). These six lines plus the heading are the whole `PIVS\b` residue in `docs/agents/**` (FR-041, FR-039, SC-010). One more pointer line, same task: `AiNative/docs/agents/_skills/test-execution/SKILL.md` (~line 72 — the compact-report shape the tester inlines, "Compact report keeps PASS/FAIL and adds `EVIDENCE: …`"), so the fragment the tester carries into its own report section cannot drop the line; it is covered by the tester doc that inlines it, sits outside TF-3's `docs/agents/*/SKILL.md` glob, and T030 checks it by path
- [X] T014 [P] [US2] Add the pointer line to `AiNative/docs/agents/pr-reviewer/SKILL.md` § Output format (~line 144) and to both report blocks in `AiNative/docs/agents/change/SKILL.md` (the `STEP: change` report — heading ~line 46, its `Report:` block ~line 57 — and the `STEP: tester` report — heading ~line 68, its `Report:` block ~line 79; the change path has no `STEP: implement`) (FR-041)
- [X] T015 [P] [US2] Add the pointer line to the job workers: `AiNative/docs/agents/learn/SKILL.md` § Report (~line 137), `AiNative/docs/agents/prd-writer/SKILL.md` § the shipping/report step (~lines 450–474), `AiNative/docs/agents/project-bootstrapper/SKILL.md` § Report (~line 71), `AiNative/docs/agents/proposal-writer/SKILL.md` § Output and report (~line 182), **and the two job skills that document their own report and were missing from the sweep** (FR-041 cannot be verified at 100% without them): `AiNative/docs/agents/speckit-ready/SKILL.md` — step 3 (~line 50) says "Return the script's stdout as the compact report", so add the one-line `FRICTION` clause there and in the `## Report` block (~line 212), noting the ready contract in the loop doc governs and that the line is appended **after** the unwrapped stdout (no `ready-check.sh` change); and `AiNative/docs/agents/server-setup/SKILL.md` — the "Compact report contract for the agent response" block (~line 417), where the `STATUS:`/`SUMMARY:` shape gains the same pointer (FR-041)
- [X] T016 [P] [US2] Make the parent *ask* for the line: in `AiNative/docs/agents/speckit-orchestrate/SKILL.md`, add `FRICTION` to the worker report template it hands each stage (§ "Tell each worker to return its compact report", ~line 857, and the sample report block ~line 891), so a hand-written worker prompt cannot drop it; keep it to the field name plus a pointer to the grammar (FR-040, FR-041)
- [X] T017 [P] [US2] Add the same one-line requirement to every harness worker prompt contract: `AiNative/docs/agents/claude-harness/worker-contract.md`, `cursor-harness/worker-contract.md`, `pi-harness/worker-contract.md`, `antigravity-harness/worker-contract.md` — each currently ends with the `STATUS:` line rule; add the `FRICTION:` requirement beside it, pointer-only (FR-041; antigravity is `FRICTION`-only here per research D11). Then add the same pointer to the `Report:` bullet of each adapter's **`SKILL.md`** prompt section — `claude-harness/SKILL.md:45`, `cursor-harness/SKILL.md:59`, `pi-harness/SKILL.md:31`, `antigravity-harness/SKILL.md:56`, each currently reading `- Report: `STATUS: ok` | `STATUS: stuck` | `STATUS: blocked`, SUMMARY (one paragraph), files changed` — because a hand-written worker prompt copies *that* template rather than `worker-contract.md`; without these four edits T017's stated goal ("a hand-written worker prompt cannot drop it") is unmet and FR-041 stays incomplete for prompts. Those four `SKILL.md` files join the TF-3 doc list (17 worker docs + 4 prompt contracts)

**Checkpoint**: TF-3 passes and no worker document restates the grammar.

---

## Phase 5: User Story 3 — Lessons stay apart from rules (Priority: P2)

**Goal**: a once-seen finding is logged and never promoted; a finding recurring on ≥2 distinct cards may become a rule proposal only when it names an existing rule to replace or merge into, so the rules file never grows a section.

**Independent Test**: read `AiNative/docs/agents/adjust/rule.md` and the skill's output section; confirm findings A (1 card) and B (1 card) stay learnings, C (2 cards) is promoted, promotion requires a merge target plus a verbatim quote of the rule being replaced, and additive-only changes are rejected — the checks live nowhere else (quickstart TF-6; scenario A).

### Implementation for User Story 3

- [X] T018 [US3] Write `AiNative/docs/agents/adjust/rule.md` § Must / § Must not / § Stop conditions: recurrence is **two or more distinct cards** counted by finding key, a card listed twice counts once, and the key is `<target-class>/<normalized-target-ref>/<short-slug>`; a rule proposal MUST name `merge target: <file>#<rule-id-or-heading>` and quote the existing rule verbatim (`existing rule quote`), and an intended edit that only adds a rule, section, or file is rejected; no merge target ⇒ stays a learning and the report states why; the verbatim prohibitions from plan W1 (no rules/config/skill/adapter edits, no board writes, no applying/staging/committing/shipping its own proposals, no gating or holding the card or merge); stop conditions table (card not terminal; `## Metrics` missing ⇒ continue on reports, never read as zero; no reports and no metrics ⇒ `ADJUST: no-findings` "evidence insufficient"; finding with no checkable evidence ⇒ learning only; recurrence < 2 ⇒ learning only; no merge target ⇒ learning only with the reason; target inside read-only AiNative ⇒ the parent files it against the AiNative repo; two workers blaming each other ⇒ record and cite both, pick no winner without a number; third failed attempt ⇒ `STATUS: blocked` with the park reason and the parent records the follow-up and completes the card); identifier rules — findings are `[adjust: A1]`, `[adjust: A2]` in the report's `PROPOSALS`/`FINDINGS` text only, and Adjust must not emit source-refs (`FR-###`, `US#/AC#`, `plan: …`, `Constitution …`) (FR-008, FR-019–FR-024, FR-042, FR-043)
- [X] T019 [US3] Add § Learnings log and finding keys to `AiNative/docs/agents/adjust/rule.md`: the log lives at `.ainative/learnings.md` in the managed project (AiNative's own at `AiNative/.ainative/learnings.md`), it is append-only and distinct from the rules file — the log is evidence, the rules file is the decision; one `## <key>` block per finding with `observed`, `cards`, `target: <class> → <ref>`, `evidence`, `observation`, `status: learning | promoted | superseded`, and `promoted-by: <artifact>#P<n>` when promoted; a second sighting appends its card and bumps `observed` instead of adding a block; supersession keeps the old lines and links forward; plus the canonicalization table (project `AGENTS.md` → `AGENTS.md`; `.ainative/project.yaml` → itself; AiNative skill → `skill:<name>`; system doc → `doc:<path>`; adapter → `harness:<name>`; lowercase refs, no line numbers, 3–6 kebab-word slug describing the observation, not the card) (FR-020, FR-023, FR-024)
- [X] T020 [US3] Add the six proposal rejection rules and the learning-only outcome to `AiNative/docs/agents/adjust/SKILL.md` § Output: a reviewer rejects a proposal block when it names fewer than two distinct cards; has no merge target or a merge target that does not resolve in the target file; describes an additive-only edit; has an empty or unopenable evidence list; names two target classes; or asks for an in-place edit of the mounted AiNative tree instead of a card against the AiNative repo. State that a rejected-amendment finding is written to the learnings log with `status: learning` and the reason appears in the report `SUMMARY`; state that the skill references `rule.md` for the threshold and merge-target test rather than restating the numbers (FR-021, FR-022, FR-042)

**Checkpoint**: TF-6 passes, and `rg 'recurrence|merge target|finding key' AiNative/docs/agents/ready AiNative/docs/agents/task-groomer AiNative/docs/knowledge/setup/harness.md` returns nothing.

---

## Phase 6: User Story 4 — Per-card numbers exist before proposals are judged (Priority: P2)

**Goal**: one `## Metrics` block per card, written by the parent at terminal state, from which converge/critic/tester/pr-review loop-backs, UAT outcome and reason, tokens, cost, and wall time are all derivable without a transcript — plus the before/after comparison rule that judges an accepted change.

**Independent Test**: fill one card's block from board data and reports alone (quickstart scenario B) and confirm each loop-back is attributed to its stage, absent stages read `n/a` rather than `0`, the UAT reason comes from the closed set with the operator's words kept, and cost/tokens fall back to `unknown` with the boundary stated (TF-7).

### Implementation for User Story 4

- [X] T021 [US4] Add `## Per-card metrics` to `AiNative/docs/systems/feature-loop.md` (place it after § Compact reports, before § Build size gate): the block lives on the card, is appended **by the parent** when the card reaches its terminal state and before Adjust is dispatched, and is one block per card; give the wire block with all fields (`path`, `terminal`, `closed_at`, `loops: converge= critic= tester= pr_review=`, `uat:` outcome/rounds/reasons, `uat_notes`, `tokens: input/output/total`, `cost_usd`, `wall_time_active`, `boundary`); define the loop-back counting rule — one count is one parent-observed **return dispatch** caused by that stage (`converge → tasks_appended`, `critic FAIL`, `tester FAIL`, `pr-review REQUEST CHANGES`), retries under the stuck policy are not loop-backs, a stage that FAILs twice in one card counts 2, UAT rounds are not a loop-back field (they live in `uat.rounds`/`uat.reasons`), `0` only when the stage ran and returned a non-looping verdict, `n/a` when the path lacks the stage or it never ran, never `0` for an absent stage; the **job-path mapping stated explicitly**, because two of its four loop-back fields are absent and it skips validation entirely — `loops.converge=n/a`, `loops.critic=n/a`, `loops.tester=n/a`, `loops.pr_review=n/a`, `uat.outcome=not_run` (job cards still carry the block and feed the roll-up, even though no per-card Adjust runs on that path); state that `closed_at` is the roll-up week anchor; state that every field is derivable from board dispatch history plus worker reports and that a re-opened card keeps its block and appends a new one (FR-025, FR-029)
- [X] T022 [US4] Continue the same section: the closed UAT failure reason set — `missing-feature`, `wrong-behavior`, `broken-ui`, `error-crash`, `missing-evidence`, `env-setup`, `scope-mismatch`, `docs-wrong`, `other` (with the meaning column), `reasons` required when `outcome: fail`, each reason allowed to carry its round (`wrong-behavior@r2`), and `uat_notes` carrying the operator's own quoted words, required when `other` is used; the cost boundary — `tokens`, `cost_usd`, `wall_time_active` are cumulative over the card's worker sessions and exclude human park/UAT idle time, `unknown` is the allowed value and never `0`, and the `boundary` line must state what is covered and what is unavailable today (cost/tokens will be `unknown` until the control plane aggregates); the comparison rule for judging an accepted change — compare `loops.*`, `uat.reasons`, `wall_time_active`, and `cost_usd` on the same path, per stage, over the 5 cards before the Change card's merge versus the 5 after it (skipping weeks where a different change landed), print the sample size, and exclude `n/a` stages from the sample rather than averaging them as zero; no comparison may require transcripts (FR-026, FR-027, FR-028)

**Escape hatch (research D6)**: if `feature-loop.md` passes ~550 lines while T021–T022 are written, move the metrics field table into `AiNative/docs/systems/adjust-metrics.md` and link it from `feature-loop.md` in one line — allowed without a spec change; keep the block, the `n/a`/`unknown` rules, and the comparison rule in the loop doc.

**Checkpoint**: TF-7 passes and scenario B fills in with zero transcript access.

---

## Phase 7: User Story 5 — A weekly cross-card roll-up finds what one card cannot (Priority: P3)

**Goal**: a defined weekly, cross-card roll-up that ranks friction targets with visible counts, shows proposals that recur without being accepted, reports evidence gaps, and runs as an ordinary skippable card.

**Independent Test**: read the roll-up definition and confirm it names the cadence, the week boundary and anchor, the input set, the output shape, the ranking-with-counts rule, the recurring-not-refiled rule, the skip/empty-week behaviour, and that the artifact is a `job` card rather than an in-process step (TF-8, scenario D).

### Implementation for User Story 5

- [X] T023 [US5] Add `## Weekly Adjust roll-up` to `AiNative/docs/systems/feature-loop.md` (after § Per-card metrics): one card per **ISO-8601 week** (Mon 00:00 → Sun 23:59 **UTC**, key `YYYY-Www`), filed by the **control plane** no later than the first business day after the week closes — AiNative owns the cadence and the shape, the scheduler is the harness's business; week membership is decided by the card's `## Metrics` `closed_at`, not by when Adjust ran or the PR opened, so a late or resumed run never moves a card between weeks and no card is counted twice; the card shape (`## Path: job`, `## Skill: adjust`, `## Step: rollup`, `## Week: <YYYY-Www>`) with the artifact at `.ainative/adjust/<YYYY>-W<ww>-rollup.md`; the artifact sections — friction by target (ranked, each line showing the observation count and the distinct-card count), recurring-not-accepted (finding key, first week, weeks seen, Change card and its state — listed once, never re-filed), stage numbers with `n=` on every figure and `n/a` stages excluded, and gaps (skipped weeks, late arrivals, cards predating `FRICTION` treated as unknown, `unknown` cost); skip semantics (the operator may skip or delete the card and nothing else in the loop changes, and the next roll-up reports the skipped week in `gaps:` with no back-fill); an empty week produces an empty ranking and an explicit gap, never invented findings (FR-030, FR-031, FR-032)
- [X] T024 [US5] Add roll-up mode to the skill: in `AiNative/docs/agents/adjust/SKILL.md` add `## STEP: rollup` describing how the same skill runs the weekly card — the input set is the week's per-card Adjust artifacts plus the `## Metrics` blocks whose `closed_at` falls in the week, plus `.ainative/learnings.md`; the output is the roll-up artifact path above with the same proposal shape and the same rejection rules, and cross-week recurrence counts as distinct cards; it never re-files an existing pending proposal, states small-sample and coverage numbers in `gaps`, and reports `ADJUST: no-findings` with the gap when the week produced no records; it cannot block, delay, or reorder any other card. Add the roll-up trigger to `AiNative/docs/agents/adjust/AGENTS.md` § When to use if T006 left it out (FR-030, FR-031, FR-032)

**Checkpoint**: TF-8 passes; a skipped week is described, not silently lost.

---

## Phase 8: User Story 6 — Each harness adapter says where its session bundle comes from (Priority: P3)

**Goal**: each of the four adapters documents a session bundle — worker prompt, worker transcript, subagent transcripts, usage — with its location, how the parent points Adjust at it, at least one real caveat, and the degrade rule; AiNative stays harness-neutral.

**Independent Test**: `rg -ni 'session bundle'` (case-insensitive — T025–T028 mandate the heading `## Session bundle`) finds a section in each of the four documents, and each section names contents, location, pointing mechanism, usage source, and ≥1 caveat; the neutrality check is diff-scoped — `git diff -U0 AiNative/docs/systems AiNative/docs/agents/adjust | rg '^\+' | rg -n '(state\.db|kanban\.db|~/\.claude|~/\.cursor|~/\.pi|SubagentStop|/opt/data/mnt)'` returns nothing, and the baseline `rg -n '/opt/data/mnt' AiNative/docs/systems` still shows only the three pre-existing lines (TF-4; FR-033–FR-036, SC-006)

### Implementation for User Story 6

- [X] T025 [P] [US6] Add `## Session bundle` to `AiNative/docs/agents/claude-harness/SKILL.md`: the six parts (worker prompt, worker transcript, subagent transcripts, usage, completeness, pointer); location — session JSONL under `~/.claude/projects/<slug>/<session>/` with subagent transcripts as `subagents/agent-*.jsonl`, `agent_transcript_path` passed by the `SubagentStop` hook, `report.json` carrying `sessionId`, `numTurns`, `totalCostUsd` (~lines 237–239); pointing — the parent attaches the directory or `sessionId` to the Adjust dispatch and Adjust records `bundle:<pointer>` / `transcript:<pointer>`; usage source — `report.json` fields, `unknown` where absent; caveats — the hook can fire before the transcript file is fully written, and the wrapper's isolated default (`--no-session-persistence`, ~line 108) can leave no transcript at all; degrade line — a partial or unavailable bundle ⇒ card data + reports + a stated partial drill-down, never an asserted cause (FR-033, FR-034, FR-035)
- [X] T026 [P] [US6] Add `## Session bundle` to `AiNative/docs/agents/cursor-harness/SKILL.md`: the same six parts; location — agent chats under `~/.cursor/chats`, resumed by `sessionId` with the same `--cwd` (~line 151); pointing — the parent passes the chat/session reference; usage — `totalCostUsd` and turn counts from the harness report, `unknown` when the account does not report usage (~line 204); caveats — background subagent stop events are unreliable so subagent transcripts may be missing, and `totalCostUsd` is null when usage is unreported; degrade line as above (FR-033, FR-034, FR-035)
- [X] T027 [P] [US6] Add `## Session bundle` to `AiNative/docs/agents/pi-harness/SKILL.md`: the same six parts; location — session files under `~/.pi/agent/sessions/<cwd>/`, pointed at with `--session <path|id>` or `--session-dir <dir>` (~lines 135–137); usage — tokens/cost/turns from the harness report, `unknown` where absent; caveat — `--no-session` leaves no session file (~line 131), so a bundle can be unavailable by design, and a job run may therefore have no worker transcript; degrade line as above (FR-033, FR-034, FR-035)
- [X] T028 [P] [US6] Add `## Session bundle` to `AiNative/docs/knowledge/setup/harness.md` (Hermes, the control plane — the fourth adapter per spec § Assumptions; do **not** create `docs/agents/hermes-harness/`, and do **not** add an Adjust row to § Gate ownership (~line 43) — Adjust is a stage, not a gate): the same six parts; location — the control plane's session store (`sessions`, `messages`, `worker_executions`) and board store (`task_runs`, `task_events`, `task_comments`), with the worker prompt as the dispatched step prompt; pointing — the parent exports or attaches the session/step ids with the Adjust dispatch; usage — per-session token/cost reporting where present, `unknown` otherwise; caveats — `sessions.parent_session_id` is not populated yet so worker and subagent records cannot be reliably joined, and the container cannot see host-only transcript directories (e.g. a host `~/.claude`) unless they are mounted; degrade line as above (FR-033, FR-034, FR-035)

**Checkpoint**: TF-4 passes in both directions — the four bundles exist, and this feature introduced no harness mechanic into `docs/systems/**` or `agents/adjust/` (the three pre-existing runtime-ownership mount lines are untouched and out of scope).

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: record the change, run the doc-review suite, and prove no forbidden artifact appeared.

- [X] T029 [P] Record the change in `AiNative/CHANGELOG.md` `## [Unreleased]`: `### Added` — the `adjust` stage/skill folder (fifth loop phase, runs after UAT + merge and after blocked/parked/killed/abandoned cards, proposals only, never a gate), the per-card `## Metrics` definition, the weekly cross-card Adjust roll-up card, the four adapter session-bundle sections; `### Changed` — PIVS → PIVSA across the loop/agent/system docs, the `FRICTION:` line required in every worker's compact report with `FRICTION: none` as the clean default, and the learnings-vs-rules rule (one card ⇒ `.ainative/learnings.md`; ≥2 distinct cards ⇒ a rule proposal that must replace or merge an existing rule). Match the file's existing entry style — one line per change, backticks for identifiers (FR-044)
- [X] T030 [P] Run the doc-review suite TF-1 … TF-12 from `specs/004-adjust-stage/quickstart.md` against the tree and fix every miss in the owning file (not in the check): `rg -n 'PIVS\b|four phases'` must hit only `docs/systems/agentic-coding.md` and `CHANGELOG.md` history; no `#pivs-mapping` link may survive and all 11 `#pivsa-mapping` links must resolve to the renamed heading; `FRICTION` counts in `feature-loop.md` must cover the definition plus all twelve contracts (**13** occurrences, the twelfth contract being job skills); `rg 'FRICTION: <target-class>'` must hit only the loop doc and the Adjust skill's report template; **stage-naming guard for FR-003**, which no other check covers — `rg -n 'learn stage|learn phase|Learn stage|Learn phase' AiNative/docs` must return nothing (the stage is `Adjust`; `learn` stays the name of the spike/demo card mode only); **harness neutrality, scoped to this feature** so the pre-existing runtime-ownership lines do not read as failures — `git diff -U0 AiNative/docs/systems AiNative/docs/agents/adjust | rg '^\+' | rg -n '(/opt/data/mnt|state\.db|kanban\.db|~/\.claude|~/\.cursor|~/\.pi|SubagentStop|agent_transcript_path|task_runs)'` must return nothing, and `rg -n '/opt/data/mnt' AiNative/docs/systems` must still return exactly the three pre-existing lines (`feature-loop.md:99`, `feature-loop.md:365`, `agentic-system.md:196`) — no fourth; the change set must equal the **File allowlist** in [plan.md](./plan.md) § Blast radius — the single owner of "which files may change", which this task only runs — so `git status --porcelain AiNative/` must show `docs/**` and `CHANGELOG.md` plus **only** the two `description:` frontmatter lines of `AiNative/.cursor/commands/{critic,tester}.md` (allowed and required by T004/W3, so they can never count as a miss here), with no `.ainative/` file, no `scripts/` change, and no `.cursor/commands/*` body change. Paste each command and its output into the PR-body evidence sheet (SC-001–SC-010, plan W10)
- [X] T031 [P] Write the tabletop answers for quickstart scenarios A–E into the PR-body evidence sheet, each naming the document line that produces the outcome: A (one card with an `ainative`/`project-config` friction and `loops.tester=2` ⇒ learning only; the same key on a second card ⇒ one promoted proposal with a merge target, or a stated reason why no merge target exists), B (fill a card's `## Metrics` from board data only), C (no reports and no metrics ⇒ `ADJUST: no-findings`, `EVIDENCE_USED: card`, `ARTIFACT: none`), D (a finding key recurring across two weeks with a pending Change card ⇒ listed under recurring, not re-filed), E (a third failed attempt ⇒ park recorded as a follow-up on a completed card, merge untouched). Then answer the five operator questions from `feature-loop.md` + `agents/adjust/` alone (TF-12, SC-001)
- [X] T032 [P] Length and link audit before hand-off: `AiNative/docs/agents/adjust/SKILL.md` under 500 lines with supporting detail in `rule.md` (links one level deep); `AiNative/docs/systems/feature-loop.md` under ~550 lines (else take the research-D6 escape hatch named in Phase 6 and leave a one-line link from the loop doc); no `.ainative/` directory created anywhere; no new file outside `AiNative/docs/**` and `AiNative/CHANGELOG.md`; the `adjust` folder contains exactly `SKILL.md`, `AGENTS.md`, `rule.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — creates the folder and the registry row
- **Foundational (Phase 2)**: depends on Setup only for the `rule.md`/`SKILL.md` skeleton being present (T003–T005 edit `feature-loop.md` and the linked docs, not the new folder) — **blocks every user story**, because US1/2/6 point at the single `FRICTION` statement and US1/4/5 write into a doc whose mapping is already PIVSA
- **User Stories (Phase 3–8)**: all depend on Phase 2
  - **US1 (P1)** after Phase 2 — no story dependency
  - **US2 (P1)** after Phase 2 and after T005 (the grammar it points at); T011 edits `feature-loop.md` § Compact reports, which T009/T010 do not touch, so it may run alongside US1
  - **US3 (P2)** after US1 T007–T008 (it extends the same `SKILL.md` procedure/output and fills `rule.md`)
  - **US4 (P2)** after Phase 2 — independent of US1–US3 in content; it appends a new section to `feature-loop.md`, so sequence it after T010 only for edit conflicts
  - **US5 (P3)** after US4 (it reads the metrics block it references) and after US3 T019 (the learnings log it reads)
  - **US6 (P3)** after Phase 2 — four independent files; independent of US1–US5
- **Polish (Phase 9)**: after all desired stories; T030–T032 must run last in that phase

### User Story Dependencies

- **US1 (P1)**: independent; the MVP
- **US2 (P1)**: independent of US1 in files (except the shared loop doc section), but its grammar statement comes from Phase 2
- **US3 (P2)**: extends US1's skill folder — not independently *deliverable* before US1, but its assertions (TF-6, scenario A) can be reviewed on their own
- **US4 (P2)**: independent of US1–US3; numbers are defined even though nothing consumes them yet
- **US5 (P3)**: depends on US4's metric fields and US3's learnings log, which is what it aggregates
- **US6 (P3)**: independent of all of the above; Adjust must work without it, which is why it is last

### Within Each User Story

- `rule.md` constrains the `SKILL.md` procedure, so US3's rules land before the rejection rules that point at them
- The `feature-loop.md` graph/table/paths (US1) land before the metrics and roll-up sections (US4/US5) that sit after them in the document
- Each story ends at its checkpoint and its TF check — do not start the next priority until the current story's check passes

### Parallel Opportunities

- T002 with T001 (different files); T004 with T003
- Phase 4: T011–T017 are seven disjoint file sets and can all run in parallel
- Phase 8: T025–T028 are four disjoint documents and can all run in parallel
- Phase 9: T029–T032 are independent (changelog, checks, tabletop write-up, link audit), but T030–T032 read the finished tree, so run them after every story edit
- Two implementers: one takes US1+US3 (the skill folder and the loop graph), the other takes US2+US6 (report lines and adapter bundles), then US4 → US5 sequentially because both grow the same loop document

---

## Parallel Example: User Story 2

```text
# One pass over the report contracts, then the worker docs in parallel:
T011  feature-loop.md § Compact reports — 12 contract blocks
T012  ready/AGENTS.md § Output + route-work/AGENTS.md § Outputs
T013  critic/{AGENTS,SKILL,rule}.md + tester/{AGENTS,SKILL,rule}.md
T014  pr-reviewer/SKILL.md + change/SKILL.md (both report blocks)
T015  learn, prd-writer, project-bootstrapper, proposal-writer
T016  speckit-orchestrate/SKILL.md worker report template
T017  claude/cursor/pi/antigravity worker-contract.md + the `Report:` bullet in each SKILL.md
```

## Parallel Example: User Story 6

```text
T025  claude-harness/SKILL.md      (JSONL sessions, SubagentStop, --no-session-persistence)
T026  cursor-harness/SKILL.md      (chats store, unreliable background subagents, null cost)
T027  pi-harness/SKILL.md          (session dir, --no-session)
T028  knowledge/setup/harness.md   (Hermes stores, parent_session_id, container mount)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup — folder + registry row
2. Phase 2: Foundational — PIVSA everywhere, one `FRICTION` statement (**blocks everything**)
3. Phase 3: US1 — the `adjust` folder content and the graph/table/path rows
4. **STOP and VALIDATE**: TF-2, TF-5, TF-12, and scenarios A/C/E. An operator can then answer where Adjust runs, what it reads, what it writes, and whether it blocks a merge — with the merge untouched
5. Ship the stage definition as the first increment

### Incremental Delivery

1. Setup + Foundational → the loop is PIVSA and the friction grammar exists
2. US1 → the stage exists and cannot gate a merge (MVP)
3. US2 → every worker now reports friction, so Adjust's second input class is real
4. US3 → recurrence and merge-target rules keep the rules file from growing
5. US4 → the numbers Adjust reads are defined, so proposals can be judged
6. US5 → the weekly roll-up sees what one card cannot
7. US6 → drill-down has a defined shape per harness
8. Polish → changelog, doc-review evidence sheet, length/consistency audit

### Parallel Team Strategy

With two implementers: Phase 1–2 together, then A = US1 → US3 → US4, B = US2 → US6 → US5 (US5 last in either track because it depends on US3 and US4). Rebase onto the other track before the final polish.

---

## Notes

- **Two implementations of nothing**: the recurrence threshold and the merge-target test appear only in `docs/agents/adjust/` (T018), the `FRICTION` grammar only in `feature-loop.md` § Compact reports (T005), the metrics block only in `feature-loop.md` § Per-card metrics (T021), and the `## Metrics` writer only in that same section. Everywhere else is a pointer (FR-040–FR-042)
- **Harness neutrality is a grep, not an intention**: no adapter path, hook name, or database table may be introduced by this change into `docs/systems/**` or `docs/agents/adjust/`; the pre-existing runtime-ownership mention of `/opt/data/mnt/AiNative` in `feature-loop.md` (lines ~99, ~365) and `agentic-system.md` (~196) stays exactly as it is, is out of scope for SC-006, and nothing new is added next to Adjust content (FR-036). The check is therefore diff-scoped in TF-4/T030, not a whole-tree grep
- **[P] tasks = different files, no dependency between them**
- **[Story] label maps a task to the user story whose independent test proves it**
- No tests are generated: the spec requests none, and the verification surface is TF-1 … TF-12 plus scenarios A–E
- Out of scope, explicitly: wiring Adjust into the live Hermes install, any transcript-parsing script, back-filling `FRICTION` on historical cards, pre-creating `.ainative/` files, installing host symlinks, editing `personalAgent/`, `.specify/`, or `.pi/`, or changing the `ready`/`task-groomer`/install gates
- Commit per story group (`docs(adjust)`, `docs(feature-loop)`, `docs: require FRICTION`, `docs(feature-loop): metrics + roll-up`, `docs(harness): session bundles`, `docs(changelog): PIVSA + Adjust`) — the parent Ship step owns git unless `keep-local`


---

## Phase 10: Convergence

- [X] T033 Specify persistent write location on a fresh short-lived branch off the merged base (parent commits and ships via dedicated Adjust PR / proposal Change card PR) for post-merge runs and base-branch commit for non-merge runs in `AiNative/docs/agents/adjust/SKILL.md:50`, `AGENTS.md:22`, and `rule.md` [critic: C1] per FR-018 (partial)
- [X] T034 Define a neutral session bundle contract with the 6 standard fields in `AiNative/docs/agents/adjust/SKILL.md` (or `AiNative/docs/systems/feature-loop.md`) and update all four harness adapters (`claude-harness`, `cursor-harness`, `pi-harness`, and `knowledge/setup/harness.md`) to cite it [critic: C2] per FR-033 (missing)
- [X] T035 Resolve append-only contradiction in `AiNative/docs/agents/adjust/rule.md` learnings log by making log updates truly append-only with a new dated sighting entry per recurrence [critic: C3] per FR-020 (contradicts)
- [X] T036 Update `AiNative/docs/agents/adjust/AGENTS.md:5` and `AiNative/docs/agents/README.md:99` from "fifth loop state" / "state #5" to "final state" [critic: C4] per FR-001 (contradicts)
- [X] T037 Unify wire format keys and field rule names for `uat` (`uat.outcome`, `uat.rounds`, `uat.reasons`) and `loops` (`loops.<stage>`) in `AiNative/docs/systems/feature-loop.md` § Per-card metrics [critic: C5] per FR-025 (contradicts)
- [X] T038 Specify delivery mechanism and PR/ship handling for the weekly roll-up card (`## Path: job`) in `AiNative/docs/systems/feature-loop.md` § Weekly Adjust roll-up [critic: C6] per FR-030 (partial)
- [X] T039 Replace restatement of recurrence threshold and merge-target test in `AiNative/docs/systems/feature-loop.md` § Weekly Adjust roll-up with a link to `AiNative/docs/agents/adjust/rule.md` per gate-ownership rule [critic: C7] per FR-023 (contradicts)

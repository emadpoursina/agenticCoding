# Feature Specification: Adjust stage (PIVS → PIVSA)

**Feature Branch**: `adjust-stage`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: full text of `.agent/orchestrate/task.md` — add an "Adjust" stage to the AiNative feature loop, turning PIVS into PIVSA, so the operator gets evidence-backed proposals after each run for improving project rules, the AiNative methodology, and harness adapters.

## Clarifications

### Session 2026-11-26

- Q: When an Adjust run parks after three attempts, does the card stay open waiting on a human, or does it complete with the park recorded? → A: The card completes. The park is recorded as a follow-up item on the card, and a parked Adjust never holds the card open.
- Q: How does a proposal become a Change card — does the Adjust worker write cards to the board, or emit proposals that the parent files? → A: Adjust emits proposals in a proposal artifact file, referenced by id in its compact report; the parent files the Change cards. Adjust never writes to the board.
- Q: How should the loop decide that two findings are the same finding when counting recurrence? → A: With a stable finding key of target class + normalized target reference + short slug, recorded on every learnings entry; recurrence counts entries sharing that key across distinct cards.
- Q: What exact shape must the `FRICTION:` line take in every worker report? → A: `FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>`, with a clean run emitting exactly `FRICTION: none`; the target class is one of the four proposal target classes.
- Q: Where should the per-card metric record live so a reviewer can fill it in and the roll-up can read it? → A: A fixed `## Metrics` block on the card itself, appended by the parent when the card reaches its terminal state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every finished card produces evidence-backed proposals (Priority: P1)

An operator finishes a feature or change card: converge, critic, tester, ship, pr-review, UAT, merge. After the merge (and also when a card is blocked, parked, or abandoned) the loop runs one more stage, Adjust. Adjust reads the card's hard numbers, the workers' compact reports, and their `FRICTION` lines, and returns a small set of proposals: "this rule caused a merge-conflict loop on card X", "this skill step was skipped three cards in a row", "this harness wrapper loses subagent transcripts". Each proposal cites its evidence, names exactly one target, and is filed as a Change card that a human approves or rejects. Adjust never edits rules, skills, methodology docs, or harness adapters itself.

**Why this priority**: This is the feature. Without it PIVS ends at validation and nothing in the loop learns from the run.

**Independent Test**: Read the Adjust skill folder and `docs/systems/feature-loop.md`. Confirm an operator can answer, using those documents alone: where Adjust runs on each path, what it may read, what it may write, how a proposal is shaped, and that it cannot block merge. Then tabletop one card whose tester FAILed twice and whose tester report carried a `FRICTION` line, and confirm the documented output is a proposal with an evidence reference, one named target, and a Change card.

**Acceptance Scenarios**:

1. **Given** a feature card whose PR was merged after a UAT pass, **When** the run ends, **Then** the loop dispatches Adjust as a fresh worker after merge, and the card completes once Adjust's outcome is recorded — either its report or its dispatch parked; a park never holds the card open.
2. **Given** a feature card that ends in a parked/blocked state, or a card the operator abandons, **When** the card leaves the active set, **Then** Adjust still runs and produces proposals or an explicit `no findings` report; an abandoned card is not treated as producing no evidence.
3. **Given** Adjust has run and produced proposals, **When** the operator reviews them, **Then** each proposal states the evidence it rests on, names one target of the four allowed target classes, and exists as a Change card awaiting human approval.
4. **Given** any card on any path, **When** Adjust is delayed, fails, or reports `blocked`, **Then** the merge and card completion are unaffected — Adjust output is never a merge gate.

---

### User Story 2 - Every worker reports friction in its compact report (Priority: P1)

Every worker on every path — ready, route, specify, clarify, plan, tasks, analyze, implement, converge, critic, tester, pr-review, change, job skills, ship — adds a `FRICTION:` line to its compact report. Mostly `FRICTION: none`. When something slowed the step down or made it guess, the worker says so in one line with an evidence reference, instead of leaving a trace the operator has to reconstruct from transcripts.

**Why this priority**: Adjust's second input class is the compact reports. If `FRICTION` is optional or invented per-worker, Adjust has nothing uniform to read, and the stage degrades into transcript mining.

**Independent Test**: Open `docs/systems/feature-loop.md` § Compact reports and count the documented report contracts. Confirm every one of them carries `FRICTION`, and that the line format and the `none` case are stated once, in that section, not restated per worker.

**Acceptance Scenarios**:

1. **Given** the compact-report section, **When** a reviewer counts worker report contracts, **Then** every one includes `FRICTION` with the same shape and the `FRICTION: none` default.
2. **Given** a worker that finished with a clean run, **When** it reports, **Then** it emits `FRICTION: none` rather than omitting the line.
3. **Given** a worker that hit friction (a missing input, a stale doc, a harness quirk, a repeated retry), **When** it reports, **Then** the line names the friction and points at an artifact the parent can check.
4. **Given** an existing worker skill folder, **When** the change lands, **Then** the skill text and the compact-report section agree — no worker documents a report without `FRICTION`.

---

### User Story 3 - Lessons stay apart from rules (Priority: P2)

A finding seen once does not become a rule. Adjust writes it to a learnings log with its evidence. Only when the same finding recurs across two or more cards does it become eligible for promotion, and a promotion must replace or merge an existing rule — never append a new one beside it. The operator ends up with a rules file that stays the same size and gets more precise, not a rules file that grows until nobody reads it.

**Why this priority**: This is the failure mode the stage exists to avoid: unmeasured, ever-growing rules files. Without the two-card threshold and the merge-on-promotion rule, Adjust actively makes the rules worse.

**Independent Test**: Give Adjust three inputs — one card with finding A, one card with finding B, two cards with finding C. Confirm the documented procedure logs A and B as learnings, promotes only C as a rule proposal, and that the C proposal points at the specific existing rule it replaces or merges into.

**Acceptance Scenarios**:

1. **Given** a finding observed on exactly one card, **When** Adjust records it, **Then** it goes to the learnings log with the card reference and never becomes a rule proposal.
2. **Given** a finding observed on two or more cards, **When** Adjust records it, **Then** it becomes a rule proposal that names the existing rule it replaces or merges into.
3. **Given** a rule proposal that cannot name an existing rule to replace or merge into, **When** Adjust considers it, **Then** it stays a learning and the report says why no merge target exists.
4. **Given** an accepted rule change, **When** a later card runs, **Then** the rules file has not gained a section — the delta is a rewrite of an existing rule, and the learnings log keeps the trail that led there.

---

### User Story 4 - Per-card numbers exist before proposals are judged (Priority: P2)

For every card, the loop records numbers Adjust can read and the operator can use to judge whether an accepted change helped: loop-back counts for converge, critic, tester, and pr-review; UAT failure reasons; tokens; cost; wall time. After an accepted rule change, the next cards' numbers show whether it worked, instead of the operator guessing from memory.

**Why this priority**: Proposals without numbers are opinions, and the learn/promote cycle has no way to be evaluated. Numbers come before judgement, so they are defined in this change even though nothing consumes them yet.

**Independent Test**: Read the metrics definition. For a single historical card, confirm a reviewer could fill in every metric from board data and worker reports alone, with no transcript access, and could say which stage each loop-back belongs to.

**Acceptance Scenarios**:

1. **Given** the metrics definition, **When** a reviewer reads one card's board record and reports, **Then** converge, critic, tester, and pr-review loop-back counts are all derivable, and each is attributed to its stage.
2. **Given** a UAT failure, **When** it is recorded, **Then** it carries a reason from a closed set (the operator's own words kept alongside), so failures can be counted rather than re-read.
3. **Given a card's cost data, **When** the operator compares it with a later card, **Then** tokens, cost, and wall time are each available per card, with the accounting boundary stated (which part of the run they cover).
4. **Given** an accepted rule change, **When** the operator wants to evaluate it, **Then** the definition names which metrics are compared, over which cards (before vs after), and over what window — without requiring transcripts.

---

### User Story 5 - A weekly cross-card roll-up finds what one card cannot (Priority: P3)

Once a week, a roll-up reads the week's Adjust outputs and card metrics across all cards and answers the questions a single card cannot: which target accumulates the most friction, which proposal keeps recurring without being accepted, whether accepted changes moved the numbers. The roll-up is a card like any other, so it is visible, reviewable, and skippable.

**Why this priority**: Per-card Adjust sees one card. Methodology-level drift only shows up across cards, and it is the slowest-moving, most valuable signal. It can wait until per-card output exists.

**Independent Test**: Read the roll-up definition and confirm it names: its trigger cadence, its inputs (per-card Adjust records plus card metrics), its output (the same proposal shape), and that it runs as an ordinary card that can be skipped without breaking the week's other work.

**Acceptance Scenarios**:

1. **Given the roll-up definition, **When** an operator reads it, **Then** it states the cadence, the input set, the output shape, and that the artifact is a card, not an in-process step.
2. **Given a week with no per-card Adjust records, **When** the roll-up runs, **Then** it reports that rather than inventing findings.
3. **Given** a roll-up that ranks targets by accumulated friction, **When** the operator reads one line, **Then** the count behind the rank is visible.
4. **Given the operator skips the week's roll-up card, **When** the next cards run, **Then** nothing else in the loop changes.

---

### User Story 6 - Each harness adapter says where its session bundle comes from (Priority: P3)

Adjust's baseline inputs are card data and compact reports. When a proposal needs a drill-down, each harness adapter documents how to hand Adjust a session bundle — the worker prompt, its transcript, its subagent transcripts, and its usage — plus the known caveats. AiNative stays harness-neutral; the mechanics live in the adapter docs.

**Why this priority**: Without it, drill-down is improvised per run and produces unevidenced claims. With it, Adjust can stay doc-level and optional. It is last because Adjust must work without it.

**Independent Test**: Open the four adapter documents (claude-harness, cursor-harness, pi-harness, Hermes) and confirm each names where worker and subagent transcripts live, what a bundle contains, and at least one stated caveat about transcript availability.

**Acceptance Scenarios**:

1. **Given** each of the four adapter docs, **When** a reviewer looks for "session bundle", **Then** each states the bundle's contents, its on-disk or database location, and how Adjust is pointed at it.
2. **Given the Hermes adapter, **When** a reviewer reads it, **Then** it names the board and session stores the bundle comes from, and states that the container cannot see host-only transcript directories unless mounted.
3. **Given an unavailable or partial transcript, **When** Adjust drills down, **Then** the documented behavior is to fall back to card data and reports and to say in the proposal that the drill-down was partial — not to assert a cause from nothing.
4. **Given the core methodology docs, **When** a reviewer greps them for harness-specific paths, **Then** harness mechanics appear only in adapter docs.

---

### Edge Cases

- **No compact reports at all.** A card abandoned before any worker ran still gets Adjust, but the only evidence is the card itself (path, timestamps, state history). Adjust must be able to say "no findings, evidence insufficient" and file nothing.
- **A card that produced no merge.** Blocked, parked, killed, or abandoned cards are eligible; the absence of a merge is itself a data point, not a disqualification.
- **`FRICTION` lines missing from older cards.** Cards that predate this change have no `FRICTION` lines. Adjust must degrade to card numbers instead of treating missing lines as "no friction".
- **Conflicting friction.** Two workers blame each other for the same delay. Adjust records both, cites both, and does not pick a winner without a number to settle it.
- **A proposal target inside read-only AiNative.** The managed-project runtime mounts AiNative read-only. A proposal targeting an AiNative skill or system doc must still be fileable; it lands as a card against the AiNative repo rather than as an in-place edit.
- **Duplicate or re-proposed findings.** The same proposal appears in consecutive weeks. The roll-up must show that it recurs and has not been accepted, rather than filing a second identical card.
- **Name collision with `learn`.** `learn` is an existing card mode. The new stage is "Adjust" and must not be called "learn" anywhere in the loop, or operators will confuse a spike card with a loop stage.
- **Transcript written late or not at all.** A hook may fire before the transcript is complete, and background subagents may not produce one. A partial bundle is usable evidence; a wrong cause is not.
- **Adjust on a job card.** A job card is one worker and a shipped PR, with no spec, plan, or validation gate — see the assumption on path scope.
- **Adjust fails on the first attempt.** Three attempts, then park, consistent with the rest of the loop; a parked Adjust does not reopen the merged PR and does not hold the card — the park is recorded as a follow-up item on the card and the card completes.

## Requirements *(mandatory)*

### Functional Requirements

**The stage**

- **FR-001**: An Adjust skill MUST exist at `AiNative/docs/agents/adjust/` as a folder of the same shape as the other agents (`SKILL.md`, `AGENTS.md`, and `rule.md`), and MUST be registered in `AiNative/docs/agents/README.md`.
- **FR-002**: The Adjust skill MUST define, in its own folder, its inputs, its procedure, its output contract, its stop conditions, and its compact report.
- **FR-003**: The stage name MUST be "Adjust" everywhere in the loop. No document may call the stage "learn", which already names the `spike`/`demo` card mode.
- **FR-004**: Adjust MUST run after the UAT pass and merge on the feature path, and after the merge on the change path.
- **FR-005**: Adjust MUST also run on cards that end without a merge — blocked, parked, killed by the operator, or abandoned.
- **FR-006**: Adjust MUST NOT gate, delay, or block merge, completion, or the release of dependent cards. A failed, skipped, or parked Adjust leaves the merged PR merged and the card completed, with a park recorded as a follow-up item on the card rather than a hold. Adjust's trigger is the card reaching a terminal state — merged, or closed/abandoned without a merge — so no new card state is required to make a non-merging card eligible.
- **FR-007**: Adjust MUST run as its own worker session, one step, under the Validation profile, on the same executor rule as every other state — not as a parent-side or in-process step.
- **FR-008**: Adjust MUST be subject to the existing stuck policy: three attempts then park, and no retry of a stable blocked report.

**Inputs**

- **FR-009**: Adjust's inputs MUST be prioritized and documented: first hard numbers from the card (board data and loop-back counts), then compact reports and their `FRICTION` lines, then raw transcripts through the harness adapter and only to investigate an anomaly.
- **FR-010**: Adjust MUST be able to run from the first two input classes alone, with no transcripts. Transcript access is an optional drill-down, never a prerequisite.
- **FR-011**: Adjust MUST treat missing `FRICTION` lines (older cards, partial reports) as "unknown", not as "no friction", and MUST say so in its report.

**Output contract**

- **FR-012**: Adjust's output MUST be proposals only. Adjust MUST NOT edit project rules, project config, AiNative skills or system docs, or harness adapter documents, and MUST NOT apply its own proposals.
- **FR-013**: Every proposal MUST cite the evidence it rests on, with a reference a reviewer can check (card id, report artifact, metric, transcript location when one was used).
- **FR-014**: Every proposal MUST name exactly one target from a closed set: the project `AGENTS.md`, the project `.ainative/project.yaml`, an AiNative skill or system doc, or a harness adapter.
- **FR-015**: Every proposal MUST become a Change card for human approval, and MUST state the target file (or file class) and the intended edit in reviewer-usable terms. Adjust MUST emit proposals in a proposal artifact file and reference them by id in its compact report; the **parent** files the Change cards on the board. Adjust MUST NOT write to the board itself.
- **FR-016**: A proposal MUST NOT be filed without cited evidence. When evidence is too thin, Adjust MUST record the observation in the learnings log only.
- **FR-017**: A proposal whose target lives in the read-only AiNative mount MUST be filed as a card against the AiNative repository, never as an in-place edit of the mounted copy.
- **FR-018**: A run that finds nothing MUST report that outcome explicitly, with the evidence checked, rather than reporting `ok` with an empty body.

**Lessons vs rules**

- **FR-019**: Adjust MUST keep findings and rules apart: a finding observed on one card goes to the learnings log and MUST NOT become a rule proposal.
- **FR-020**: A finding MUST recur on two or more distinct cards before Adjust may propose it as a rule, with recurrence counted by finding key across distinct cards — two entries from the same card count once.
- **FR-021**: A rule proposal MUST name the existing rule it replaces or merges into. A rule change that only adds a new rule, section, or file MUST be rejected by the documented procedure.
- **FR-022**: A rule proposal that cannot name an existing rule to replace or merge MUST remain a learning, and Adjust's report MUST state why no merge target exists.
- **FR-023**: Each learnings entry MUST carry the card reference(s) that produced it, the date, the target class it points at, a stable finding key, and a short statement of the observation, so that the recurrence count can be computed without re-reading transcripts. The finding key is `<target-class> / <normalized target reference> / <short slug>`; two findings are the same finding when their keys match.
- **FR-024**: The learnings log MUST be distinct from the project's rules file(s) — the log is evidence, the rules file is the decision.

**Metrics**

- **FR-025**: The methodology MUST define a per-card metric set covering loop-back counts for converge, critic, tester, and pr-review, each attributed to its stage, and MUST name the record's home: a fixed `## Metrics` block on the card, appended by the parent when the card reaches its terminal state, so feature, change, and job cards share one location.
- **FR-026**: The per-card metric set MUST include UAT outcome (pass/fail) with a failure reason drawn from a closed set, keeping the operator's own words alongside.
- **FR-027**: The per-card metric set MUST include tokens, cost, and wall time, with the accounting boundary stated (what part of a run they cover, and what is expected to be unavailable today).
- **FR-028**: The metrics definition MUST state which metrics are compared when judging whether an accepted change helped, over which cards (before vs after), and over what window.
- **FR-029**: Every metric in the set MUST be derivable from board data plus worker reports, without transcript access.

**Weekly roll-up**

- **FR-030**: The methodology MUST define a cross-card weekly Adjust roll-up with a stated cadence, its input set, its output shape, and its artifact form (a card).
- **FR-031**: The roll-up MUST rank targets by accumulated friction with the count visible, and MUST show proposals that recur without being accepted.
- **FR-032**: The roll-up MUST be skippable without affecting other cards, and MUST report an evidence gap rather than invent findings when the week produced no Adjust records.

**Harness session bundles**

- **FR-033**: Each of the four harness adapters (`claude-harness`, `cursor-harness`, `pi-harness`, and Hermes) MUST document a "session bundle": what it contains (worker prompt, worker transcript, subagent transcripts, usage/cost), where it lives, and how Adjust is pointed at it.
- **FR-034**: Each adapter document MUST state at least one known caveat about transcript availability — for example a hook firing before the transcript finishes writing, background subagents not producing transcripts, host-only paths invisible inside a container, or a session-link field not yet populated.
- **FR-035**: A partial bundle MUST have a documented behavior: Adjust degrades to card data and reports and says in the proposal that the drill-down was partial.
- **FR-036**: Harness-specific paths, hook names, and database tables MUST appear only in the adapter documents, not in the AiNative methodology documents.

**Loop documentation**

- **FR-037**: `docs/systems/feature-loop.md` MUST show Adjust in the canonical state graph, in the state table, and in the card-path tables for the feature and change paths, including its position after UAT and merge and its behavior on cards that never merge.
- **FR-038**: The PIVS mapping in the same document MUST become PIVSA, with Adjust defined as the fifth phase and its relationship to the merge stated (it runs after merge and never gates it).
- **FR-039**: The graph string and any equality between "the graph" and PIVS MUST be updated so the document is internally consistent — no leftover statement that the loop is four phases.
- **FR-040**: The compact-report contract MUST require a `FRICTION:` line from every worker on every path, with one stated format — `FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>`, where `<target-class>` is one of the four classes in FR-014 and the evidence reference is checkable by the parent — and a stated `FRICTION: none` default, which is the exact line a clean run emits.
- **FR-041**: Every worker's own skill document that describes its report MUST agree with the compact-report section on `FRICTION`.
- **FR-042**: The gate-ownership rule MUST be honored: the recurrence threshold and the merge-target requirement are checked in exactly one place (the Adjust skill), and MUST NOT be re-implemented in `ready`, `task-groomer`, or any other gate.
- **FR-043**: Any new validator or finding identifiers introduced for Adjust MUST follow the existing ID conventions and MUST appear only in the task/report line, not as source-refs.
- **FR-044**: `AiNative/CHANGELOG.md` MUST record the new stage, the PIVSA rename, the `FRICTION` requirement, the metrics definition, the roll-up, the adapter bundle notes, and the learnings-vs-rules rule, under `[Unreleased]`.

### Key Entities

- **Adjust run**: one card's post-merge (or post-abandonment) Adjust step. Attributes: card id, path, terminal state (merged / blocked / abandoned), evidence classes available, number of findings, number of proposals, outcome.
- **Finding**: one observation drawn from evidence. Attributes: text, finding key, target class, card reference(s), date, evidence reference, recurrence count.
- **Learnings entry**: a logged finding that has not (yet) been promoted. Attributes: the finding, finding key (target class + normalized target reference + short slug), first-seen card, subsequent cards, target class, date.
- **Rule proposal**: a finding that met the recurrence threshold and names an existing rule to replace or merge into. Attributes: target file, existing rule reference, evidence, intended edit, resulting Change card.
- **Proposal card (Change card)**: the artifact a proposal becomes for human approval. Attributes: target, evidence, intended edit, approval state. Filed by the parent from Adjust's report and proposal artifact; Adjust never writes it.
- **Per-card metric record**: the numbers Adjust reads. Attributes: card id, path, loop-back counts by stage, UAT outcome and reason, tokens, cost, wall time. Home: the card's `## Metrics` block, written by the parent at card close.
- **Weekly roll-up**: the cross-card aggregation artifact. Attributes: week, input set, target ranking with counts, recurring unaccepted proposals, evidence gaps.
- **Session bundle**: the optional drill-down input a harness supplies. Attributes: worker prompt, worker transcript reference, subagent transcript references, usage/cost, completeness flag.
- **FRICTION line**: the one-line friction report every worker emits. Attributes: target class, observation, evidence reference, or `none`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator reading only the loop document and the Adjust skill folder can answer all four questions correctly — where Adjust runs on each path, what it may read, what it may write, whether it can block merge — with zero follow-up questions.
- **SC-002**: 100% of the worker report contracts documented in the loop document carry `FRICTION`, and 100% of the worker skill documents that describe a report agree with it. Zero workers documented without it.
- **SC-003**: In a review of the first ten Adjust runs, 100% of filed proposals cite at least one checkable evidence reference and name exactly one target from the allowed set. Zero proposals filed without evidence.
- **SC-004**: Zero single-observation findings appear as rule proposals, and 100% of rule proposals name an existing rule they replace or merge into. The project rules file does not grow in rule count as a result of Adjust promotions.
- **SC-005**: Every metric in the per-card set can be filled in for a historical card from board data and worker reports alone — measured by an independent reviewer reproducing one card's numbers with no transcript access.
- **SC-006**: All four harness adapter documents describe a session bundle and state at least one caveat each; this feature introduces **zero** harness-specific paths, hook names, or database tables into the methodology documents (`docs/systems/**`, `docs/agents/adjust/`). Pre-existing runtime-ownership mentions of the read-only AiNative mount are out of scope: they are neither removed nor counted, so the check is scoped to lines this feature adds (TF-4).
- **SC-007**: Adjust adds zero blocking time to any merge: across the first twenty cards, zero merges or dependent-card releases are observed waiting on Adjust.
- **SC-008**: After four weekly roll-ups, the operator can name the top friction target from the roll-up numbers alone, and can state whether an accepted change moved the before/after metrics.
- **SC-009**: A card that ends blocked or abandoned produces an Adjust record in 100% of observed cases — no terminal state is silently skipped.
- **SC-010**: Zero documents in the tree still describe the loop as four phases (PIVS) after the change; every remaining reference reads PIVSA or names Adjust explicitly.

## Assumptions

### Open decisions resolved

The task listed three open decisions. Each was decided here rather than left open; the reasoning is recorded so a later reader can overturn it deliberately.

- **Open decision 1 — does Adjust also run on the job path after the human merges?**
  **Decided: no. Adjust is feature and change only.**
  Reasoning: the job path is a single named skill, a ship, and a human merge — it has no spec, plan, critic, tester, or pr-review, so its evidence base is one report plus a PR. Running Adjust there would create a second adopt-surface with almost no numbers, and job cards already carry their own after-work hooks (`doc-update-after-work`, changelog). Job workers still emit `FRICTION` lines and their cards still feed the weekly roll-up, so nothing about the job path is invisible — it is just not a per-card Adjust trigger. This keeps the stage's gate ownership clean and can be revisited once the roll-up shows the job path concentrating friction.
- **Open decision 2 — where does the learnings log live: per project or in `AiNative/docs/records`?**
  **Decided: per project, at `.ainative/learnings.md` in the managed project's repository (AiNative's own log at `AiNative/.ainative/learnings.md`).**
  Reasoning: learnings are card evidence and belong next to the project's other card-level artifacts, `.ainative/project.yaml` and `AGENTS.md`; they must travel with the repo and be readable by the same worker that reads the rules. `AiNative/docs/records/` holds AiNative's own postmortems and evaluations — methodology-level records, in a repo the runtime mounts read-only, which makes it a bad append target for per-card output. When a finding targets AiNative itself, the proposal becomes a card against the AiNative repo and lands in the appropriate record file then, not at log time.
- **Open decision 3 — does Adjust run in a fresh worker session with the Validation profile, or as a parent step?**
  **Decided: a fresh worker session under the Validation profile, exactly like `critic`, `tester`, and `pr-review`.**
  Reasoning: the executor rule already forbids the parent from executing stages in-process, and the Validation profile is where the reading-and-judging stages already live. A parent step would also put rule proposals in the same context as the merge decision, which is exactly how an auto-applied rule change would sneak in; a separate session keeps the "proposals only" boundary enforceable.

### Further assumptions

- **Document-level change.** This feature is methodology plus adapter documentation. No parser, hook, or dispatcher is built, and no worker loop is wired into the live Hermes install — consistent with the loop's current "target methodology" status. The only artifacts are documents and the spec-kit spec/plan/tasks themselves.
- **The loop document stays the single graph.** Adjust is added to `docs/systems/feature-loop.md` rather than given its own graph document, so there is still one place that says what the loop is.
- **`FRICTION` is additive and non-blocking.** Adding the field to every report contract does not change any existing report parsing; the parent reads the line when present and tolerates its absence on older artifacts. The line does not affect any verdict, gate, or merge decision.
- **Metrics are defined, not instrumented.** The metric set is a definition that Adjust reads and a reviewer can fill in; no collection code is in scope, and any field the runtime cannot supply today is marked as such rather than faked.
- **The roll-up is a card, not a scheduler.** Cadence is documented (weekly); the scheduling mechanism belongs to the harness, so the definition names the cadence and the card shape and leaves the trigger to the control plane.
- **Hermes is the fourth adapter.** The task names "Hermes" alongside the three `docs/agents/*-harness` folders. Hermes is the control plane rather than a spawn wrapper, so its adapter notes live with the harness/runtime documentation (`docs/knowledge/setup/harness.md`), not in a new `docs/agents/hermes-harness/` folder.
- **AiNative stays harness-neutral.** Any mechanic that is specific to a tool, hook, container mount, or database table belongs in that harness's adapter document.
- **Transcripts are optional forever, not "optional for now".** The baseline input set (card numbers plus compact reports) is the contract; the bundle is an enhancement for anomalies.
- **Validator and finding IDs follow existing conventions.** Adjust reuses the `[<gate>: <id>]` style used by `[tester: flow-2]`, `[critic: C1]`, and `[pr-review: C1]` rather than inventing a new namespace.
- **Abandoned cards are in scope.** "Abandoned" is an operator decision on a card, so the card's terminal state is the trigger; no separate mechanism is needed.
- **No migration.** Existing cards without `FRICTION` lines are not back-filled; the assumption that missing means "unknown" covers them.

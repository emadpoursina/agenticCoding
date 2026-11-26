---
name: adjust
description: Turns a finished card's numbers, reports, and FRICTION lines into learnings entries and evidence-backed proposals after a feature or change card reaches a terminal state — merged or closed without a merge — and during the weekly roll-up card.
disable-model-invocation: true
---

# Adjust

Turns a finished card's numbers, reports, and `FRICTION:` lines into learnings entries and evidence-backed proposals. Proposes only; never edits rules, never edits config, never edits the board, and never gates or delays merge or card completion.

Architecture and loop placement: [feature-loop.md](../../systems/feature-loop.md#pivsa-mapping). Model selection: Validation profile ([validation-layer.md#model-selection](../../systems/validation-layer.md#model-selection)).

---

## Inputs

Inputs must be consulted in this priority order:

1. **Hard numbers from the card** — path, terminal state (`merged`, `blocked`, `parked`, `killed`, `abandoned`), `## Metrics` block (loop-back counts per stage, UAT outcome and reasons, tokens, cost, wall time), dispatch and state history.
2. **Compact reports and their `FRICTION:` lines** — every report artifact named on the card, verdict fields, and friction lines, with a count of how many reports carried one.
3. **Raw transcripts, through the harness adapter, only to investigate an anomaly** already visible in (1) or (2). Never the first thing read, never required.

Adjust runs from (1) and (2) alone. Transcript access is an optional drill-down, never a prerequisite. A card with neither reports nor metrics still runs and reports evidence insufficiency.

### Session bundle contract

When investigating an anomaly, Adjust accesses execution records through a neutral session bundle. Adapters map their runtime specifics to these six standard fields:

1. `worker_prompt`: The exact prompt dispatched to the worker process.
2. `worker_transcript`: Worker session transcript file, stream, or database records.
3. `subagent_transcripts`: List of transcripts for subagents or child sessions spawned by the worker.
4. `usage`: Token counts, cost in USD, and turn counts from the harness execution report, or `unknown` where absent.
5. `completeness`: `complete | partial | unavailable` with a one-line reason.
6. `pointer`: Session identifier, directory path, or execution ID passed by the parent to the Adjust dispatch and cited as `transcript:<pointer>`.

**Degrade rule**: A partial or unavailable session bundle allows Adjust to proceed using card data and reports alone, stating that the drill-down was partial; Adjust must never assert a cause from unevidenced or missing transcripts.

---

## Procedure

Execute these eight steps in order:

1. **Confirm the trigger** — Confirm that the card has reached a terminal state (`merged`, `blocked`, `parked`, `killed`, `abandoned`) or is a weekly roll-up card (`STEP: rollup`). If the card is still active, stop with `STATUS: blocked`, emit `ADJUST: blocked`, and report that the card is not in a terminal state (do not invent a run).
2. **Read the numbers** — Read the card's `## Metrics` block and dispatch history. Note which fields are `unknown` or `n/a` and note that absence of data is recorded as unknown, not zero.
3. **Read the reports** — Read every compact report artifact named on the card. Extract verdicts, findings, and `FRICTION:` lines. Record the count of reports seen versus the count of reports carrying a friction line (missing lines mean unknown, never "no friction").
4. **Build candidate observations** — Build one-line candidate observations, each keyed by finding key: `<target-class>/<normalized-target-ref>/<slug>`. Target class must be one of the four closed classes: `project-rules`, `project-config`, `ainative`, `harness`. Group observations by key. Drop any candidate observation that lacks a checkable evidence reference.
5. **Check recurrence** — Read `.ainative/learnings.md` in the project root (create the file on first write if missing). Union the `cards` lists across all entries sharing the key, adding the current card if not already present. Count the number of **distinct cards**.
6. **Decide per finding** — Consult `rule.md`:
   - If recurrence is exactly 1 distinct card ⇒ learning only.
   - If recurrence is ≥ 2 distinct cards ⇒ eligible to become a proposal **only if** an existing rule can be named as the merge target.
   - If no existing rule can be named as the merge target (`merge_target: none`) ⇒ stays a learning, and the report states why no merge target exists.
7. **Write** — Write learnings first by appending new entries to `.ainative/learnings.md`. Then write the proposal artifact to `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` (or `.ainative/adjust/<YYYY>-W<ww>-rollup.md`). Write nothing else.
8. **Report** — Emit the compact report contract. If no findings survived, report `ADJUST: no-findings` with the evidence actually checked listed in `SUMMARY`. On an unresolvable input problem, report `STATUS: blocked`; after three failed attempts, the parent parks and completes the card.

---

## Output

Adjust performs two writes:
1. `.ainative/learnings.md` — append-only findings log.
2. `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` (or `.ainative/adjust/<YYYY>-W<ww>-rollup.md` for roll-up runs).

### Persistent write location and branch lifecycle

No workflow may ever commit to or push a protected base branch (`main` etc.). For **both** post-merge runs and non-merge (`blocked`, `parked`, `killed`, `abandoned`) runs:
- Outputs are written on a fresh, short-lived branch cut from the current base branch (e.g. `adjust/<card-id>`).
- Adjust itself **never commits, stages, pushes, or opens PRs**.
- The **parent** (control plane / orchestrator) commits the written artifacts on that short-lived branch, pushes, and opens a dedicated PR (or attaches the commit to a proposal Change card PR) against the base branch for human review and merge.
- This guarantees that `.ainative/learnings.md` and Adjust proposal artifacts persist across worktree removals and branch deletions, ensuring recurrence counting (step 5) and weekly roll-ups never lose the log.

### Proposal artifact shape

The artifact header contains:
- `flow`: `<FLOW_ID>`
- `path`: `feature | change`
- `terminal`: `merged | blocked | parked | killed | abandoned` (closed_at: `<ISO-8601 UTC>`)
- `evidence`: `card-data[, reports][, bundle:<ref>]`
- `reports seen`: `<n> (with FRICTION: <m>)`
- `learnings appended`: `<n>`

Followed by optional `## Learnings (this run)` and one `## P<n> — <short title>` block per proposal.

Each proposal block MUST contain:
- `finding key`: `<target-class>/<normalized-target-ref>/<slug>`
- `target class`: exactly one of `project-rules`, `project-config`, `ainative`, `harness`
- `target file`: `<path or file-class:...>`
- `merge target`: `<file>#<rule-id-or-heading>`
- `existing rule quote`: `"<verbatim text of the rule being replaced or merged>"`
- `intended edit`: `<description of rewrite or merge; never an append>`
- `evidence`: list of ≥ 1 checkable items (`card:<id>`, `report:<path>#<verdict>`, `metric:<field>=<value>`, `transcript:<pointer>`)
- `cards`: comma-separated list of ≥ 2 distinct cards
- `status`: `pending-change-card`

### Verbatim prohibitions

Adjust:
- MUST NOT edit project rules (`AGENTS.md`), project config (`.ainative/project.yaml`), AiNative skills or system docs, or harness adapters.
- MUST NOT write to the Kanban board; the **parent** files the Change cards from the proposal artifact.
- MUST NOT apply, stage, commit, or ship its own proposals.
- MUST NOT gate, delay, or hold the card completion or its merge.

When a proposal target is inside the read-only AiNative tree, the proposal is filed as a card against the AiNative repo by the parent (never an in-place edit).

When no findings survive, Adjust emits `ADJUST: no-findings` as the explicit empty outcome, listing the evidence that was checked in `SUMMARY` and setting `ARTIFACT: none`.

### Proposal rejection rules

A reviewer rejects a proposal block if any of these hold:
1. Fewer than two distinct cards named in `cards`.
2. No `merge target`, or a `merge target` that does not resolve in the target file.
3. `intended edit` is additive-only (e.g., "add a new rule", "add a section", "create a file").
4. Evidence list is empty or contains only unopenable references.
5. Names two target classes (exactly one is allowed).
6. Target is an AiNative path and asks for an in-place edit of the mounted tree instead of a card against the AiNative repo.

When a proposal is rejected or lacks a merge target, the finding is written to `.ainative/learnings.md` with `status: learning` and the reason is recorded in the report `SUMMARY`. Consult `rule.md` for the recurrence threshold and merge-target test.

---

## Compact report

```text
FLOW_ID: <flow id>
ADJUST: ok | no-findings | blocked
EVIDENCE_USED: card, reports | card, reports, bundle:<ref> | card
LEARNINGS: <count appended, or 0>
PROPOSALS: <none, or one line each: P<n> | target-class | target ref | merge-target-or-none | evidence-ref>
ARTIFACT: <path, or none>
SUMMARY: <one paragraph: what was checked, what survived, what was dropped and why; includes reports seen and friction lines count>
FRICTION: <target-class> | <observation> | <evidence-ref>
STATUS: ok | stuck | blocked
```

Every report ends with a `FRICTION:` line; grammar in `docs/systems/feature-loop.md` § Compact reports — emit exactly `FRICTION: none` when nothing slowed the step down.

---

## STEP: rollup

When dispatched on a weekly roll-up card (`## Path: job`, `## Skill: adjust`, `STEP: rollup`, `## Week: <YYYY-Www>`):

1. **Inputs** — Read all per-card Adjust artifacts (`.ainative/adjust/*-<card>.md`) and card `## Metrics` blocks whose `closed_at` falls in the ISO-8601 week (Mon 00:00 → Sun 23:59 UTC), plus the existing `.ainative/learnings.md`.
2. **Aggregation** — Group friction observations by finding key across all cards in the week. Union card sightings to compute distinct-card recurrence. Rank targets by observation count, displaying both observation counts and distinct-card counts.
3. **Recurring proposals** — Check previous roll-ups or learnings log for proposals whose Change card is still pending or not accepted. List them under `## Recurring, not accepted` with first week and weeks seen; do NOT re-file an identical Change card.
4. **Stage metrics** — Compute average loop-backs (`loops.converge`, `loops.critic`, `loops.tester`, `loops.pr_review`) and UAT failure rate per path. State sample size (`n=`) for every figure and exclude `n/a` stages from the sample.
5. **Gaps** — Note any skipped weeks, cards predating friction reporting, missing metrics, or small sample sizes under `## Gaps`. An empty week produces an empty ranking and an explicit gap note; never invent findings.
6. **Output** — Write `.ainative/adjust/<YYYY>-W<ww>-rollup.md` using the roll-up artifact shape. Same proposal rejection rules apply. Report `ADJUST: ok` with proposals or `ADJUST: no-findings` with the gap reason. The roll-up never blocks, delays, or reorders any other card.

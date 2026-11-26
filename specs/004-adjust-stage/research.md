# Research: Adjust stage (PIVS → PIVSA)

**Feature**: `specs/004-adjust-stage` | **Date**: 2026-11-26 | **Plan**: [plan.md](./plan.md)

All findings are from this repository and from the machine checks recorded in
the task input (`/Users/emad/Projects/playground/agenticCoding/AiNative`); no
external fetch was needed because every decision below is a documentation
policy decision, not a technology selection. Prior art named in the task
(Alderson's JSONL→`CLAUDE.md` proposal mining with human curation, Osmani's
self-improving agents, `entelligence.ai`'s unmeasured rules growth, the
`learnings.md`-separate-from-rules pattern) is used as the *shape* of the
design, not as a citation of implementation detail.

Two items were left deferred by `/speckit.clarify` and are resolved here:
**D1** (loop-back counting granularity) and **D2** (weekly roll-up week
boundary and scheduling owner).

---

## D1 — Loop-back counting granularity (deferred item #1)

**Decision**: A per-card metric field per raising stage, counting **return
dispatches**, with `n/a` for stages a path does not have.

- Fields: `loops.converge`, `loops.critic`, `loops.tester`, `loops.pr_review`.
- **One count = one parent-observed return dispatch** caused by that stage's
  report: `converge → tasks_appended` (re-enters implement), `critic FAIL`
  (`LOOP_BACK: implement`, or `plan` when it parks), `tester FAIL`
  (`LOOP_BACK: implement`/`plan`; change path: FAIL → re-run the change
  worker), `pr-review REQUEST CHANGES` (→ converge on feature, → change worker
  on change).
- **Retries are not loop-backs.** A stage re-run under the stuck policy
  (attempt 2 or 3 of the *same* verdict-less dispatch) is not a loop-back.
  A stage that runs twice and FAILs twice in one card counts **2**.
- **UAT rounds are not a loop-back field.** UAT failures are counted as
  `uat.rounds` and `uat.reasons[]`, because a UAT failure loops back into
  converge/change-worker and would otherwise be double-counted under
  `loops.converge`. To preserve the trail, `uat.reasons[]` entries carry the
  round number (`uat: r2`), so a UAT-caused converge pass is visible in both
  places without inflating `loops`.
- **Change path**: `converge` and `critic` are recorded as `n/a`, never `0`,
  because the path lacks them (feature-loop card-paths table). Roll-up
  aggregation skips `n/a` and reports the sample size, so a change card never
  drags a converge average toward zero.
- **Job path**: the path is `ready → route → one worker → ship` (loop doc card-paths
  job row), so it has no converge, no critic, no tester, no pr-review, and no UAT.
  The block therefore records `loops.converge=n/a`, `loops.critic=n/a`,
  `loops.tester=n/a`, `loops.pr_review=n/a`, and `uat.outcome=not_run` — all four
  loop-back fields are `n/a`, not two. Per-card Adjust does not run on the job
  path (spec § Assumptions), but the Metrics block is still written, so job cards
  contribute numbers (UAT outcome, tokens, cost, wall time) to the roll-up.
- **No-verdict and paused states**: a card abandoned mid-`implement` records
  `loops.<stage>: n/a` for stages that never ran and `0` only where the stage ran
  and returned a non-looping verdict (`PASS`, `converged`, `APPROVE`).

**Rationale**: FR-025 requires the four counts "each attributed to its stage",
and FR-029 requires derivation from board data plus reports. Dispatch history
(a parent-owned fact) plus each report's verdict field gives exactly that, with
no transcript. Counting *return dispatches* rather than *stage runs* survives
retries and resumes, which are the two ways a naive run counter drifts.

**Alternatives considered**:
1. *Count stage runs* (`tester` ran 3× ⇒ 3) — rejected: retries under the stuck
   policy inflate friction that no rule change can reduce, and the number stops
   being comparable between cards.
2. *Single `loops` total* — rejected: FR-025 requires per-stage attribution,
   and the roll-up's "which target accumulates friction" question needs to know
   whether the friction is tester-side or pr-review-side.
3. *Count UAT rounds as `loops.tester`* — rejected: double counts the converge
   pass that a UAT failure triggers, and mixes a human verdict into an agent
   stage's count.

---

## D2 — Weekly roll-up week boundary and scheduling owner (deferred item #2)

**Decision**: **ISO-8601 week (Monday 00:00 → Sunday 23:59, UTC)**, anchored on
the card's terminal-state timestamp; the **control plane (Hermes parent) owns
the trigger**; AiNative owns only the cadence and the card shape.

- **Boundary**: week key `YYYY-Www` (e.g. `2026-W48`). A card belongs to the week
  its **terminal-state timestamp** falls in — the same timestamp that closes its
  `## Metrics` block — not the week Adjust ran and not the week the PR opened.
  Late or resumed Adjust runs therefore never move a card between weeks, and a
  card can never be counted twice.
- **Scope of a roll-up**: exactly its own week. Records that arrive after the
  week closes are picked up by *that* week's roll-up if it has not run yet; once
  a week's roll-up card exists, later records appear as a late-arrivals line
  rather than being folded in silently.
- **Skipped week**: the next roll-up reports the skipped week in its
  `gaps:` line. Nothing is back-filled, and no other card's behavior changes.
- **Owner**: the control plane files one `job` card per week with
  `SKILL: adjust`, `STEP: rollup`, `week: <YYYY-Www>`. The cadence ("one card
  per ISO week, filed no later than the first business day after the week
  closes") is documented in `feature-loop.md`; the scheduler is Hermes's
  business, exactly as the loop's other runtime mechanics are. If the operator
  skips the card, the loop is unaffected (FR-032).
- **Timezone**: UTC, not operator-local. A local boundary would make the same
  card fall in different weeks on two machines and make two roll-ups
  irreconcilable; UTC plus ISO week is deterministic and harness-neutral.

**Rationale**: FR-030 requires a stated cadence and artifact; FR-031 requires a
visible count behind the ranking; FR-032 requires skippability and an
evidence-gap path. Anchoring on the terminal state is the only rule that keeps
the input set closed (a card's week is fixed for its lifetime) and it reuses the
timestamp the metrics block already requires.

**Alternatives considered**:
1. *Calendar month / rolling 7 days* — rejected: rolling windows make consecutive
   roll-ups overlap and double-report the same card; a month is too slow for a
   methodology-level signal (SC-008 expects four roll-ups to be useful).
2. *Anchor on Adjust run time* — rejected: a parked Adjust resumed a week later
   would move the card, so a card's contribution would depend on dispatch luck.
3. *AiNative owns a scheduler* — rejected: the repo holds no runtime; adding one
   would contradict harness neutrality (FR-036) and "Hermes owns runtime".
4. *Operator-local week* — rejected: non-deterministic across hosts (see above).

---

## D3 — Where the stage sits, and the trigger

**Decision**: `adjust` is the fifth state, entered from the card's **terminal
state**, not from a new card state.

- Feature: `… → pr-review → uat → adjust`; change: `… → pr-review → uat → adjust`.
- Non-merging terminal states (blocked, parked, operator-killed, abandoned) also
  dispatch Adjust. A card's terminal state *is* the trigger, so no extra state
  or field is needed (FR-006).
- Job path: no per-card Adjust (spec § Assumptions, open decision 1). Job cards
  still emit `FRICTION` and still carry a `## Metrics` block, so the roll-up
  sees them.

**Rationale**: FR-004/FR-005/FR-006 as clarified. Making Adjust a *sibling* of
the terminal state rather than a *precondition* of it is what makes "never
blocks merge" true by construction: the parent completes the card first and
dispatches Adjust after.

**Alternatives considered**: (a) Adjust before merge — rejected, it would sit on
the merge path; (b) Adjust as a child card of the feature card — rejected, child
cards are the planning output of `tasks.md` and share the card's worktree, which
is removed at merge; (c) Adjust as an in-process parent step — rejected by
FR-007 and the executor rule.

---

## D4 — Skill folder shape and naming

**Decision**: `AiNative/docs/agents/adjust/` with `SKILL.md` (`name: adjust`,
`disable-model-invocation: true` like `critic`/`tester`), `AGENTS.md`, `rule.md`
— copied in shape from `docs/agents/template/` and matching `critic/`.

**Rationale**: FR-001/FR-002 and the README file contract. `disable-model-invocation`
matches the other loop stages so the skill is only dispatched by the parent, not
auto-invoked by a host model.

**Alternatives considered**: extend `learn/` — rejected explicitly (FR-003, name
collision with the `learn` card mode); put it under `docs/systems/` — rejected,
it is a per-card stage with a compact report, i.e. an agent.

---

## D5 — Where Adjust writes: proposal artifact and learnings log home

**Decision**:

| Artifact | Path (project repo) | Writer | Persistence |
|---|---|---|---|
| Learnings log | `.ainative/learnings.md` | Adjust (append only) | copied to base branch by the parent |
| Per-run proposal artifact | `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` | Adjust | same |
| Weekly roll-up artifact | `.ainative/adjust/<YYYY>-W<ww>-rollup.md` | roll-up Adjust run | same |
| Per-card numbers | `## Metrics` block **on the card** | parent, at terminal state | board |

- Adjust writes into the card worktree (the only tree a worker may write).
  The worktree is removed at merge, so the **parent** copies the two `.ainative/`
  artifacts onto the base branch in its existing post-merge base sync (the same
  mechanism used for the onboarding commit), best-effort and non-blocking: if
  it fails, the artifacts are attached to the card and the proposal table is
  also written into each Change card's body by the parent, so no evidence is
  lost and no card is held.
- AiNative's own log is `AiNative/.ainative/learnings.md`; this feature does
  **not** pre-create either file — the skill creates them on first writing.

**Rationale**: FR-024 requires the log be distinct from the rules file; the
clarified output contract requires Adjust to emit an artifact and the parent to
file cards; FR-006 forbids Adjust from holding a card. `.ainative/` is the
existing project-side home for card-level config (`.ainative/project.yaml`), the
repo is mounted read-only only from AiNative's side, and a committed log travels
with the repo so the *next* card's worker can read it — which `docs/records/`
cannot provide (append-only historical records, and read-only when mounted).

**Alternatives considered**:
1. `docs/records/adjust/` — rejected: records are dated, never-rewritten
   history; a learnings log is read-modify-append working memory, and the
   AiNative mount is read-only for the managed project (spec edge case).
2. Board-only (proposal table in the card body) — rejected as the *primary*
   store: FR-023 needs a recurrence count computed across cards without
   re-reading boards by hand, and a log gives one `rg` over one file.
3. A `specs/<flow>/adjust-proposals.md` — rejected: change-path cards have no
   spec directory, so the home would differ per path.

---

## D6 — Metrics and roll-up live inside `feature-loop.md`

**Decision**: define both in `feature-loop.md` (new `## Per-card metrics` and
`## Weekly Adjust roll-up` sections), with the wire formats in
`specs/004-adjust-stage/contracts/metrics-block.md` and `…/contracts/rollup-card.md`.

**Rationale**: spec § Assumptions — the loop document stays the single graph.
Both definitions are short (a field list and a cadence), and splitting them into
new system docs would create a second place that describes the loop.

**Alternatives considered**: `docs/systems/metrics.md` + `docs/systems/roll-up.md`
— rejected for the reason above; if `feature-loop.md` exceeds ~550 lines during
implementation, splitting the *metrics field table* into
`docs/systems/adjust-metrics.md` is the accepted escape hatch, referenced from
the loop document (implementation may take it without a spec change).

---

## D7 — `FRICTION` grammar, target classes, and where it is stated once

**Decision**: one grammar, stated once in `feature-loop.md` § Compact reports:

```text
FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>
FRICTION: none
```

`<target-class>` ∈ `project-rules` (project `AGENTS.md`), `project-config`
(`.ainative/project.yaml`), `ainative` (an AiNative skill or system doc),
`harness` (a harness adapter). The observation is one sentence with `|` replaced
by `/`; the evidence reference is a card id, artifact path, metric, or report id
the parent can check. A clean run emits the exact line `FRICTION: none`; missing
lines mean **unknown**, never "no friction".

Worker skill docs carry a **one-line pointer** ("every report ends with a
`FRICTION:` line — grammar in feature-loop.md § Compact reports"), never a
restatement, so the two cannot drift.

**Rationale**: FR-040 and the clarify answer fix the shape; four classes match
FR-014 exactly, so a friction line maps to a proposal target without
translation. Pointer-only edits are the cheapest way to satisfy FR-041 (no
worker documents a report without it) without creating twelve copies of the
grammar — the drift risk noted in plan § Heuristic risks.

**Alternatives considered**: (a) free-form "friction:" prose — rejected, Adjust
could not group or count it; (b) a fifth class for "tooling/env" — rejected,
every observed friction in this repo's history maps to one of the four (a tool
quirk is a harness adapter issue; a missing input is a skill/doc issue);
(c) restating the grammar per worker — rejected (drift).

---

## D8 — Proposal, finding key, and recurrence mechanics

**Decision**:

- **Finding key**: `<target-class>/<normalized-target-ref>/<slug>`.
  Normalized ref: repo-relative path, no line numbers, no versions; harness
  targets normalize to `harness:<name>`; AiNative skills to `skill:<name>`;
  system docs to `doc:<path>`. Slug: 3–6 kebab words, stable across runs.
- **Recurrence**: count **distinct cards** whose learnings entries share the
  key. Threshold ≥ 2. Two entries from one card count once (FR-020).
- **Promotion gate**: a rule proposal MUST carry `merge_target:` (existing file
  + rule id or heading) and `existing_rule_quote:`. No merge target ⇒ stays a
  learning and the report says why (FR-022).
- **Ids**: run-local `P<n>` proposal ids; findings use `[adjust: A<n>]` in the
  report's `PROPOSALS`/`FINDINGS` line only (never source-refs), matching
  `[tester: flow-2]` / `[critic: C1]` (FR-043).
- **Evidence ref** per proposal: one or more of `card:<id>`, `report:<path>`,
  `metric:<field>=<value>`, `transcript:<path>` (only when a bundle was used).

**Rationale**: the clarify answer fixes the key; the merge-target quote is what
makes "replace or merge, never append" checkable by a reviewer who does not
re-read the run. `existing_rule_quote` is the anti-append proof: if there is no
text to quote, there is no rule to merge into.

**Alternatives considered**: embedding similarity / fuzzy dedupe — rejected: not
auditable and not doc-level; counting entries rather than cards — rejected by
FR-020's "two entries from the same card count once".

---

## D9 — Adjust compact report shape

**Decision**:

```text
FLOW_ID: <flow id>
ADJUST: ok | no-findings | blocked
EVIDENCE_USED: card, reports | card, reports, bundle:<path> | card
LEARNINGS: <count appended, or 0>
PROPOSALS: <none, or one line each: P<n> | target-class | target ref | merge-target-or-none | evidence-ref>
ARTIFACT: <path, or none>
SUMMARY: <one paragraph>
FRICTION: <target-class> | <observation> | <evidence-ref>
STATUS: ok | stuck | blocked
```

`FRICTION` is either that three-field line or exactly `FRICTION: none` — two
forms, no `| none` tail (the contract's single statement is
[friction-line.md](./contracts/friction-line.md)).

`ADJUST: no-findings` is the explicit empty outcome (FR-018) and still carries
`STATUS: ok`. A park is `STATUS: blocked` with the follow-up item named in
`SUMMARY`; the parent records the follow-up and completes the card (clarified).

**Rationale**: keeps the existing `FLOW_ID`/`ARTIFACTS`/`STATUS`/`SUMMARY`
skeleton, adds the one verdict field the parent must branch on, and puts the
proposal list in the report so the parent can file cards even if the artifact
copy fails. `ARTIFACT` (singular, Adjust's own file) is distinguished from
`ARTIFACTS` (files a producing stage changed) to avoid implying Adjust edited
project files.

**Alternatives considered**: reuse `STATUS` as the verdict — rejected: "ok with
an empty body" is exactly the failure mode FR-018 forbids, so the empty outcome
needs its own value.

---

## D10 — Session bundle contract (harness-neutral shape)

**Decision**: AiNative defines the *shape* and the degrade rule; each adapter
defines the *location*:

Bundle contents: `worker-prompt`, `worker-transcript`, `subagent-transcripts[]`,
`usage` (tokens/cost/turns), `completeness: complete | partial | unavailable`
plus a one-line reason. Adjust is pointed at a bundle by a path or identifier
recorded in the proposal's `evidence-ref`, and may only use it to investigate an
anomaly already visible in card data or reports (input priority 3).

Per-adapter mechanics (documented in the adapters, not here in AiNative):

- **Claude Code** (`claude-harness`): session JSONL under the host's
  `~/.claude/projects/<slug>/<session>/`, subagent transcripts as
  `subagents/agent-*.jsonl`; the SubagentStop hook passes
  `agent_transcript_path`. Caveats: the hook can fire before the file is fully
  written, and the wrapper's default isolated mode
  (`--no-session-persistence`, `claude-harness/SKILL.md:108`) means a job may
  leave no transcript at all. `report.json` already carries `sessionId`,
  `numTurns`, `totalCostUsd` (`SKILL.md:237-239`) — enough for the usage part.
- **Cursor** (`cursor-harness`): chats under `~/.cursor/chats`, resumed by
  `sessionId` with the same `--cwd` (`SKILL.md:151`). Caveats: background
  subagent stop events are unreliable, so subagent transcripts may be missing;
  `totalCostUsd` is null when the account does not report it (`SKILL.md:204`).
- **pi** (`pi-harness`): session files under `~/.pi/agent/sessions/<cwd>/`, with
  `--session <path|id>` / `--session-dir <dir>` to point at one
  (`SKILL.md:135-137`). Caveat: `--no-session` leaves no file, so a bundle may be
  unavailable by design.
- **Hermes** (`docs/knowledge/setup/harness.md`): the control plane's own stores
  hold sessions, messages, and per-step runs, plus board task runs, events, and
  comments. Caveats: the session parent link is not populated yet, so worker and
  subagent transcripts cannot be reliably joined today; and the container
  cannot see host-only transcript directories unless they are mounted.

**Rationale**: FR-033–FR-036. Putting the *shape* in one contract and the
*paths* in four adapters is what keeps AiNative harness-neutral while still
giving Adjust a defined drill-down input. The caveats are evidence-based: each
one is a real condition recorded in this repo or in the task's machine check.

**Alternatives considered**: a fifth shared "session-bundle.md" adapter doc —
rejected: it would centralize harness paths in AiNative, the exact thing FR-036
forbids; a mandatory bundle — rejected by FR-010 (Adjust works from the first
two input classes alone).

---

## D11 — Antigravity is deliberately out of the adapter scope

**Decision**: the four session-bundle sections are `claude-harness`,
`cursor-harness`, `pi-harness`, and Hermes (`docs/knowledge/setup/harness.md`),
exactly as FR-033 lists. `antigravity-harness` receives only the `FRICTION` line
in its `worker-contract.md` (it composes worker prompts, so the line must be
there), and an **optional** short session-bundle paragraph may be added if the
implementer can state it truthfully; skipping it costs no FR.

**Rationale**: the task and FR-033 name four, and Antigravity is the default
`SPECKIT_WORKER` in `ready` — a real gap, but inventing its on-disk session
layout without verifying it would be exactly the unevidenced claim the spec
warns against. Recording the gap is better than guessing.

**Alternatives considered**: forcing a fourth paragraph with a guess — rejected;
extending FR-033 to five — rejected (spec is binding, and the gap is visible).

---

## D12 — No new gate, and no scripts

**Decision**: nothing is added to `ready-check.sh`, `task-groomer`, or
`harness.md`'s gate-ownership table. The recurrence threshold and merge-target
rule live only in `docs/agents/adjust/rule.md` (procedure) and are enforced by
the Adjust worker's own verdict. No parser, hook, or collector is written; the
`## Metrics` block is filled by the parent from data it already holds.

**Rationale**: FR-042/FR-043 and the "gate ownership (one gate per concern)"
rule in `harness.md`; task out-of-scope forbids transcript parsers unless trivially
small, and even a trivial parser would need a home outside the docs tree.

**Alternatives considered**: a `ready` check that a learnings entry carries a
finding key — rejected, that is Adjust's check and duplicating it in `ready` is
the exact anti-pattern FR-042 names.

---

## Open items carried into implementation

1. If `feature-loop.md` grows past ~550 lines, split the metrics field table into
   `docs/systems/adjust-metrics.md` (allowed without a spec change; D6).
2. Verify the Antigravity session location before writing its optional paragraph
   (D11); omit rather than guess.
3. Confirm during implementation that no `.cursor/commands/*.md` body needs
   editing — frontmatter `description` only (they are thin wrappers).

No `NEEDS CLARIFICATION` markers remain.

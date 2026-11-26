# Contract: Adjust skill folder and compact report

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-001, FR-002, FR-007, FR-008, FR-009–FR-018, FR-043 | **Plan**: [../plan.md](../plan.md) (W1)

---

## Folder

`AiNative/docs/agents/adjust/` — shape copied from `docs/agents/template/`, sibling of `critic/`, `tester/`, `change/`.

| File | Must contain | Must not contain |
|---|---|---|
| `SKILL.md` | Frontmatter `name: adjust` (matches folder), `description` = WHAT + WHEN in third person, `disable-model-invocation: true`; body: inputs in priority order, the 8-step procedure, output contract, `no-findings` path, compact report | Board mechanics, harness paths, hook names, database tables, any rule-editing instruction |
| `AGENTS.md` | Purpose paragraph, `## When to use` (trigger: a card reached a terminal state, or a weekly roll-up card), `## Inputs`, `## Outputs`, `## Supporting files` table | Duplicated procedure |
| `rule.md` | Must/must-not list, recurrence threshold, merge-target requirement, stop conditions, park behaviour, ID rules | A second copy of the metrics or `FRICTION` grammar (link instead) |

Registered in `AiNative/docs/agents/README.md` agents table:

| Agent | Hermes use | Purpose |
|---|---|---|
| `adjust` | Feature-loop Adjust (after UAT + merge, and on non-merging terminal states) | Turns a finished card's numbers, reports, and `FRICTION` lines into learnings entries and evidence-backed proposals; proposes only |

---

## Inputs (priority order — must be stated in this order in `SKILL.md`)

1. **Hard numbers from the card** — path, terminal state, `## Metrics` block (loop-back counts per stage, UAT outcome and reasons, tokens, cost, wall time), dispatch/state history.
2. **Compact reports and their `FRICTION` lines** — the reports listed on the card, their verdict fields, and the friction lines, with a count of how many reports carried one.
3. **Raw transcripts, through the harness adapter, only to investigate an anomaly** already visible in (1) or (2). Never the first thing read, never required.

Statement that must appear: *"Adjust runs from (1) and (2) alone. Transcript access is an optional drill-down, never a prerequisite."* A card with neither reports nor metrics still runs and reports evidence insufficiency.

---

## Procedure (8 steps, in `SKILL.md`)

1. **Confirm the trigger** — the card is in a terminal state (merged, blocked, parked, killed, abandoned) or is a `STEP: rollup` card. If the card is still active, stop with `STATUS: blocked` and say the card is not terminal.
2. **Read the numbers** — the `## Metrics` block and the state/dispatch history. Note which fields are `unknown`/`n/a` and why that matters.
3. **Read the reports** — every report artifact named on the card; extract verdicts, findings, and `FRICTION` lines; count reports seen vs reports carrying a friction line.
4. **Build candidate observations** — one line each, keyed `<target-class>/<normalized-target-ref>/<slug>` (D8). Group by key. Drop anything with no evidence reference.
5. **Check recurrence** — read `.ainative/learnings.md` (create on first writing). Union the `cards` of entries sharing each key, add the current card if not present. Count **distinct cards**.
6. **Decide per finding** — 1 distinct card ⇒ learning only. ≥ 2 distinct cards ⇒ eligible for a proposal **only if** an existing rule can be named as the merge target. No merge target ⇒ stays a learning, with the reason.
7. **Write** — append learnings entries (`.ainative/learnings.md`), then write the proposal artifact with the header and one block per proposal. Nothing else is written.
8. **Report** — emit the compact report below. `ADJUST: no-findings` when nothing survived, with the evidence actually checked. `STATUS: blocked` on an unresolvable input problem; after three attempts the parent parks and completes the card.

**Hard prohibitions (must be verbatim in `rule.md`)**: Adjust MUST NOT edit
project rules, project config, AiNative skills or system docs, or harness
adapters; MUST NOT write to the board; MUST NOT apply, stage, commit, or ship
its own proposals; MUST NOT gate, delay, or hold the card or its merge.

---

## Output contract

Two writes, both in the card worktree:

| Path | Shape |
|---|---|
| `.ainative/learnings.md` | Append-only entries per [data-model.md § 3](../data-model.md#3-learningsentry) |
| `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` (or `<YYYY>-W<ww>-rollup.md`) | Header + one block per proposal per [proposal-artifact.md](./proposal-artifact.md) |

The **parent** files the Change cards from the artifact and copies both files
onto the base branch (D5). Persistence failure is a follow-up item, never a hold.

---

## Compact report

```text
FLOW_ID: <flow id>
ADJUST: ok | no-findings | blocked
EVIDENCE_USED: card, reports | card, reports, bundle:<ref> | card
LEARNINGS: <count appended, or 0>
PROPOSALS: <none, or one line each: P<n> | target-class | target ref | merge-target-or-none | evidence-ref>
ARTIFACT: <path, or none>
SUMMARY: <one paragraph: what was checked, what survived, what was dropped and why>
FRICTION: <target-class> | <observation> | <evidence-ref>
STATUS: ok | stuck | blocked
```

`FRICTION` has exactly **two** permitted forms (per
[friction-line.md](./friction-line.md), the single statement): the three-field
form above, or the whole line `FRICTION: none`. There is no fourth `| none`
segment — a clean run is the two-token line, not a form with an empty tail.

Field rules:

| Field | Rule |
|---|---|
| `ADJUST` | `ok` = proposals filed; `no-findings` = nothing survived, evidence listed in `SUMMARY`; `blocked` = could not read a required input |
| `EVIDENCE_USED` | Exactly the classes used; `bundle:` only with a pointer |
| `LEARNINGS` | Entries appended this run (0 is valid with `ok`, e.g. a proposal promoted from an older entry) |
| `PROPOSALS` | One line per proposal; `merge-target-or-none` is `none` only for the learning-only case, which must not be listed here — a proposal line with `none` is a defect |
| `ARTIFACT` | `none` only with `ADJUST: no-findings` |
| `SUMMARY` | Must state the report count and the friction-line count (e.g. "9 reports, 7 with FRICTION") — this is how missing lines stay visible |
| `FRICTION` | This run's own friction: either the three-field form or exactly `FRICTION: none`. Usually `none` |
| `STATUS` | Worker status; a park is `blocked`, never `ok` with a note |

---

## Stop conditions (`rule.md`)

| Condition | Behaviour |
|---|---|
| Card not terminal | `ADJUST: blocked`, `STATUS: blocked`; do not invent a run |
| `## Metrics` block missing | Continue on reports; say the numbers were unavailable; never treat as zero |
| No reports and no metrics | `ADJUST: no-findings`, "evidence insufficient", no artifact |
| Finding with no checkable evidence | Learning only; the report says the evidence was dropped |
| Recurrence < 2 distinct cards | Learning only; no proposal |
| No existing rule to merge into | Learning only; the report names why no merge target exists |
| Proposal target inside read-only AiNative | Proposal stands; the parent files it against the AiNative repo |
| Two workers blame each other | Record both frictions, cite both, pick no winner without a number |
| Third attempt fails | `STATUS: blocked` with the park reason; the parent records the follow-up and completes the card |

---

## Identifier rules (FR-043)

- Finding ids use the existing gate style: `[adjust: A1]`, `[adjust: A2]` — in the report's `PROPOSALS`/`FINDINGS` text only.
- Adjust must **not** emit source-refs (`FR-###`, `US#/AC#`, `plan: …`, `Constitution …`) and must not invent PR-review source-refs.
- Proposal ids are `P1`, `P2`, … scoped to one run/artifact; a proposal is referenced as `<artifact>#P<n>`.

---

## Acceptance (checked by TF-2, TF-5, TF-6, TF-9)

Skill folder exists with the three files and the frontmatter name; the inputs
appear in the stated order; the prohibitions are verbatim in `rule.md`; the
report has all nine fields; `ADJUST: no-findings` is documented with an evidence
list; recurrence and merge-target appear in `rule.md` and nowhere else.

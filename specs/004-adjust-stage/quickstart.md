# Quickstart: validating the Adjust stage (PIVS → PIVSA)

**Feature**: `specs/004-adjust-stage` | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

This feature ships **documents**, so "running" it means reviewing the documents
against the acceptance criteria. Everything below is either a `rg`/`grep`
assertion with an expected result, or a tabletop scenario with a stated
conclusion. No runtime, server, model call, or historical board is required.

---

## Prerequisites

- Working directory: the feature worktree root (the directory containing `AiNative/` and `specs/`).
- `rg` (ripgrep) or `grep`; each command below is given in `rg` form — substitute `grep -rn` when `rg` is absent.
- The changed docs from this feature are in the working tree (not necessarily committed).
- Nothing else: no network, no Hermes install, no worker loop. The loop itself is not wired (spec § Assumptions).

```bash
cd "$(git rev-parse --show-toplevel)"   # or the worktree root you were given
git status --porcelain AiNative/        # expect docs/**, CHANGELOG.md, 2 .cursor descriptions
```

Expected: changes limited to the plan's **file allowlist** —
`AiNative/docs/**`, `AiNative/CHANGELOG.md`, and the two `description:`
frontmatter lines in `AiNative/.cursor/commands/{critic,tester}.md` (mandated by
plan W3 / T004). The allowlist has exactly one owner:
[plan.md](./plan.md) § Blast radius. Anything else — `AiNative/scripts/`, a
`*.mjs`/`*.py` parser, a pre-created `.ainative/` file — is a failure (see
TF-11). The `.cursor` bodies are wrappers and must stay untouched.

---

## TF-1 — The loop reads PIVSA, and only PIVSA (SC-010)

```bash
rg -n 'PIVS\b|four phases' AiNative/docs AiNative/CHANGELOG.md
```

**Expected**: matches only in

- `AiNative/docs/systems/agentic-coding.md` (explicitly historical — its own PIVS prose and link text stay),
- `AiNative/CHANGELOG.md` (history, including the rename entry).

Any hit in `feature-loop.md`, `validation-layer.md`, `agentic-system.md`,
`jev/README.md`, `docs/agents/**` (including the `critic`/`tester` `AGENTS.md`
intro lines and the two `SKILL.md` descriptions), `docs/systems/README.md`, or
`.cursor/commands/*.md` is a failure. The heading itself must read
`## PIVSA mapping` with **no** `(PIVS)` suffix — a retained literal is exactly
the match this step forbids.

Then prove the anchor moved cleanly (the heading slug changes from
`#pivs-mapping` to `#pivsa-mapping`):

```bash
rg -n '#pivs-mapping' AiNative/            # expect: no output
rg -n '#pivsa-mapping' AiNative/ | wc -l   # expect: 11 links in 8 files
```

The 11 retargeted links are `docs/systems/agentic-system.md:239`,
`docs/systems/validation-layer.md:3`, `docs/systems/agentic-coding.md:3,6,87`,
`docs/agents/README.md:105`, `docs/agents/critic/AGENTS.md:5`,
`docs/agents/tester/AGENTS.md:5`, `docs/agents/pr-reviewer/AGENTS.md:9`, and
`docs/agents/prd-writer/SKILL.md:467,473`.

```bash
rg -c 'PIVSA' \
  AiNative/docs/systems/feature-loop.md \
  AiNative/docs/systems/agentic-system.md \
  AiNative/docs/systems/validation-layer.md \
  AiNative/docs/systems/jev/README.md \
  AiNative/docs/agents/README.md \
  AiNative/docs/systems/README.md
```

**Expected**: one count per file, all ≥ 1 (zero matches make `rg -c` print `0`
and exit non-zero — check every listed path appears).

---

## TF-2 — Adjust is in the graph, the table, and both paths (FR-037–FR-039, AC-2)

```bash
rg -n 'adjust' AiNative/docs/systems/feature-loop.md
```

**Expected** (read each hit):

| Where | Must say |
|---|---|
| State graph block | `… → uat` followed by `→ adjust` |
| Graph string line | `… → uat → adjust` |
| State table row | `\| adjust \|` — AiNative skill, worker **yes**, runs after `uat`/merge *and* on blocked/parked/killed/abandoned, never gates |
| `feature` card-path row | sequence ends `… → uat → adjust` |
| `change` card-path row | sequence ends `… → uat → adjust` |
| `job` row / notes | the job path has **no per-card Adjust**, and why (one worker + a PR, no spec/plan/critic/tester) |
| PIVSA mapping | `Adjust = adjust` as the fifth phase, with "runs after merge, never gates it" |
| Metrics section | heading present |
| Weekly roll-up section | heading present |

Also check the trigger statement is unambiguous:

```bash
rg -n 'terminal state' AiNative/docs/systems/feature-loop.md
```

**Expected**: a sentence saying Adjust's trigger is the card reaching a terminal
state (merged, or closed without a merge), so no new card state is required.

---

## TF-3 — Every report contract carries `FRICTION`, stated once (FR-040, FR-041, SC-002)

```bash
rg -n 'FRICTION' AiNative/docs/systems/feature-loop.md
```

**Expected**: exactly **one** definition paragraph (grammar, the four target
classes, the `FRICTION: none` default, the missing-line-means-unknown rule),
then one `FRICTION` mention inside each documented report contract — **13**
occurrences in the file in total (1 grammar statement + 12 contract blocks), so
`rg -c 'FRICTION' AiNative/docs/systems/feature-loop.md` prints `13` or more.
Count the occurrences and compare: the contract count and the occurrence count
must differ by exactly one.

The **12** contract blocks are fixed: (1) ready, (2) route,
(3) specify/clarify/plan/tasks/analyze, (4) implement, (5) converge, (6) critic,
(7) tester (feature), (8) tester (change), (9) pr-reviewer, (10) ship,
(11) adjust, (12) job skills. Eleven are worker-emitted; **`ship`'s line is
emitted by the parent** (ship is a parent step), which is how "every worker" and
"12 contracts" hold at the same time. The job-skills block covers skills that
document their own report (`prd-writer`, `project-bootstrapper`,
`proposal-writer`, `learn`, `server-setup`), and the ready block subsumes
`speckit-ready`, whose output *is* the ready report — so ready's `FRICTION:` line
is appended by the **ready worker** as the last line after the unwrapped
`ready-check.sh` stdout (harness-neutral, no script change; `ready-check.sh` is
not modified and stays byte-identical).

```bash
rg -c 'FRICTION' AiNative/docs/agents/*/SKILL.md AiNative/docs/agents/*/AGENTS.md AiNative/docs/agents/*/worker-contract.md
```

**Expected** matches for: `ready`, `route-work`, `critic`, `tester`, `change`,
`learn`, `pr-reviewer`, `prd-writer`, `project-bootstrapper`, `proposal-writer`,
`speckit-ready`, `server-setup`, `speckit-orchestrate`, the four harness
`SKILL.md` prompt templates (`claude-harness` ~line 45, `cursor-harness` ~line 59,
`pi-harness` ~line 31, `antigravity-harness` ~line 56 — their `Report:` bullet is
what hand-written prompts copy), and the `worker-contract.md` of the same four
adapters — **17 worker docs plus 4 prompt contracts = 21 hits**.

The tester inlines the `_skills` fragment
`AiNative/docs/agents/_skills/test-execution/SKILL.md` (~line 72, "Compact report
keeps PASS/FAIL and adds `EVIDENCE: …`"). It is edited by T013 but is **not** in
the glob above (two levels down), so verify it on its own:

```bash
rg -c 'FRICTION' AiNative/docs/agents/_skills/test-execution/SKILL.md   # expect ≥ 1
```

A `_skills/**` fragment never restates the grammar: it is covered through the
skill doc that inlines it (see [contracts/friction-line.md](./contracts/friction-line.md)).

Then confirm no worker restates the grammar (drift check):

```bash
rg -n 'FRICTION: <target-class>' AiNative/docs
```

**Expected**: only `AiNative/docs/systems/feature-loop.md` (the single
statement) and the Adjust skill's own report template.

---

## TF-4 — Harness neutrality, introduced paths only (FR-036, AC-11, SC-006)

```bash
# Only lines this feature ADDS are in scope (SC-006 covers introduced paths;
# the three pre-existing runtime-ownership lines are excluded)
git diff -U0 AiNative/docs/systems AiNative/docs/agents/adjust | rg '^\+' | \
  rg -n '(/opt/data/mnt|state\.db|kanban\.db|~/\.claude|~/\.cursor|~/\.pi|SubagentStop|agent_transcript_path|task_runs)'
```

**Expected**: no output — this change introduces no harness path, hook name, or
database table into the methodology docs.

Baseline, so a new leak stays visible beside the old ones:

```bash
rg -n '/opt/data/mnt' AiNative/docs/systems
```

**Expected**: exactly the three **pre-existing** runtime-ownership lines —
`feature-loop.md:99` (the runtime-ownership bullet), `feature-loop.md:365`
(the "do not duplicate this document into Hermes" anti-pattern), and
`agentic-system.md:196` (the read-only mount note). They are runtime-ownership
statements, not Adjust mechanics; this feature neither removes nor adds to them,
and they are out of scope for SC-006. A fourth hit, or any hit under
`docs/agents/adjust/`, is a failure.

```bash
rg -ni 'session bundle' \
  AiNative/docs/agents/claude-harness \
  AiNative/docs/agents/cursor-harness \
  AiNative/docs/agents/pi-harness \
  AiNative/docs/knowledge/setup/harness.md
```

**Expected**: ≥ 1 hit per location, and each section contains: contents (worker
prompt, worker transcript, subagent transcripts, usage), location, how the parent
points Adjust at it, and ≥ 1 caveat.

Caveat spot-checks (each must be present):

```bash
rg -n 'not fully written|no-session-persistence|no transcript' AiNative/docs/agents/claude-harness
rg -n 'subagent|unreliable|totalCostUsd' AiNative/docs/agents/cursor-harness
rg -n 'no-session|session file' AiNative/docs/agents/pi-harness
rg -n 'mount|parent_session_id|not populated|container' AiNative/docs/knowledge/setup/harness.md
```

---

## TF-5 — Proposals only, and the parent files them (FR-012–FR-018, AC-6)

Read `AiNative/docs/agents/adjust/SKILL.md` § Output and
`AiNative/docs/agents/adjust/rule.md`.

**Expected**:

- [ ] Adjust's writes are limited to `.ainative/learnings.md` and `.ainative/adjust/<…>.md`
- [ ] A verbatim prohibition: it must not edit project rules, project config, AiNative skills/system docs, or harness adapters
- [ ] A verbatim prohibition: it must not write to the board; the **parent** files the Change cards
- [ ] `ADJUST: no-findings` documented, with the evidence that was checked listed
- [ ] An explicit statement that Adjust cannot block, delay, or hold a merge or card completion, and that a park is a follow-up item on a completed card
- [ ] Each proposal requires exactly one target class from the closed four, ≥ 1 checkable evidence ref, ≥ 2 distinct cards, a named merge target, and an `existing rule quote`

---

## TF-6 — Lessons stay apart from rules, checked in one place (FR-019–FR-024, FR-042, AC-8)

```bash
rg -n 'two or more|distinct card|merge target|recurrence' AiNative/docs/agents/adjust/
```

**Expected**: the threshold is **2 or more distinct cards**, counted by finding
key (`<target-class>/<normalized-ref>/<slug>`), with same-card duplicates counted
once; a rule proposal must name the existing rule it replaces or merges into; an
additive-only change is rejected; no merge target ⇒ stays a learning with the
reason stated.

```bash
rg -n 'recurrence|merge target|finding key' AiNative/docs/agents/ready AiNative/docs/agents/task-groomer AiNative/docs/knowledge/setup/harness.md
```

**Expected**: no output (gate ownership — the check lives in exactly one place).

---

## TF-7 — Per-card metrics are derivable without transcripts (FR-025–FR-029, AC-9)

```bash
rg -n '## Metrics|loops:|uat:|boundary:' AiNative/docs/systems/feature-loop.md
```

**Expected**: the block definition with all fields, plus the rules that
`unknown`/`n/a` replace omission, that `closed_at` anchors the roll-up week, and
the closed UAT failure reason set with `other` requiring the operator's words.

Then run **Scenario B** below.

---

## TF-8 — Weekly roll-up (FR-030–FR-032, AC-10)

```bash
rg -n 'ISO|week|roll-up|gaps' AiNative/docs/systems/feature-loop.md | head -40
```

**Expected**: ISO week Mon–Sun UTC, anchored on `closed_at`, control plane owns
the trigger, artifact is a `job` card with `SKILL: adjust` + `STEP: rollup` +
`week: <YYYY-Www>`, ranking prints counts, recurring-unaccepted proposals are
listed rather than re-filed, a skipped week appears in `gaps:`, an empty week
never produces invented findings, and skipping changes nothing else.

---

## TF-9 — Error and edge behaviour is documented (FR-005, FR-011, FR-018, FR-008)

Read the stop-conditions tables in `docs/agents/adjust/rule.md` and
`contracts/adjust-report.md`, then run scenarios **C** and **E** below.

**Expected**, one documented outcome each:

1. A card abandoned before any worker ran ⇒ `ADJUST: no-findings`,
   "evidence insufficient", no proposal artifact, card completes.
2. A card predating `FRICTION` ⇒ missing lines read as **unknown**, never as
   "no friction", and the report says so.
3. Two workers blaming each other ⇒ both frictions recorded and cited, no winner
   picked without a number.
4. A proposal targeting AiNative while the mount is read-only ⇒ filed as a card
   against the AiNative repo, never an in-place edit.
5. Adjust blocked/parks three times ⇒ the card completes, the park is recorded
   as a follow-up item, and the merge is untouched.

---

## TF-10 — Changelog (FR-044, AC-12)

```bash
sed -n '/## \[Unreleased\]/,/## \[/p' AiNative/CHANGELOG.md | rg -n 'Adjust|PIVSA|FRICTION|roll-up|learnings|session bundle'
```

**Expected**: `[Unreleased]` names the new stage, the PIVSA rename, the
`FRICTION` requirement, the metrics definition, the roll-up, the adapter session
bundle notes, and the learnings-vs-rules rule.

---

## TF-11 — No forbidden artifacts (AC-14)

Run from the worktree root (the directory holding `AiNative/`):

```bash
git status --porcelain AiNative/
git diff --stat AiNative/
```

**Expected**: exactly the three entries of the **file allowlist** in
[plan.md](./plan.md) § Blast radius, which is the single owner of "which files
may change" — this check restates nothing, it only runs it:

1. `AiNative/docs/**`
2. `AiNative/CHANGELOG.md`
3. the two `description:` frontmatter lines in
   `AiNative/.cursor/commands/{critic,tester}.md` — **allowed and required**,
   because T004/W3 mandate them; omitting them fails TF-1, so they can never be
   a TF-11 failure

Nothing else appears: no `AiNative/scripts/` change, no `*.mjs`/`*.py` parser, no
pre-created `.ainative/` file or directory, no new file outside the docs tree,
and no `.cursor/commands/*.md` **body** change.

```bash
git diff AiNative/.cursor/commands/ | rg '^[-+]' | rg -v '^(---|\+\+\+)'
```

**Expected**: only `description:` lines — anything else means a wrapper body was
forked.

---

## TF-12 — Operator answers the five questions with zero follow-ups (SC-001)

Give a reader **only** `AiNative/docs/systems/feature-loop.md` and
`AiNative/docs/agents/adjust/`. They must answer, without another file:

1. Where does Adjust run on each path?
2. What may it read?
3. What may it write?
4. Can it block merge?
5. How does a proposal get filed?

**Expected**: all five answered, with the policy in those two places (formats may
be linked). Any "I'd need to check the skill/harness doc for that" on questions
1–5 is a failure.

---

## Tabletop scenarios

Write each outcome down in the PR body (the tester's evidence). No board is
needed; use the shapes from [contracts/](./contracts/).

### Scenario A — a card with friction (US1)

Card `0412`, `feature`, merged after one UAT pass; tester FAILed twice
(`loops.tester=2`) and its second report ended:

```text
FRICTION: ainative | Had to guess which validation command was authoritative because both are listed without priority. | card:0412
```

**Expected documented outcome**: Adjust reads the metrics + reports, sees an
`ainative` friction with evidence `card:0412`, computes the finding key
(`ainative/doc:.ainative/project.yaml/validation-cmd-priority` or
`project-config/.ainative/project.yaml/validation-cmd-priority` — one class, not
both), finds 1 distinct card ⇒ **learning only**, no proposal. The report reads
`ADJUST: ok` with `LEARNINGS: 1`, `PROPOSALS: none`, and states that recurrence
needs a second card.

Now add card `0431` with the same key ⇒ **promoted**: one proposal, target
`project-config`, and a merge target that quotes the existing rule it rewrites.
If no such rule exists, it stays a learning and the report says so — that is the
FR-022 path, not a failure.

### Scenario B — filling the metrics block from board data only (US4, TF-7)

Card `0431`, `change` path, closed `blocked` after tester FAILed once and the
operator abandoned it.

| Field | Fill from | Expected value |
|---|---|---|
| `path` | card | `change` |
| `terminal` / `closed_at` | card | `abandoned` / ISO UTC timestamp |
| `loops.converge` / `loops.critic` | path lacks them | `n/a` / `n/a` |
| `loops.tester` | one FAIL → one re-dispatch, then abandoned | `1` |
| `loops.pr_review` | never reached | `n/a` |
| `uat.outcome` / `rounds` | never shipped | `not_run` / `0` |
| `tokens` / `cost_usd` | harness reports, or not | numbers or `unknown` |
| `wall_time_active` | dispatch timestamps minus park time | duration |
| `boundary` | one line | e.g. "two tester sessions; cost unknown, harness does not aggregate" |

**Expected**: every field fills with zero transcript access. If any field
requires a transcript, the metrics definition fails FR-029.

### Scenario C — no evidence at all (edge case)

Card `0398` abandoned before any worker ran. **Expected**: `ADJUST: no-findings`,
`EVIDENCE_USED: card`, `ARTIFACT: none`, and a `SUMMARY` that says evidence was
insufficient. No Change card filed, and the card is already complete.

### Scenario D — duplicate proposal across weeks (edge case, US5)

The same finding key appears in week W45 and W46 and its Change card is still
`pending`. **Expected**: the W46 roll-up lists it under `Recurring, not
accepted` with both weeks and the card id; it does **not** file a second card.

### Scenario E — Adjust never blocks (FR-006, SC-007)

Adjust parks on attempt three. **Expected**: the merged PR stays merged, the card
completes, and the park is recorded as a follow-up item. Nothing downstream
waits.

---

## Failure signature cheat-sheet

| Symptom | Likely miss |
|---|---|
| `rg 'PIVS\b'` hits `validation-layer.md` or `docs/agents/{critic,tester}` | W3/T004 not applied to linked docs / not complete in the agent docs |
| `rg '#pivs-mapping'` still returns hits | the heading was renamed but the links were not retargeted |
| `rg 'FRICTION'` count in `feature-loop.md` < 13 | a report contract lacks the line |
| `rg '/opt/data/mnt' AiNative/docs/systems` returns 4+ lines | a harness path was added next to pre-existing runtime-ownership lines |
| A worker skill repeats the grammar in full | two statements of one rule (drift) |
| `rg '~/.claude'` hits `docs/systems/**` | harness mechanics leaked (FR-036) |
| Proposal blocks lack `merge target` or `existing rule quote` | FR-021 not enforceable |
| Metrics block omits `n/a` for absent stages | D1 granularity rule lost |
| Roll-up lists a duplicate card for a recurring finding | FR-031 handled as "file again" |
| Changelog entry missing the roll-up or the adapter notes | FR-044 partial |

---

## Definition of done for the tester

1. TF-1 … TF-12 run, with command + output pasted into the PR body.
2. Scenarios A–E answered in writing, each naming the document line that produces
   the outcome.
3. `git status` shows only the plan's file allowlist — `AiNative/docs/**`,
   `AiNative/CHANGELOG.md`, and the two `.cursor/commands/{critic,tester}.md`
   `description:` frontmatter lines — with no `.cursor` wrapper-body change.
4. Report `TESTER: PASS` with `EVIDENCE: specs/004-adjust-stage/` references, or
   `FAIL` with the failing TF id in `FINDINGS`.

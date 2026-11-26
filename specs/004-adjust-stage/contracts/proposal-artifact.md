# Contract: proposal artifact and learnings log

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-012–FR-017, FR-019–FR-024 | **Plan**: [../plan.md](../plan.md) (W1, W6) | **Research**: [../research.md](../research.md) (D5, D8)

Adjust's only writes. Both live under `.ainative/` in the managed project's
repository (AiNative's own copies under `AiNative/.ainative/`). Neither file is
pre-created by this feature.

---

## 1. Proposal artifact

Path: `.ainative/adjust/<YYYY-MM-DD>-<card-id>.md` — date = run date UTC, card id
= board id. Weekly roll-up: `.ainative/adjust/<YYYY>-W<ww>-rollup.md`.

```markdown
# Adjust — card <card-id>

- flow: <FLOW_ID>
- path: feature | change
- terminal: merged | blocked | parked | killed | abandoned  (closed_at: <ISO-8601 UTC>)
- evidence: card-data[, reports][, bundle:<ref>]
- reports seen: <n> (with FRICTION: <m>)
- learnings appended: <n>

## Learnings (this run)

### <target-class>/<normalized-target-ref>/<slug>
- observed: <YYYY-MM-DD>
- cards: <card-id>
- target: <target-class> → <target-ref>
- evidence: <evidence-ref>
- observation: <one sentence>
- status: learning
- recurrence: <distinct card count> (threshold 2)

## P1 — <short title>

- finding key: <target-class>/<normalized-target-ref>/<slug>
- target class: project-rules | project-config | ainative | harness
- target file: <path or file-class:<…>>
- merge target: <file>#<rule-id-or-heading>
- existing rule quote: "<verbatim text of the rule being replaced or merged>"
- intended edit: <what changes, in reviewer-usable terms; a rewrite or merge>
- evidence:
  - card:<id>
  - report:<path>#<verdict>
  - metric:loops.tester=2
- cards: <card-id>, <card-id>
- status: pending-change-card
```

### Field rules

| Field | Rule |
|---|---|
| `reports seen` | Always printed, even when zero. This is the FR-011 guard: a card with no reports cannot look friction-free |
| `learnings` section | Present with every entry this run appended; a run with proposals but no new learnings still prints the section with `none this run` |
| `recurrence` | Count of **distinct cards**, computed per D8; a proposal line requires ≥ 2 |
| `merge target` | Mandatory in a proposal block; `<file>#<rule-id-or-heading>` must resolve to text in that file |
| `existing rule quote` | Verbatim, ≤ 2 lines. No quote ⇒ no merge target ⇒ no proposal |
| `intended edit` | Must describe a replacement/merge. "Add a new section", "add a rule", "create a file" is a rejected proposal (FR-021) |
| `evidence` | ≥ 1 item; each item is openable by a reviewer |
| `status` | `pending-change-card` until the parent files the card; the parent does not edit the block, it records the card id on the card side |

### Rejection rules (a reviewer rejects the proposal if any holds)

1. Fewer than two distinct cards in `cards`.
2. No `merge target`, or a `merge target` that does not exist in the target file.
3. `intended edit` is additive-only.
4. Evidence list empty, or all items unopenable.
5. Two target classes named in one proposal (exactly one is allowed).
6. Target is an AiNative path but the proposal asks for an in-place edit of the
   mounted tree instead of a card against the AiNative repo (FR-017).

---

## 2. Learnings log

Path: `.ainative/learnings.md`. Append-only; never rewritten.

```markdown
# Learnings

Evidence collected by Adjust. A finding becomes a rule only after it recurs on
two or more distinct cards and names an existing rule it replaces or merges into.
The rules file is the decision; this file is the evidence.

## <target-class>/<normalized-target-ref>/<slug>

- observed: 2026-11-26
- cards: 0412, 0431
- target: ainative → skill:critic
- evidence: report:specs/002-agentic-validation/critic.md#FAIL, card:0412
- observation: Critic plan review repeatedly flagged criteria with no proof type.
- status: promoted
- promoted-by: .ainative/adjust/2026-11-26-0431.md#P1
```

| Rule | Detail |
|---|---|
| One `## ` block per key | A second sighting appends its card to `cards` and bumps `observed`; it does not add a block |
| `status` values | `learning` \| `promoted` \| `superseded` |
| `promoted-by` | Artifact path + proposal id; required when `promoted` |
| Supersession | A later key that replaces an earlier one sets the earlier block to `superseded` and links forward; the old lines stay |
| No rules here | A rule text never lives in this file; the log is evidence (FR-024) |
| Distinction from rules file | The log carries observations + evidence; the rules file (`AGENTS.md` or an AiNative doc) carries the decision |

---

## 3. Canonicalization table (finding keys)

| Target | `normalized-target-ref` | Example key |
|---|---|---|
| Project `AGENTS.md` | `AGENTS.md` | `project-rules/AGENTS.md/testing-section` |
| `.ainative/project.yaml` | `.ainative/project.yaml` | `project-config/.ainative/project.yaml/validation-cmds` |
| AiNative skill | `skill:<name>` | `ainative/skill:critic/proof-type-gap` |
| AiNative system doc | `doc:<path>` | `ainative/doc:systems/feature-loop.md/friction-missing` |
| Harness adapter | `harness:<name>` | `harness/harness:claude-harness/no-transcript` |

Normalization: lowercase refs except paths as-is; no line numbers; no versions;
no dates; slug is 3–6 kebab words describing the *observation*, stable across
runs (rewording the observation must not create a second key — keep the slug
descriptive of the finding, not of the card).

---

## 4. Who writes what

| Artifact | Writer | When |
|---|---|---|
| Proposal artifact | Adjust worker | end of the Adjust step |
| Learnings log | Adjust worker | step 7, before the artifact |
| Change card | **parent** | after reading the report; one per proposal line |
| Card `## Metrics` block | **parent** | when the card reaches its terminal state, before Adjust is dispatched |
| Base-branch copy of `.ainative/adjust/*` and `learnings.md` | **parent** | in the existing post-merge base sync; best-effort, never blocking |

If the base-branch copy fails, the artifact stays attached to the card and the
Change card bodies carry target + evidence + intended edit, so no proposal is
lost and no card is held.

---

## Acceptance (checked by TF-5, TF-6)

- Artifact path, header fields, and the six rejection rules appear in
  `adjust/SKILL.md` + `rule.md` (or a sibling file in the folder, linked one
  level deep).
- The learnings block shape and the canonicalization table appear once, in the
  skill folder; `feature-loop.md` links to them instead of restating them.
- The proposal shape requires exactly one target class, ≥ 1 evidence item, ≥ 2
  distinct cards, a merge target, and an `existing rule quote`.

# Rules — Adjust agent

Constraints and promotion criteria for the Adjust stage. Architecture: [feature-loop.md](../../systems/feature-loop.md#pivsa-mapping).

## Must

- Enforce recurrence threshold: a finding becomes eligible for a rule proposal only when it recurs on **two or more distinct cards** (counted by finding key `<target-class>/<normalized-target-ref>/<short-slug>`). A card listed twice counts once.
- Require merge target: every rule proposal MUST name `merge target: <file>#<rule-id-or-heading>` and quote the existing rule verbatim (`existing rule quote`).
- Reject additive-only edits: an intended edit that only adds a rule, section, or file is rejected by review and must not be proposed.
- Fall back to learning: if a finding lacks a merge target or has recurrence < 2 distinct cards, it MUST stay a learning in `.ainative/learnings.md` and the report must state why.
- Check gate ownership: recurrence thresholds and merge-target tests live only in this file and the Adjust skill; they are not duplicated into `ready`, `task-groomer`, or install gates.
- Require evidence: every proposal block MUST contain ≥ 1 checkable evidence reference (`card:<id>`, `report:<path>#<verdict>`, `metric:<field>=<value>`, or `transcript:<pointer>`).
- Use gate finding IDs: findings in report text use `[adjust: A1]`, `[adjust: A2]`, matching validator conventions.
- Proposal IDs: scoped to the run as `P1`, `P2`, … and referenced as `<artifact>#P<n>`.
- Propose only: all proposals are written to the proposal artifact for the parent to file as Change cards.

## Must not

- MUST NOT edit project rules (`AGENTS.md`), project config (`.ainative/project.yaml`), AiNative skills or system docs, or harness adapters.
- MUST NOT write to the Kanban board; the **parent** files Change cards from the proposal artifact.
- MUST NOT apply, stage, commit, or ship its own proposals. For both post-merge and non-merge runs, outputs go on a fresh short-lived branch cut from the current base, and the parent commits and ships them via PR; no workflow may commit to or push a protected base branch (see [SKILL.md](./SKILL.md#persistent-write-location-and-branch-lifecycle)).
- MUST NOT gate, delay, or hold the card completion or its merge.
- MUST NOT emit source-refs (`FR-###`, `US#/AC#`, `plan: …`, `Constitution …`) and must not invent PR-review source-refs.
- MUST NOT propose an in-place edit of the mounted AiNative tree when a proposal targets AiNative; the parent files a card against the AiNative repo instead.
- MUST NOT invent findings or speculate on causes when evidence is insufficient or transcripts are missing.

## Stop conditions

| Condition | Behaviour |
|---|---|
| Card not terminal | `ADJUST: blocked`, `STATUS: blocked`; do not invent a run |
| `## Metrics` block missing | Continue on reports; state that numbers were unavailable; never treat missing as zero |
| No reports and no metrics | `ADJUST: no-findings` with "evidence insufficient"; no artifact written |
| Finding with no checkable evidence | Downgrade to learning only; state in report that uncheckable evidence was dropped |
| Recurrence < 2 distinct cards | Keep as learning only; no proposal |
| No existing rule to merge into | Keep as learning only; report states why no merge target exists |
| Proposal target inside read-only AiNative | Proposal stands; the parent files it against the AiNative repo |
| Two workers blame each other | Record both frictions, cite both, pick no winner without a number |
| Third attempt fails | `STATUS: blocked` with park reason; parent records follow-up on completed card and merge is untouched |

## Learnings log and finding keys

The learnings log lives at `.ainative/learnings.md` in the managed project (AiNative's own at `AiNative/.ainative/learnings.md`). It is strictly append-only, never rewritten in place, and distinct from the rules file: the log is evidence, the rules file (`AGENTS.md` or an AiNative doc) is the decision. Persistent write location and PR shipping lifecycle are governed by [SKILL.md](./SKILL.md#persistent-write-location-and-branch-lifecycle).

### Format

Each sighting or status change is appended as a new dated entry at the bottom of the file:

```markdown
### <YYYY-MM-DD> — <key>
- card: <card-id>
- target: <target-class> → <target-ref>
- evidence: <evidence-ref>[, <evidence-ref>...]
- observation: <one sentence>
- status: learning | promoted | superseded
- promoted-by: <artifact>#P<n> (when status is promoted)
- supersedes: <YYYY-MM-DD>#<key> (when status is superseded)
```

- Truly append-only: existing entries are never edited or rewritten in place.
- When a finding recurs on another card, a new dated sighting entry for `<key>` is appended with the new card ID and evidence.
- Recurrence is computed by scanning `.ainative/learnings.md` and unioning all card IDs across appended entries sharing the same `<key>` to count distinct cards.
- Supersession appends a new entry marking `status: superseded` with a forward link; older entries remain unmodified.
- The log never carries rule text; it carries observations and evidence.

### Canonicalization table

| Target | `normalized-target-ref` | Example key |
|---|---|---|
| Project `AGENTS.md` | `AGENTS.md` | `project-rules/AGENTS.md/testing-section` |
| `.ainative/project.yaml` | `.ainative/project.yaml` | `project-config/.ainative/project.yaml/validation-cmds` |
| AiNative skill | `skill:<name>` | `ainative/skill:critic/proof-type-gap` |
| AiNative system doc | `doc:<path>` | `ainative/doc:systems/feature-loop.md/friction-missing` |
| Harness adapter | `harness:<name>` | `harness/harness:claude-harness/no-transcript` |

Normalization rules:
- Lowercase references, except file paths as-is.
- No line numbers, no versions, no dates in refs.
- Slug is 3–6 kebab-case words describing the observation (stable across runs and cards).

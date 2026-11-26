# Contract: `FRICTION` line

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-011, FR-040, FR-041, FR-014 | **Plan**: [../plan.md](../plan.md) (W4, W5)

The single friction-reporting field every worker adds to its compact report.
Adjust's second input class, after card numbers.

---

## Grammar

```text
FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>
```

Clean run:

```text
FRICTION: none
```

`none` is the **entire** line — no pipes, no trailing text — and it is what a
run with nothing to report emits. Omitting the line is a report defect; the
line is required, its content is not.

### `<target-class>` (closed set, exactly four)

| Value | Means | Maps to proposal target |
|---|---|---|
| `project-rules` | The managed project's `AGENTS.md` | FR-014 class 1 |
| `project-config` | The managed project's `.ainative/project.yaml` | FR-014 class 2 |
| `ainative` | An AiNative skill (`docs/agents/<name>/`) or system doc (`docs/systems/<name>.md`) | FR-014 class 3 |
| `harness` | A harness adapter (`docs/agents/*-harness/`, or the Hermes runtime doc) | FR-014 class 4 |

A friction line's class is a *hint for Adjust*, not a verdict: Adjust decides
whether the observation survives as a finding.

### `<one-sentence observation>`

- One sentence, ≤ 30 words, past tense, no `|` character (use `/` instead).
- Says what slowed the step down or forced a guess, not what the worker wishes
  the rule said. "Had to guess the validation command because
  `.ainative/project.yaml` lists two, one of which fails" — not "project.yaml
  should be clearer".
- No speculation about cause when the worker did not investigate it.
- Names the other party when two workers disagree; the worker must not resolve
  the disagreement by asserting fault.

### `<evidence-reference>`

Anything the parent can open without asking the worker:
a card id, a path (`specs/002-agentic-validation/plan.md`), a report artifact
id (`tester#r2`), a metric (`loops.tester=2`), or an error line
(`ready-check.sh: case 18`). Vague references (`"docs"`, `"the spec"`) are a
defect: Adjust cannot cite them as evidence and will drop the observation.

---

## Where the line is required

**Stated once** in `docs/systems/feature-loop.md` § Compact reports, with the
grammar, the four classes, the `none` default, and the missing-line rule. Every
report contract in that section then carries the token — one line each, no
restatement of the grammar:

1. ready (`READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE`, `CHECKS`, `FIXES`; the ready worker appends its `FRICTION:` line **after** the unwrapped `ready-check.sh` stdout — the script is not touched, so the contract and the script stay in step with `docs/agents/ready/AGENTS.md` § Output and `speckit-ready/SKILL.md` § Report, which are authoritative for these fields and list `WORKER`/`WORKTREE`; the field list here is illustrative of order, not a second definition)
2. route (`ROUTE`, `SKILL`, `SKILL_PATH`, `WHY`)
3. specify / clarify / plan / tasks / analyze (`FLOW_ID`, `ARTIFACTS`, `STATUS`, `SUMMARY`, plan `ANALYZE`)
4. implement (`IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`, `SUMMARY`)
5. converge (`CONVERGE_OUTCOME`, `FINDINGS`, `FINGERPRINT`, …)
6. critic (`CRITIC`, `LOOP_BACK`, `FINDINGS`, `SUMMARY`)
7. tester, feature path (`TESTER`, `LOOP_BACK`, `EVIDENCE`, `FINDINGS`, `SUMMARY`)
8. tester, change path (`TESTER`, `TESTS`, `FINDINGS`, `SUMMARY`)
9. pr-reviewer (`VERDICT`, `CRITICAL_COUNT`, `CRITICALS`, `REPORT`, `SUMMARY`)
10. ship (`SHIP`, `PR`, `WALKTHROUGH`, `EVIDENCE`, `SUMMARY`) — the parent emits
    `FRICTION: none` unless a harness or tooling friction occurred
11. adjust (`ADJUST`, `EVIDENCE_USED`, `LEARNINGS`, `PROPOSALS`, `ARTIFACT`, `SUMMARY`)
12. job skills (whatever report the named skill defines — `STATUS`, `SUMMARY`,
    files changed at minimum)

**Worker-side pointers** (one line each, never the grammar): `ready`,
`route-work`, `critic`, `tester`, `change`, `learn`, `pr-reviewer`, `prd-writer`,
`project-bootstrapper`, `proposal-writer`, `speckit-ready`, `server-setup`, and
the worker instruction in `speckit-orchestrate` — 13 documents. `speckit-ready`
is covered on the contract side by item 1 (its output *is* the ready report) and
`server-setup` by item 12 (a job skill that documents its own report), so the
sweep and the contract list agree. Harness adapters that compose the worker
prompt carry the same one-line requirement in **two** places each — the
`worker-contract.md` (`claude-harness`, `cursor-harness`, `pi-harness`,
`antigravity-harness`) *and* the `Report:` bullet of each adapter's `SKILL.md`
(`claude-harness/SKILL.md:45`, `cursor-harness/SKILL.md:59`,
`pi-harness/SKILL.md:31`, `antigravity-harness/SKILL.md:56`) — because a
hand-written worker prompt is copied from the `SKILL.md` template, so
contract-only coverage would let a prompt drop the line. That makes **17 worker
docs plus 4 prompt contracts = 21** docs carrying the token.

A `_skills/**` fragment is **not** a 22nd document: the tester's inlined
`docs/agents/_skills/test-execution/SKILL.md` (~line 72) gains the pointer line
because it states the compact-report shape the tester carries, but it is covered
through the skill doc that inlines it and sits outside the
`docs/agents/*/SKILL.md` glob, so TF-3 checks it by path. Same rule for any other
`_skills` fragment: covered by its owning doc, never counted twice.

**Count, stated once**: twelve contract blocks (the twelfth is the job-skills
line) ⇒ **13** `FRICTION` occurrences in `feature-loop.md` (one grammar statement
+ twelve blocks). Eleven blocks are worker-emitted; item 10 (`ship`) is
**parent**-emitted, because ship is a parent step, not a worker — that is how
FR-040's "every worker" and the 12-contract count stay consistent.

---

## Missing-line rule

An absent `FRICTION` line (card predates this change, partial report, abandoned
card) means **unknown**, never "no friction". Adjust must record the count of
reports seen and the count that carried the line, and must not conclude
"friction-free" from an absence (FR-011).

## Non-goals

- The line never changes a verdict, a loop-back, a gate, or a merge decision.
- The line is not a severity scale: no `critical`/`minor`. Severity belongs to
  critic/tester findings.
- The line is not free-form prose to be parsed by tooling; a human or Adjust
  reads it. No script in this change parses it.

---

## Acceptance (checked by TF-3)

- `rg -n 'FRICTION' AiNative/docs/systems/feature-loop.md` shows exactly one
  grammar paragraph plus one mention inside each of the 12 contract blocks —
  **13** occurrences in total (1 + 12; the twelfth block is the job-skills line).
- Every worker doc that describes a report contains the token — the 13 docs
  listed above (eleven worker folders plus `speckit-ready` and `server-setup`),
  the four harness `SKILL.md` prompt templates, and the four `worker-contract.md`
  files (17 + 4 = 21), plus the tester's inlined `_skills/test-execution`
  fragment checked by path — and none of them repeats the grammar.
- The four-value class set is byte-identical wherever it appears (loop doc,
  Adjust skill, adapters).

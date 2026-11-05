# Jev for LOOP_BACK classification

**Date:** 2026-11-05
**Status:** Queued
**Category:** model

## Hypothesis

After a critic or tester FAIL, Jev can supply the judgments that decide the loop-back target, and code can make the decision from them. The result should match the current LOOP_BACK rule at least as often as the current LLM does, and its probabilities can drive a park-for-human band. Phase: Validation. Part of the system: Model (new judgment use) and Agents (critic/tester output contract).

Scope is this one decision only. Jev answers judgments. It does not choose the loop, write code, plans, or critic prose.

## Source

- Jev announcement: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Official Jev skill guidance: [_skills/typesafe-ai/SKILL.md](../../agents/_skills/typesafe-ai/SKILL.md) (TypeSafe's file, unmodified).
- Live docs: https://docs.typesafe.ai (primitives, confidence, models).

## Design

Follows the official guidance: judgments from Jev, decisions in code. The reusable spec is [loop-back.yaml](../../systems/jev/loop-back.yaml), with the method in [systems/jev/README.md](../../systems/jev/README.md). The draft dataset is [jev/loop-back/cases.yaml](./jev/loop-back/cases.yaml); its labels are proposed and need human review before use.

### Questions (Noul, one per judgment, asked per finding)

Each question is a single judgment, phrased so that yes is the answer that matters. Both can be true at once, so they are two Nouls, not one Choice.

- `plan_defect`: a specific criterion or test flow from the plan is wrong, missing, or untestable. General concerns do not count.
- `code_defect`: code or a test does not do what the plan's criteria specify.

Exact wording lives in [loop-back.yaml](../../systems/jev/loop-back.yaml) and is the only copy used for the run.

### Truth table (code, not Jev)

`high` means probability at or above 0.7, `low` means at or below 0.3. Rows are checked in order.

| plan_defect | code_defect | Outcome |
|---|---|---|
| high | any | `plan` (mixed or plan-level findings go to plan, matching the existing rule) |
| low | high | `implement` |
| otherwise (including any unsettled value) | | `park` (a person decides) |

Thresholds 0.7 and 0.3 are the starting values from the Noul guidance. They are frozen only after the evaluation, not tuned on the test cases.

### State

Jev sees only what a person would need to judge the finding:

- `FLOW_ID` and the report type (critic or tester).
- The acceptance criteria and test flow the finding refers to, copied from the plan artifact. Without this, Jev cannot judge `plan_defect`.
- The finding line (`ID | severity | file:line | summary`) and the code at that location, when the finding cites one.
- No raw logs, chat history, or unrelated files.

Questions are answered independently, so each one carries the context it needs in the state or its own instructions.

### Request

- `model`: `jev-1.14.0`, pinned for the evaluation. Record it with every run. Do not use `jev-latest` for evals, since the alias moves.
- One request per finding, with both Nouls in it, so the state is sent once.

## Test plan

- [ ] Build a labeled set of 30–50 cases. Each case is one finding from a critic or tester report, with the plan context and the code it cites, plus a human label (`plan`, `implement`, or `park`) and a one-line reason.
- [ ] Sources, in order of preference:
  1. Real critic or tester FAIL reports from enrolled projects, if any exist. None are in this repo yet.
  2. Synthetic cases written from the report formats, reviewed by a human before labeling.
  3. Replays of past failures, if they can be reconstructed from git history.
- [ ] Include negative and boundary cases: findings that are neither plan nor code problems, and findings that are both.
- [ ] Run the baseline: the current LLM judgment on the same cases.
- [ ] Run the Jev design on the same cases, with the truth table applied in code.
- [ ] Record each request payload, the returned probabilities, latency, and token usage (`usage`), so any result can be rerun.
- [ ] Check the wording on a held-out subset the questions were not tuned on.
- [ ] Run the smoke test in [systems/jev/README.md](../../systems/jev/README.md#smoke-test) first: Phase 1 (draft cases, no project data), then Phase 2 (3–5 real findings, after operator approval).

### Success criteria (set before running)

- Agreement with the human label is at least the baseline's agreement.
- Cases that land in `plan` or `implement` (not `park`) are at least 95% correct.
- Park rate is no more than 10 points above the labeled park share (7 of 30 in the draft set, about 23%), so the human load stays manageable.
- No failed calls counted as answers. A failed call is an error, not a `no`.
- Median latency under 500 ms.

## Results

_Fill after testing._

| Run | Date | Model | Cases | Agreement (Jev) | Agreement (baseline) | Park rate | Notes |
|-----|------|-------|-------|-----------------|----------------------|-----------|-------|
| 1 | 2026-11-05 | jev-1.14.0 | 30 synthetic | 13/30 (43%) | not run | 53% (16/30) | Pipeline PASS: 30/30 accepted, 0 errors, model echoed as jev-1.14.0, 60/60 probabilities. Labels unreviewed (`reviewed_by: null`), so agreement is informational. `plan_defect` does not discriminate (6 of 13 code defects score ≥0.7), so the `implement` row was unreachable for them. Park rate misses the ≤33% limit. Median latency 1,185 ms exceeds 500 ms. Details: [jev/loop-back/phase1-run1.md](./jev/loop-back/phase1-run1.md). |

### Summary

**Run 1 (Phase 1 smoke test, 2026-11-05, spec v1 draft, `jev-1.14.0`, 30 synthetic cases).**

- **Pipeline: pass.** All 30 requests were accepted with 0 errors, every response echoed `jev-1.14.0`, and all 60 judgments returned a probability.
- **Decision quality: weak.** Agreement with the unreviewed draft labels was 13/30 (43%), and the park rate was 53%.
- **Cause:** `plan_defect` doesn't separate code defects from plan defects. 6 of 13 code defects score ≥0.7 and go to `plan`. No code defect scores ≤0.3, so the `implement` row was almost unreachable. `code_defect` works as intended.
- The 0.7/0.3 bands and the truth table stay unchanged. The problem is the judgment, not the table.

**Next steps, in order:**

1. A human reviews the 30 labels and sets `reviewed_by` in [cases.yaml](./jev/loop-back/cases.yaml).
2. The operator decides whether to reword `plan_defect`. If so, bump [loop-back.yaml](../../systems/jev/loop-back.yaml) to v2 and rerun Phase 1.
3. Build a baseline harness for the current LOOP_BACK rule and run it on the same cases.
4. Phase 2: 3–5 real findings, with content approved by the operator and expectations written before any call. `breuer` and `zharfa` have no critic or tester reports yet, so those must be collected first.

## Verdict

**Adopted** / **Rejected** / **More testing needed**

If adopted, where it was promoted:

- [ ] [agentic-system.md](../../systems/agentic-system.md) — Model table, and the profile rule amended for this one decision
- [ ] [validation-layer.md](../../systems/validation-layer.md) — LOOP_BACK judgments and truth table
- [ ] [feature-loop.md](../../systems/feature-loop.md) — compact report fields (`LOOP_BACK_SOURCE`, plus the two judgment values)
- [ ] [decisions/](../decisions/) — ADR for the profile-rule change
- [ ] Other: _link_

If rejected, why not worth another look (or when to re-open).

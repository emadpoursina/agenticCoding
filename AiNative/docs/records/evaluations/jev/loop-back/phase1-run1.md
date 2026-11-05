# Jev `loop-back` — Phase 1 smoke test results

**Run:** 2026-11-05, live API, `POST /v1/systemone`
**Spec:** `loop-back` v1, `draft`, pinned `jev-1.14.0` (`sha256 9ced66e7…26c5c8`)
**Cases:** 30 synthetic (`dataset_version 1`, `reviewed_by: null`, `sha256 fb19cfaf…0ec9dc3`)
**Runner:** `/opt/data/mnt/workspace/jev-eval/run_smoke.py`, artifacts in `runs/live-phase1/`

> Promoted from `scratch/PHASE1-RESULTS.md`. The runner and raw artifacts (`results.jsonl`, `payloads.json`) were on the run host under `/opt/data/mnt/workspace/jev-eval/`, which does not exist on this machine; they are not in the repo.

## Pipeline result — PASS

| Criterion | Result |
|---|---|
| Every request accepted | yes, 30/30 (0 retries) |
| Response `model` equals pinned model | yes, `jev-1.14.0` on all 30 |
| Every judgment returned a probability | yes, 60/60 |
| Every case produced an outcome in `outcomes` | yes |
| No failed call counted as an answer | yes, 0 errors |
| Payload and response logged per case | yes, `results.jsonl` + `payloads.json` |

Cost: 13,290 input tokens, 1,200 output tokens, **$0.000558**. Median latency **1,185 ms**.

Note: `GET /v1/models` lists only aliases (`jev-latest`, `jev-preview`); `jev-1.14.0` is not listed
but was accepted and echoed back as the response model on every call.

## Decision result — weak on this set (informational, labels unreviewed)

| | count |
|---|---|
| Agreement with draft labels | **13 / 30 (43%)** |
| Outcomes | plan 13, park 16, implement 1 |
| Labels | implement 13, plan 10, park 7 |
| Park rate | 53% (gate limit: label share +10 pts ≈ 33%) |

Confusion (label → outcome):

| label \ outcome | plan | implement | park |
|---|---|---|---|
| plan (10) | 7 | 0 | 3 |
| implement (13) | 6 | 0 | 7 |
| park (7) | 0 | 1 | 6 |

## Diagnosis: `code_defect` discriminates, `plan_defect` does not

| label group | `plan_defect` mean | ≥0.7 | `code_defect` mean | ≥0.7 |
|---|---|---|---|---|
| plan (10) | 0.81 | 7 | 0.66 | 6 |
| implement (13) | 0.70 | 6 | 0.96 | 13 |
| park (7) | 0.12 | 0 | 0.36 | 1 |

`code_defect` behaves as intended: all 13 code defects are high, parks are mostly low.

`plan_defect` tracks "this is a real defect", not "the plan is wrong":

- 6 of 13 pure code defects score `plan_defect ≥ 0.7` (LB-01 0.86, LB-06 0.77, LB-15 0.80,
  LB-19 0.72, LB-21 0.82, LB-25 0.92), which row 1 sends to `plan`.
- The other 7 code defects land `unsettled` (0.45–0.68), which can only reach `otherwise` → `park`.
- **No `implement`-labeled case scored `plan_defect ≤ 0.3`**, so the `implement` row was structurally
  unreachable for them. The single `implement` outcome in the run came from LB-29 (an environment
  case labeled `park`: plan 0.12, code 0.70), i.e. the one case where the code row fired.

So the park rate is not caution, it is the shape of the first judgment: with `plan_defect` rarely
low, the truth table cannot reach `implement`. Loosening row 2 to `plan_defect: not high` would send
mixed findings to implementation, which the recorded rule forbids — the judgment, not the table,
is what needs work.

## Caveats

- Labels are the drafter's proposals (`reviewed_by: null`); a human may agree with some mismatches.
- Cases are synthetic and were not used to tune the wording — so this is a first signal, not an
  accuracy evaluation, and the AiNative method says not to tune on them.
- No baseline (current critic/tester LOOP_BACK rule) has been run on these cases yet.
- Median latency 1,185 ms exceeds the record's 500 ms success criterion.

## Recommended next steps

1. Human review of the 30 labels; set `reviewed_by` before treating them as ground truth.
2. Reword `plan_defect` so it asks only about the criterion itself, with an explicit false case
   ("the criterion is clear and the code simply does not follow it → false"), bump the spec to v2,
   rerun Phase 1. Do not move the 0.7/0.3 bands on this evidence.
3. Phase 2 needs 3–5 real findings with operator-approved content and expectations written before
   the call. `breuer` and `zharfa` have no critic/tester reports, so that step must run first.
4. Build the baseline harness before the evaluation gate, so "agreement ≥ baseline" is measurable.

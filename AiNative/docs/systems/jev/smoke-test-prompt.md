# Instruction: run the Jev loop-back smoke test

Give this file to a coding agent in any harness. It is self-contained: the agent needs no other context. The human operator approves the run before the first request.

## Goal

Check that the pipeline works: send every case in a labeled dataset to Jev, apply the decision spec's rules, and report the results. This is **not** an accuracy evaluation. Do not tune anything.

## Scope

- Run **only** the 30 synthetic cases in `cases.yaml`. They contain no project data.
- Do **not** send any code, plan, ticket, or log from a real project.
- Do **not** change any file in the AiNative repo. Do not commit results.

## Inputs (read these first)

From the AiNative repo root:

- Spec (questions, bands, truth table): `docs/systems/jev/loop-back.yaml`
- Cases (inputs and expected labels): `docs/records/evaluations/jev/loop-back/cases.yaml`
- Contract and pass criteria: `docs/systems/jev/README.md` → "Runner contract" and "Smoke test"

## Setup

1. Keep the API key in the harness's configured environment. Never print it, log it, or write it into a file, a script, or the repo.
2. Check network access to `https://api.typesafe.ai`.
3. Ask the operator to confirm the budget. The 30 cases are roughly 30k input tokens total. At $0.042 per million input tokens, that is well under a cent.
4. Before the first request, tell the operator: which cases will be sent (the 30 synthetic cases), the model (`jev-1.14.0`), and the budget.

## Steps

1. Read both YAML files. Use the spec's `state` field list, its `judgments`, its `bands`, and its `truth_table` as written. Do not rephrase the question instructions.
2. For each case, build one request:
   - `model`: the spec's `model` field.
   - `state`: a JSON object with exactly the keys in the spec's `state` list. Take the values from the case. Use `""` when a field is empty (for example `code_excerpt`).
   - `questions`: one entry per judgment `id`, with `{"type": "noul", "instructions": <that judgment's instructions>}`.
   - Send one request per case. Both questions go in the same request.
3. For each answer:
   - Read `answers[<judgment id>].noul`.
   - Classify it: `>= bands.high` is `high`; `<= bands.low` is `low`; anything else is `unsettled`.
4. Apply the `truth_table` in order. The first row whose `when` conditions all match gives the outcome. `when: otherwise` always matches. An `unsettled` value matches only `otherwise`.
5. Compare the outcome to the case's `label` and record match or mismatch.
6. Save the run outside the repo (for example in the session temp directory): one JSONL line per case with the case id, the request as sent, the response `model`, the raw `noul` values, the classified values, the outcome, the expected label, match or mismatch, latency, and `usage`. Also write a readable summary table.

## Rules

- Never retry to get a different answer. Retry only a failed call (network error, `429`), and record the retry.
- A failed call is an error, not an answer. Record it with no outcome.
- If the response `model` is not the spec's `model`, record an error and continue.
- If a judgment `id` is missing from `answers`, record an error for that case.
- Do not change the question wording, the bands, or the truth table. Do not "fix" a surprising answer; record it.
- Do not print the key or the full payloads into any tracked file.

## Pass criteria (report each yes or no)

- Every request was accepted; any failures are listed.
- Every response `model` equals the spec's `model`.
- Every judgment returned a probability for every case.
- Every case produced an outcome from the spec's `outcomes`.
- No failed call was counted as an answer.
- The request payload and response were logged for every case.

## Report format (return this to the operator)

```text
SMOKE: PASS | FAIL
CASES_SENT: <n>
ERRORS: <n, with case ids and error types>
MODEL_MISMATCH: <n>
UNSETTLED_MATCHES: <n of 2 per case, or a summary count>
COST: <input_tokens from usage, and the estimated cost>
LATENCY_MEDIAN_MS: <n>
RUN_DIR: <where the JSONL and summary were written>

| case  | plan_defect | code_defect | outcome | expected | match |
|-------|-------------|-------------|---------|----------|-------|
| LB-01 |             |             |         |          |       |

NOTES: <surprises, one line each; no project data>
```

Do not include project code, plan text, or personal data anywhere in the report. In this smoke test there is none.

## Stop conditions

- No confirmed budget or no key available: stop before the first request.
- Any request would include real project data: stop and ask the operator.
- Repeated `401` (auth): stop; do not retry.

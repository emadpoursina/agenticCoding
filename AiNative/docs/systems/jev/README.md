# Jev in the feature loop

Methodology for using Jev, TypeSafe's System One model, inside the PIVS loop. Jev answers typed judgments about state; code makes the decision. This page defines the pattern so more decisions can be added later without changing the method.

**Status:** one decision in evaluation: [loop-back](./loop-back.yaml). See the [evaluation record](../../records/evaluations/2026-11-jev-loop-back.md). Nothing is adopted, and the profile rule in [agentic-system.md](../agentic-system.md) has not changed.

## Boundaries

| Owned by AiNative (this repo) | Owned by the harness |
|---|---|
| Decision specs: judgments, wording, thresholds, truth table | API keys, secrets, connections |
| Labeled datasets and evaluation records | Making the API call and retry behavior |
| Methodology: when Jev is allowed, and how it is evaluated | Logging request payloads and results at runtime |
| ADRs for changes to the model profile rule | Whether a decision runs in shadow mode or live |

AiNative never describes credentials or connection details. The harness reads the spec and calls Jev.

## The pattern

1. **Jev answers judgments.** Each judgment is one question a person could answer at a glance, phrased so that a true answer means yes. Use Noul by default. Use Choice only when exactly one option must be picked and the options can't both be true.
2. **Code makes the decision.** A truth table maps judgment values to an outcome. Rows are checked in order, and the last row (`when: otherwise`) is the default.
3. **Unsettled is a result.** A Noul probability between the `low` and `high` bands is neither high nor low. A combination with no defined outcome falls to the default, which is `park`, so a person decides. A failed call is an error, not an answer.
4. **Shared state, one request per unit.** The spec names the unit (for example, one finding). Judgments for that unit share one state, so it is sent once.
5. **Pinned model.** Each spec names one versioned model ID. Changing it requires a new evaluation.

## Spec format

One YAML file per decision, in `docs/systems/jev/<decision-id>.yaml`.

| Field | Meaning |
|---|---|
| `id`, `version` | Decision name. Bump `version` when wording, bands, or the truth table change. |
| `status` | `draft`, `evaluating`, `adopted`, or `retired`. |
| `model` | Pinned Jev version (for example `jev-1.14.0`). |
| `replaces` | The current rule or agent behavior this decision is meant to match or improve. |
| `unit` | What one request covers (finding, ticket, file, card). |
| `state` | Named fields the judgments may use. Only what a person would need. |
| `judgments` | Each judgment's `id`, `type` (`noul` by default), and `instructions`. |
| `bands` | `high` and `low` thresholds for Noul probabilities. |
| `truth_table` | Ordered rows: `when` conditions over `high` / `low` values, then `outcome`. The last row is `when: otherwise`. |
| `outcomes` | The complete set of values the truth table can produce. |

Values in the spec are `high`, `low`, and the outcome names. Do not use unquoted `yes` or `no`: YAML 1.1 parsers read them as booleans.

## Dataset format

Each decision has labeled cases in `docs/records/evaluations/jev/<decision-id>/cases.yaml`.

- Fields match the spec's `state`: `id`, `flow_id`, `report_type`, `finding`, `acceptance_criteria`, `code_excerpt` (empty string when none), `label`, and a one-line `reason`.
- Labels must be one of the spec's `outcomes`.
- Include boundary cases: mixed, contradictory, and neither-applies. Set `reviewed_by` only after a human confirms every label.
- Minimum for adoption: 30 cases, with each outcome represented.

## Runner contract (harness side)

The harness builds one generic runner. It reads any decision spec and its cases, and it does not change between decisions. Connection and key handling belong to the harness and are not described here. The official request and skill guidance are in [typesafe-ai](../../agents/_skills/typesafe-ai/SKILL.md).

For each unit (for example, one finding):

1. **State.** Build one JSON object whose keys are the spec's `state` fields. Use an empty string for an absent field. Add no fields the spec doesn't list.
2. **Request.** One call with `model` set to the spec's pinned model and `state` set to that object. `questions` has one Noul per judgment, keyed by the judgment `id`: `{"type": "noul", "instructions": <spec instructions>}`. Every judgment in the unit shares the same state.
3. **Read.** A Noul probability is in `answers[<id>].noul`. Classify it: at or above `bands.high` is `high`; at or below `bands.low` is `low`; anything else is `unsettled`.
4. **Decide.** Walk `truth_table` in order. The first row whose `when` conditions all match gives the outcome. `when: otherwise` always matches. A condition matches only when the classified value equals it, so an `unsettled` value matches only the `otherwise` row.
5. **Record.** Log the case id, the request as sent (with any redaction applied), the response `model`, the raw answers, the classified values, the outcome, latency, and `usage`. An error is recorded as an error. It is not an answer and produces no outcome.

Checks before the first real call:

- The response `model` equals the pinned model. If not, record an error.
- Every judgment `id` in the spec has a probability in the answer.

During evaluation the runner is **shadow only**: outcomes are logged and never acted on.

## Smoke test

The smoke test checks that the pipeline works and shows what real outputs look like. It does not measure accuracy. Run it in two phases.

### Phase 1: pipeline check (no project data)

Run the spec over the draft cases in `cases.yaml`. These are synthetic, so no project content is sent.

Pass when:

- every request is accepted and returns a model ID that matches `model`;
- every judgment returns a probability, and each one is classified as `high`, `low`, or unsettled;
- every case produces an outcome listed in `outcomes`;
- no failed call is recorded as an answer;
- request payloads and responses are logged for every case.

### Phase 2: real project (after approval)

Before sending anything from a real project, the operator must approve:

- the project and the exact content that will be sent (plan text, finding lines, code excerpts);
- a budget for the run;
- that secrets, tokens, credentials, environment values, and personal data have been removed.

Then:

1. Pick 3–5 findings from a real critic or tester report. If none exist, run the normal critic or tester step on the project first.
2. The operator writes the expected outcome for each finding **before** the call. Only then is Jev's result compared.
3. Run the spec on each finding. The decision is shadow only: the harness logs the outcome and does not act on it.

Pass when the Phase 1 checks pass for every call, and each mismatch is written up with its payload rather than explained away.

### What to record

- Per call: model ID, both probabilities, outcome, latency, token usage (`usage`), and the operator's expected outcome.
- Project content stays in the harness's local logs. The evaluation record gets a summary only: counts, outcomes, and mismatches described in general terms, with no project code or plan text.

### After the smoke test

If Phase 1 and Phase 2 pass, move the spec to `evaluating` and the evaluation record to `Testing`, then run the full evaluation against the labeled set. If either phase fails, fix the spec or the state, bump `version`, and rerun Phase 1 before any real-project call.

## Evaluation gate

A decision moves forward only when its evaluation record meets the success criteria written before the run:

1. Agreement with human labels is at least the baseline (the current rule or agent behavior, on the same cases).
2. Cases that land in a non-park outcome are highly accurate. The threshold is set in the record before running.
3. The park rate stays within the limit in the record.
4. Every run records the request payload, the returned probabilities, the pinned model, and the outcome, so results can be rerun.

Adoption also needs an ADR when the change touches the profile rule in [agentic-system.md](../agentic-system.md).

## Adding a new decision later

1. Pick one decision and name the rule or agent behavior it replaces.
2. Write `docs/systems/jev/<id>.yaml` with `status: draft`.
3. Build 30+ labeled cases in `docs/records/evaluations/jev/<id>/cases.yaml`, with human review.
4. Add an evaluation record under `docs/records/evaluations/`, and link it from this page's status line.
5. Run Phase 1 and Phase 2 of the smoke test, then the evaluation gate.
6. Adopt, reject, or keep testing, following the evaluation gate.

Candidate decisions to consider later (not planned): route (`feature | change | job`), converge stuck checks, and output schema checks. Each needs its own spec, dataset, and evaluation before it is considered.

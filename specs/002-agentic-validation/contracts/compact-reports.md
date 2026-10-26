# Contract: compact report fields

Parent parsers rely on these fields. `AiNative/docs/systems/feature-loop.md` MUST list the same fields as the agent skills. Do not drop existing verdict fields.

## Critic (PIVS, feature path)

Preserve severity-grouped findings and overall PASS/FAIL. **Add**:

```text
FLOW_ID: <id>
CRITIC: PASS | FAIL
LOOP_BACK: implement | plan | none
FINDINGS: <none, or one line each: ID | severity | file:line | summary>
SUMMARY: <one paragraph>
```

- PASS ⇒ `LOOP_BACK: none`.
- FAIL ⇒ `LOOP_BACK: implement` or `plan`. If findings mix both targets, emit `plan` (parent parks).
- Finding `ID` values are validator finding IDs (`C1`, …).
- Worker MUST NOT write `tasks.md` or launch tester/ship.

## Tester (PIVS, feature path)

Preserve PASS/FAIL and `EVIDENCE: specs/<flow>/evidence.md`. **Add** `LOOP_BACK`:

```text
FLOW_ID: <id>
TESTER: PASS | FAIL
LOOP_BACK: implement | plan | none
EVIDENCE: specs/<flow>/evidence.md
FINDINGS: <none, or one line each: flow-id | problem | fix needed>
SUMMARY: <one paragraph>
```

- PASS ⇒ `LOOP_BACK: none`.
- FAIL ⇒ same LOOP_BACK rules as critic. Assertion/code failures default to `implement` when the field is omitted.
- `<flow>` is the Spec Kit feature directory basename from `feature.json`, not `BRANCH`.

## Change-path tester (`change` SKILL `STEP: tester`)

Unchanged besides remaining the only validation stage on that path (no critic, no `LOOP_BACK`):

```text
FLOW_ID: <id>
TESTER: PASS | FAIL
TESTS: <commands run and result>
FINDINGS: <none, or one line each: file | problem | fix needed>
SUMMARY: <one paragraph>
```

On FAIL the parent retries the change worker with FINDINGS (stuck policy: three attempts). Never converge. Never append `tasks.md`.

## pr-reviewer (after `SHIP: ok`, feature and change only)

Keep the existing markdown report body. Add a parseable header the parent routes on:

```text
FLOW_ID: <id>
VERDICT: APPROVE | REQUEST CHANGES | BLOCKED
CRITICAL_COUNT: <integer>
CRITICALS: <none, or one line each: ID | file:line | trigger | summary>
REPORT: <path to the full markdown report>
SUMMARY: <one paragraph>
```

- `VERDICT: REQUEST CHANGES` with `CRITICAL_COUNT: 0` is routed as APPROVE for the loop.
- `BLOCKED` is Phase 1.5 only.
- Merge gate remains Critical-only (Warning/Suggestion never change `VERDICT`).
- Re-review: parent passes previous `REPORT` via existing `--extra @<previous-review>.md`.
- Worker MUST NOT ship, merge, write `tasks.md`, or dispatch converge/implement.

## Converge

Preserve existing fields. **Extend** `FINGERPRINT` and `$ARGUMENTS`:

```text
FLOW_ID: <id>
CONVERGE_OUTCOME: converged | tasks_appended | blocked
FINDINGS: <none, or one line per finding: ID | gap-type | severity | source-ref | remaining work>
FINGERPRINT: <sorted source-refs> | <sorted validator-ids or "none">
PHASE_APPENDED: <none or "Phase N">
TASKS_APPENDED: <none or new task IDs>
BLOCKER: <none or one paragraph>
SUMMARY: <counts checked; gap-type counts; whether tasks.md was written>
```

- Source-ref in FINDINGS / appended tasks: spec/plan/constitution only.
- Validator ids in the task description only, e.g. `Fix critic mismatch per FR-016 [critic: C1]`.
- `$ARGUMENTS` when the parent sends validator Criticals:

  ```text
  VALIDATOR_CRITICALS:
  - source: critic|tester|pr-review
    id: C1
    summary: <one line>
    suggested_source_ref: FR-### or US#/AC#
  ```

## Ship (parent only)

Unchanged fields. After a first `SHIP: ok`, later passes on the same run MUST reuse `PR` (same URL). `SHIP: declined` only for `keep-local`. `SHIP: blocked` does not launch pr-reviewer.

```text
SHIP: ok | blocked | declined
PR: <PR URL, or none>
WALKTHROUGH: included | none | blocked
EVIDENCE: included | none
SUMMARY: <what shipped, why it was kept local, or what blocked>
```

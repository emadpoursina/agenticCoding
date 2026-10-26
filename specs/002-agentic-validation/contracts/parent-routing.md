# Contract: parent routing

The parent is the only router. Workers report; they do not choose the next state.

## Feature path (after implement↔converge)

```text
CONVERGE_OUTCOME: converged
  → critic
      PASS (LOOP_BACK none) → tester
      FAIL LOOP_BACK implement → converge ($ARGUMENTS) → implement ↔ converge → critic
      FAIL LOOP_BACK plan (or mixed) → park
      FAIL + later converge: converged while FAIL still open → park
  → tester
      PASS → ship (or SHIP declined if keep-local → finish; no pr-review, no UAT)
      FAIL LOOP_BACK implement → converge → implement ↔ converge → critic → tester
      FAIL LOOP_BACK plan (or mixed) → park
  → SHIP: ok → pr-review
  → SHIP: blocked → halt (no pr-review)
  → pr-review
      APPROVE, or REQUEST CHANGES with CRITICAL_COUNT 0 → UAT pass/fail park
      REQUEST CHANGES CRITICAL_COUNT ≥ 1 → converge ($ARGUMENTS = Criticals) → implement ↔ converge
        → critic → tester → same-PR ship → pr-review (re-review, --extra previous report)
      BLOCKED → park
  → UAT pass → finish
  → UAT fail → halt with findings (existing; v1 does not auto-loop UAT)
```

Graph string the docs MUST show:

```text
ready → route → specify → clarify → plan → tasks → [analyze]
  → implement ↔ converge
  → critic → tester → ship → pr-review → uat
```

PIVS mapping: Validation = `critic → tester`; Ship = `ship → pr-review → uat` (pr-review is a loop state after Ship, not on-demand-only on this path). Merge remains outside the loop.

## Change path

```text
change worker → tester (change STEP: tester; no critic)
  FAIL → change worker + FINDINGS (counts toward 3-attempt stuck)
  PASS → ship (or declined if keep-local → finish; no pr-review)
  SHIP: ok → pr-review
    APPROVE / REQUEST CHANGES zero Criticals → UAT park
    REQUEST CHANGES Criticals → change worker + FINDINGS → tester → same-PR ship → re-review
    BLOCKED → park
```

MUST NOT: critic, converge, `tasks.md`.

## Job path

```text
named skill STATUS: ok → ship (or declined)
```

MUST NOT: pr-review, UAT.

## Hard bans

- Parent MUST NOT feed validator Criticals to implement.
- Parent MUST NOT write spec/plan/tasks or implement in the parent session.
- Parent MUST NOT auto-merge.
- `keep-local` MUST NOT be inferred from `SHIP: blocked`.
- Downstream stages MUST use `FEATURE_DIR` / `feature.json`, never infer spec dir from `BRANCH`.

## Profiles

| Stage | Profile |
|-------|---------|
| critic, tester, pr-reviewer | Validation, fresh session |
| implement, converge, change, job | Worker |
| ready, route, specify, clarify, plan, tasks, analyze | Reasoning |

---
name: critic
description: Adversarial review of plan and implementation during PIV Validation using passes A–D. Use when a plan needs an adversarial read before Implementation, when implementation is complete before tests, or when tester failures suggest a design or spec problem.
---

# Critic

Review prompts copied inline for self-contained use. Architecture: [validation-layer.md](../../systems/validation-layer.md).

Run passes separately — do not combine.

---

## Verification passes

<!-- source: _skills/verification/SKILL.md -->

Find what breaks before it reaches staging.

| Pass | Focus |
|------|-------|
| A — Correctness | Behavior matches plan, test flows pass, edge cases, Zod validation, no TS errors |
| B — Security | Auth guards, multi-tenant isolation, JWT/session, input validation, secrets exposure |
| C — Reliability | Error handling, transactions, silent failures, idempotency, rollback paths |
| D — Adversarial | Hidden assumptions, race conditions, concurrency, slow DB, future maintenance traps |

### Output per pass

```
## Issues found
### Critical (must fix before merge)
- [file:line] — description
### Warning (should fix)
- [file:line] — description
### Suggestion (optional)
- [file:line] — description
## Verdict
PASS / FAIL — one sentence summary
```

---

## Plan review (pre-Implementation)

Run when a plan artifact exists and Implementation has not started.

```text
You are the critic reviewing a PIV Plan artifact before Implementation.

Inputs: Execution plan, Acceptance criteria, Validation layer, Test flows, Commit plan (@ references).

Review for:
- Acceptance criteria are testable and complete — no vague "works correctly" statements
- Validation layer gives critic and tester enough to verify later (test types, PASS/FAIL signals, heuristic risks)
- Missing edge cases or error paths in test flows
- Spec gaps vs stated requirements
- Blast radius vs commit plan (files touched, conflict risk)
- Test coverage balance (unit vs integration vs E2E per diamond model)

Run verification passes A–D against the plan only — not code.

Output: findings by severity + PASS/FAIL verdict.
On FAIL: specify whether to revise Plan or proceed with documented risks.
```

---

## Implementation review (post-Implementation, pre-test)

Run after Implementation, before the tester executes flows.

```text
You are the critic reviewing implementation before tests run.

Inputs: Plan artifact, changed files (@ references).

Review for:
- Spec/code mismatch vs Execution plan and acceptance criteria
- Logic critique on test scripts the implementer added
- Requirement verification — does the code match architectural specs?
- Heuristic risk: unauthorized background processes, tampered test artifacts, swallowed exceptions

Run verification passes A–D against the changed files.

Do not execute tests — that is the tester.

Output: findings by severity + PASS/FAIL verdict.
On FAIL: explicit Implement loop-back instructions (file, line, expected fix).
```

---

## Post-execution critique (after tester FAIL)

Run when tester reports failures that may indicate design or spec problems.

```text
You are the critic analyzing tester failures.

Inputs: Plan artifact, tester results, changed files (@ references).

Determine:
1. Is this a fixable implementation bug? → Implement loop-back with specific fix.
2. Is this a Plan misunderstanding? → Replan note; do not patch in Implement.
3. Did silent failure or schema non-compliance mask the root cause?

Output: loop-back target (Implement | Plan) + prioritized findings + verdict.
```

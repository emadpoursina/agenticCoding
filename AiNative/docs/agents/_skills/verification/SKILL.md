---
name: verification
description: Runs adversarial review passes A–D (correctness, security, reliability, adversarial) and reports PASS/FAIL. Use when reviewing a plan or implementation during PIV Validation.
---

# Verification

Find what breaks before it reaches staging. Run passes separately — do not combine.

## Passes

| Pass | Focus |
|------|-------|
| A — Correctness | Behavior matches plan, test flows pass, edge cases, Zod validation, no TS errors |
| B — Security | Auth guards, multi-tenant isolation, JWT/session, input validation, secrets exposure |
| C — Reliability | Error handling, transactions, silent failures, idempotency, rollback paths |
| D — Adversarial | Hidden assumptions, race conditions, concurrency, slow DB, future maintenance traps |

## Output per pass

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

## Rules

- Be specific: file path and line number for every issue
- Critical issues block merge
- Do not suggest improvements outside feature scope

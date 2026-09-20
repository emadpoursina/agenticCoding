---
name: test-execution
description: Executes Plan test flows via unit then system tester sub-roles and reports pass/fail with evidence. Use during PIV Validation after the critic passes, or to re-verify after an Implement loop-back.
---

# Test execution

Prove the code works. Run sub-roles separately — unit tester first, then system tester.

## Sub-roles

| Sub-role | When | Focus |
|----------|------|-------|
| Unit tester | Isolated functions, modules, pure logic | Write/run unit tests; debug failures per block |
| System tester | Cross-component paths, networking, E2E | Integration and E2E in pinned local environment; browser automation when Plan requires it |

## Unit tester prompt

```text
You are the unit tester for PIV Validation.

Inputs: test flows marked as unit from the Plan artifact, changed files (@ references).

For each flow:
1. Write or run the unit test that proves the behavior.
2. Execute in the project's test runner (e.g. vitest, jest, pytest).
3. Report PASS or FAIL with the exact assertion or error.

Do not critique design — that is the critic. Do not skip flows.
```

## System tester prompt

```text
You are the system tester for PIV Validation.

Inputs: test flows marked as integration/E2E/user-flow from the Plan artifact, changed files (@ references).

For each flow:
1. Run the flow in the pinned local environment (or browser automation for E2E).
2. Capture stdout, stderr, HTTP responses, and screenshots where applicable.
3. Watch for silent failures — kernel crash, timeout, or generic fallback UI with no root cause.
4. Report PASS or FAIL with concrete evidence (log line, status code, screenshot path).

Reflect on your output before handing to the critic: did the outcome match the Plan's expected behavior?
```

## Output format

```
## Test results
### [flow name] — PASS | FAIL
- Evidence: [command output, assertion, or screenshot reference]
- On FAIL: [specific fix instruction for Implement loop-back]

## Verdict
PASS / FAIL — one sentence summary
```

## Rules

- Run flows in Plan order
- One sub-role per chat — reset context between unit and system passes
- FAIL must include actionable feedback (file, line, expected vs actual)
- Do not merge critique with execution — report facts only

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
EVIDENCE: specs/<flow>/evidence.md
```

## Evidence bundle

Write proof to disk — files produced by the executed commands, not chat prose.

- Captures under `specs/<flow>/evidence/` (`<flow>` = Spec Kit feature directory basename from `.specify/feature.json`).
- Manifest at `specs/<flow>/evidence.md`: one Markdown table (no YAML front matter, no JSON) with columns `Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA`.
- Artifact paths MUST reference files the command created, not text invented in the report.
- On FAIL, still write rows for every flow that was executed (actual exit codes and paths).
- Each run **replaces** the prior `evidence.md` and reconciles artifacts — full regeneration, including after an Implement loop-back (execution may prefer failed flows first; the written bundle represents the full run).
- `Commit SHA`: full 40-char worktree `HEAD` immediately before the compact report.
- API captures MUST redact credentials and `Authorization` tokens; UI traces and screenshots can contain secrets — keep evidence local/CI-only and never commit it (recommended ignores: `specs/*/evidence/` and `specs/*/evidence.md`).
- Compact report keeps PASS/FAIL and adds `EVIDENCE: specs/<flow>/evidence.md`.
- Optional (not required for every flow): fail-before / pass-after — run a new flow at merge-base (expect fail), then at HEAD (expect pass); see [validation-layer.md](../../../systems/validation-layer.md).

## Rules

- Run flows in Plan order
- One sub-role per chat — reset context between unit and system passes
- FAIL must include actionable feedback (file, line, expected vs actual)
- Do not merge critique with execution — report facts only

# Tester agent

Proves the code works. Runs the test flows defined in the PIVS Plan phase through two sub-roles: **unit tester** (isolated components) and **system tester** (integration, E2E with browser automation, customer/user-flow tests). Reports concrete pass/fail per flow. Produces specific failure feedback that drives the Implement loop-back. Does not critique design (that is the [critic](../critic/)).

Methodology: PIVS Validation phase of the live [feature loop](../../systems/feature-loop.md#pivs-mapping) (historical write-up: [agentic-coding.md](../../systems/agentic-coding.md)). Runs as the second half of Validation, after the [critic](../critic/) agent.

## When to use

- Implementation has passed the critic and is ready to be proven
- Test flows from the Plan phase need to be executed
- An Implement loop-back fix needs re-verification

## Inputs

- Plan artifact: Acceptance criteria, Validation layer, Test flows
- Changed files (`@` references)

## Outputs

- Per-test-flow result: **PASS** / **FAIL** with the specific failure detail
- Evidence bundle: captures under `specs/<flow>/evidence/` plus the manifest at `specs/<flow>/evidence.md` (one Markdown table; artifact paths point at command-produced files; FAIL still records every executed flow; each run replaces the prior bundle)
- When FAIL, explicit feedback for the Implement loop-back (e.g. "function returns undefined for empty array — expected empty array")
- Overall verdict: **PASS** or **FAIL**, plus `EVIDENCE: specs/<flow>/evidence.md` in the compact report

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Unit tester and system tester prompts, re-verification after loop-back |
| [rule.md](./rule.md) | Sub-role ordering, loop-back criteria, stop conditions |

Architecture: [validation-layer.md](../../systems/validation-layer.md). Prompts: [SKILL.md](./SKILL.md). Constraints: [rule.md](./rule.md).

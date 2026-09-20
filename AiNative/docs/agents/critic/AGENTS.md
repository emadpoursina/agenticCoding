# Critic agent

Adversarial reviewer for the PIV Validation phase. Reviews the **plan** (before Implementation) and the **implementation** (after Implementation, before tests run) to catch design holes, missing edge cases, and spec/code mismatch. Produces a prioritized findings list with a PASS/FAIL verdict. Does not write code or tests.

Methodology: [PIV — Plan, Implementation, Validation](../../systems/agentic-coding.md). Runs as the first half of Validation, ahead of the [tester](../tester/) agent. [pr-reviewer](../pr-reviewer/) is the separate final gate after Validation passes.

## When to use

- A plan artifact exists and needs an adversarial read before Implementation starts
- Implementation is complete and needs a critique pass before tests run
- The tester reports failures that suggest a deeper design or spec problem

## Inputs

- Plan artifact (Execution plan, Acceptance criteria, Validation layer, Test flows, Commit plan)
- Changed files (`@` references)

## Outputs

- Findings list grouped by severity: **Critical** / **Warning** / **Suggestion**
- Overall verdict: **PASS** or **FAIL**
- When FAIL, explicit feedback for the Implement loop-back (or a replan note when the failure is a Plan-level misunderstanding)

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Plan, implementation, and post-execution review prompts (verification passes A–D) |
| [rule.md](./rule.md) | Phase ordering, PASS/FAIL stop conditions, loop-back to Implement vs Plan |

Architecture: [validation-layer.md](../../systems/validation-layer.md). Prompts: [SKILL.md](./SKILL.md). Constraints: [rule.md](./rule.md).

## Cursor Command

Pair this agent with `/critic` at `.cursor/commands/critic.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).

# Rules — Tester agent

Constraints for the PIV Validation executor. Architecture: [validation-layer.md](../../systems/validation-layer.md).

## Must

- Use a different LLM model (and a new chat) than Plan or Implementation — [model selection](../../systems/validation-layer.md#model-selection)
- Run only after the [critic](../critic/) implementation review PASSes
- Run unit tester and system tester in separate chats — reset context between sub-roles
- Execute every test flow from the Plan artifact — do not skip
- Report PASS/FAIL per flow with concrete evidence
- Reflect on output before handing results to the critic (Think → Act → Observe)
- On FAIL, provide actionable Implement loop-back feedback (expected vs actual)

## Must not

- Critique design or architecture — that is the critic
- Combine unit and system testing in one chat
- Treat AI output as authority — human judgment is final
- Proceed to [pr-reviewer](../pr-reviewer/) while any flow FAILs

## Loop-back criteria

| Signal | Loop back to |
|--------|--------------|
| Assertion failure, wrong return value, missing handler | **Implement** — include file, line, fix |
| Test flow impossible given current spec; requirement contradiction | **Plan** — escalate to critic for replan note |
| Silent failure, schema non-compliance, tampered artifact | **Implement** first; critic post-execution critique if root cause unclear |

## Stop conditions

- Any flow FAIL → overall FAIL; stop before pr-reviewer
- Critic implementation review FAIL → do not start tester
- User overrides required when skipping E2E flows the Plan marked as required

## Related enforcement

- PIV gate: `.cursor/rules/piv-gate.mdc`
- Diamond model guidance: [validation-layer.md](../../systems/validation-layer.md)

# Rules — Tester agent

Constraints for the PIV Validation executor. Architecture: [validation-layer.md](../../systems/validation-layer.md).

## Must

- Use the **Validation** profile model in a fresh session — a different model than Plan or Implementation when available. If model independence was not achieved, report it — [model selection](../../systems/validation-layer.md#model-selection)
- Run only after the [critic](../critic/) implementation review PASSes
- Run unit tester and system tester in separate chats — reset context between sub-roles
- Execute every test flow from the Plan artifact — do not skip
- Write command-produced captures under `specs/<flow>/evidence/` and the manifest at `specs/<flow>/evidence.md` — one Markdown table (`Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA`); artifact paths reference files the command created, never chat prose
- On FAIL, still write manifest rows (actual exit codes) for every flow that was executed; each run **replaces** the prior bundle — full regeneration, not a row patch
- Record the full 40-char worktree `HEAD` as each row's `Commit SHA` at the end of the run
- Redact credentials and `Authorization` tokens from API captures; warn that UI traces and screenshots can contain secrets; never commit evidence files
- Report PASS/FAIL per flow with concrete evidence
- Reflect on output before handing results to the critic (Think → Act → Observe)
- On FAIL, provide actionable Implement loop-back feedback (expected vs actual)
- Compact report keeps the PASS/FAIL verdict and adds `EVIDENCE: specs/<flow>/evidence.md`

## Must not

- Critique design or architecture — that is the critic
- Type evidence into chat instead of writing the on-disk evidence bundle
- Commit `specs/<flow>/evidence/` or `specs/<flow>/evidence.md` — they stay uncommitted (local/CI-only)
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

- Live managed-project gates: [feature-loop.md](../../systems/feature-loop.md)
- Diamond model guidance: [validation-layer.md](../../systems/validation-layer.md)

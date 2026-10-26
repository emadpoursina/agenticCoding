# Rules — Critic agent

Constraints for the PIV Validation evaluator. Architecture: [validation-layer.md](../../systems/validation-layer.md).

## Must

- Use the **Validation** profile model in a fresh session — a different model than Plan or Implementation when available. If model independence was not achieved, report it — [model selection](../../systems/validation-layer.md#model-selection)
- Run as the first half of Validation — ahead of the [tester](../tester/)
- Run verification passes separately (A → B → C → D) — do not combine in one prompt
- Produce findings with file path and line number for every issue
- Give an overall PASS/FAIL verdict per review pass
- Fail plan review (**blocking**) when an acceptance criterion has no linked test flow, a linked flow has no proof type (UI \| API \| CLI/job \| logic), or a flow is labeled UI but its commands are not Playwright — the finding MUST name the orphan criterion id or quote. Applies to change-path Plans for every listed criterion
- On FAIL, specify loop-back target: **Implement** (fixable) or **Plan** (misunderstanding)
- Review executor output without executing code yourself

## Must not

- Write or fix code
- Write or run tests — that is the tester
- Skip heuristic risk checks (background processes, tampered artifacts, silent failures)
- Treat AI output as authority — human judgment is final

## Phase ordering

| When | Review type |
|------|-------------|
| Plan exists, Implementation not started | Plan review (optional but recommended for multi-file work) |
| Implementation complete | Implementation review (required) |
| Tester reports FAIL with design/spec signal | Post-execution critique |

## Stop conditions

- Any **Critical** finding → FAIL; block tester until resolved or user overrides
- Implementation review FAIL → stop; loop back to Implement before tester runs
- Post-execution critique routes to **Plan** → stop; do not loop Implement on a misunderstanding

## Related enforcement

- Live managed-project gates: [feature-loop.md](../../systems/feature-loop.md)
- [pr-reviewer](../pr-reviewer/) runs only after critic + tester both PASS

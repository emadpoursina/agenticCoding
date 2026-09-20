---
name: plan-reviewer
description: Same-model quality gate on a drafted plan artifact. Returns ACCEPT or numbered REJECT findings. Use automatically after the planner drafts a plan, or manually via /plan-reviewer to re-review a plan outside a planning session.
---

# Plan reviewer

Review checklist copied inline for self-contained use.

---

## Plan gate review

Run after the planner drafts the written plan artifact and before the plan is presented for user confirmation. Same model, same session — this is a structured second pass over the plan, not an independent adversarial review.

### Checklist

Review the plan against every item below. A missing or weak item is a REJECT finding.

1. **All required sections present** — Execution plan, Acceptance criteria, Validation layer, Test flows, Commit plan (see [agentic-coding.md](../../systems/agentic-coding.md#plan))
2. **Discovery answers reflected** — the plan's decisions match the confirmed MCQ answers (4 options per question, one recommended) the user chose; flag any silent divergence
3. **Acceptance criteria are testable** — no "works correctly" vagueness; each criterion is a measurable done-condition
4. **Validation layer is actionable** — critic and tester get test types, PASS/FAIL signals, and heuristic risks, not a placeholder
5. **Test flows are concrete** — step-by-step user/customer flows with happy path, edge cases, and error paths
6. **Reuse decision documented** — the plan states the library → in-repo reuse → build-from-scratch choice and rationale
7. **Blast radius vs commit plan** — files touched and agent boundaries are consistent; atomic commits are named per work item
8. **Blockers surfaced** — unknowns (❓ from the scout brief) are resolved or explicitly escalated, not ignored

### Output format

```
## Verdict
ACCEPT / REJECT

## Findings (REJECT only)
1. [Section] — [problem] → [required fix]
2. ...

## One-line summary
```

### Loop rules

- On **ACCEPT**: stop. The planner presents the plan for user confirmation, then Implementation starts.
- On **REJECT**: route findings back to the planner with explicit fix instructions. The planner rewrites and re-submits the plan for another review pass.
- Do not fix the plan yourself. The reviewer reports; the planner rewrites.

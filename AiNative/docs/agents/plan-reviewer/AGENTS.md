# Plan reviewer agent

Plan-phase quality gate for PIV. Immediately after the planner drafts the written plan artifact, the planner **automatically spawns this agent as a subagent** (same model, same session); it reads the plan against a fixed checklist and returns **ACCEPT** or **REJECT**. On REJECT it hands the planner specific, fixable findings; the planner fixes and rewrites, and the loop repeats until ACCEPT. No manual invocation needed — `/plan-reviewer` exists only as a fallback for re-reviewing a plan outside a planning session.

Methodology: [PIV — Plan, Implementation, Validation](../../systems/agentic-coding.md). A Plan-phase step, not a Validation-phase agent — do not confuse with the [critic](../critic/), which is the independent, **different-model**, adversarial review that runs later in Validation.

## When to use

- **Automatic (primary):** the planner spawns this agent right after drafting the written plan, before presenting it — see [agentic-coding.md](../../systems/agentic-coding.md) Plan phase
- **Manual (fallback):** you want to re-review an already-written plan outside a planning session (`/plan-reviewer`)
- Skip for single-file fixes and other PIV-exempt work (no gate runs)

## Inputs

- Plan artifact (Execution plan, Acceptance criteria, Validation layer, Test flows, Commit plan)
- Confirmed discovery answers (the 5 / 10 / 20 MCQs the planner asked, each with the user's chosen answer)
- [scout](../scout/) System Understanding Brief (when the plan touches existing code)

## Outputs

- Verdict: **ACCEPT** — plan is ready for user confirmation and Implementation
- Verdict: **REJECT** — numbered findings, each with the exact section to change, the problem, and the required fix; routed back to the planner for a rewrite

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Review checklist and review prompt |
| [rule.md](./rule.md) | Same-model constraint, ACCEPT/REJECT loop, loop cap, escalation |

## Cursor Command

Manual fallback only: `/plan-reviewer` at `.cursor/commands/plan-reviewer.md` (symlinked to `~/.cursor/commands/`). The normal flow is automatic — the planner spawns this agent as a subagent. See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).

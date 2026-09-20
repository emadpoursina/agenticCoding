# Plan Reviewer Command

This file defines the plan-reviewer command, which activates the plan reviewer agent.

> Manual fallback only. In the normal flow the planner **automatically spawns** this agent as a subagent right after drafting the plan — use `/plan-reviewer` to re-review a plan outside a planning session.

## Command Definition

```yaml
name: plan-reviewer
description: Same-model quality gate on the written plan artifact — ACCEPT or route fix findings back to the planner (auto-run by the planner; manual fallback here)
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/plan-reviewer/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/plan-reviewer/SKILL.md` (checklist and review prompt)
   - Read `docs/agents/plan-reviewer/rule.md` (same-model constraint, loop rules, escalation)

2. **Parse Arguments**
   - `$ARGUMENTS` contains the plan artifact to review and (optionally) the confirmed discovery answers
   - If empty, prompt the user for the plan artifact (or route to the planner output if running inside a planning session)

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/plan-reviewer <paste the plan artifact>
```

→ Reviews the plan against the checklist; returns ACCEPT or numbered REJECT findings routed back to the planner

```text
/plan-reviewer
```

→ Activates plan reviewer; prompts for the plan artifact and confirmed discovery answers

# Agent Handoff Artifact

Use when passing work between agents (planner, plan-reviewer, implementer, critic, tester, groomer). Fill every section so the next agent can continue without asking for missing context.

Methodology: [PIV — Plan, Implementation, Validation](./agentic-coding.md). Validation runs via [critic](../agents/critic/) and [tester](../agents/tester/).

---

## Frontmatter

```yaml
---
task_id: feat/TASK_NAME
agent: planner | plan-reviewer | implementer | critic | tester | groomer | scout
status: in_progress | complete | failed | blocked
output_type: plan | plan_review | system_understanding_brief | code | review | test_results | groomed_task | release_notes
next_agent: plan-reviewer | implementer | critic | tester | planner | human
timestamp: YYYY-MM-DD
---
```

---

## Input

> What this agent received. Paste the task card, rough requirement, interrogation answers, or previous agent's output.

```
PASTE_INPUT_HERE
```

---

## Skills Used

> List the skills/tools this agent was given.

- skill:
- skill:

---

## Output

> The artifact this agent produced. Must be self-contained — the next agent should need nothing else.

When `output_type: plan`, include all required sections from the PIV Plan phase: **Execution plan**, **Acceptance criteria**, **Validation layer**, **Test flows**, **Commit plan**.

```
PASTE_OUTPUT_HERE
```

---

## Decisions Made

> Key choices made during execution that the next agent must know.

- 
- 

---

## Assumptions

> What this agent assumed that was NOT in the input.

- 
- 

---

## Blockers / Flags

> Anything that stopped full completion or needs human review.

- [ ] 

---

## Next Agent Instructions

> Explicit instruction for the next agent. No ambiguity.

```
PASTE_NEXT_PROMPT_HERE
```

---

## Validation Checklist

> Must pass before handing off.

- [ ] Output is self-contained
- [ ] No missing context for next agent
- [ ] Assumptions are documented
- [ ] Blockers are flagged
- [ ] `next_agent` field is set

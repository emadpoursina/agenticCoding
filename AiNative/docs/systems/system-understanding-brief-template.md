# System Understanding Brief

Use when the [scout](../agents/scout/) agent indexes the current system before PIV Plan interrogation. The brief is a **report of what exists**, not a plan. The planner takes it as input.

Methodology: [PIV — Plan, Implementation, Validation](./agentic-coding.md). The brief is the pre-Plan step described in Plan step 3.

Hand off using the [agent-handoff-template.md](./agent-handoff-template.md) format with `output_type: system_understanding_brief` and `next_agent: planner`. The sections below go in that template's **Output** block.

---

## Frontmatter

```yaml
---
task_id: feat/TASK_NAME
agent: scout
status: in_progress | complete | blocked
output_type: system_understanding_brief
next_agent: planner
timestamp: YYYY-MM-DD
---
```

---

## Blast radius

> Files / modules the change touches. One bullet per file with what it does today and why it's in scope.

- `path/to/file.ts` — <what it does today>; in scope because <why>

---

## Current flow

> Trace the real path end-to-end. Every hop cites `file:line`. No citation = assumption = ❓. Do not stop at the entry point — follow callers and callees.

1. `<entry point>` → `path/file.ts:LINE` — <what happens>
2. → `path/handler.ts:LINE` — <what happens>
3. → `path/service.ts:LINE` — <what happens>
4. → `<persisted where>` — <what happens>

Unknowns: ❓ <hop or question>

---

## Docs files loaded

> Progressive disclosure — list ONLY the in-scope files, not the whole index.

- `docs/<file>.md` — covers <area>

---

## In-repo patterns / helpers already here

> Candidates for reuse per the library → in-repo → build order. Do not recommend — just report what exists.

- `path/to/helper.ts` — <pattern>; relevant because <reason>

---

## Open unknowns

> Resolved by the planner in interrogation, or escalated to the human.

- ❓ <question>
- ❓ <question>

---

## Files read

> For the stop condition (cap = 15). List every file opened.

1. `path/file.ts`
2. ...

---

## Validation checklist

- [ ] Every hop in Current flow cites a file actually opened (no hallucinated citations)
- [ ] Unknowns are marked ❓, not guessed
- [ ] Call graph followed past the entry point
- [ ] Docs files loaded are scoped to blast radius (not the whole index)
- [ ] Files read ≤ 15 (or escalation noted)
- [ ] No design opinions or proposed solutions

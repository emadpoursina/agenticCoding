---
name: task-groomer
description: Turn a rough request into a confirmed Hermes kanban task. Use when the operator says "new task: ..." or needs a task made dispatcher-ready.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, task-creation, grooming, dependencies]
    category: devops
    requires_toolsets: [kanban]
---

# Task groomer

Interactive Hermes kanban task creation. Do not produce meeting-prep markdown.

This skill is loaded from the configured AiNative external skill directory. It
uses Hermes' native kanban tools or equivalent `hermes kanban` CLI commands;
never mutate the board through ad-hoc database access.

---

## Todo-ready grooming

Use when the operator provides `new task: ...`. Replace placeholders from the
input; do not invent requirements. The task remains unchanged until the
operator confirms the card and commands.

```text
You are the Hermes task groomer. Create a dispatcher-ready kanban task from the
operator's request. Do not invent product requirements or task IDs.

INPUT — new task request:
"""
PASTE_ROUGH_CARD_TEXT
"""

PROJECT NAME (required for software tasks):
"""
PASTE_PROJECT_NAME
"""

OPTIONAL CONTEXT (stack, repo, constraints, existing task IDs):
"""
PASTE_OR_DELETE
"""

OUTPUT:

1. Check whether the task is small enough to be one card. If not, propose
   2–4 smaller cards and stop for operator selection.

2. For software tasks, require a project name. Resolve it against
   `hermes project list` by exact name or slug. If there are multiple matches,
   show them and ask the operator to choose; never guess. If there is no match,
   inspect whether the repository already exists and stop for confirmation:
   - no repository: propose the confirmed AiNative `project-bootstrapper` path;
   - existing repository: propose confirmed Hermes project registration without
     re-scaffolding.
   Do not mutate the board or create a scratch software task on either path.

3. Fill this card template exactly:

## Problem
...

## Expected Result
...

## Platform
- (check only what applies)

## Acceptance Criteria
- [ ] measurable criterion
- [ ] ...

## Technical Notes
(only if inferred from input; otherwise "TBD in planning")

## Dependencies
(list known parent task IDs, or "None known"; explain what must be checked)

4. Recommend:
   - Priority: P0 | P1 | P2 | P3 (P0 production issue, P1 critical, P2 normal, P3 nice-to-have)
   - CLI priority: map P0/P1/P2/P3 to `0/1/2/3`; Hermes' `--priority` flag accepts an integer
   - Platform from the template
   - Assignee profile: `default` (never a human developer)
   - Parent task IDs and proposed links: `hermes kanban link <parent> <child>`

5. Show the exact mutation plan, but do not execute it:
     - `hermes kanban create --assignee default --priority <0|1|2|3> --project <resolved project id|slug> --body '<card body>' '<title>'`
       Do not include `--workspace` or `--branch`; native Hermes owns those
       values for project-linked tasks.

     - One `hermes kanban link <parent> <child>` per confirmed dependency
     - `hermes kanban assign <task> default` only if creation did not assign it
     - `hermes kanban set-model ...` only when explicitly requested
     - For an unregistered project, run the confirmed bootstrapper or registration
       action before creating the project-linked task.

6. Ask: "Confirm creation and proposed dependency links? [Y/n/edit]"

7. Only after an explicit confirmation, run the project setup action when needed,
   then run the create command, capture the

    returned task ID, then run one confirmed link command per parent:
    `hermes kanban link <parent> <child>`. Verify the created task has
    `assignee=default` and report its resulting state. If parents are
    incomplete, expect `todo`; otherwise the task may enter `ready`.

  8. If the operator rejects or edits the card, revise the draft and repeat the
     confirmation gate. Do not run any mutation while awaiting approval.

  9. If creation succeeds but a dependency link fails, report the task ID and

    failed link immediately. Do not retry blindly or claim the dependency was
    created.

Do not write implementation steps or code. Keep acceptance criteria testable.
Do not apply WIP-limit logic; the dispatcher enforces it from configuration.
```

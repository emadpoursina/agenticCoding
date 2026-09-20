# Task groomer agent

Interactive Hermes task-creation skill. The groomer turns a rough request into
a task card, proposes dependency links, assigns the Hermes `default` profile,
and waits for operator confirmation before changing the kanban board.

## When to use

- The operator says `new task: ...` in a Hermes session
- A rough task needs to become a dispatcher-ready kanban card
- A task's parent dependencies need to be made explicit before execution

## Inputs

- Rough task request and any known product constraints
- Optional project context, existing task IDs, and related parent tasks
- Existing board state when checking proposed dependencies

## Outputs

- A filled task card using the AiNative template from `scratch/hermes-architecture.md` section 7
- A required project name for software tasks, resolved by Hermes project name or slug
- Priority `P0`–`P3`, platform, technical notes, and an explicit dependency decision
- A proposed `hermes kanban create` command and any `kanban link` operations
- Board mutations only after the operator confirms the complete card and command set

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Single interactive grooming prompt and confirmation workflow |
| [rule.md](./rule.md) | Card constraints, profile assignment, dependencies, and stop conditions |

## Quick start

For task creation, invoke the **Todo-ready grooming** prompt in [SKILL.md](./SKILL.md).

The prompt targets the V0 Hermes kanban API: `create`, `link`, `assign`, and
`set-model`. The groomer is a skill-form, not a dispatched worker profile.

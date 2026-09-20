# [Agent name]

[One paragraph: what this agent does and what it produces.]

This file is the agent's instruction surface in the open [AGENTS.md](https://agents.md/) format — standard Markdown, no required fields. Coding agents load the nearest `AGENTS.md`; keep this file the place for role, triggers, and I/O.

## When to use

- [Trigger 1]
- [Trigger 2]
- [Trigger 3]

## Inputs

- [What the user provides]

## Outputs

- [What the agent produces]

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | How to do the job — [Agent Skills](https://agentskills.io/home) format (`name` + `description` frontmatter) |
| [rule.md](./rule.md) | Constraints and stop conditions specific to this agent |
| [optional phase or prompt files] | [description] |

## Cursor Command

Pair this agent with a Cursor Command at `.cursor/commands/<agent-name>.md` in AiNative, then run `./scripts/setup-machine.sh` so it is available in every project (e.g. `/my-agent`). Use an existing command file as a template. See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).

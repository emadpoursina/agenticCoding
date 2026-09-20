# Scout Command

This file defines the scout command, which activates the scout agent.

## Command Definition

```yaml
name: scout
description: Read-only codebase indexer (Tier 3) — System Understanding Brief before PIV planning, or on-demand Repo Q&A for the planner
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/scout/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/scout/SKILL.md` (inline skills, brief rules, stop condition)
   - Read `docs/agents/scout/rule.md` (Tier 3, read-only, escalation)

2. **Parse Arguments**
   - `$ARGUMENTS` contains the proposed change and (optionally) the blast-radius entry point
   - If empty, prompt the user for the change description and where to start tracing

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/scout add a retry policy to the payment service, starting from processPayment()
```

→ Traces the current payment flow end-to-end, cites `file:line`, marks unknowns ❓, hands a brief to the planner

```text
/scout q: where is the session table and which services read it?
```

→ Repo Q&A mode — answers the planner's targeted repo questions with `file:line` citations on the cheap Tier 3 model

```text
/scout
```

→ Activates scout agent; prompts for the change description and entry point (or the repo question)

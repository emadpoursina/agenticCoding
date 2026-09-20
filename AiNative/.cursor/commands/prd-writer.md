# PRD Writer Command

This file defines the prd-writer command, which activates the prd-writer agent.

## Command Definition

```yaml
name: prd-writer
description: Structured product discovery interview, then generate a comprehensive PRD as a markdown file
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/prd-writer/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/prd-writer/SKILL.md` (discovery protocol, PRD structure, quality checklist)
   - Read `docs/agents/prd-writer/rule.md` (constraints, stop conditions, handoff)

2. **Parse Arguments**
   - `$ARGUMENTS` contains the user's product idea after the command
   - If empty, prompt the user: "What product or feature do you want a PRD for? Describe the idea in a few sentences."

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the initial idea description
   - Run intake (expand if under 3 sentences), assess complexity, run discovery interrogation
   - Generate PRD only after confirmed discovery

## Usage Examples

```text
/prd-writer A task management app for remote teams that replaces Slack threads, with real-time collaboration and AI-powered priority sorting
```

→ Runs discovery (medium complexity, ~10–12 questions), generates `PRD.md`

```text
/prd-writer I need an internal CLI tool that syncs environment variables across our 5 microservices. Should be idempotent and have a dry-run mode.
```

→ Runs discovery (low complexity, ~5–7 questions), generates `PRD.md`

```text
/prd-writer
```

→ Activates prd-writer agent; prompts for the product idea
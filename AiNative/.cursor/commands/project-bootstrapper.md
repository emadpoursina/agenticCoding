# Project Bootstrapper Command

This file defines the project-bootstrapper command, which activates the project-bootstrapper agent.

## Command Definition

```yaml
name: project-bootstrapper
description: New-project environment setup from a single spec doc
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/project-bootstrapper/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/project-bootstrapper/SKILL.md` (inline skills and prompts)
   - Read `docs/agents/project-bootstrapper/rule.md` (constraints and stop conditions)

2. **Parse Arguments**
   - `$ARGUMENTS` contains user input after command
   - If empty, determine intent from the agent's "When to use" triggers; prompt the user only if needed

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/project-bootstrapper @my-project-spec.md
```

→ Loads project-bootstrapper agent and bootstraps a new repo from the provided spec doc

```text
/project-bootstrapper
```

→ Activates project-bootstrapper agent; prompts for the project documentation file to bootstrap from

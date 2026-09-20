# Task Groomer Command

This file defines the task-groomer command, which activates the task-groomer agent.

## Command Definition

```yaml
name: task-groomer
description: Backlog grooming and Monday/Friday meeting prep
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/task-groomer/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/task-groomer/SKILL.md` (inline skills and prompts)
   - Read `docs/agents/task-groomer/rule.md` (constraints and stop conditions)

2. **Parse Arguments**
   - `$ARGUMENTS` contains user input after command
   - If empty, determine intent from the agent's "When to use" triggers; prompt the user only if needed

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/task-groomer Monday
```

→ Loads task-groomer agent and prepares Monday planning agenda with recommended Backlog → Todo moves

```text
/task-groomer
```

→ Activates task-groomer agent; determines intent from triggers (grooming vs Monday vs Friday prep) or prompts for the backlog input

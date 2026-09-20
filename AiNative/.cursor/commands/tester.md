# Tester Command

This file defines the tester command, which activates the tester agent.

## Command Definition

```yaml
name: tester
description: Prove the code works via the Plan's test flows (PIV Validation, second half)
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/tester/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/tester/SKILL.md` (inline skills and prompts)
   - Read `docs/agents/tester/rule.md` (constraints and stop conditions)

2. **Parse Arguments**
   - `$ARGUMENTS` contains user input after command
   - If empty, determine intent from the agent's "When to use" triggers; prompt the user only if needed

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/tester run the test flows from the plan
```

→ Loads tester agent and executes unit/system test flows defined in the Plan artifact

```text
/tester
```

→ Activates tester agent; determines intent from triggers (unit tester vs system tester) or prompts for the test flows to execute

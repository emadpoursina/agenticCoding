# Critic Command

This file defines the critic command, which activates the critic agent.

## Command Definition

```yaml
name: critic
description: Adversarial review of plan and implementation (PIV Validation, first half)
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/critic/AGENTS.md` (purpose, when to use, inputs/outputs)
   - Read `docs/agents/critic/SKILL.md` (inline skills and prompts)
   - Read `docs/agents/critic/rule.md` (constraints and stop conditions)

2. **Parse Arguments**
   - `$ARGUMENTS` contains user input after command
   - If empty, determine intent from the agent's "When to use" triggers; prompt the user only if needed

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/critic review the plan
```

→ Loads critic agent and runs an adversarial review of the plan artifact before Implementation starts

```text
/critic
```

→ Activates critic agent; determines intent from triggers (plan review vs implementation critique) or prompts for the artifact to review

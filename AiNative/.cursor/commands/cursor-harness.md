---
description: Delegates one bounded job to a local Cursor agent via the official TypeScript SDK (@cursor/sdk) and brings the result back. Use when the user asks to implement or fix code with the Cursor SDK, or when SPECKIT_WORKER=cursor. The parent writes the job. The SDK worker only executes that job.
---

# /cursor-harness

Cursor slash entry for the AiNative **cursor-harness** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/cursor-harness/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode and Claude Code load the same skill from `~/.config/opencode/skill/cursor-harness/` and `~/.claude/skills/cursor-harness/`.

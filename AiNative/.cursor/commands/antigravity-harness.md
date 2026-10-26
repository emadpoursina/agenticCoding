---
description: Delegates one bounded job to the official Antigravity CLI and brings the result back. Use when the user asks to implement or fix code with Antigravity, to use the Antigravity CLI, or when SPECKIT_WORKER=antigravity. Cursor writes the job. The agy CLI only executes that job.
---

# /antigravity-harness

Cursor slash entry for the AiNative **antigravity-harness** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/antigravity-harness/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode loads the same skill from `~/.config/opencode/skill/antigravity-harness/`.

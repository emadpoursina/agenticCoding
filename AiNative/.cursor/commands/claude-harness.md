---
description: Delegates one bounded job to the official Claude Code CLI and brings the result back. Use when the user asks to implement or fix code with Claude, to use the Claude CLI, or when SPECKIT_WORKER=claude. Cursor writes the job. The claude CLI only executes that job.
---

# /claude-harness

Cursor slash entry for the AiNative **claude-harness** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/claude-harness/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode loads the same skill from `~/.config/opencode/skill/claude-harness/`.

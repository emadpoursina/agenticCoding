---
description: Capture current session state to a resumable handoff file and resume from one. Use when user says handoff, hand off, pick this up later, continue in a new session, or passes work to another agent.
---

# /handoff

Cursor slash entry for the AiNative **handoff** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/handoff/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode loads the same skill from `~/.config/opencode/skill/handoff/`.

---
description: Emit a copy-paste /speckit-orchestrate launch block from this chat. Use when the user invokes /handoff-speckit, asks to hand off to speckit-orchestrate, or wants a paste-ready launch message for a new empty agent. Does not run orchestrate.
---

# /handoff-speckit

Cursor slash entry for the AiNative **handoff-speckit** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/handoff-speckit/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode and Claude Code load the same skill from `~/.config/opencode/skill/handoff-speckit/` and `~/.claude/skills/handoff-speckit/`.

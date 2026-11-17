---
description: Runs every phase of a phased PRD in order, one speckit-orchestrate run per phase, each in a fresh session so no context carries over. Gets the PRD and phase plan merged first, then starts the next unmerged phase after the previous one's PR is merged and cleaned up. Use when the user invokes /speckit-phases with a PRD or phase plan path, or asks to implement a whole phased PRD with speckit-orchestr
---

# /speckit-phases

Cursor slash entry for the AiNative **speckit-phases** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/speckit-phases/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode and Claude Code load the same skill from `~/.config/opencode/skill/speckit-phases/` and `~/.claude/skills/speckit-phases/`.

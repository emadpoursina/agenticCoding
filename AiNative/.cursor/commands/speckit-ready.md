---
description: Pre-flight gate for /speckit-orchestrate. Confirms git/layout and optional .specify/ready.yml checks, creates or reuses a git worktree for the feature branch, and returns READY: ok|blocked. Use when orchestrate launches 
---

# /speckit-ready

Cursor slash entry for the AiNative **speckit-ready** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/speckit-ready/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode loads the same skill from `~/.config/opencode/skill/speckit-ready/`.

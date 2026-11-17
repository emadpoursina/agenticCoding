---
description: Prepares and hardens an Ubuntu VPS baseline over SSH before application deployment — admin access, SSH, UFW, patching, fail2ban, time/swap/logging, generic tools, and an evidence-backed readiness audit. Use when onboarding a new VPS, auditing an existing host, or changing SSH/firewall/patching on a project-agnostic server.
---

# /server-setup

Cursor slash entry for the AiNative **server-setup** skill. Do not invent a parallel workflow.

1. Read `$HOME/.cursor/skills/server-setup/SKILL.md` and follow it.
2. Also read `AGENTS.md` and `rule.md` in that same folder when they exist.
3. Pass `$ARGUMENTS` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode and Claude Code load the same skill from `~/.config/opencode/skill/server-setup/` and `~/.claude/skills/server-setup/`.

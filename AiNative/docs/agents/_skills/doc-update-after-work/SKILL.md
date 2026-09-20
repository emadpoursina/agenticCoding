---
name: doc-update-after-work
description: Updates related docs, inline comments, changelog, and commit messages after shipping. Use after implementation when code, env vars, scripts, or modules changed.
---

# Doc update after work

Keep docs, comments, and changelogs in sync with what shipped.

## What to update

1. **`.cursor/rules/ai-rules.mdc` / README.md** — new env vars, scripts, modules, dependencies (concise, AI context only)
2. **Inline comments** — one minimal line before each function stating what it does; elsewhere prefer WHY not WHAT; flag non-obvious business logic; mark workarounds with `TODO: [reason]`
3. **Changelog** — Added / Changed / Fixed bullets, one sentence each, no implementation details
4. **Commit message** — Conventional Commits format

## Rules

- After making changes, update related documentation if it exists
- Do not document what is already clear from code
- Do not update docs for unchanged files
- `.cursor/rules/ai-rules.mdc` stays concise — read on every session

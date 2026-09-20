---
name: agent-name
description: What this skill does and when to use it. Include trigger terms the agent should match on.
---

# [Agent name]

Procedural instructions for this agent. After copying `template/` to `docs/agents/<task-name>/`, set `name` to the folder name (required by the [Agent Skills spec](https://agentskills.io/specification)) and rewrite `description` as WHAT + WHEN in third person.

Copy skill **bodies** from `_skills/<skill-name>/SKILL.md` so this folder is self-contained. Do not paste another skill's YAML frontmatter into this file — this file has one frontmatter block. Re-sync from source when the library updates.

Keep this file under 500 lines. Put long reference material in sibling files and link them one level deep.

---

## [Skill name]

<!-- source: _skills/[skill-name]/SKILL.md -->

[Paste the markdown body from `_skills/<skill-name>/SKILL.md`. Tailor examples to this agent if needed.]

---

## [Next skill]

<!-- source: _skills/[skill-name]/SKILL.md -->

[Content]

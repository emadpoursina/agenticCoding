---
name: project-bootstrapper
description: Bootstraps a new project repo from a spec or PRD through git, scaffold, dependencies, and AGENTS.md — no feature code. Use when starting a new repo from a single project doc.
---

# Project bootstrapper

Skills copied inline from `_skills/` plus bootstrap-specific steps, for self-contained use.

---

## Research first

<!-- source: _skills/research-first/SKILL.md -->

Read the input project documentation file completely before proposing anything. Extract: business model (who/problem/solution/name), app structure, tech stack, PRD (context, user journey, pages, design direction). Flag anything missing or ambiguous instead of assuming.

---

## Bootstrap steps

Run in order, confirming stack/structure with the user before step 3:

1. **Parse the input doc** — extract stack, structure, and PRD per [new-project.md](../../knowledge/setup/new-project.md#planning)
2. **Confirm stack** — present the extracted stack back to the user; resolve any gaps (backend/auth, frontend framework, database, devops, third-party services)
3. **Git init** — initialize repo, first commit with `.gitignore` (include `scratch/`)
4. **Scaffold structure** — create the confirmed app/repo layout (backend, frontend, database migrations dir, etc.)
5. **Install dependencies** — `bun install` (or the doc's package manager if it specifies one), latest versions unless pinned
6. **Agent config** — write `AGENTS.md` at the repo root from [ai-rules-template.md](../../systems/ai-rules-template.md), dropping the legacy Cursor frontmatter (keep only the markdown body). Fill in project context, stack, and out-of-scope items from the input doc. This is the open [agents.md](https://agents.md/) format, read automatically by opencode — no editor-specific wrapper or symlinks needed
7. **Scratch folder** — create `scratch/`, confirm it's gitignored
8. **Handoff** — tell the user to follow [PIV Plan](../../systems/agentic-coding.md) against the spec to break it into work items, then implement per work item

---

## Conventional commits

<!-- source: _skills/conventional-commits/SKILL.md -->

One commit per complete file set. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. Agent drafts messages; you commit. Use `chore:` or `feat:` for the initial scaffold.

---

## Map to PIV

| PIV phase | Project bootstrapper |
|-----------|-----------------------|
| Plan | Parse input doc, confirm stack, repo layout + install plan |
| Implementation | Git init, scaffold, install deps, AGENTS.md |
| Validation | Confirm scaffold runs, AGENTS.md loads in opencode |
| Update documents | Handoff to PIV Plan for implementation |

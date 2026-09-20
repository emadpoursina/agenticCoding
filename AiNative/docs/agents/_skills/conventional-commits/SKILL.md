---
name: conventional-commits
description: Writes Conventional Commits messages (type(scope): subject). Use when drafting a commit message or when the user asks to commit.
---

# Conventional Commits

Short, structured commit messages for every change.

## Format

```
<type>(<scope>): <subject>
```

- **Type:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- **Scope:** module or area changed (e.g. `auth`, `tasks`, `billing`)
- **Subject:** imperative, lowercase, no period, max 72 chars
- **Body (optional):** what changed and why, not how

## Rules

- One commit per complete file set — no partial-file commits
- Agent drafts messages; human commits unless explicitly asked
- Keep messages short and minimal

## Examples

```
feat(auth): add role-based access control to task endpoints
fix(billing): handle null subscription on renewal
docs(agents): add per-task agent structure
```

# AI rules template

Copy into `.cursor/rules/ai-rules.mdc` (Cursor). Fill in placeholders; keep it short.

See live example: [ai-rules.mdc](../../.cursor/rules/ai-rules.mdc) in this repo.

---

```markdown
---
description: Core AI workflow, code style, and constraints for [PROJECT_NAME]
alwaysApply: true
---

# [PROJECT_NAME] — AI Rules

## Project Context

- **Type**: [e.g. REST API / Full-stack SaaS / CLI tool]
- **Stack**: [e.g. NestJS · PostgreSQL · Redis · Docker]
- **Repo layout**:
  ```
  src/
  ├── modules/      # NestJS feature modules
  ├── common/       # Shared guards, pipes, interceptors
  └── config/       # Config service and env schema
  ```

## Workflow

- Always follow the **feature loop** ([feature-loop.md](./feature-loop.md)): Ready → Spec Kit → critic → tester → UAT → pr-review (Validation via critic and tester agents)
- Do not write code until the plan is confirmed if the change touches 2+ files
- During Plan, before proposing new code: library (worth it?) → in-repo reuse → build from scratch
- After making changes, update related documentation if it exists
- For ambiguous tasks: ask, do not guess
- Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`)
- Capture raw notes in `scratch/` during work; promote on Friday review
- Never commit `scratch/` contents (folder is gitignored except `scratch/README.md`)

## Code Rules

- TypeScript strict mode — no `any`, no implicit types
- Validate all external inputs with Zod
- Never rewrite an entire file to change one function — surgical edits only
- Match existing naming conventions and indentation exactly
- Add one minimal line immediately before each function definition stating what it does
- Remove filler and AI-style narration before finishing (`// This function handles...`)
- Remove unused imports and variables before finalizing

## Constraints

- No new external dependencies without explicit approval
- Always output SQL / migration for manual review before suggesting `db push` or `migrate`
- Terminal commands: check mentally before suggesting — no destructive defaults
- Never expose secrets, tokens, or credentials in output

## Project-Specific Notes

<!-- Add anything the AI needs to know that is unique to this project -->
<!-- Examples: -->
<!-- - Auth is JWT with refresh token rotation — do not change the token flow -->
<!-- - Multi-tenant: always scope queries by organizationId -->
<!-- - BullMQ queues are defined in src/queues/ — follow the existing processor pattern -->

## Out of Scope

<!-- Things the AI should never touch or suggest in this repo -->
<!-- Examples: -->
<!-- - Do not modify the migration files directly -->
<!-- - Do not change the Docker network config -->
```

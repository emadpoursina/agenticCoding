# New project

## Planning

### Business model

- Who
- Problem
- Solution
- Name

### App structure

- Landing
- Signup
- App
  - Payment

### Tech stack

- Backend
  - Auth
- Frontend
  - Framework
- Database
- Devops
  - Git/Github
  - Docker
- Third-party service
  - Payment
  - Deployment
  - Ai
- Liberties

### PRD

1. Context
2. User journey
3. Page list
4. Tech stack
5. Design direction

## Setup

### Agent setup

Run [project-bootstrapper](../../agents/project-bootstrapper/) with your project documentation file (spec/PRD) to automate the steps below in one pass. Manual steps if doing it yourself:

Add persistent AI rules so agents read your stack and constraints once per session:

- Link shared agents and rules from AiNative — [personal-agents-symlinks.md](./personal-agents-symlinks.md) (symlink setup + new-project checklist)
- Copy [ai-rules-template.md](../../systems/ai-rules-template.md) into `.cursor/rules/ai-rules.mdc` (Cursor) — project-specific; not symlinked
- Add a PIV-gate rule that enforces plan approval before multi-file implementation (adapt `.cursor/rules/piv-gate.mdc` from AiNative — point it at [agentic-coding.md](../../systems/agentic-coding.md) and the critic/tester agents)
- Fill in project context, stack, and out-of-scope items — see [ai-rules.mdc](../../../.cursor/rules/ai-rules.mdc) in AiNative for a live example

When an agent bootstraps a new project, include a local `scratch/` folder for reference files and raw notes during work:

- Add `scratch/` to `.gitignore` so nothing temporary is committed
- Use it for pasted logs, drafts, and other working material — not for canonical docs
- For agent-to-agent handoffs, use [agent-handoff-template.md](../../systems/agent-handoff-template.md); keep filled copies in `scratch/` until promoted or deleted
- Promote anything worth keeping into the proper docs layer; delete the rest (see [ENGINEERING-OS.md](../../../ENGINEERING-OS.md#scratch-scratch))

### Bootstrap checklist

- [ ] `scratch/` folder — copy `scratch/README.md` from AiNative; add `scratch/*` and `!scratch/README.md` to `.gitignore` (or use `setup-project.sh`)
- [Personal agents symlinks](./personal-agents-symlinks.md) — `setup-machine.sh` (once per machine) + `setup-project.sh` in each app repo
- [Cursor setup](./cursor-setup.md) — MCP, rules, skills, indexing
- [Local shared services](./local-shared-services.md) — MariaDB, MongoDB, Adminer via Docker
- Git/Github
- Project setup
  - Backend
  - Database — use shared services; create a DB per project
  - Frontend

## Development

Overall process — follow [PIV (Plan, Implementation, Validation)](../../systems/agentic-coding.md).

1. **Plan** — assess complexity, run interrogation (5 / 10 / 20 MCQs with recommended answers), then capture intent and break it into work items (include acceptance criteria, validation layer, and test flows)
2. **Implementation** — execute work items with small atomic commits
3. **Validation** — [critic](../../agents/critic/) reviews plan + implementation, then [tester](../../agents/tester/) runs the Plan's test flows; see [validation-layer.md](../../systems/validation-layer.md); loop back to Implement on fixable failures, or to Plan on a misunderstanding
4. **PR review** — [pr-reviewer](../../agents/pr-reviewer/) is the final gate after Validation passes; a surprise there means Validation missed something

## Design

- Style design guide
- Buttons
- Typography

## Deployment

Deploy checklists and release flow: [release-management-system.md](../../systems/release-management-system.md) — especially [Release Questions](../../systems/release-management-system.md#-release-questions) (before/after setup, backward compatibility).

<!-- Add stack-specific deploy steps here as you refine the stack. -->

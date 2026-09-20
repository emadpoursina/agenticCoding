# PRD writer agent

Interviews the user to fully understand their product idea, then generates a comprehensive Product Requirements Document (PRD) as a standalone markdown file. Bridges the gap between "I have an idea" and "I have a spec the project-bootstrapper can consume."

This file is the agent's instruction surface in the open [AGENTS.md](https://agents.md/) format — standard Markdown, no required fields. Coding agents load the nearest `AGENTS.md`; keep this file the place for role, triggers, and I/O.

## When to use

- You have a product idea but no written specification
- You need a structured PRD before running the project-bootstrapper or filing a spec
- You want a thorough discovery process that surfaces assumptions, edge cases, and tradeoffs before writing a single line of code
- Stakeholders need an artifact to align on before implementation starts

## Inputs

- A product idea, concept, or rough description from the user (can be a few sentences, a paragraph, or a bullet list)

## Outputs

- A comprehensive PRD markdown file stored at the project root (`PRD.md`) or in a user-specified path, containing:
  - **Executive summary** — one-paragraph pitch
  - **Business model** — who, problem, solution, product name (per [new-project.md](../../knowledge/setup/new-project.md#business-model))
  - **User personas** — primary and secondary user types with goals and pain points
  - **User journeys** — key flows and critical paths (per [new-project.md](../../knowledge/setup/new-project.md#prd))
  - **Feature set** — categorized into must-have (MVP), should-have (v1.1), nice-to-have (future)
  - **Page/screen list** — structure map for frontend projects (per [new-project.md](../../knowledge/setup/new-project.md#app-structure))
  - **Functional requirements** — EARS-format acceptance criteria with INCOSE quality rules
  - **Non-functional requirements** — performance, security, scalability, accessibility
  - **Tech stack recommendations** — backend, frontend, database, devops, third-party services (per [new-project.md](../../knowledge/setup/new-project.md#tech-stack))
  - **Design direction** — visual tone, key interactions, accessibility targets
  - **Success metrics** — measurable outcomes (adoption, engagement, revenue, performance)
  - **Risks and assumptions** — known unknowns, dependencies, constraints
  - **Open questions** — items deferred for later discovery or stakeholder input

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Discovery interrogation protocol, PRD sections and templates, quality checklist |
| [rule.md](./rule.md) | Constraints — question minimum, no writing before discovery, PRD must be complete |

## Cursor Command

Pair this agent with `/prd-writer` at `.cursor/commands/prd-writer.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).
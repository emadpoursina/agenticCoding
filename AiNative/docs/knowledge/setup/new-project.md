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

- Backend and auth
- Frontend and framework
- Database
- DevOps (GitHub, Docker, deployment)
- Third-party services (payments, AI, etc.)
- Constraints and out-of-scope work

### PRD

1. Context
2. User journey
3. Page or screen list
4. Tech stack
5. Design direction

## Setup and enrollment

> **Status: target flow — not wired into the current install.** The Hermes
> install provides native `hermes project` and `hermes kanban` commands, but
> no project is enrolled and no automated onboarding operation exists yet.
> Treat this section as the intended flow, not a procedure that runs today.

### 1. Create the repository

Create the GitHub repository and clone it under the Hermes workspace root
(default `/opt/data/mnt/workspace`). Use `<workspace-root>/<project-id>`, with
the project ID derived from the repository name. Set the correct default branch
before enrolling.

### 2. Register the project in Hermes

Register the repository as a named Hermes project and give it a board:

```bash
hermes project create <name> <workspace-root>/<project-id>
hermes kanban init
hermes project bind-board <name> <board-slug>
```

Verify both are readable before continuing (`hermes project show <name>`,
`hermes kanban boards`). Registration records the project and its board; it
does not scaffold the application or create work cards.

The onboarding scaffold (only missing `README.md`, `AGENTS.md`,
`.ainative/project.yaml`) is the intended next step once the enrollment
operation is wired. Until then, create those files by hand or ask Hermes to
draft them, and never overwrite existing content. Do not push a scaffold commit
unless you explicitly intend to publish it.

### 3. Make the repo ready (target job)

The intended flow is a `job` card with `## Skill: project-bootstrapper` and a
reference to the PRD. The [project-bootstrapper](../../agents/project-bootstrapper/)
confirms ambiguous stack or layout choices with you, scaffolds the app,
declares dependencies and real `validation_commands`, and fills project rules
in `AGENTS.md`. It writes no feature code, runs no installs or tests, and does
no Git publishing.

Review the job result and make the publish decision. Once the bootstrap is
published, use Kanban cards for all further work. PRD-to-card import is an
optional convenience; the normal workflow is to define the desired work
directly as cards.

## Development

The card's `## Path` selects the workflow; internal workflow stages are not
Kanban cards. See the [target feature loop](../../systems/feature-loop.md).

- `feature` — desired outcome; full spec/plan/implementation/review flow.
- `change` — a small, already-specified code change.
- `job` — one named skill, such as project bootstrap or PRD writing.

In the target design Hermes dispatches one worker session per agent state,
keeps workflow state outside the Kanban work items, and parks for operator
decisions when needed. The current install runs none of this yet; the UAT
policy is still being refined and is not an onboarding prerequisite.

## Design

- Style design guide
- Buttons
- Typography

## Local services

[Local shared services](./local-shared-services.md) documents MariaDB,
MongoDB, and Adminer via Docker. Create a database per project.

## Deployment

Deploy checklists and release flow: [release-management-system.md](../../systems/release-management-system.md) — especially [Release Questions](../../systems/release-management-system.md#-release-questions) (before/after setup, backward compatibility).

<!-- Add stack-specific deploy steps here as you refine the stack. -->

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

### 1. Create and clone the repository

Create the GitHub repository, then clone it under the workspace root configured
for Hermes. The expected directory is `<workspace-root>/<project-id>`; by
default the project ID is derived from the repository name. Set the correct
default branch before enrolling. Clone to that exact directory so the Hermes
CLI reuses the checkout you prepared.

Hermes can clone a missing workspace itself. If you clone it first, onboarding
reuses it only when its `origin` matches the requested `OWNER/NAME`.

### 2. Add it to Hermes

Create or connect the native Hermes project and board first if needed. Then
preview and enroll:

```bash
python -m hermes_kanban --config /path/to/default.yaml \
  --onboard OWNER/NAME --branch DEFAULT_BRANCH --dry-run

python -m hermes_kanban --config /path/to/default.yaml \
  --onboard OWNER/NAME --branch DEFAULT_BRANCH
```

Onboarding resolves or creates the native Hermes project, checks that its
Kanban board is readable, records the project in Hermes, and creates only
missing `README.md`, `AGENTS.md`, and `.ainative/project.yaml` files. It is
idempotent and fails closed on identity or workspace conflicts. The scaffold
is committed locally; do not push it unless you explicitly intend to publish
the scaffold commit. Leave `--push-scaffold` off by default.

`--dry-run` is read-only: it does not create the native Hermes project or its
board. The matching project and readable board must already exist for the
preview to complete.

If the board check fails, create or connect the board in Hermes and retry.
Review the generated files after enrollment. The manifest initially contains
a placeholder validation command, so ordinary work must wait for the
bootstrap job below.

### 3. Make the repo ready through a Kanban job

Create a `job` card with `## Skill: project-bootstrapper` and a reference to
the PRD. The repo must already be enrolled. The [project-bootstrapper](../../agents/project-bootstrapper/)
confirms ambiguous stack or layout choices with you, scaffolds the app,
declares dependencies and real `validation_commands`, and fills project rules
in `AGENTS.md` while preserving Hermes's control-plane section. It writes no
feature code, runs no installs or tests, and does no Git publishing.

Review the job result and make the publish decision. Once the bootstrap is
published, use Kanban cards for all further work. PRD-to-card import is an
optional CLI convenience; the normal workflow is to define the desired work
directly as cards.

## Development

The card's `## Path` selects the workflow; internal workflow stages are not
Kanban cards. See the [live feature loop](../../systems/feature-loop.md).

- `feature` — desired outcome; full spec/plan/implementation/review flow.
- `change` — a small, already-specified code change.
- `job` — one named skill, such as project bootstrap or PRD writing.

Hermes dispatches one Pi session per agent state, keeps workflow state outside
the Kanban work items, and parks for operator decisions when needed. The UAT
policy is still being refined; it is not an onboarding prerequisite.

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

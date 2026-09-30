# Project rules template

Use this as source material for the project-specific section of a managed
repo's `AGENTS.md`. Keep any existing project control-plane or agent-rules
section intact, and replace every placeholder with verified project facts.
Keep the result short enough for a worker to read at the start of a task.
(Project enrollment and dispatch are target methodology; see
[new-project.md](../knowledge/setup/new-project.md).)

```markdown
# Project rules — [PROJECT_NAME]

## Project context

- **Purpose:** [What the project does]
- **Stack:** [Languages, frameworks, database, infrastructure]
- **Layout:** [Important source, test, and configuration directories]

## Workflow

- Work is submitted through this project's Hermes Kanban board.
- Follow the card's `## Path` and the workflow stage assigned by Hermes.
- Keep `validation_commands` in `.ainative/project.yaml` accurate; the tester
  state runs them for managed work.
- For a `feature`, follow the spec/plan/tasks workflow and its reviews. A
  `change` is already specified; a `job` runs only its named skill.
- Ask rather than guessing when a consequential project decision is unclear.
- Update related project documentation when behavior or interfaces change.

## Code and design constraints

- [Existing naming, formatting, layering, and architectural conventions]
- [Input validation, error handling, logging, accessibility, or security rules]
- [Database migration and compatibility requirements]
- Prefer existing project abstractions; justify new dependencies.

## Project-specific notes

- [Domain rules, data ownership, important integration boundaries]
- [How to run development services or focused tests]

## Out of scope

- [Explicitly excluded systems, paths, and operations]
```

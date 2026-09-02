# Contract: Operational project manifest

**Feature**: `002-project-registry` | **Default path**: `.ainative/project.yaml`

Project-side structured source. The control plane reads this file in place; it does not copy it. If the operational record sets `manifest`, that project-relative path is used instead of the default, and this default file is not required.

Parser subset: see [research.md](../research.md) §5. Full YAML is not promised.

## Document shape

```yaml
name: fixture-project
description: Disposable V0 fixture  # optional
repository: github.com/example/fixture
default_branch: main

workflow:                 # optional
  default: piv

validation:
  commands:
    - uv run pytest

development:              # optional
  commands:
    - uv run ruff check src tests

ai:                       # optional
  context:
    - docs/notes.md
```

## Required

| Field | Meaning |
|---|---|
| `name` | Project-side name (wins over operational name in context) |
| `repository` | Project-side repository declaration (does not retarget enrollment) |
| `default_branch` | Project-side default branch (wins over operational) |
| `validation.commands` | Non-empty list of exact command strings. The loader MUST NOT invent commands if this is missing or empty |

## Optional

| Field | Meaning |
|---|---|
| `description` | Free text |
| `workflow.default` | Workflow name string (returned, not executed this phase) |
| `development.commands` | List of command strings; omit the block if unused |
| `ai.context` | List of project-relative files to load as text. Each is required if listed |

## Path rules for `ai.context` entries

- Relative to the project location
- MUST stay inside the project root after resolve
- Missing, unreadable, or out-of-root → context load fails
- Returned as path + unmodified UTF-8 text

## Non-goals

- The file is not a task list, Kanban board, or methodology copy
- Conventional slots (`README.md`, `AGENTS.md`, …) are separate from this file; they are not declared here unless also listed under `ai.context`
- Tooling files (`pyproject.toml`, …) are discovered by closed-set name at the project root; they are not listed in this manifest

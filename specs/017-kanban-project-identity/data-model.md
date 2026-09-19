# Data Model: Kanban Project Identity Mapping

**Feature**: `017-kanban-project-identity`

This feature adds one configuration field and one in-memory resolution
index. It adds no database, table, overlay schema field, or native-board
write. The native `kanban.db` remains read-only and `projects.db` is never
read at runtime.

## ProjectRecord aliases

**Entity**: `ProjectRecord` (existing; one new field)

| Field | Type | Rules |
|---|---|---|
| `id` | string | Existing operational key. Non-empty, not path-like, unique. |
| `kanban_project_ids` | tuple of strings | New. Zero or more declared native ids that resolve to this project. Each non-empty, non-path-like, unique across all projects and aliases, and never equal to any project's operational `id`. Defaults to `()`. |

Config shape:

```yaml
projects:
  - id: ich-mag-dich
    name: emadpoursina/ich-mag-dich
    repository: github.com/emadpoursina/ich-mag-dich
    location: /workspaces/ich-mag-dich
    default_branch: master
    kanban_project_ids:
      - p_f1577341
```

A scalar is accepted and normalized to a one-element tuple.

## Canonical id resolution

**Entity**: `ProjectRegistry`

| Member | Type | Rules |
|---|---|---|
| `_by_id` | mapping | Existing: operational id → record. |
| `_by_kanban_id` | mapping | New: declared alias → record. |
| `canonical_id(value)` | method | Returns `value` when it is an operational id, the operational id of a declared alias, otherwise raises `UnknownProjectError`. |

Resolution is exact string equality. There is no case folding, prefix, or
fuzzy match.

## Card project identity

**Entity**: board `BoardTask.project_id`

```text
native row project_id ──▶ resolver(raw) ──▶ BoardTask.project_id
                                     │
                  declared alias ────┤──▶ operational id
                  operational id ────┤──▶ unchanged
                  undeclared id ─────┴──▶ unchanged (fail-closed later)
```

The resolver wrapper used by the live board returns the raw value when
resolution raises, so an undeclared id reaches the existing
`resolve_eligible_project` gate unchanged and fails closed exactly as
before.

## Invariant

After the board boundary, no operational artifact carries a native id as a
project identity. Specifically:

- `WorkflowRecord.project_id` and `WorkflowRecord.task.project_id`;
- overlay `overlay.json`;
- prepared worktree path `<workspace_root>/<operational-id>/<task>`;
- `CorrelationIdentity.project_id`;
- publish identity passed to the GitHub boundary; and
- Telegram `/status`, `/tasks`, `/blockers`, and `/projects` output.

## Failure state

```text
card project_id
   │
   ├── declared alias / operational id ──▶ canonical operational id ──▶ workflow
   │
   └── undeclared id
           ├── --task      ──▶ UnknownProjectError (fail closed, no writes)
           └── --next-ready ──▶ skipped; if nothing else is ready,
                                NoReadyTaskError naming the unmapped id
```

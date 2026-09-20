# Contract: Kanban Project Identity

This feature defines a local Python/filesystem contract. It adds no HTTP
API, second project/task store, or native `projects.db` read.

## Configuration contract

Each `projects` entry MAY declare a native-id alias list:

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

Rules enforced at registry construction:

1. each alias is a non-empty string and not path-like;
2. aliases are unique within a project;
3. no alias equals any project's operational `id`; and
4. no alias equals another project's alias.

Violation raises `InvalidProjectConfigError`. A scalar value is accepted
and normalized to a one-element tuple.

## Registry contract

`ProjectRegistry` exposes:

```python
canonical_id(project_id: str) -> str
```

- an operational id returns itself;
- a declared alias returns its operational id;
- anything else raises `UnknownProjectError`.

`get_project`, `resolve_eligible_project`, and `load_project_context`
accept either form and behave identically to the operational id.

## Board contract

`SqliteTaskBoard` accepts an optional resolver:

```python
SqliteTaskBoard(db_path, *, resolve_project_id: Callable[[str], str] | None = None)
```

- when a resolver is present and the row `project_id` is a non-empty
  string, `BoardTask.project_id` is the resolver's output;
- a resolver that cannot map an id returns the raw value;
- without a resolver, behavior is unchanged; and
- the database is still opened read-only and never written.

## Native board resolution contract

`runtime.build_live_orchestrator()` resolves the native database as:

1. `HERMES_KANBAN_DB` when set;
2. `HERMES_HOME/kanban/boards/<operational-id>/kanban.db` (Hermes 0.21
   per-board layout) for the first enrolled project whose file exists;
3. `HERMES_HOME/kanban.db` (legacy single-board layout) otherwise.

## Harness result contract

Advisory result paths are sanitized instead of rejecting a finished run:

- `artifacts` accept objects `{kind, relative_path}` or bare path strings;
- artifact, change, and output-reference entries that are not normalized
  relative paths inside the worktree are dropped; and
- status, reason, questions, and resume context remain strict.

## Orchestration contract

- `run_workflow` and `run_next_workflow` operate on canonical ids only.
- `resume_workflow` canonicalizes its incoming `project_id` before
  comparing to the parked record.
- Restart recovery canonicalizes a legacy overlay `project_id` before the
  board comparison and reclaim path math.
- When no task is ready and at least one card was skipped for an unenrolled
  project id, `NoReadyTaskError` names the unmapped id(s). The error type
  and exit behavior are unchanged.
- No push, pull request, or board write occurs for an unmapped id.

## Diagnostic contract

`--doctor` includes each enrolled project's declared aliases as metadata:

```json
{
  "configured_projects": ["..."],
  "project_kanban_ids": {"ich-mag-dich": ["p_f1577341"]}
}
```

The diagnostic remains body-free and secret-free and does not query
`projects.db`.

## Operator runbook contract

```bash
# 1. Read the native id once (inside the container).
docker exec hermes-personal-agent \
  sqlite3 /opt/data/projects.db "select id, slug from projects;"

# 2. Declare it under the enrolled project, then recreate the container.
docker compose up -d --force-recreate

# 3. Verify the mapping and that a card is selectable.
docker exec hermes-personal-agent \
  python -m hermes_kanban --config /opt/personal-agent/config/default.yaml --doctor
docker exec hermes-personal-agent \
  python -m hermes_kanban --config /opt/personal-agent/config/default.yaml --next-ready
```

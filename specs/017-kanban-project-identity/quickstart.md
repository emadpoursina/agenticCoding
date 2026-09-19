# Quickstart: Kanban Project Identity Mapping

This guide validates native-to-operational project id mapping end to end. It
uses a temporary `kanban.db` for automated checks and the existing Hermes
container for the operator path. It does not require a live model, GitHub
push, pull request, or production repository.

## Prerequisites

- Python 3.12 and `uv`
- Docker Compose for the container check
- The repository at `/Users/emad/Projects/playground/agenticCoding`
- A disposable Hermes home/workspace for any live check

Keep credentials and secrets out of config, fixtures, and diagnostics.

## 1. Run focused identity checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest tests/test_project_registry.py tests/test_kanban_project_identity.py
uv run ruff check src tests
```

Focused checks must cover:

- a declared alias resolves to the operational id via `canonical_id`,
  `get_project`, `resolve_eligible_project`, and `load_project_context`;
- duplicate aliases, alias/operational-id collisions, path-like aliases, and
  empty aliases fail at construction;
- a card carrying a declared alias is selected by `run_next_workflow` and
  runs the enrolled project;
- the worktree is created under `<workspace_root>/<operational-id>/<task>`;
- the overlay record, correlation identity, and publish identity use the
  operational id;
- an unmapped id fails closed and is named in the no-ready error;
- a near-miss alias does not resolve; and
- a legacy overlay stored with an alias still reclaims.

## 2. Run the complete Hermes checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest
uv run ruff check src tests
```

The existing harness, orchestrator, workspace, startup-context, and
read-only AiNative checks must continue to pass.

## 3. Declare the native id once

Read the native id from Hermes `projects.db` (inside the container), then
declare it under the enrolled project:

```bash
docker exec hermes-personal-agent \
  sqlite3 /opt/data/projects.db "select id, slug from projects;"
```

Edit `personalAgent/config/default.yaml`:

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

The config mount is read-only in the container, so this is a repository
change followed by a recreate.

## 4. Recreate and inspect the mapping

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
docker compose up -d --force-recreate
docker exec hermes-personal-agent \
  python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --doctor
```

Expected result: the doctor output lists `project_kanban_ids` for the
enrolled project and still prints no file bodies or secrets.

## 5. Verify selection

```bash
docker exec hermes-personal-agent \
  python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --next-ready
```

Expected result: a card whose native `project_id` matches the declared alias
is selected and the harness starts. The worktree appears under
`/workspaces/ich-mag-dich/<task>`, not under the native id.

## 6. Verify fail-closed reporting

Seed a disposable card whose `project_id` is an undeclared native id and run
`--next-ready` again. Expected result: the command reports the unmapped id
and selects no task; no push, pull request, or board write occurs.

## Completion criteria

1. Focused and complete Hermes checks pass.
2. The declared alias selects and runs the enrolled project.
3. Worktree, overlay, and publish identities use the operational id.
4. Unmapped ids fail closed and are named.
5. `--doctor` lists declared aliases without secrets or file bodies.

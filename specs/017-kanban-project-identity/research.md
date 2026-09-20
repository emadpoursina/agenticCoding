# Research: Kanban Project Identity Mapping

**Feature**: `017-kanban-project-identity`

## Findings

### 1. Where the two identities are introduced

- The operational id is `ProjectRecord.id`, parsed from the `projects`
  block in `config/default.yaml` (`projects.py` `load_project_entries`,
  `_validate_records`). It is the key for `_by_id` and the value returned by
  `resolve_eligible_project` / `load_project_context`.
- The native id is `tasks.project_id` in `kanban.db`, surfaced verbatim by
  `board.py` `SqliteTaskBoard._task`:
  `project_id=str(row["project_id"] or "").strip()`.
- Native `projects.db` assigns ids as `"p_" + hex` and exposes no supported
  command to choose or change one. The enrolled project's native id is
  `p_f1577341`; its slug is `ich-mag-dich`.

### 2. Where the mismatch bites

- `orchestrator.py` `run_workflow` calls
  `registry.resolve_eligible_project(project_id)` on the board value. With
  `p_f1577341`, `get_project` raises `UnknownProjectError` (exact `_by_id`
  lookup, `projects.py` `get_project`).
- `run_next_workflow` catches that error and `continue`s, so the card
  disappears and the caller sees `NoReadyTaskError("no ready task")`.
- `runtime.py` `main` for `--task` reads the card and passes
  `task.project_id` straight into `run_workflow`, so the same failure occurs
  on the explicit path.

### 3. Why registry-only alias resolution is not enough

Many seams key off the passed id rather than `project.id`:

- `orchestrator.py` `_reclaim` computes
  `workspace_root / record.project_id / task_id`.
- `executor.py` `start_harness` computes
  `workspace_root / project_id / task_id` and compares it to the inspected
  worktree.
- `workspace.py` `_reuse_or_refuse` and `_existing_copy` compare against
  `workspace_root / project_id / task_id`.
- `orchestrator.py` `_board_record` and `run_workflow` compare
  `task.project_id` to `record.project_id` / the passed id.

If the native id is accepted but passed through, these comparisons disagree
with the worktree created under `project.id`, producing a workspace-boundary
mismatch or a blocked reclaim. Therefore the fix must canonicalize at the
native-store boundary so the native id never travels further.

### 4. Options considered

| Option | Verdict | Reason |
|---|---|---|
| Rewrite the native project id to `ich-mag-dich` | Rejected | Direct state write into Hermes `projects.db`; unsupported and out of bounds. |
| Stamp the operational id onto the card row | Rejected | Direct write to `kanban.db`, which is read-only; duplicates task SoT. |
| Read `projects.db` at runtime to derive the mapping | Rejected | Couples the bridge to a Hermes internal schema; adds a second DB read path. |
| Declare aliases in operational config and canonicalize at the board | **Chosen** | Explicit, validated, versioned, no native write, one translation point. |
| Display-name / fuzzy matching in the registry | Rejected | Enrolled identity must stay exact; `--smoke` already matches by `ProjectRecord.name`. |

### 5. Legacy overlay behavior

Before the fix no record could be written with the native id, because
resolution failed first. A pre-fix overlay can therefore hold only the
operational id. Still, canonicalizing `record.project_id` defensively in
reclaim is cheap and makes recovery robust if an id form ever changes; it
also covers an overlay written by a future/older build.

### 6. Fail-closed reporting

`run_next_workflow`'s skip is correct safety behavior; the missing piece is
visibility. Collecting the skipped card project ids and naming them in the
`NoReadyTaskError` keeps the same control flow and error type while removing
the "no ready task" dead end.

## Live-verification findings (2026-09-20)

### 7. Hermes 0.21 stores one database per board

The 0.20 discovery assumed a single `kanban.db`. On the 0.21 install the
enrolled project's board database lives at
`kanban/boards/<board-slug>/kanban.db`; `HERMES_HOME/kanban.db` is the
(empty) `default` board. Cards created on the project board were therefore
invisible to the bridge. The live board now resolves per enrolled project
first, with the legacy single-database layout as fallback and
`HERMES_KANBAN_DB` still overriding both.

### 8. Live project id is already reconciled

A 2026-09-17 session rewrote `projects.id` `p_f1577341` → `ich-mag-dich`
directly (the original diagnosis's first option, done outside this code).
The declared alias is dormant but kept: if the project is ever recreated,
Hermes assigns a fresh `p_…` id and the alias mechanism covers it without
another manual state write.

### 9. Model schema drift on harness results

Live Pi runs returned `artifacts` as bare path strings and
`changes`/`output_reference` as descriptive text, so two otherwise
successful runs were discarded at the strict result gates. Advisory paths
are now sanitized (validated, invalid entries dropped) instead of rejecting
the run; status, reason, and questions stay strict.

## Decisions

1. Mapping source: `kanban_project_ids` alias list on each project entry.
2. Translation point: `SqliteTaskBoard` (the only reader of native ids).
3. Resolution rule: exact match only; unknown ids are left untouched so the
   existing gates fail closed.
4. Diagnostics: `--next-ready` names unmapped ids; `--doctor` lists declared
   aliases.
5. No new dependency, table, or native write.

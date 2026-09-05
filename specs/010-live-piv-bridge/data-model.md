# Data Model: Live Hermes PIV Bridge

**Feature**: `010-live-piv-bridge` | **Date**: 2026-09-05

Extends 009. No second task store. No native Kanban writes. `BoardTask` remains the read model. Execution truth stays on the overlay (`WorkflowRecord`). Types remain frozen dataclasses.

## Native Kanban file

**Entity**: existing Hermes board file

| Field | Type | Rules |
|---|---|---|
| path | `Path` | `{HERMES_HOME}/kanban.db`. Required on the live entry. MUST exist and be readable. MUST NOT be created by this feature. |
| engine | SQLite | Installed Hermes schema (`tasks`, `task_links`, …). Read-only connection (`mode=ro`). |

**Validation**: Missing `HERMES_HOME`, missing file, or unreadable/corrupt DB → live-entry error at the trust boundary. 0 agent runs. MUST NOT insert rows to “repair.”

**Relationships**: Sole source of *what* the work is. Overlay is *how the run is going*. One file; 0 extra task tables.

## Native task row (read-only)

**Entity**: one `tasks` row plus body parse

See [research.md](./research.md) §2 for column → `BoardTask` mapping. Adapter MUST NOT UPDATE/INSERT/DELETE.

## Board task (delta)

`BoardTask` from 005 plus:

| Field | Type | Rules |
|---|---|---|
| `column` | `str` | Native `tasks.status`. Empty string on `MemoryTaskBoard` fixtures (eligible if other 005 rules pass). Live adapter always sets a native status. |

Unchanged: problem, expected result, platform, AC, notes, deps, owner, reviewer, priority `P0`–`P3`, `created_at`, `complete`. Orchestrator still MUST NOT rewrite those fields.

**Completeness (live)**: required body headings present; priority heading exact `P0`–`P3`; `project_id` non-empty. Incomplete → not eligible for next-ready; named start fails at the boundary.

## Ready set (derived)

A live card is eligible for **next-ready** when all of:

1. `column` in `{todo, ready}` (installed Ready / To Do).
2. Required fields present (same as named-start completeness).
3. Existing 005 gates: enrolled eligible project, valid priority, dependencies `complete`.

Selection: `P0` then `P1` then `P2` then `P3`, then oldest `created_at`. At most one. Empty set → `NoReadyTaskError`.

**Named start**: same completeness; `column` in `{todo, ready}` **or** (`column == running` **and** task id equals `allow_running_task_id` from the worker env). Wrong project → `TaskProjectMismatchError`. Missing id → `UnknownTaskError`.

## Live board adapter

**Entity**: `SqliteTaskBoard`

| Operation | Rules |
|---|---|
| `get(task_id)` | Read one row; parse body; map fields; unknown id → `UnknownTaskError`. |
| `list()` | Read all rows (needed for dependency `get`); do not filter in `list` so deps in `done` remain visible. Eligibility is orchestrator-side. |
| writes | None. Connection read-only. |

**Forbidden**: constructing this adapter against a second path “copy of the board”; using `MemoryTaskBoard` on the live entry.

## Dispatcher / runtime entry

**Entity**: one process start surface

| Input | Rules |
|---|---|
| config path | Existing operational YAML |
| mode | `run` (named or next-ready), `resume`, `smoke` |
| named id | From argv or `HERMES_KANBAN_TASK` |
| next-ready | No id; fail closed if none eligible |
| smoke name | Explicit `owner/name`; empty-by-default env |

Does not store state of its own. Calls `become_ready` then existing public operations.

## Smoke identity

**Entity**: disposable repository gate

| Field | Type | Rules |
|---|---|---|
| `requested` | `str` | Required non-blank `owner/name` |
| `github_name` | `str` | Parsed from the enrolled project’s git remote (github.com SSH). |
| `enrolled_name` | `str` | `ProjectRecord.name` |

Proceed only if `requested == github_name == enrolled_name`. Else refuse, 0 pushes.

## Unchanged entities

`WorkflowRecord`, overlay snapshot, `PullRequestIdentity`, messaging `pr_created` occurrence `{run_id}:pr_created`, work branch `feature/task-<id>`, one V0 slot, `LiveGitHost` / `MemoryGitHost`.

Secrets MUST NOT appear on any of these records.

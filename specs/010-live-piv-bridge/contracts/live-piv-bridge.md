# Contract: Live Hermes PIV Bridge

**Feature**: `010-live-piv-bridge` | **Packages**: `hermes_kanban.board`, `hermes_kanban.runtime`, `hermes_kanban.orchestrator`

Extends [009 restart recovery](../../009-restart-recovery/contracts/restart-recovery.md). Same three public start/resume operations. This contract adds the **read-only live board**, the **dispatcher/CLI entry**, **column eligibility**, and the **named-repo smoke gate**. Merge, deploy, a second bot, a second task store, and AiNative writes remain out of contract.

Types: [data-model.md](../data-model.md). Reuse overlay, GitHost, messaging, executor, registry, workspace.

## Live board

```python
class SqliteTaskBoard:
    def __init__(self, db_path: Path) -> None: ...
    def get(self, task_id: str) -> BoardTask: ...
    def list(self) -> tuple[BoardTask, ...]: ...
```

Open `db_path` with SQLite **read-only**. Missing/unreadable file → visible error at construction or first read (implementation may fail at open). `get` maps native row + body headings per [research.md](../research.md). MUST NOT INSERT/UPDATE/DELETE. MUST NOT create `kanban.db`.

`MemoryTaskBoard` remains check-only. The live entry MUST NOT construct it.

## Production entry

```python
def build_live_orchestrator(config_path: Path, **kwargs) -> PivOrchestrator: ...

def main(argv: list[str] | None = None) -> int: ...
```

`build_live_orchestrator`:

- Requires `HERMES_HOME` → board `{HERMES_HOME}/kanban.db`.
- Constructs `SqliteTaskBoard`, omitted `git_host` → `LiveGitHost`, messaging as 008 (`HermesTelegramChannel` when enabled + home chat; else skip-send).
- Calls existing `become_ready`.
- If a caller passes `MemoryTaskBoard` → fail closed (`MissingTaskBoardError` or equivalent live-board error).

`main` is the **one** start surface (Hermes worker and CLI). Subcommands:

| Invocation | Behavior |
|---|---|
| named task (`--task` or `HERMES_KANBAN_TASK`) | `run_workflow(project_id, task_id)` after board `get` supplies `project_id` |
| `--next-ready` | `run_next_workflow()` |
| `--resume PROJECT TASK OPTION` | `resume_workflow` |
| `--smoke --repo owner/name` | smoke gate then live publish path |

No background worker. No Telegram-only start. No second orchestrator.

Checks MAY still call `PivOrchestrator.from_config(..., task_board=MemoryTaskBoard(...))`.

## Eligibility (orchestrator trust boundary)

`BoardTask.column`: empty → fixture (005 behavior). Native values from installed status set.

`run_next_workflow`: skip cards whose `column` is non-empty and not in `{todo, ready}`. Then existing priority/oldest sort. None left → `NoReadyTaskError` (0 agent runs).

`run_workflow`: refuse non-empty `column` outside `{todo, ready}`, except `running` when `task_id == allow_running_task_id` (worker claim). Incomplete required fields / invalid priority / unmet deps — existing errors. Wrong column → `OrchestratorError` subclass visible at the boundary (name is an implementation choice; MUST be distinct from silent skip).

## Wait / publish / notice

Unchanged wait-returns: `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`.

On `PR_CREATED`, existing `_emit("pr_created", …)` — same kind, same already-connected chat. 0 new event kinds. Send failure does not close the PR.

Commit/push only on `feature/task-<id>`. `forbidden(merge|approve|deploy|protected-push)` unchanged. 0 methodology writes.

## Smoke

Before `push_feature_branch` / `upsert_pull_request`:

1. Disposable `owner/name` present and non-blank.
2. Equals git remote github.com `owner/name`.
3. Equals enrolled `ProjectRecord.name`.

Any miss → visible error, 0 pushes, 0 PR opens. Matching name → feature branch only, never `main`/`master`.

Pytest MUST prove the refuse path with a recording `MemoryGitHost` (0 `pushes`). MUST NOT require github.com, live Telegram, or the operator’s real `kanban.db`.

## Isolation

- Temp SQLite fixtures for adapter tests (copy schema, not production data).
- `MemoryGitHost` for automated publish assertions.
- Live smoke is operator-invoked and documented; credentials stay outside git.

## Errors (additions)

| Condition | Result |
|---|---|
| Live entry without `HERMES_HOME` / board file | Visible construction error; 0 runs |
| `MemoryTaskBoard` on live entry | Fail closed |
| Unknown / incomplete / wrong-column named start | Existing or column error; 0 runs |
| Next-ready empty eligible set | `NoReadyTaskError` |
| Smoke name missing or mismatch | Visible error; 0 pushes |

Prior 005–009 errors unchanged.

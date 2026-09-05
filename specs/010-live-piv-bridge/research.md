# Research: Live Hermes PIV Bridge

**Feature**: `010-live-piv-bridge` | **Date**: 2026-09-05

Phase 0 resolves Technical Context against `spec.md` (clarify session 2026-09-05; remaining skip-style answers already in the spec), the constitution, whole-project `scratch/implimentation.md` (this slice only — live board wiring, not later milestones), prior specs `001`–`009`, live `personalAgent` contracts, and the **installed** Hermes image (`hermes-agent:local`, `hermes_cli` reports **0.21.0**; Kanban schema matches the 0.20 discovery notes). No `[NEEDS CLARIFICATION]` remains.

This is **not** a rewrite of PIV, recovery, GitHub rules, Telegram kinds, or restart overlay. Those already exist. This slice wires live I/O.

## 1. Inspect first: what already exists

**Decision**: Do not rebuild the orchestrator. Reuse `PivOrchestrator.run_workflow` / `run_next_workflow` / `resume_workflow`, `become_ready`, `LiveGitHost` / `MemoryGitHost`, existing `pr_created` emit, overlay persist, and workspace `feature/task-<id>`. Add a **read-only** `SqliteTaskBoard`, a **minimal** runtime entry, focused pytest, a named-repo smoke gate, docs, and changelog.

**Rationale**: Spec FR-005/US4; constitution II–III; 005 `ponytail:` already named `SqliteTaskBoard` as the upgrade. Fixture E2E (`tests/test_v0_e2e.py`) already proves the in-process chain with `MemoryTaskBoard` + `MemoryGitHost`.

**Alternatives considered**:
- Second orchestrator or background poller — forbidden (FR-004).
- `MemoryTaskBoard` in production — forbidden (FR-002).
- Writing Kanban rows for run state — forbidden (read-only adapter; overlay remains execution truth).
- Calling Hermes `github-pr-workflow` skill to publish — already rejected in 007 (builder/worker-owned publish).

## 2. Installed Kanban schema (Hermes image, not docs)

**Decision**: Open the existing file `{HERMES_HOME}/kanban.db` read-only via stdlib `sqlite3`. Schema inspected on the isolated home copy (`~/.hermes/personal-agent/kanban.db`, same engine as the container mount `/opt/data/kanban.db`):

- Table `tasks`: `id`, `title`, `body`, `assignee`, `status`, `priority` (INTEGER, default 0, dispatcher tie-break `ORDER BY priority DESC, created_at ASC`), `created_at` (unix seconds), `project_id`, workspace columns, claims/heartbeats, etc.
- Table `task_links`: `parent_id`, `child_id` (dependencies).
- Closed status set from `hermes_cli/kanban_db.py`: `triage`, `todo`, `scheduled`, `ready`, `running`, `blocked`, `review`, `done`, `archived`.

**Eligible columns for this slice** (spec Ready / To Do mapped after inspection): **`todo`** and **`ready`**. Not backlog-equivalents: `triage`, `scheduled`, `blocked`, `review`, `done`, `archived`. Hermes dispatcher auto-spawn uses **`ready` only** (`has_spawnable_ready`). Our next-ready still includes `todo` as specified.

**Card body** (human-readable SoT for problem/result/platform/AC/notes): markdown headings already used in grooming (`## Problem`, `## Expected Result`, `## Platform`, `## Acceptance Criteria`, `## Technical Notes`, `## Dependencies`). Optional `## Reviewer` / `## Owner` / `## Priority` with exact `P0`–`P3`. Missing required headings → incomplete at the trust boundary (do not invent text).

**Field mapping**:

| `BoardTask` | Native source |
|---|---|
| `id` | `tasks.id` |
| `project_id` | `tasks.project_id` (must match enrolled id) |
| `problem` | body `## Problem` (not `title` alone) |
| `expected_result` | body `## Expected Result` |
| `platform` | body `## Platform` (empty if omitted) |
| `acceptance_criteria` | body `## Acceptance Criteria` |
| `technical_notes` | body `## Technical Notes` |
| `dependencies` | `task_links` where this id is child, plus body list if present (ids must exist) |
| `owner` | `tasks.assignee` (Hermes has no owner column) |
| `reviewer` | body `## Reviewer` or empty |
| `priority` | body `## Priority` exact `P0`–`P3`. Native INTEGER is **not** guessed into P0–P3 (default `0` would make every ungroomed card P0). |
| `created_at` | `tasks.created_at` as ISO-8601 UTC string |
| `complete` | `status` in `{done, archived}` (dependency gating only) |
| `column` | `tasks.status` (new optional field; empty on `MemoryTaskBoard` so existing fixtures stay eligible) |

**Rationale**: FR-001/FR-003; constitution III; spec “do not invent fields.”

**Alternatives considered**:
- Treat `title` as problem — too lossy vs the groomed body.
- Map INTEGER `0`→`P0` — invents priority on Hermes default.
- Create a second SQLite file “with the right columns” — forbidden.

## 3. Hermes 0.20/0.21 extension points (adapt, do not fork)

**Decision**: One runtime entry the **already-spawned** worker or a CLI process calls. Do **not** subscribe `on_kanban_dispatch_tick` to start PIV (observer-only; firing work there would be a second scheduler). Do **not** add a plugin that claims tasks. Do **not** fork `hermes_cli`.

Installed hooks (image): `invoke_hook` / `on_kanban_dispatch_tick` / `on_kanban_worker_spawned` / `on_kanban_worker_exited` — telemetry. Kanban **tools** (`tools/kanban_tools.py`) register when `HERMES_KANBAN_TASK` is set or the profile has the `kanban` toolset. Dispatcher spawn: `dispatch_once` claims `ready` → `running` and sets `HERMES_KANBAN_TASK`.

**Worker named-start exception**: After Hermes claims, native `status` is `running`. Spec eligible columns are todo/ready. The worker must still start **that** id. Runtime passes `allow_running_task_id` from `HERMES_KANBAN_TASK` into the orchestrator so named start of the claimed id is allowed; next-ready still never selects `running`. The adapter still reports `column=running` (no lie). CLI named start without that env still refuses `running`.

**Package visibility in Docker**: Compose today does not mount `personalAgent`. Implementation MUST mount the package (or install it) into `hermes-personal-agent` so `python -m hermes_kanban` works with `HERMES_HOME=/opt/data`. That is wiring, not a Hermes fork.

**Rationale**: FR-004/FR-005; clarify “one dispatcher entry”; constitution III.

**Alternatives considered**:
- New Hermes plugin package — extra product; fork risk.
- Poll `ready` from a sidecar process — second worker.
- Telegram-only start — forbidden this slice.

## 4. Production vs check construction

**Decision**:

- Checks keep injecting `MemoryTaskBoard` + `MemoryGitHost` + stand-in model (existing tests stay green).
- **Production/dispatcher entry** (`hermes_kanban.runtime`) MUST construct `SqliteTaskBoard` on `{HERMES_HOME}/kanban.db` (uri `mode=ro`). `HERMES_HOME` is already the platform env (`/opt/data` in compose). MUST NOT default to `$HOME/.hermes` or invent a path. Missing env, missing file, or unreadable DB → visible error, 0 agent runs.
- Production entry MUST refuse `MemoryTaskBoard` (type check) even if a caller tries to pass one.
- Existing `PivOrchestrator.from_config(..., task_board=...)` **keeps** accepting an injected board so 005–009 tests do not break. The new live constructor is the production path.

**Rationale**: FR-001/FR-002; 005 originally forbade guessing `kanban.db` in `from_config` — that guess is now an explicit live entry using `HERMES_HOME`, not a silent `$HOME` default.

**Alternatives considered**: Change `from_config` to always open SQLite — would break every check that injects `MemoryTaskBoard`. Dual board files — forbidden.

## 5. Next-ready selection

**Decision**: Keep existing priority then oldest `created_at` sort. Add eligibility: native `column` in `{todo, ready}` **or** empty (fixture). Required body fields present; existing completeness/deps/enrolled-project gates unchanged. Zero eligible → `NoReadyTaskError`, 0 agent runs, no poll, no fallback to `triage`/`scheduled`.

**Rationale**: Clarify session 2026-09-05; FR-004a. Hermes dispatcher sort (`priority DESC`) is a different integer scale; we sort on mapped `P0`–`P3` strings already on `BoardTask`.

**Alternatives considered**: Spawn only `ready` to match Hermes dispatcher — spec includes To Do.

## 6. Smoke gate

**Decision**: CLI/runtime subcommand (same entry) requires an **explicit** disposable identity `owner/name` (argv or env that is empty-by-default). Refuse before any `git push` / `gh pr` if:

- name missing or blank, or
- GitHub remote `owner/name` ≠ that name, or
- enrolled `ProjectRecord.name` ≠ that name.

Allowed smoke: `LiveGitHost` against that repo’s **feature** branch only. Automated pytest of the gate uses no network: missing name → 0 push calls on a recording host.

**Rationale**: FR-015; human authority; `ich-mag-dich` display name today is not `owner/name`, so default smoke refuses that enrollment — correct.

**Alternatives considered**: Match enrolled `id` only — weaker than the clarify answer. Silently pick the first enrolled project — forbidden.

## 7. Tests, tools, docs

**Decision**: New `personalAgent/tests/test_live_piv_bridge.py`. Temp SQLite file with the installed `tasks` / `task_links` shape (not the operator’s live file). `MemoryGitHost` for publish/PR. Existing suite + `uv run ruff check src tests` must stay green. No new dependencies. Python 3.12 via uv. Update `personalAgent/README.md` + `docs/` as needed and root + package changelogs at **implement** time; this plan version records design artifacts in the playground changelog.

**Rationale**: FR-013/FR-014/FR-016; constitution IV.

**Alternatives considered**: Point tests at `~/.hermes/personal-agent/kanban.db` — not hermetic; forbidden as the only gate.

## 8. Language / storage / scale (Technical Context)

| Topic | Decision |
|---|---|
| Language | Python 3.12 (`>=3.12,<3.14`), uv, existing package |
| Dependencies | None new. `sqlite3` stdlib read-only URI |
| Storage | Existing `kanban.db` + existing overlay dir. 0 new task DBs |
| Testing | pytest + ruff; temp fixtures; `MemoryGitHost` |
| Platform | Host pytest; live path inside `hermes-personal-agent` with `HERMES_HOME=/opt/data` |
| Performance | One blocking start; no throughput target |
| Scale | One V0 slot (unchanged) |

All prior NEEDS CLARIFICATION items are closed by the spec session and this inspection.

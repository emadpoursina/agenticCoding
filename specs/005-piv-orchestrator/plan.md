# Implementation Plan: PIV Orchestrator

**Branch**: `005-piv-orchestrator` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-piv-orchestrator/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phases 1–2 can enroll a project, prepare an isolated working copy, and run one methodology agent once. Nothing yet chains those runs. This phase implements a **PIV orchestrator** in the existing `hermes_kanban` package: `run_workflow` / `run_next_workflow` / `resume_workflow` as the trust boundary, discovery → planning → implementation → validation with no plan-approval gate, an explicit execution-state overlay, a human-decision pause when discovery/planning return a questions list (items labeled A/B/C; resume re-runs the parked step), and one-at-a-time next-ready selection from the existing task board. No second task database, no background worker, no retry, no push/PR, no Telegram, no agents added to live methodology.

Technical approach: one Python 3.12 module, stdlib + existing executor/workspace/registry/adapter, pytest contract file against disposable git + methodology + in-memory board fixtures. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib (`pathlib`, `dataclasses`, `re`) + existing `AgentExecutor`, `WorkspaceManager`, `ProjectRegistry`, `AiNativeAdapter`. Dev: pytest 9.1.1, ruff 0.16.5 (already listed)

**Storage**: Operational YAML (existing `workflow.default`, role map, model env *names*). Isolated git worktrees already created by Phase 1. In-memory `WorkflowRecord` overlay (single V0 slot). Injected `TaskBoard` for human-readable task fields (fixture in checks; live `kanban.db` reader not this phase). Hermes `kanban.db` / `projects.db` unwritten. No second SQLite file. Plan artifact remains `{workspace}/PLAN.md`

**Testing**: pytest + ruff; one contract module `personalAgent/tests/test_piv_orchestrator.py`; stand-in `ModelService` + `MemoryTaskBoard`; methodology and git fixtures as in 004; git repos created in `tmp_path`

**Target Platform**: Host pytest (macOS/Linux) and the existing Docker Compose service (`hermes-agent:local`, workspaces mounted `/workspaces`). A live model account, live Kanban gateway, and live hosting account are not required for contract checks

**Project Type**: Library (in-process orchestrator inside `hermes_kanban`). Not a CLI, HTTP service, or Hermes fork

**Performance Goals**: One blocking chain of at most four existing role executes per start/resume (plus one re-run of a parked step). No throughput target

**Constraints**: No new third-party libraries. No hardcoded provider or model names. No host-path defaults. No silent production-repo target. Isolated Hermes home unchanged. No `git push` / merge / deploy / background worker. Methodology is read-only. Other V0 items (recovery, GitHub hosting, Telegram, restart persistence) stay out of this diff. `execution.max_concurrent_tasks` stays `1` in config; the orchestrator hard-enforces one slot

**Scale/Scope**: Orchestrator + board seam + state overlay + next-ready selection only. ~one production module + one test module. Production `projects: []` and empty role model ids remain until the owner configures them

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; checklist all items checked; clarify session recorded; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Single module in existing package; reuse adapter/registry/workspace/executor; Protocol seam for fixture vs live board; no workflow engine, no background worker |
| III. Platform-native | PASS | Existing prepare + execute_role. Native Kanban remains the task SoT (fixture board is the check seam, not a second table). Overlay for states Hermes cannot represent. Do not fork Hermes or add agents to live AiNative. Do not write methodology |
| IV. Trust-boundary tests | PASS | Validate project/task/priority/deps/slot/resume at run/resume; one pytest contract file; stand-in model + fixture board so checks need no live account or `kanban.db` |
| V. Human authority | PASS | No merge/deploy/push. Park on consequential questions; humans resume with a listed letter. Tests use disposable fixtures. Default managed set stays empty |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Secrets never on records; do not touch `~/.hermes` or guess `kanban.db` paths |
| Model routing | PASS | Unchanged from 004; orchestrator does not hardcode models |
| Out-of-scope list | PASS | Recovery, GitHub push/PR, Telegram, Obsidian, concurrent workers, adding methodology agents, specs.md install: not in this plan |
| Surgical edits | PASS | Add orchestrator module + tests + re-exports; do not rewrite adapter, registry, workspace, executor, Hermes, or AiNative |

### Post-design (PASS)

Design artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) stay inside the orchestrator contract. No extra services, queues, or `execution.db`. In-memory slot + fixture `TaskBoard` is the documented ceiling (native SQLite reader and restart persistence are later phases). Native field *names* are reused on the overlay; native card `status` / body are not overwritten. Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-piv-orchestrator/
├── plan.md              # This file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── piv-orchestrator.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

Implementation lands in the existing control-plane repo `personalAgent/` (not the playground root, not AiNative).

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export public orchestrator types (keep prior exports)
│   ├── ainative.py          # unchanged this phase
│   ├── projects.py          # unchanged this phase (reuse resolve_eligible_project + load_project_context)
│   ├── workspace.py         # unchanged this phase (reuse prepare_workspace + inspect)
│   ├── executor.py          # unchanged this phase (reuse execute_role + ExecutePayload)
│   └── orchestrator.py      # orchestrator, board protocol, workflow record, errors (this feature)
├── tests/
│   ├── test_import.py       # existing — keep passing
│   ├── test_ainative_adapter.py
│   ├── test_project_registry.py
│   ├── test_workspace_manager.py
│   ├── test_agent_executor.py
│   └── test_piv_orchestrator.py
├── tests/fixtures/ainative-full/docs/agents/ # existing four role agents; do not add to live AiNative
├── tests/fixtures/projects/standard/  # existing; validation commands already declared
├── config/default.yaml          # unchanged; still projects: [] and no live model name literals
└── docker-compose.yml           # unchanged
```

**Structure Decision**: Keep the scaffold layout. Add `orchestrator.py` rather than a new package or `orchestration/` tree. Do not add a SQLite file. Do not add `builder` / `specs-planner` to the live `AiNative` checkout. Do not commit `.git` fixture repos; create them in `tmp_path`. Do not change `executor.py` (resume decision text rides on `ExecutePayload.description`).

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/piv-orchestrator.md](./contracts/piv-orchestrator.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names: `run_workflow`, `run_next_workflow`, `resume_workflow`.
- Roles in order: `discovery`, `planning`, `implementation`, `validation`.
- Default map unchanged: discovery→`scout`, planning→`specs-planner`, implementation→`builder`, validation→`tester`.
- Payload: `title`←problem, `description`←expected result (+ `Human decision: {letter} — {text}` after resume), `acceptance_criteria`←AC, `priority`←priority, `plan`←`PLAN.md` text after successful planning.
- Start prepares; execute still must not. Dirty reuse stays prepare’s error.
- Questions on discovery/planning → park with A/B/C labels; resume re-runs that role; attempt stays `1`.
- Implementation/validation questions or any `failure` / blocked-without-questions → `FAILED`, no retry.
- One slot per orchestrator instance; parked occupies it; `COMPLETED`/`FAILED` release it.
- Next-ready: skip ineligible / unmet deps / invalid priority; `P0>P1>P2>P3` then oldest; none → `NoReadyTaskError`.
- `ponytail:` in-memory overlay + fixture `TaskBoard`. Upgrade: read-only `SqliteTaskBoard` against isolated `kanban.db` when a Hermes worker is wired; persist overlay fields Hermes cannot represent in Phase 7. Still no second task table.
- Stop after orchestrator contract checks pass; do not start recovery, GitHub hosting, or Telegram.

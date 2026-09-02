# Implementation Plan: PIV Recovery

**Branch**: `006-piv-recovery` | **Date**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-piv-recovery/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phase 3 chains discovery → planning → implementation → validation and **stops on the first validation miss**. This phase adds **classification**, a **bounded recovery loop** (transient re-validate, or diagnosis → debug in the isolated copy → re-validate), **`BLOCKED`**, and **A/B human escalation** on the existing `run_workflow` / `run_next_workflow` / `resume_workflow` boundary. Validation questions park instead of failing. No second orchestrator, no native Kanban retry writes, no push/PR, no Telegram, no background worker, no methodology agents added.

Technical approach: extend `orchestrator.py` + a surgical `execute_agent(model_slot=)` and cannot-start status encoding in `executor.py`; one existing pytest module. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib + existing `AgentExecutor`, `WorkspaceManager`, `ProjectRegistry`, `AiNativeAdapter`, 005 orchestrator types. Dev: pytest, ruff (already listed)

**Storage**: Same in-memory `WorkflowRecord` overlay (single V0 slot). Native `consecutive_failures` / `max_retries` / `block_kind` unwritten. Hermes `kanban.db` / `projects.db` unwritten. No second SQLite file. Isolated git worktrees unchanged.

**Testing**: pytest + ruff; extend `personalAgent/tests/test_piv_orchestrator.py`; update cannot-start case in `personalAgent/tests/test_agent_executor.py`; stand-in `ModelService` + `MemoryTaskBoard`; TRANSIENT via `AgentExecutor` subclass in tests

**Target Platform**: Host pytest (macOS/Linux) and existing Docker Compose service. Live model / Kanban / hosting not required for contract checks

**Project Type**: Library (in-process orchestrator inside `hermes_kanban`)

**Performance Goals**: One blocking start/resume; at most original 4 role runs + 3×(diagnosis+debug+validate) + one granted `B` cycle. No throughput target

**Constraints**: No new third-party libraries. No hardcoded provider/model names. No host-path defaults. No silent production-repo target. No `git push` / merge / deploy / background worker. Methodology read-only. Recovery limit fixed at 3. Do not recover discovery/planning/original-implementation failures. Do not add debugger folders to live AiNative

**Scale/Scope**: Recovery loop + classification + blocked resume on the existing module. ~orchestrator + small executor + tests. Production `projects: []` unchanged

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; clarify session recorded; checklist 16/16; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Same module; reuse execute/prepare/board; surgical `model_slot` instead of new roles; no workflow engine |
| III. Platform-native | PASS | Overlay for retry/blocked (native retry columns exist but spec defers writes). No second task table. No Hermes fork. No live AiNative agent folders |
| IV. Trust-boundary tests | PASS | Same three public calls; one pytest contract file; stand-in model + fixture board; cannot-start vs retryable vs transient covered |
| V. Human authority | PASS | Park/blocked letter resume; no merge/deploy/push; disposable fixtures; default managed set empty |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Secrets never on records/diagnostics/briefs |
| Model routing | PASS | Diagnosis uses validation slot via `model_slot`; no model name literals |
| Out-of-scope list | PASS | Hosting, Telegram, restart persistence, concurrent workers, recovering pre-validation failures: not in this plan |
| Surgical edits | PASS | Orchestrator + small executor + tests; do not rewrite adapter/registry/workspace |

### Post-design (PASS)

Design artifacts stay inside the orchestrator/executor contract. No extra services or `execution.db`. Overlay + fixture board remains the ceiling. Cannot-start encoding and `execute_agent(model_slot=)` are the only executor edits. Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-piv-recovery/
├── plan.md
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

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export DiagnosticReport if public
│   ├── ainative.py          # unchanged
│   ├── projects.py          # unchanged
│   ├── workspace.py         # unchanged
│   ├── executor.py          # execute_agent(model_slot=); cannot-start status=failure
│   └── orchestrator.py      # classification, recovery loop, BLOCKED resume
├── tests/
│   ├── test_piv_orchestrator.py   # extend SC-007 recovery checks
│   └── test_agent_executor.py     # cannot-start encoding; model_slot
├── tests/fixtures/ainative/       # existing four agents; do not add debugger
├── tests/fixtures/projects/standard/
├── config/default.yaml            # unchanged; projects: []
└── docker-compose.yml             # unchanged
```

**Structure Decision**: Keep the 005 layout. Do not add `recovery.py` unless `orchestrator.py` is unreadable after the diff (prefer one module). Do not add agents to live `AiNative`. Do not open `kanban.db`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data Model | [data-model.md](./data-model.md) |
| Contracts | [contracts/piv-orchestrator.md](./contracts/piv-orchestrator.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names unchanged: `run_workflow`, `run_next_workflow`, `resume_workflow`.
- Diagnosis: `execute_agent(role_agents["validation"], model_slot="validation")`.
- Debug: `execute_role("implementation")` with diagnostic text on `payload.validation`.
- Re-validate: existing validation role + project commands.
- Automatic budget 3; `B` is one extra cycle, shape from last class.
- Validation/diagnosis/debug questions park; original implementation questions still fail.
- `ponytail:` overlay (not native retry columns); TRANSIENT live path waits on executor timeout.
- Stop after recovery contract checks pass; do not start GitHub hosting or Telegram.

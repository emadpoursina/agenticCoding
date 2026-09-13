# Implementation Plan: Agent Execution

**Branch**: `004-agent-execution` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-agent-execution/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phase 1 can discover methodology, enroll a project, load project context, and prepare an isolated working copy. Nothing yet runs an agent. This phase implements an **agent executor** in the existing `hermes_kanban` package: `execute_agent` / `execute_role` as the trust boundary, assembled context from existing adapters plus an optional execute payload, per-role model assignment from operational config, a stand-in model service for checks (stdlib OpenAI-compatible HTTP for a live run), structured results, a planning Markdown artifact in the isolated copy, optional local commit on the work branch, and validation status from the project’s declared commands. No PIV chain, no retry, no push/PR, no Telegram, no second task store, no agents added to live methodology.

Technical approach: one Python 3.12 module, stdlib + existing `git` CLI, pytest contract file against disposable git + methodology fixtures. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib (`pathlib`, `dataclasses`, `subprocess`, `json`, `urllib.request`, `shlex`, `os`, `re`) + system `git`. Reuse `AiNativeAdapter`, `ProjectRegistry`, `WorkspaceManager`. Dev: pytest 9.1.1, ruff 0.16.5 (already listed)

**Storage**: Operational YAML (`workflow.default`, role→agent map, `model.roles`, OpenAI-compatible env *names*). Isolated git worktrees already created by Phase 1. In-memory assembled context and execute result. Hermes `kanban.db` / `projects.db` untouched. No second SQLite file. Plan artifact is a Markdown file inside the prepared working copy only

**Testing**: pytest + ruff; one contract module `personalAgent/tests/test_agent_executor.py`; stand-in `ModelService`; methodology fixture extended with `specs-planner` and `builder`; git repos created in `tmp_path`

**Target Platform**: Host pytest (macOS/Linux) and the existing Docker Compose service (`hermes-agent:local`, workspaces mounted `/workspaces`). A live model account is not required for contract checks

**Project Type**: Library (in-process executor inside `hermes_kanban`). Not a CLI, HTTP service, or Hermes fork

**Performance Goals**: One model round-trip per execute (single-shot structured response). No throughput target

**Constraints**: No new third-party libraries. No hardcoded provider or model names in agent documents or executor source. No host-path defaults. No silent production-repo target. Isolated Hermes home unchanged. No `git push` / merge / deploy / prepare-as-side-effect. Methodology is read-only. Other V0 items (PIV orchestration, GitHub hosting, Telegram, retry) stay out of this diff

**Scale/Scope**: Agent executor + model assignment + context assembly + structured result only. ~one production module + one test module + fixture agent folders. Production `projects: []` and empty role model ids remain until the owner configures them

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; checklist all items checked; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Single module in existing package; reuse adapter/registry/workspace; Protocol seam for stand-in vs live; no ReAct loop, no new HTTP framework |
| III. Platform-native | PASS | Methodology/registry/workspace operations reused. Model routing stays config+env (Hermes-compatible OpenAI override already in `default.yaml`). No second DB. Do not fork Hermes or add agents to live AiNative |
| IV. Trust-boundary tests | PASS | Validate payload, eligibility, workspace, agent, mapping, and model assignment at execute; one pytest contract file; stand-in injected so checks need no live account |
| V. Human authority | PASS | No merge/deploy/push. Local commit only on the task work branch in the isolated copy. Tests use disposable fixtures. Default managed set stays empty |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal; `urllib.request` for optional live path |
| Secrets / isolated Hermes home | PASS | Secrets from env names in config; never in results; do not touch `~/.hermes` |
| Model routing | PASS | Role assignments are configuration values, never literals in agent documents |
| Out-of-scope list | PASS | PIV chain, retry, GitHub push/PR, Telegram, Obsidian, adding methodology agents: not in this plan |
| Surgical edits | PASS | Add executor module + tests + re-exports + fixture agents; do not rewrite adapter, registry, workspace, Hermes, or AiNative |

### Post-design (PASS)

Design artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) stay inside the execute contract. No extra services, queues, or `execution.db`. Single-shot structured model response (not a tool loop) is the documented ceiling. Native `kanban.db` is still unwritten this phase. Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-agent-execution/
├── plan.md              # This file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── agent-executor.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

Implementation lands in the existing control-plane repo `personalAgent/` (not the playground root, not AiNative).

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export public executor types (keep prior exports)
│   ├── ainative.py          # unchanged this phase (reuse get/resolve/revision/context/read-only)
│   ├── projects.py          # unchanged this phase (reuse resolve_eligible_project + load_project_context)
│   ├── workspace.py         # unchanged this phase (reuse inspect_workspace + assert_publish_allowed)
│   └── executor.py          # executor, payload, context, result, model seam (this feature)
├── tests/
│   ├── test_import.py       # existing — keep passing
│   ├── test_ainative_adapter.py
│   ├── test_project_registry.py
│   ├── test_workspace_manager.py
│   └── test_agent_executor.py
├── tests/fixtures/ainative-full/docs/agents/
│   ├── scout/               # existing
│   ├── tester/              # existing
│   ├── specs-planner/       # add (fixture only; do not add to live AiNative)
│   └── builder/             # add (fixture only)
├── tests/fixtures/projects/standard/  # existing; validation commands already declared
├── config/default.yaml      # optional commented role/model slots; do not hardcode live model names
└── docker-compose.yml       # unchanged
```

**Structure Decision**: Keep the scaffold layout. Add `executor.py` rather than a new package or `executor/` tree. Do not add `builder` / `specs-planner` to the live `AiNative` checkout. Do not commit `.git` fixture repos; create them in `tmp_path`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/agent-executor.md](./contracts/agent-executor.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names: `execute_agent`, `execute_role`.
- Roles: `discovery`, `planning`, `implementation`, `validation`.
- Default map: discovery→`scout`, planning→`specs-planner`, implementation→`builder`, validation→`tester`.
- Discovery uses the planning model assignment. Debugging slot is out of scope.
- Plan artifact path: `PLAN.md` at the isolated working copy root. Eight required section headings (see data-model).
- Execute inspects; it MUST NOT call `prepare_workspace`.
- Implementation MAY `git commit` in the isolated copy only after `assert_publish_allowed`. Forbidden: push, PR, merge, deploy, enrolled-tree edits, methodology writes.
- Validation status comes from declared command exit codes run in the isolated copy (`shlex.split`, `cwd=workspace.path`).
- `ponytail:` single-shot structured model response (files + optional commit flag). Upgrade: Hermes-native tool-using worker in a later phase.
- Stop after executor contract checks pass; do not start PIV orchestration, GitHub hosting, or Telegram.

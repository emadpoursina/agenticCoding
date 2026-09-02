# Implementation Plan: Workspace Manager

**Branch**: `003-workspace-manager` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-workspace-manager/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hermes needs an isolated place to change one project for one task without touching another task’s files, without editing the project’s protected default branch, and without guessing which run produced a result. This phase implements a **workspace manager** in the existing `hermes_kanban` package: load `workspace.root` from operational YAML, `prepare_workspace` / `inspect_workspace` / `assert_publish_allowed`, git worktrees under `{root}/{project_id}/{task_id}` on `feature/task-<task_id>`, and a correlation identity on every successful prepare. Eligibility comes from the existing project registry. No agents, models, push, PRs, Telegram, or second workspace database.

Technical approach: one Python 3.12 module, stdlib + `git` CLI, pytest contract file against disposable git fixtures. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib (`pathlib`, `dataclasses`, `subprocess`, `uuid`, `os`, `re`) + system `git`. Dev: pytest 9.1.1, ruff 0.16.5 (already listed)

**Storage**: Operational YAML (`workspace.root` in caller-supplied config). Git worktrees on disk under that root. In-memory prepare/inspect records. Hermes `kanban.db` / `projects.db` untouched this phase. No second SQLite file. No identity sidecar inside the worktree

**Testing**: pytest + ruff; one contract module `personalAgent/tests/test_workspace_manager.py`; git repos created in `tmp_path` (may copy `personalAgent/tests/fixtures/projects/standard/` then `git init`)

**Target Platform**: Host pytest (macOS/Linux) and the existing Docker Compose service (`hermes-agent:local`, workspaces mounted `/workspaces`)

**Project Type**: Library (in-process manager inside `hermes_kanban`). Not a CLI, HTTP service, or Hermes fork

**Performance Goals**: One worktree create or reuse per prepare. No throughput target

**Constraints**: No new third-party libraries. No hardcoded workstation paths. No silent production-repo target. Isolated Hermes home unchanged. No `git push` / reset / clean / clone-from-network. Other V0 items (PIV, GitHub hosting, Telegram, agent execution) stay out of this diff

**Scale/Scope**: Workspace manager + Git safety + execution identity only. ~one production module + one test module. Production config keeps `projects: []` until the owner names a non-critical repo; `workspace.root` stays `/workspaces` as already configured

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; checklist all items checked; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Single module in existing package; `git` CLI already used by the adapter; no extra layers |
| III. Platform-native | PASS | `git worktree` from enrolled location; reuse `resolve_eligible_project`; reuse Kanban field names on the return record. No second DB. Do not fork Hermes or copy project knowledge |
| IV. Trust-boundary tests | PASS | Validate workspace root at construction; task id / eligibility / git safety at prepare; one pytest contract file |
| V. Human authority | PASS | No merge/deploy/push. Tests use disposable git fixtures, not a production repo. Default managed set stays empty |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Manager does not touch `~/.hermes` or credentials |
| Model routing | PASS | No model names; no agent execution |
| Out-of-scope list | PASS | PIV, GitHub push/PR, Telegram, Obsidian, concurrent workers, auto-reset: not in this plan |
| Surgical edits | PASS | Add workspace module + tests + re-exports; do not rewrite the adapter, registry, Hermes, or AiNative |

### Post-design (PASS)

Design artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) stay inside the workspace contract. No extra services, queues, or `workspace.db`. Git YAML scanner is a documented subset (ceiling + upgrade path in research). Native `kanban.db` workspace columns are mapped on the return record and left unwritten this phase so prepare does not require a live Hermes task row; that is reuse of host field names, not a second store. Worktrees attach to the enrolled repo rather than cloning. Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-workspace-manager/
├── plan.md              # This file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── workspace-manager.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

Implementation lands in the existing control-plane repo `personalAgent/` (not the playground root, not AiNative).

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export public workspace types (keep adapter + registry exports)
│   ├── ainative.py          # unchanged this phase
│   ├── projects.py          # unchanged this phase (reuse resolve_eligible_project + _path_like_id)
│   └── workspace.py         # manager, records, errors (this feature)
├── tests/
│   ├── test_import.py       # existing — keep passing
│   ├── test_ainative_adapter.py  # existing — keep passing
│   ├── test_project_registry.py  # existing — keep passing
│   └── test_workspace_manager.py
├── tests/fixtures/projects/standard/  # existing files; tests git-init a copy in tmp_path
├── config/default.yaml      # already has workspace.root: /workspaces — no host-path change
└── docker-compose.yml       # already mounts WORKSPACE_ROOT → /workspaces — no compose change required
```

**Structure Decision**: Keep the scaffold layout. Add `workspace.py` rather than a new package or `workspace/` tree. Do not add copies of real application repos under `personalAgent/`. Do not commit `.git` fixture repos; create them in `tmp_path`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/workspace-manager.md](./contracts/workspace-manager.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names: `prepare_workspace`, `inspect_workspace`, `assert_publish_allowed`.
- Worktree path: `{workspace_root}/{project_id}/{task_id}`.
- Work branch: `feature/task-<task_id>`.
- Protected: `main`, `master`, project `default_branch`.
- `workspace_id`: `ws-{project_id}-{task_id}`. `execution_id`: new UUID hex per successful prepare.
- Allowed git: status, rev-parse, remote, fetch, worktree add/list, porcelain/diff names. Forbidden: push, reset --hard, clean, clone, init, worktree remove, checkout of enrolled HEAD.
- Stop after workspace contract checks pass; do not start PIV, GitHub hosting, or agent execution.

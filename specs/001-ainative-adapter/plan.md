# Implementation Plan: AiNative Adapter

**Branch**: `001-ainative-adapter` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ainative-adapter/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hermes needs reusable AiNative methodology without owning or copying it. This phase implements a **read-only in-process adapter** in the existing `hermes_kanban` package: load `ainative.path` / `ainative.read_only` from operational config, discover agent folders under `docs/8-agents/`, load purpose/how-to/constraints as separate raw-text fields, resolve referenced `_skills` plus the agent’s `rule.md`, stamp git revision (`repository`, `sha`, `branch`, `dirty`) onto an execution context, and refuse writes. No PIV, worktrees, GitHub, Telegram, model calls, or `execute_agent`.

Technical approach: one Python 3.12 module, stdlib + `git` CLI, pytest contract file against a fixture methodology tree. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib (`pathlib`, `subprocess`, `dataclasses`, `re`) + `git` CLI. Dev: pytest 9.1.1, ruff 0.16.5 (already listed)

**Storage**: N/A (read-only files + git metadata). No database. Hermes `kanban.db` / `projects.db` untouched

**Testing**: pytest + ruff; one contract module `personalAgent/tests/test_ainative_adapter.py` + fixture tree under `personalAgent/tests/fixtures/ainative/`

**Target Platform**: Host pytest (macOS/Linux with git) and the existing Docker Compose service (`hermes-agent:local`, methodology mounted `/ainative:ro`)

**Project Type**: Library (in-process adapter inside `hermes_kanban`). Not a CLI, HTTP service, or Hermes fork

**Performance Goals**: Roster and single-agent load are small-N directory reads (tens of agent folders). No throughput target

**Constraints**: No new third-party libraries. No hardcoded workstation paths. Methodology read-only. Isolated Hermes home unchanged. Other V0 Phase 1 items (registry, workspaces, Git safety, execution identity) stay out of this diff

**Scale/Scope**: Adapter-only. ~one production module + one test module + a tiny fixture tree. Live AiNative roster is currently eight real agents plus reserved `template` / `_skills`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; no `[NEEDS CLARIFICATION]`; clarify session recorded |
| II. Least Code | PASS | Single module in existing package; stdlib YAML subset scan; no extra layers |
| III. Platform-native | PASS | Reuse `hermes_kanban`, `config/default.yaml`, Docker `:ro` mount, `git` CLI. No second DB, no AiNative copy, no Hermes fork |
| IV. Trust-boundary tests | PASS | Validate config/path/`read_only` at construction; one pytest contract file |
| V. Human authority | PASS | No merge/deploy/push. Tests use a disposable fixture, not a production repo |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Adapter does not touch `~/.hermes` or credentials |
| Model routing | PASS | No model names |
| Out-of-scope list | PASS | PIV, worktrees, GitHub, Telegram, Obsidian, specs.md install, editor configs: not in this plan |
| Surgical edits | PASS | Only add adapter + tests; do not rewrite Hermes or AiNative |

### Post-design (PASS)

Design artifacts (`research.md`, `data-model.md`, `contracts/ainative-adapter.md`, `quickstart.md`) stay inside the adapter contract. No extra services, queues, or methodology duplication. Write API exists only to raise. Config parser is a documented subset (ceiling + upgrade path in research). Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-ainative-adapter/
├── plan.md              # This file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ainative-adapter.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

Implementation lands in the existing control-plane repo `personalAgent/` (not the playground root, not AiNative).

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export public adapter types
│   └── ainative.py          # settings, adapter, errors (this feature)
├── tests/
│   ├── test_import.py       # existing
│   ├── test_ainative_adapter.py
│   └── fixtures/
│       └── ainative/        # scout, tester, critic, template, _skills, broken-skill agent
├── config/default.yaml       # already has ainative.path / read_only — do not hardcode host paths
└── docker-compose.yml       # already mounts AiNative :ro — no compose change required for this phase
```

**Structure Decision**: Keep the scaffold layout. Add `ainative.py` rather than a new package or `adapters/` tree. Fixture methodology is committed under `tests/fixtures/` (documents only); tests `git init` a temp copy so revision tests do not depend on the live AiNative git state. Do not add methodology copies under `personalAgent/` outside tests.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contract | [contracts/ainative-adapter.md](./contracts/ainative-adapter.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names: `list_agents`, `get_agent`, `resolve_agent_dependencies`, `capture_revision`, `build_execution_context`, plus refused `write_file` / `copy_tree`.
- Skill references: `<!-- source: _skills/<name>/SKILL.md -->`.
- Dirty revision: succeed with `dirty=True`.
- Stop after adapter checks pass; do not start registry, workspaces, or PIV.

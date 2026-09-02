# Implementation Plan: Project Registry

**Branch**: `002-project-registry` | **Date**: 2026-08-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-project-registry/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hermes needs to know which software projects it may touch, without owning those projects’ knowledge. This phase implements a **hybrid in-process registry** in the existing `hermes_kanban` package: load an explicit managed set from operational YAML, expose `list_projects` / `get_project` / `resolve_eligible_project`, and `load_project_context` from the project tree (structured manifest + conventional text slots + closed-set tooling paths). Project-side name/branch/commands win; enrollment id and repository stay operational. No workspaces, agents, models, Git hosting, Telegram, or second project database.

Technical approach: one Python 3.12 module, stdlib YAML subset, pytest contract file against a disposable fixture tree. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib (`pathlib`, `dataclasses`, `re`). Dev: pytest 9.1.1, ruff 0.16.5 (already listed)

**Storage**: Operational YAML (`projects:` in caller-supplied config). In-memory records. Hermes `kanban.db` / `projects.db` untouched this phase. No second SQLite file. Project files read in place, not copied

**Testing**: pytest + ruff; one contract module `personalAgent/tests/test_project_registry.py` + fixture tree under `personalAgent/tests/fixtures/projects/`

**Target Platform**: Host pytest (macOS/Linux) and the existing Docker Compose service (`hermes-agent:local`, workspaces mounted `/workspaces`)

**Project Type**: Library (in-process registry inside `hermes_kanban`). Not a CLI, HTTP service, or Hermes fork

**Performance Goals**: Small-N config list and a handful of file reads per context load. No throughput target

**Constraints**: No new third-party libraries. No hardcoded workstation paths. No silent production-repo target. Isolated Hermes home unchanged. Other V0 items (workspaces, Git safety, PIV, GitHub, Telegram) stay out of this diff. `settings` is opaque

**Scale/Scope**: Registry + context load only. ~one production module + one test module + a tiny fixture project. Production config keeps `projects: []` until the owner names a non-critical repo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; no `[NEEDS CLARIFICATION]`; clarify session recorded |
| II. Least Code | PASS | Single module in existing package; stdlib YAML subset; no extra layers |
| III. Platform-native | PASS | Reuse `hermes_kanban`, `config/default.yaml`, existing `/workspaces` mount. No second DB. Do not wrap `discovered_repos`. Do not fork Hermes or copy project knowledge |
| IV. Trust-boundary tests | PASS | Validate managed set at construction; path/manifest at load; one pytest contract file |
| V. Human authority | PASS | No merge/deploy/push. Tests use a disposable fixture, not a production repo. Default config is an empty managed set |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Registry does not touch `~/.hermes` or credentials |
| Model routing | PASS | No model names; `settings` not interpreted |
| Out-of-scope list | PASS | Workspaces, PIV, GitHub, Telegram, Obsidian, auto-enrollment, specs.md install: not in this plan |
| Surgical edits | PASS | Add registry + tests + `projects: []`; do not rewrite the adapter, Hermes, or AiNative |

### Post-design (PASS)

Design artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) stay inside the registry contract. No extra services, queues, or project-knowledge duplication. YAML parser is a documented subset (ceiling + upgrade path in research). Native `projects.db` is deliberately unread this phase so discovery tables cannot enroll repos; that is reuse of config as the operator-owned identity capability, not a second store. Gates still pass. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-project-registry/
├── plan.md              # This file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── project-registry.md
│   └── project-manifest.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

Implementation lands in the existing control-plane repo `personalAgent/` (not the playground root, not AiNative).

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export public registry types (keep adapter exports)
│   ├── ainative.py          # unchanged this phase
│   └── projects.py          # records, registry, errors (this feature)
├── tests/
│   ├── test_import.py       # existing
│   ├── test_ainative_adapter.py  # existing — must keep passing
│   ├── test_project_registry.py
│   └── fixtures/
│       └── projects/
│           └── standard/    # README, AGENTS.md, .ainative/project.yaml, pyproject.toml
├── config/default.yaml       # add `projects: []` — do not hardcode host paths or enroll a real repo
└── docker-compose.yml       # already mounts WORKSPACE_ROOT → /workspaces — no compose change required
```

**Structure Decision**: Keep the scaffold layout. Add `projects.py` rather than a new package or `registry/` tree. Fixture project is committed under `tests/fixtures/projects/standard/` (documents + a tiny manifest); additional layouts are built in `tmp_path`. Do not add copies of real application repos under `personalAgent/`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/project-registry.md](./contracts/project-registry.md), [contracts/project-manifest.md](./contracts/project-manifest.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names: `list_projects`, `get_project`, `resolve_eligible_project`, `load_project_context`.
- Default structured source: `.ainative/project.yaml` when `manifest` is omitted.
- Closed tooling set: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Makefile`, `pytest.ini`, `tsconfig.json`.
- Conventional slots: overview `README.md`/`README`; agent/AI `AGENTS.md`/`CLAUDE.md`; contributing `CONTRIBUTING.md`; architecture `docs/architecture.md`/`ARCHITECTURE.md`.
- Stop after registry checks pass; do not start workspaces or PIV.

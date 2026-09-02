# Quickstart: Project Registry

**Feature**: `002-project-registry`

Validation guide for the registry contract. Implementation lives in `personalAgent/` (existing control-plane package). Do not start workspaces, PIV, GitHub, Telegram, or model calls to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/project-registry.md](./contracts/project-registry.md), [contracts/project-manifest.md](./contracts/project-manifest.md).

## Prerequisites

- Python 3.12 and uv (see `personalAgent/.python-version`)
- This repo’s `personalAgent` checkout

A live managed project is **not** required. Contract tests use `personalAgent/tests/fixtures/projects/` plus trees built under pytest’s `tmp_path`. Production `config/default.yaml` MUST keep `projects: []` until the owner names a non-critical repo.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Do not point the registry at a hardcoded host path. Tests construct config that lists the fixture under `tmp_path`. Docker already mounts workspaces at `/workspaces`; application code reads **configured** locations, not `WORKSPACE_ROOT` from the host `.env`.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_project_registry.py
uv run ruff check src tests
```

Keep existing tests passing (`tests/test_import.py`, `tests/test_ainative_adapter.py`).

## Expected outcomes (SC-006)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| List managed projects | Config with one enabled fixture (and optionally a disabled second) returns those operational records; knowledge files are not on the record |
| Resolve known ID | `get_project(id)` returns id, name, repository, location, default branch, enabled, settings map |
| Reject unknown ID | Unknown, path-like, and `../` ids raise `UnknownProjectError`; no empty record; no disk join |
| Reject disabled project | `resolve_eligible_project` / `load_project_context` raise `DisabledProjectError`; no context bundle |
| Load fixture context | Bundle has operational identity, README/AGENTS text when those files exist, the fixture’s own validation commands, and `pyproject.toml` as a relative path (not file text) if present |
| Refuse missing configuration | Hidden/missing chosen manifest or missing validation commands raises `MissingProjectConfigurationError`; no invented `pytest`/`npm test` |

Also required by the spec (same test file is fine):

- Empty `projects:` → empty list; an unlisted directory on disk is never returned
- Missing location → `InvalidProjectLocationError` on resolve/load; no substitute path
- Named `manifest` other than `.ainative/project.yaml` is used; default file is not required
- Operational `default_branch: main` + project `default_branch: master` → context branch is `master`
- Duplicate ids or duplicate repository/location in config → `InvalidProjectConfigError`
- After load, nothing under `personalAgent/` (except the committed fixture and tests) holds a copied knowledge base of the project

## Fixture

Committed tree `tests/fixtures/projects/standard/` MUST include at least:

- `README.md`
- `AGENTS.md`
- `.ainative/project.yaml` with `name`, `repository`, `default_branch`, and a non-empty `validation.commands`
- `pyproject.toml` (so the tooling-path slot is exercised)

Do not point tests at a real application repository.

## Out of scope for this guide

Docker e2e, writing `projects.db`, worktrees, PIV, GitHub, Telegram, model calls, and auto-enrollment. Those wait for later specs.

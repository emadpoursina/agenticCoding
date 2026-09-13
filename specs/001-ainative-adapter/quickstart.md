# Quickstart: AiNative Adapter

**Feature**: `001-ainative-adapter`

Validation guide for the adapter contract. Implementation lives in `personalAgent/` (existing control-plane package). Do not start other V0 phases to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/ainative-adapter.md](./contracts/ainative-adapter.md).

## Prerequisites

- Python 3.12 and uv (see `personalAgent/.python-version`)
- `git` on `PATH` (revision capture)
- This repo’s `personalAgent` checkout

A live AiNative mount is **not** required. Contract tests use `personalAgent/tests/fixtures/ainative-full/` (copied into a temp git repo at test time) with agents under `docs/agents/`.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Do not point the adapter at a hardcoded host path. Tests construct settings from the fixture. Production Docker already mounts methodology at `/ainative:ro` and `config/default.yaml` already has `ainative.path: /ainative` and `ainative.read_only: true`.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_ainative_adapter.py
uv run ruff check src tests
```

Keep `tests/test_import.py` passing (`hermes_kanban` still imports).

## Expected outcomes (SC-006)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| List known agents | Fixture roster includes names such as `scout`, `tester`, `critic` and excludes `template` and `_skills` |
| Load scout | `get_agent("scout")` has `name == "scout"` and separate `purpose` / `howto` / `constraints` text for files that exist; no concatenated blob |
| Capture revision | Context/revision has configured path, non-empty `sha`, `repository`, `branch` or `"detached"`, and a `dirty` bool; dirty fixture still succeeds with `dirty=True` |
| Refused write | `write_file` / `copy_tree` raise `ReadOnlyError`; fixture tree unchanged |
| Invalid path | Missing/empty/non-dir/`read_only: false` / missing `docs/agents/` raises `InvalidMethodologyError`; no substitute path |

Also required by the spec (same test file is fine):

- `get_agent` / `resolve_agent_dependencies` of `template`, `_skills`, `../x`, and `a/b` raise `UnknownAgentError`
- Resolve of an agent whose how-to references a missing skill raises `UnresolvedDependencyError` (no partial list)
- `capture_revision` on a non-git directory raises `RevisionError`

## Optional live mount

If `/ainative` (container) or a locally configured methodology path exists, an extra test MAY list agents there and assert the returned names are real folders. It MUST NOT require `specs-planner` or any name that is absent from that checkout. Skip when the path is missing.

## Out of scope for this guide

Docker e2e, PIV, worktrees, GitHub, Telegram, model calls, and `execute_agent`. Those wait for later specs.

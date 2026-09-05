# Quickstart: Live Hermes PIV Bridge

Validation guide for the read-only native board adapter, the one dispatcher/CLI entry, column eligibility, and the named-repo smoke gate. Implementation stays in `personalAgent/`. Automated checks MUST NOT require github.com, live Telegram, a live model, or the operator’s real `kanban.db`.

Types and signatures: [data-model.md](./data-model.md), [contracts/live-piv-bridge.md](./contracts/live-piv-bridge.md). Prior chain: [009 quickstart](../../009-restart-recovery/quickstart.md).

## Prerequisites

Python 3.12, uv, git, `personalAgent/` checkout. `OPENAI_API_KEY`, live chat, and github.com are **not** required for pytest. Do not point tests at `$HOME/.hermes/personal-agent/kanban.db`.

## Setup

```bash
cd personalAgent
uv sync --extra dev
```

## Contract checks

```bash
cd personalAgent
uv run pytest tests/test_live_piv_bridge.py
uv run pytest
uv run ruff check src tests
```

Expected: all pass, including existing 001–009 modules. New tests create a **temporary** SQLite board in the installed `tasks` / `task_links` shape, read through `SqliteTaskBoard`, and use `MemoryGitHost` for publish/PR.

## Scenarios (map to spec)

Stand-in model, temp overlay dir, temp workspace root, temp enrolled git project.

1. **Read-only get** — Fixture card fields match stored body headings; file bytes/mtime unchanged after get/list/start.
2. **Production construction** — Live entry builds `SqliteTaskBoard` + `LiveGitHost` (or injected host in checks); constructing the live entry with `MemoryTaskBoard` fails.
3. **Missing board / unknown id / wrong column / incomplete card** — Visible error; 0 agent runs.
4. **Next-ready** — Only `todo`/`ready` with required fields; highest `P0`–`P3` then oldest; empty set → `NoReadyTaskError`.
5. **Named start + chain** — Isolated `feature/task-<id>`, discovery → planning → implementation → validation, recover-or-block unchanged, `PR_CREATED` + existing `pr_created` notice on the memory channel; 0 default-branch commits; 0 merges; 0 secrets on the record.
6. **Worker claim** — `column=running` allowed only when id equals `HERMES_KANBAN_TASK` / `allow_running_task_id`.
7. **Smoke refuse** — No `--repo` / blank name → 0 `MemoryGitHost.pushes`. Mismatched GitHub `owner/name` vs enrolled `name` → 0 pushes.
8. **Smoke match (fixture)** — Requested name equals both identities → would target that repo’s feature branch only (still `MemoryGitHost` in pytest).
9. **One board file** — After a live-adapter run against a temp DB, no extra task database files appear.

Details: [contracts/live-piv-bridge.md](./contracts/live-piv-bridge.md).

## Dispatcher / CLI (after implement)

One entry (names may match the contract `main`):

```bash
# Worker (Hermes already set HERMES_KANBAN_TASK)
python -m hermes_kanban --config /path/to/default.yaml

# Named or next-ready from a shell
python -m hermes_kanban --config /path/to/default.yaml --task TASK_ID
python -m hermes_kanban --config /path/to/default.yaml --next-ready
```

Compose must make the package importable inside `hermes-personal-agent` with `HERMES_HOME=/opt/data`. Do not write `~/.hermes` root.

## Live smoke (operator; not pytest)

Requires an **explicit** disposable `owner/name`. Default is refuse.

```bash
python -m hermes_kanban --config /path/to/default.yaml --smoke --repo owner/name
```

Proceeds only if that string equals both the github.com remote `owner/name` **and** the enrolled project `name`. Then push/PR the feature branch only. Never `main`/`master`. Never pick `ich-mag-dich` (or any other enrollment) unless that same identity was passed **and** enrollment agrees.

### Credentials still required (never in git)

1. GitHub SSH agent forwarding (compose already mounts the agent socket).
2. Existing Hermes Telegram bot token + home chat (already-connected gateway).
3. Model provider key already configured inside Hermes / optional `OPENAI_API_KEY` env.

Smoke documents these; it MUST NOT write them into the repo, overlay, PR body, or notices.

## Out of scope

Concurrent workers, Obsidian, learning PRs, automatic merge/deploy, a second Telegram bot, modifying AiNative, installing extra planning frameworks.

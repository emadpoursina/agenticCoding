# Quickstart: External Framework Planning Adapter

Validation guide for the Spec Kit adapter, isolated bootstrap, native
artifacts, and planning-only live workflow. Implementation remains in
`personalAgent/`. Checks are offline and do not use the operator's Hermes
home, production repository, GitHub, live model credentials, or writable
AiNative mount.

Types and workflow rules: [data-model.md](./data-model.md) and
[contracts/external-framework-planning.md](./contracts/external-framework-planning.md).

## Prerequisites

- Python 3.12 and `uv`
- `git`
- A checkout of this repository
- No API key, GitHub account, Telegram session, Docker daemon, or live model

The production image additionally supplies a build-time-pinned Spec Kit
runtime and sets `HERMES_SPECKIT_RUNTIME` to its read-only runtime directory.
The pytest path uses a committed disposable runtime fixture instead.

## Focused checks

```bash
cd personalAgent
uv sync --extra dev
uv run pytest tests/test_external_framework_planning.py
uv run ruff check src tests
```

Expected: the focused contract checks pass without network access, and the
existing suite remains green:

```bash
uv run pytest
```

## Fixture scenarios

Each scenario creates a temporary enrolled git project, isolated task
worktree, overlay directory, AiNative fixture, provider runtime fixture, and
stand-in `ModelService`.

1. **Provider selection** — exactly one active `github-spec-kit` provider with
   a matching pinned runtime is accepted. Zero active providers, two active
   providers, unsupported ids, empty version pins, missing runtime paths, and
   manifest mismatches fail before the stand-in receives a call.
2. **Discovery first** — recorded model contexts are ordered `discovery`,
   `plan`, `tasks`; a missing/failing `scout` produces no Spec Kit call.
3. **No live planner dependency** — the methodology fixture has `scout` but
   no `specs-planner` or `builder`; planning still reaches the external
   adapter.
4. **Bootstrap isolation** — an unconfigured worktree receives only the
   provider setup bundle. The enrolled root, AiNative fixture, overlay, and
   runtime source remain byte-for-byte unchanged. Setup remains after
   success. A matching pre-existing setup is reused without a second
   workspace or task store.
5. **Native artifacts** — the runtime writes its native implementation plan
   and task list under its own feature directory. The normalized result
   returns both paths, they resolve under the worktree, and no `PLAN.md` or
   `TASKS.md` is created.
6. **Result safety** — missing, unreadable, directory, escaping, or
   secret-bearing provider outputs fail closed without fabricated paths.
7. **Planning-only completion** — a live-style workflow records
   `PLANNING_COMPLETE`, stores provider/version/revision and native paths,
   leaves validation pending, writes a free slot, and makes zero
   implementation, validation, GitHub, merge, deploy, or publish calls.
8. **Questions and failures** — provider questions park through the existing
   Hermes decision state; provider failures remain visible. The adapter does
   not answer questions or add retries.
9. **Later-task readiness** — after `PLANNING_COMPLETE`, the same
   single-task slot can accept another eligible task.

## Live-style command shape

After implementation, a configured Hermes worker or shell uses the existing
single dispatcher entry:

```bash
export HERMES_HOME="$HOME/.hermes/personal-agent"
export HERMES_SPECKIT_RUNTIME="/opt/spec-kit"

python -m hermes_kanban --config /path/to/default.yaml --task TASK_ID
python -m hermes_kanban --config /path/to/default.yaml --next-ready
```

The successful planning slice prints `planning complete` and stops. It does
not run implementation, validation, or GitHub publish. A later feature will
consume the native paths from the recorded framework result.

## Production runtime provisioning

The Docker image build pins the Spec Kit release and records its exact
revision in the runtime manifest. Runtime tasks never run `uv tool install`,
`pip install`, `git clone`, or an external planning API. Rebuild the image
when changing the pin, then verify the manifest/version before starting the
worker.

Credentials remain outside git: the existing Hermes/model configuration,
GitHub SSH agent or token, and Telegram credentials are not copied into the
worktree, runtime bundle, native artifacts, overlay, or notices.

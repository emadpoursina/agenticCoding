# Quickstart: Spec Kit Implementation and Publish

Validation guide for the native plan/task handoff, Spec Kit implementation,
existing validation/recovery, and orchestrator-owned GitHub publish. The
implementation remains in `personalAgent/`. Automated checks are offline and
do not use the operator's Hermes home, production repositories, GitHub,
Telegram, live model credentials, or writable live AiNative.

Types and workflow rules:
[data-model.md](./data-model.md) and
[contracts/external-framework-implementation.md](./contracts/external-framework-implementation.md).

## Prerequisites

- Python 3.12 and `uv`
- `git`
- A checkout of this repository
- No GitHub account, Telegram session, API key, Docker daemon, or live model
  credential for the focused checks

The production image supplies the build-time-pinned Spec Kit runtime and
sets `HERMES_SPECKIT_RUNTIME` to its read-only runtime directory. Tests use
the committed disposable runtime fixture instead.

## Focused checks

```bash
cd personalAgent
uv sync --extra dev
uv run pytest tests/test_external_framework_planning.py
uv run pytest tests/test_live_piv_bridge.py
uv run pytest tests/test_restart_recovery.py
uv run ruff check src tests
```

Expected: the focused checks pass without network access and the existing
suite remains green:

```bash
uv run pytest
```

## Fixture scenarios

Each scenario creates a temporary enrolled git project, one isolated task
worktree and feature branch, overlay directory, scout-plus-validation
AiNative fixture, pinned Spec Kit runtime fixture, stand-in model, simulated
GitHub host, and in-memory messaging channel.

1. **Provider/runtime gate** — exactly one active `github-spec-kit` provider
   and matching runtime revision are accepted. Zero-active, two-active,
   unsupported, empty-pin, missing-runtime, and mismatched-revision inputs
   fail before a model call.
2. **Full call order** — model/framework contexts are observed in the order
   `discovery → plan → tasks → implement → validation`; plan/tasks use the
   configured `planning` assignment and implement/recovery uses
   `implementation`. Implement receives the exact native plan/task paths from
   the same worktree.
3. **No builder lookup** — the live methodology fixture contains `scout` and
   the validation role but no `specs-planner` or `builder`; the live path
   never looks up either missing role.
4. **Implementation isolation** — model files and retained `.specify` setup
   appear only under the task worktree. The enrolled root, AiNative,
   runtime source, overlay control data, and sibling worktree remain
   unchanged.
5. **Native handoff** — native `specs/<feature>/plan.md` and
   `specs/<feature>/tasks.md` remain the source of truth. No `PLAN.md`,
   `TASKS.md`, second task list, or second workspace is created.
6. **Implementation questions/failures** — questions park in the existing
   human-decision state; model failure does not start validation or publish;
   partial files remain available for existing inspection/recovery.
7. **Validation pass and publish** — a passing project check reaches the
   existing `MemoryGitHost` sequence with one feature-branch push, one
   create-or-update PR identity containing number and URL, and one existing
   `pr_created` notice. `PLANNING_COMPLETE` is only an intermediate
   checkpoint; the live dispatcher reports `PR_CREATED` after validation and
   publish. No merge, deploy, or protected-branch write occurs.
8. **Retryable recovery** — a retryable validation failure follows
   `diagnosis → Spec Kit implement fix → validation`, keeps the same
   provider/worktree/native paths, and does not call an AiNative builder.
9. **Transient/non-retryable recovery** — transient failures use the existing
   validation-only retry behavior; non-retryable failures block. Neither
   invokes implement or publish when the current rules do not allow it.
10. **Legacy planning handoff** — a saved valid `PLANNING_COMPLETE` record
    is selected by task name or next-ready, reuses the same worktree and
    native paths, skips plan/tasks, then implements, validates, and publishes.
    Its checkpoint is never reported as PIV-complete.
11. **Invalid handoff** — missing, unreadable, non-regular, secret-bearing,
    escaping, provider-drifted, runtime-drifted, or wrong-worktree paths fail
    closed before implementation, validation, or publish.
12. **Overlay safety** — external result, implementation outcome, validation
    outcome, recovery state, and final PR identity round-trip through the
    existing atomic overlay without transcripts, private reasoning, tokens,
    or secrets.

## Live-style command shape

After implementation, a configured Hermes worker or shell uses the existing
dispatcher:

```bash
export HERMES_HOME="$HOME/.hermes/personal-agent"
export HERMES_SPECKIT_RUNTIME="/opt/spec-kit"

python -m hermes_kanban --config /path/to/default.yaml --task TASK_ID
python -m hermes_kanban --config /path/to/default.yaml --next-ready
python -m hermes_kanban --config /path/to/default.yaml \
  --resume PROJECT_ID TASK_ID OPTION
```

With a valid active provider and a passing project check, the live-style path
ends in the existing `PR_CREATED` result. It does not stop at the planning
checkpoint. A previous valid planning-only result continues from its native
handoff when the task is selected again.

## Production runtime and credentials

The Docker image build pins the Spec Kit release and records its exact
revision in the runtime manifest. Task execution never runs `uv tool install`,
`pip install`, `git clone`, or an external planning API. Rebuild the image
when changing the runtime pin, then verify the manifest before starting the
worker.

Credentials remain outside git: the existing Hermes/model configuration,
GitHub SSH agent or token, and Telegram credentials are supplied at runtime
and are not copied into the worktree, runtime bundle, native artifacts,
overlay, notices, pull requests, or changelog.

# Quickstart: Pi Harness Adapter

This guide validates the one-run Hermes-to-Pi path offline. It uses disposable
repositories, a stand-in Pi runtime/model, `MemoryGitHost`, and in-memory
messaging. It does not use the operator's Hermes home, live GitHub, live Pi
credentials, or writable AiNative.

## Prerequisites

- Python 3.12 and `uv`
- Git
- Repository checkout at `/Users/emad/Projects/playground/agenticCoding`
- Existing `personalAgent/` development environment

From the repository root:

```bash
cd personalAgent
uv sync --extra dev
```

## Focused fixture proof

Run the generic contract, Pi adapter, human parking, timeout, isolation, and
publication-gating fixtures:

```bash
uv run pytest tests/test_harness_adapter.py
uv run pytest tests/test_piv_orchestrator.py tests/test_restart_recovery.py
uv run pytest tests/test_live_piv_bridge.py
```

The focused checks must prove:

1. Hermes sends exactly one `HarnessStartRequest` for a work attempt and
   receives exactly one `HarnessResult`.
2. The fixture Pi runtime records the internal order
   `specify → clarify/continue (when needed) → plan → tasks → analyze? →
   implement ↔ converge`, while Hermes makes no per-stage call.
3. Native `specs/<feature>/spec.md`, `plan.md`, `tasks.md`, and related files
   are below the disposable task worktree.
4. The enrolled project root, AiNative fixture, Hermes overlay/control state,
   runtime source, and sibling worktree are unchanged.
5. Generic request/result records contain no Pi SDK object, provider/model
   slug, token, transcript, or secret.
6. Missing timeout, unsupported playbook, invalid worktree/branch, unsafe
   paths, malformed status, unavailable runtime, and timeout fail before
   validation or publication.
7. Clarify/skip/continue and implementation questions park in Hermes; resume
   passes the recorded answer/context through another whole-run boundary.
8. The third recoverable stuck attempt parks and no fourth automatic attempt
   starts.
9. A `completed` result runs project validation before any push or PR; a
   validation pass reaches the existing simulated PR path, and every
   pre-validation outcome leaves GitHub untouched.
10. A legacy Hermes planning checkpoint is parked for human review and never
    resumes the removed stage machine or auto-starts Pi.

## Full quality gates

```bash
uv run pytest
uv run ruff check src tests
```

Expected result: all tests pass and Ruff reports no errors.

## Inspect the disposable artifacts

The tests expose the temporary worktree path in their failure output and
assert the native paths directly. When running an individual fixture under
`pytest -s`, inspect the reported task worktree and confirm:

```text
specs/<feature>/spec.md
specs/<feature>/plan.md
specs/<feature>/tasks.md
```

There must be no Hermes `PLAN.md` or `TASKS.md` aliases. The feature branch
must be the prepared `feature/task-<id>` branch, and the simulated PR must
exist only after validation passes.

## Optional live-style construction check

Use a disposable Hermes home and a disposable project fixture only. Configure
the Pi runtime path and a named model profile in an untracked local config;
keep credentials outside the repository. The live constructor must reject a
missing or mismatched Pi runtime before creating a harness run. Do not point
this check at a production repository or the operator's live Hermes home.

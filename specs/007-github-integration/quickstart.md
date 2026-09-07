# Quickstart: GitHub Integration

**Feature**: `007-github-integration`

Validation guide for orchestrator-owned publish after PIV-complete, `PR_CREATED`, builder-never-publish, merge/protected-push refuse, and simulated-remote checks. Implementation stays in `personalAgent/`. Do not start Telegram, a live model account, or native `kanban.db` writes to run the pytest contract.

Types and signatures: [data-model.md](./data-model.md), [contracts/github-publish.md](./contracts/github-publish.md). Prior chain: [006 quickstart](../../006-piv-recovery/quickstart.md).

## Prerequisites

Same as 006: Python 3.12, uv, git, `personalAgent/` checkout. Live managed project, live `kanban.db`, github.com account, Telegram, and `OPENAI_API_KEY` are **not** required for pytest. `config/default.yaml` MUST keep `projects: []`. Tests MUST NOT bind host home paths or call github.com.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests reuse 006 helpers plus `MemoryGitHost`: temp methodology, temp enrolled git project, `MemoryTaskBoard`, stand-in `ModelService`. Simulate an existing PR by preloading the memory host with a number + URL for the work branch. Simulate auth failure / transient failure by making the host raise classified errors. Implementation-role commit checks spy that `GitHost.push_feature_branch` was not called until after validation pass.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_github_publish.py tests/test_piv_orchestrator.py tests/test_agent_executor.py
uv run ruff check src tests
```

Keep 001–006 tests passing. Success paths that used to wait-return `COMPLETED` MUST now wait-return `PR_CREATED` when a GitHost is wired (inject memory host in those tests).

## Expected outcomes (SC-007)

`tests/test_github_publish.py` MUST fail if any of these break:

| Check | Passes when |
|---|---|
| PIV-complete then `PR_CREATED` | Validation pass, start returns `PR_CREATED` with `number` + `html_url`, PR targets default branch, body has five sections + task id, published branch is `feature/task-*`, enrolled location unchanged, history includes `COMPLETED` then `PR_CREATED` |
| Builder never publishes | Implementation/debug local commit: 0 `push_feature_branch` / upsert calls; after pass, only the orchestrator GitHub step records the push |
| Merge and protected-push refused | Merge/approve/deploy/push-to-default through the workflow raises; state is not `PR_CREATED`; `assert_publish_allowed` still blocks `main`/`master`/default |
| Idempotent PR update | Second publish with more commits reuses the same `number`, rewrites title and body (not stale), does not allocate a second PR |
| No publish before validation pass | Parked / failed / recovery-blocked runs: 0 pushes, 0 PRs |
| Auth-fail → `BLOCKED` without diagnosis | After validation pass, auth error → `BLOCKED`, `current_phase=="github"`, 0 diagnosis, 0 debug |
| Simulated remote without live hosting | Entire file passes with `MemoryGitHost` (or local bare remote); no github.com network |

Also required (same file is fine):

- Transient publish: two failures then success → `PR_CREATED`, 0 diagnosis; three transients → `BLOCKED`, no fourth automatic publish
- Blocked-publish resume `A` → `FAILED`; `B` retries publish only
- Empty branch (nothing ahead, clean) → visible fail, 0 PRs
- Ensure-commit: dirty reviewable, nothing ahead → exactly one new commit, no amend/force in git argv
- Non-github.com live URL refused (unit on `LiveGitHost` / URL gate; memory host still used for chain tests)
- Secrets absent from record and PR body
- Slot: `PR_CREATED` releases; second start while `BLOCKED` still `WorkflowBusyError`

## Live container proof (phase-complete for FR-005; not pytest)

Requires an operator-named **non-critical** or disposable github.com repository. MUST NOT silently use a production remote.

1. Compose already mounts `${SSH_AUTH_SOCK}` and sets `SSH_AUTH_SOCK` in `hermes-personal-agent`. Set `SSH_AUTH_SOCK` in `.env` (Docker Desktop `/run/host-services/ssh-auth.sock` vs Linux host socket). Do not copy private keys into the image. Optional: set `GH_TOKEN` on the host or in local `.env` (never in git) so the boot script can log `gh` in.
2. Recreate the control-plane container (`docker compose up -d`). Rebuild `hermes-agent:local` after Dockerfile or boot-script changes so verified github.com host keys are present.
3. Inside the container: `ssh -T git@github.com` (handshake), `git fetch` on the disposable remote, feature-branch `git push` (not `main`/`master`).
4. Confirm 0 private keys in the image layers / Dockerfile. Host keys in `docker/ssh/github_known_hosts` are public GitHub keys, not credentials.

Contract pytest MUST still pass when this socket is absent.

## Out of scope for this guide

Telegram, writing `kanban.db`, adding agents to live AiNative, GitHub Enterprise, automatic merge, restart persistence.

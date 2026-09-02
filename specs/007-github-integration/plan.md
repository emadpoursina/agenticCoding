# Implementation Plan: GitHub Integration

**Branch**: `007-github-integration` | **Date**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-github-integration/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phase 4 stops at PIV-complete (`COMPLETED` wait-return, unpublished isolated copy). This phase adds an **orchestrator-owned GitHub sequence** after validation pass: ensure one new commit if needed (never amend/force-push) → push the task feature branch to **github.com over SSH** → create or **reuse and rewrite** the pull request (five body sections + task reference). Success wait-return is **`PR_CREATED`** with PR number + HTML URL. Builder/debug still must not push. Merge, approve-as-human, deploy, and protected/default-branch push stay impossible. Publish failures `BLOCKED` without diagnosis. Contract checks use `MemoryGitHost`; shipped compose MAY enable SSH agent forwarding.

Technical approach: `github.py` seam + extend `orchestrator.py` / overlay fields; pytest module `test_github_publish.py`; update 006 success assertions. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib + existing orchestrator/workspace/executor. Live: `git` + `gh` CLI. Dev: pytest, ruff (already listed)

**Storage**: Same in-memory `WorkflowRecord` overlay. `pull_request` identity on that record. No second SQLite file. Hermes `kanban.db` / `projects.db` unwritten. Isolated git worktrees unchanged (push from the copy, enrolled location not rewritten)

**Testing**: pytest + ruff; new `personalAgent/tests/test_github_publish.py`; update `test_piv_orchestrator.py` wait-return; `MemoryGitHost` + stand-in model + `MemoryTaskBoard`

**Target Platform**: Host pytest (macOS/Linux) and existing Docker Compose service with SSH agent forwarding enabled this phase. Live github.com not required for contract checks

**Project Type**: Library (in-process orchestrator inside `hermes_kanban`)

**Performance Goals**: One blocking start/resume through publish. At most 3 automatic publish attempts. No throughput target

**Constraints**: No new third-party libraries. github.com SSH only for live git. No keys in images. No silent production repo. No merge/deploy/amend/force-push. No Telegram. No background worker. Methodology read-only. Publish retry limit fixed at 3. Do not recover publish via diagnosis/debug

**Scale/Scope**: GitHost module + orchestrator publish/blocked-resume branch + compose SSH + one contract file. Production `projects: []` unchanged

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; clarify 2026-09-01 recorded; checklist 16/16; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Reuse workspace `assert_publish_allowed`, slot, A/B resume, executor no-push. New file only for GitHost I/O. No PyGithub |
| III. Platform-native | PASS | Overlay for PR identity (no second task table). `git`/`gh` over a new GitHub service. Hermes GitHub **skills** are not the publish actor (would be worker-owned; US2) |
| IV. Trust-boundary tests | PASS | Same three public calls; one pytest contract file; simulated host; live SSH is a separate operator done-check |
| V. Human authority | PASS | Merge/protected-push refused even if `allow_merge` is flipped; disposable/named non-critical live repo only |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | No keys in image; secrets not on records/PR bodies |
| Model routing | PASS | Publish does not call models |
| Out-of-scope list | PASS | Telegram, restart persistence, concurrent workers, GHES, auto-merge: not in this plan |
| Surgical edits | PASS | Orchestrator + github.py + compose/docs + tests; do not rewrite adapter/registry/workspace safety |

### Post-design (PASS)

Design stays in-process. `MemoryGitHost` is the contract ceiling. `LiveGitHost` is git+gh with SSH github.com gate. `COMPLETED` is history-only; wait-return is `PR_CREATED`. Dual `BLOCKED` resume is keyed by `current_phase=="github"` vs recovery — no extra product. Compose SSH forwarding is the allowed runtime change. Gates still pass. Complexity Tracking remains empty (skills-not-as-publisher is a constraint compliance, not a violation).

## Project Structure

### Documentation (this feature)

```text
specs/007-github-integration/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── github-publish.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export PullRequestIdentity, GitHost types, ForbiddenGitHubActionError
│   ├── ainative.py          # unchanged
│   ├── projects.py          # unchanged (live URL gate is GitHost, not a second registry)
│   ├── workspace.py         # reuse assert_publish_allowed; no second safety wrapper
│   ├── executor.py          # unchanged no-push behavior
│   ├── orchestrator.py      # after validation pass → github; PR_CREATED; blocked-publish B
│   └── github.py            # GitHost, MemoryGitHost, LiveGitHost, URL gate, PR body
├── tests/
│   ├── test_github_publish.py     # SC-007 seven checks
│   ├── test_piv_orchestrator.py   # success wait-return PR_CREATED
│   └── test_agent_executor.py     # still 0 push from implementation
├── config/default.yaml            # github flags already present; do not set allow_merge true
├── docker-compose.yml             # enable SSH agent mount + SSH_AUTH_SOCK
├── .env.example                   # document SSH_AUTH_SOCK
└── README.md                      # SSH-from-container steps (this phase)
```

**Structure Decision**: Add `github.py` for the hosting seam. Do not add `recovery.py`. Do not open `kanban.db`. Do not vendor Hermes GitHub skills into the package. Do not add agents to live `AiNative`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data Model | [data-model.md](./data-model.md) |
| Contracts | [contracts/github-publish.md](./contracts/github-publish.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names unchanged: `run_workflow`, `run_next_workflow`, `resume_workflow`.
- Inject `git_host` like `task_board`; tests use `MemoryGitHost`.
- History `COMPLETED` then `github`; wait-return `PR_CREATED`.
- `publish_attempt` independent of recovery `attempt`.
- Resume `B` on `current_phase=="github"` retries publish only.
- PR body: five headings; rewrite on every upsert.
- Live URL: SSH `git@github.com` / `ssh://git@github.com/...` only.
- Compose: forward `SSH_AUTH_SOCK`; never copy private keys.
- `ponytail:` overlay PR identity (not a `pull_requests` table). Upgrade: map onto native hosting metadata without a second task DB.
- Stop after GitHub contract checks + documented live SSH proof; do not start Telegram.

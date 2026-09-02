# Data Model: GitHub Integration

**Feature**: `007-github-integration` | **Date**: 2026-09-01

Extends the 006 overlay. No new database. No native Kanban writes. Types remain frozen dataclasses. Pull-request identity lives on `WorkflowRecord`, not on `BoardTask`.

## Board task (unchanged)

`BoardTask` stays read-only. Publish MUST NOT overwrite problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, or priority. Task reference on the PR points at `task.id`; it is not a board mutation.

## Pull-request identity

**Entity**: `PullRequestIdentity`

| Field | Type | Rules |
|---|---|---|
| `number` | `int` | Hosting pull-request number. Required for `PR_CREATED`. |
| `html_url` | `str` | Public HTML URL (e.g. `https://github.com/owner/repo/pull/N`). Required for `PR_CREATED`. MUST NOT contain tokens or agent sockets. |

`WorkflowRecord.pull_request`: `PullRequestIdentity | None`. `None` until a successful upsert. MUST NOT be inferred from `summary` prose.

## Publish class (closed set)

Separate from validation `failure_class` when the failure is GitHub. Store the last **publish** class on the overlay (reuse `failure_class` only when `current_phase=="github"`; recovery classes remain when phase is diagnosis/debug/validation).

| Value | When |
|---|---|
| `TRANSIENT` | Network timeout or hosting unavailable on push or PR upsert |
| `NON_RETRYABLE` | Auth, permission, non-github.com remote, empty publish, dirty-no-intent, incomplete PR body, force/amend/merge/protected-push attempt |

MUST NOT classify publish from summary prose.

## Execution state (closed set)

Previous values remain. This phase adds / changes:

| Value | Meaning |
|---|---|
| `COMPLETED` | **History only**: PIV-complete (validation passed). Not a start/resume wait-return. |
| `PR_CREATED` | Terminal success wait-return. Feature branch published; PR created or updated with required body; identity present. Releases the slot. |

`QUEUED`, `RUNNING`, `VALIDATING`, `RETRYABLE_FAILURE`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`, `FAILED` unchanged in meaning except `BLOCKED` MAY now follow publish (phase `github`) as well as recovery.

## Phase (closed set)

Previous: `discovery`, `planning`, `implementation`, `validation`, `diagnosis`, `debug`.

| Value | Actor | Notes |
|---|---|---|
| `github` | Orchestrator → `GitHost` | Commit-ensure → push feature branch → upsert PR. Not an executor role. |

## Workflow record (additions)

Existing fields remain. Change / add:

| Field | Type | Rules |
|---|---|---|
| `pull_request` | `PullRequestIdentity \| None` | Set on `PR_CREATED`. Empty until then. |
| `publish_attempt` | `int` | `0` until the first GitHub try; increments each automatic publish attempt. Independent of recovery `attempt`. |
| `state` | `str` | Includes `PR_CREATED`. |
| `current_phase` | `str` | May be `github`. |

`next_action`: `""` on `PR_CREATED`/`FAILED`; `reply with the option letter` on parked or blocked; `publish` while GitHub is in progress (history).

`steps` MUST include the PIV-complete `COMPLETED` row immediately before GitHub when validation passed, then `PR_CREATED` or `BLOCKED`/`FAILED` for publish.

Secrets, tokens, `SSH_AUTH_SOCK` paths, and private key material MUST NOT appear on the record, briefs, or PR body.

## Feature branch

Unchanged naming: `feature/task-<task_id>`. Only this branch may be pushed. Default/protected names remain `ProtectedBranchError` via existing `assert_publish_allowed`.

## Pull request (hosting)

| Field | Rules |
|---|---|
| Head | Task feature branch |
| Base | Project default branch (not a push to that branch) |
| Title | Rewritten every successful publish |
| Body | Five sections + task reference; rewritten every successful publish |
| Merge | Impossible through this workflow |

Idempotency key: same work-branch head → same PR number.

## Publish attempt (derived / overlay)

Not a second table. `publish_attempt` + `steps` rows with `phase=="github"`. Automatic stop when three **transient** publish tries have failed. Auth failures block without spinning the transient budget.

## PIV-complete (predicate)

Validation passed for this run. Necessary. **Not** sufficient for wait-return. History MAY show `COMPLETED` then `github`.

## State transitions

```text
(006 recovery/chain) --> VALIDATING
VALIDATING + pass --> history COMPLETED --> github
github + upsert ok + identity complete --> PR_CREATED (slot free)
github + NON_RETRYABLE --> BLOCKED (phase github; occupy)
github + TRANSIENT, publish_attempt < 3 --> retry github
github + TRANSIENT, third fail --> BLOCKED (phase github)
HUMAN_DECISION_REQUIRED | FAILED | BLOCKED(recovery, never passed validation) --> 0 GitHost calls
BLOCKED(github) + resume A --> FAILED (slot free)
BLOCKED(github) + resume B --> one publish retry (not diagnosis/debug)
BLOCKED(recovery) + resume B --> 006 granted cycle (unchanged)
PR_CREATED / FAILED --> slot free
```

| Event | Slot | Recovery `attempt` | `publish_attempt` |
|---|---|---|---|
| Validation pass → publish start | occupied | unchanged | 1 (first try) |
| Transient publish retry | occupied | unchanged | +1 |
| `PR_CREATED` | released | as recorded | as recorded |
| Blocked publish | occupied | unchanged | as recorded |
| Blocked-publish `B` | occupied then run | unchanged | +1 |
| Recovery cycle | occupied | +1 | `0` (never published) |
| Second start while occupied | refuse | unchanged | unchanged |

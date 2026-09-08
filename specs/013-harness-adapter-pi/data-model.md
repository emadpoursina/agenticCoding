# Data Model: Pi Harness Adapter

**Feature**: `013-harness-adapter-pi` | **Date**: 2026-09-08

The model extends the existing Hermes `WorkflowRecord` and atomic
`overlay.json`. It adds no task table, queue, event stream, Pi database, or
second worktree.

## Harness start request

**Entity**: one Hermes-to-harness work attempt.

| Field | Type | Rules |
|---|---|---|
| `project_id` | `str` | Required; matches the selected board task and enrolled project. |
| `task_id` | `str` | Required; non-empty and not path-like. |
| `task_context` | `TaskContext` | Bounded task description, expected result, acceptance criteria, priority, platform, notes, and dependencies; no secrets or transcripts. |
| `repository_context` | `RepositoryContext` | Repository identity and configured default branch; read-only context for the harness. |
| `workspace_path` | `Path` | Prepared task worktree; must equal Hermes' expected project/task location and differ from the enrolled root. |
| `workspace_branch` | `str` | Current feature branch; must be non-protected and match the task. |
| `playbook_id` | `str` | V1 accepts exactly `speckit-orchestrate`; no stage names or stage list. |
| `model_profile` | `str` | Required provider-neutral profile reference; no provider name, SDK client, or model slug. |
| `timeout_seconds` | `float` | Required finite positive wall-clock limit. Missing, zero, negative, or non-finite values are rejected before adapter start. |
| `safety_limits` | `SafetyLimits` | Current worktree write root, feature-branch-only rule, no-publish rule, no-protected-branch rule, and secret-free-output rule. |
| `operator_flags` | `tuple[str, ...]` | Bounded flags such as `skip`; unknown or secret-bearing flags are rejected. |
| `resume_context` | `ResumeContext \| None` | Safe answers, assumptions, continue confirmation, prior diagnostics, and an optional opaque resume reference. |

`workspace_path` may be a `Path` inside the process boundary, but serialized
requests and model-facing context use a worktree-relative location. The
request never contains a Pi SDK object or an ordered Spec Kit method.

## Task and repository context

`TaskContext` and `RepositoryContext` are provider-neutral projections of the
existing `BoardTask` and `ProjectContext`. They contain only fields needed to
execute and inspect the task:

- identity, goal, expected result, acceptance criteria, priority, platform,
  technical notes, dependencies, repository name, and default branch;
- no board write handle, Kanban database path, GitHub credential, model
  transcript, or private reasoning.

Hermes remains the source of truth for the full board/project records. The
projection prevents a harness from receiving control-plane internals.

## Safety limits

| Field | Type | Rules |
|---|---|---|
| `write_root` | `str` | Worktree-relative root, normally `"."`; the adapter may not widen it. |
| `feature_branch_only` | `bool` | Must be `True`. |
| `allow_publish` | `bool` | Must be `False`. |
| `allow_protected_branch` | `bool` | Must be `False`. |
| `allow_external_writes` | `bool` | Must be `False`. |
| `reject_secrets` | `bool` | Must be `True`. |

These values are validated by Hermes and independently enforced by the Pi
adapter/runtime. A harness operation that attempts a forbidden write or GitHub
operation fails the run and cannot produce `completed`.

## Resume context

**Entity**: the safe human/recovery information Hermes passes into a new
whole-run attempt.

| Field | Type | Rules |
|---|---|---|
| `answers` | `tuple[str, ...]` | Operator answers to the parked question batch; bounded and secret-free. |
| `assumptions` | `tuple[str, ...]` | Hermes' documented skip assumptions and choice report inputs. |
| `continue_confirmed` | `bool` | Set only after the single post-clarification/skip continuation decision. |
| `diagnostic_summary` | `str` | Bounded validation/stuck context; no transcript or credentials. |
| `prior_reason` | `str` | Bounded reason from the prior normalized result. |
| `resume_reference` | `str \| None` | Optional opaque, safe runtime reference; it is never interpreted by Hermes. |

Native Spec Kit files remain in the worktree. Hermes does not create a second
resume database or copy the playbook cursor into stage-specific workflow
columns.

## Harness artifact

**Entity**: one native file produced by a harness.

| Field | Type | Rules |
|---|---|---|
| `kind` | `str` | Safe label such as `specification`, `plan`, `tasks`, or `related`; not a Hermes alias. |
| `relative_path` | `str` | Normalized path below the current task worktree; no absolute path, traversal, symlink, directory, or secret. |

Expected successful Pi fixtures include native `specs/<feature>/spec.md`,
`plan.md`, `tasks.md`, and any related playbook files. Hermes stores relative
paths for inspection and resolves them only against the validated worktree.

## Normalized harness result

**Entity**: the sole result returned for one harness invocation.

| Field | Type | Rules |
|---|---|---|
| `status` | `Literal["completed", "failed", "needs_human", "stuck"]` | Closed set; unknown statuses fail closed. |
| `reason` | `str` | Required bounded safe explanation; no private reasoning or secrets. |
| `next_action` | `str` | Safe operator/orchestrator action; required when a follow-up is needed. |
| `artifacts` | `tuple[HarnessArtifact, ...]` | Optional validated native artifact paths under the worktree. |
| `changes` | `tuple[str, ...]` | Optional worktree-relative changed paths; validated like artifacts. |
| `output_reference` | `str \| None` | Optional safe relative log/output reference; never a token, transcript, or secret. |
| `retryable` | `bool` | Whether Hermes may start another whole harness attempt. |
| `questions` | `tuple[str, ...]` | Required for `needs_human`; safe operator questions only. |
| `resume_context` | `ResumeContext \| None` | Required when later resume needs information not recoverable from the worktree. |
| `harness_id` | `str` | Generic selected adapter identity; no SDK type or provider/model slug. |

`completed` means only that the selected playbook ended. It does not mean
validation passed or that a commit, push, or pull request is allowed.

Status rules:

- `completed`: playbook finished and returned valid native artifacts/changes;
  Hermes proceeds to existing validation.
- `failed`: startup, timeout, malformed output, unsafe operation, runtime, or
  unrecoverable execution failure; Hermes does not validate or publish.
- `needs_human`: Pi stopped at a human gate and returned questions; Hermes
  parks without starting later playbook work.
- `stuck`: the harness could not progress at a recoverable or unrecoverable
  stuck point; Hermes owns bounded whole-run retry and escalation.

## Workflow record extension

`WorkflowRecord` remains the single operational record in `overlay.json`.
Replace the old `external_result`/stage-handoff meaning with:

| Field | Type | Rules |
|---|---|---|
| `harness_result` | `HarnessResult \| None` | Last normalized result, with relative artifacts and safe metadata only. |
| `harness_attempt` | `int` | Whole-run attempt number; increments only when a new harness start occurs. |
| `resume_context` | `ResumeContext \| None` | Parked human decision, skip/continue state, or recovery diagnostics on the existing record. |
| `legacy_migration_reason` | `str \| None` | Set when an old Hermes stage record is parked for human review; never triggers automatic migration. |

The overlay reader remains backward-compatible enough to load old snapshots
for migration detection, but old `PLANNING_COMPLETE` and stage-phase records
are converted to a human-parking outcome before any harness or legacy stage
call. They are not silently rewritten as a new successful harness result.

## Hermes orchestration states

Hermes records orchestration states only:

```text
TASK_SELECTED
  -> WORKSPACE_READY
  -> EXECUTION_STARTED
  -> EXECUTION_RUNNING
  -> NEEDS_HUMAN
  -> EXECUTION_FINISHED
  -> VALIDATION
  -> PUBLISHING
  -> COMPLETED / PR_CREATED

EXECUTION_FAILED -> FAILED
EXECUTION_STUCK  -> retry whole run (at most three) or NEEDS_HUMAN
VALIDATION failure -> existing recovery or human/block
```

The existing storage may retain compatible `RUNNING`, `VALIDATING`, and
`HUMAN_DECISION_REQUIRED` labels where changing them would create unrelated
overlay churn, but `current_phase` is limited to orchestration values such as
`execution`, `validation`, `github`, and `human`. It must not record
`specify`, `clarify`, `plan`, `tasks`, `analyze`, `implement`, `converge`, or
`PLANNING_COMPLETE` as a live Hermes checkpoint.

## Safety invariants

1. One harness start produces one normalized result.
2. Every request has a positive timeout and a validated task worktree.
3. Every result is status-closed, secret-free, and path-contained.
4. Pi owns its internal playbook cursor; Hermes owns only orchestration state.
5. Human questions, skip assumptions, continue confirmation, and diagnostics
   live on the existing workflow record.
6. A failed, human, or stuck result cannot reach validation or GitHub publish.
7. Validation must pass before Hermes commits/pushes or creates/updates a PR.
8. Pi cannot push, merge, deploy, write protected/default branches, write
   AiNative, or write a sibling worktree.

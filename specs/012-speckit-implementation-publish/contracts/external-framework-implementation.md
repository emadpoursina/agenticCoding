# Contract: Spec Kit Implementation and Publish

**Feature**: `012-speckit-implementation-publish`

This contract extends the delivered external-framework planning boundary.
Hermes remains the owner of sequencing, state, recovery, validation gating,
Git commits required for publish, GitHub operations, and notices.

## Configuration and runtime identity

The live configuration keeps one active pinned provider:

```yaml
external_framework:
  providers:
    - id: github-spec-kit
      version: 1.0.1
      active: true
  runtime:
    path_env: HERMES_SPECKIT_RUNTIME
```

The live constructor MUST:

1. require exactly one active provider;
2. reject unsupported ids and empty pins;
3. resolve the preinstalled runtime through the configured environment
   variable;
4. require exact provider id, version, and non-empty revision equality in the
   runtime and setup manifests;
5. complete all checks before any plan, tasks, implement, validation, or
   publish model/framework work.

Plan, tasks, implement, and recovery-fix calls MUST use the same selected
identity and runtime revision.

## Provider-neutral Python surface

The existing provider-neutral types remain the public boundary:

```python
class ExternalFrameworkAdapter(Protocol):
    identity: FrameworkIdentity
    framework_revision: str

    def execute(
        self,
        context: ExternalFrameworkContext,
    ) -> ExternalFrameworkResult: ...
```

`ExternalFrameworkContext` MUST carry:

- lifecycle step (`plan`, `tasks`, or `implement` in this feature);
- current board task and project;
- current task worktree and feature branch;
- active provider identity and exact runtime revision;
- model assignment selected by Hermes;
- discovery summary;
- validated native prior artifact paths;
- validation and diagnostic context for recovery fixes;
- safe human decision text when resuming a parked step.

`ExternalFrameworkResult` MUST carry:

- explicit `success`, `failure`, or `blocked` status;
- provider id, version, and exact framework revision;
- only validated native worktree artifact paths;
- safe questions, next action, and summary.

`specify` and `clarify` remain visible unsupported lifecycle steps. They MUST
not be silently mapped to implement or another provider.

## Spec Kit adapter

The provider implementation remains `personalAgent/src/hermes_kanban/speckit.py`:

```python
class SpecKitAdapter:
    def __init__(
        self,
        runtime: SpecKitRuntime,
        model_service: ModelService,
    ) -> None: ...

    def execute(
        self,
        context: ExternalFrameworkContext,
    ) -> ExternalFrameworkResult: ...
```

`PinnedSpecKitRuntime` MUST:

- reuse a matching setup marker in the current worktree;
- reject a mismatched marker without overwriting it;
- invoke only Hermes's injected model service;
- support plan/tasks native artifact materialization and implement file
  materialization;
- write only below the task worktree;
- preserve partial files for existing inspection/recovery rules;
- optionally create a local commit when the structured model result requests
  it, without pushing or opening/updating a PR.

Implement MUST consume the exact validated `plan` and `tasks` paths supplied
in `previous_artifacts`. It MUST not create `PLAN.md`, `TASKS.md`, a second
task list, a second workspace, or a framework-owned model client.

## Safe model/file boundary

The existing `ModelService.complete` remains the only model surface:

```python
class ModelService(Protocol):
    def complete(
        self,
        *,
        assignment: str,
        context: AssembledContext | ExternalFrameworkContext,
    ) -> ModelResponse: ...
```

Hermes chooses the assignment:

- `planning` for plan and tasks;
- `implementation` for initial implement and retryable implementation fixes;
- existing validation assignment for tester/diagnosis roles.

Implementation file keys MUST be relative to the current worktree and MUST
be rejected when they are absolute, traversal-based, symlinked, outside the
worktree, or secret-bearing. The adapter MUST NOT write AiNative, the
enrolled root, runtime source, control-plane state, or sibling worktrees.

Validation receives the native artifact-path handoff through the existing
context seam. It MUST NOT require Hermes plan aliases.

## Executor contract

The executor keeps one trust boundary and adds lifecycle-aware routing:

```python
def execute_framework(
    self,
    adapter: ExternalFrameworkAdapter,
    lifecycle_step: str,
    project_id: str,
    task_id: str,
    *,
    task: BoardTask,
    discovery_summary: str = "",
    previous_artifacts: dict[str, Path] | None = None,
    validation_summary: str = "",
    diagnostic_summary: str = "",
    decision: str | None = None,
) -> ExternalFrameworkResult: ...
```

It MUST validate task/project/workspace/branch/model inputs, select the
correct configured model slot, validate previous native paths, and call no
AiNative agent lookup for framework steps.

## Orchestrator sequence

For a new live-style task with the active external provider, the sequence is:

```text
scout
  → plan
  → tasks
  → PLANNING_COMPLETE checkpoint
  → implement
  → existing validation
  → existing GitHub publish
```

After successful tasks:

1. combine and validate the native plan/tasks paths;
2. append a `PLANNING_COMPLETE` step;
3. keep the workflow active and the single-task slot occupied;
4. invoke implement in the same worktree without routine plan approval.

A framework question parks through the existing human-decision state and
resumes the exact incomplete framework step after a listed decision.

## Historical planning-handoff resume

A terminal `PLANNING_COMPLETE` record from the previous planning-only slice is
not PIV-complete. When that task is selected by name or next-ready, Hermes
MUST:

1. occupy the slot;
2. validate the saved provider identity, revision, worktree, branch, setup
   marker, and native plan/tasks files;
3. skip completed plan/tasks calls;
4. continue with Spec Kit implement;
5. continue through validation and, after a pass, the existing GitHub publish.

Malformed, missing, unreadable, secret-bearing, escaping, or drifted handoffs
MUST return a visible failure or blocked result before implementation,
validation, or publish. Hermes MUST NOT guess a path or silently rerun
planning with a different provider.

## Recovery contract

The existing validation state machine remains authoritative:

```text
validation failure (RETRYABLE)
  → diagnosis (existing validation/diagnostic role)
  → implement fix (Spec Kit)
  → re-validation
```

The implementation-fix request MUST include the native plan/tasks paths, the
diagnostic report, and the last validation context. It MUST use the
implementation model assignment and the same worktree/provider identity.

Transient failures retain the existing validation-only retry behavior.
Non-retryable failures retain the existing blocked outcome. Neither may
invoke an unauthorized implement step, and no adapter-local retry is added.
Questions in diagnosis, implement, or validation use the existing human
decision state.

## GitHub publish contract

No implementation, diagnosis, recovery, or validation step may call GitHub.
After validation passes, the orchestrator MUST reuse the existing sequence:

1. ensure a history-preserving local commit only when needed;
2. enforce the task feature branch and configured default base branch;
3. publish only the feature branch;
4. create or update one pull request;
5. require pull-request number and HTML URL;
6. emit the existing `pr_created` notice.

Merge, approval-as-human, deployment, force-push, amend, and protected/default
branch writes remain forbidden.

## Persistence contract

`WorkflowRecord.external_result` MUST round-trip provider identity, runtime
revision, native paths, implementation outcome, questions, next action, and
safe summary through the existing atomic overlay. Records MUST NOT contain
model transcripts, private reasoning, credentials, tokens, or secrets.

`PLANNING_COMPLETE` MUST never be treated as `COMPLETED`, PIV-complete, or
`PR_CREATED`. A successful run ends only after validation and the existing
publish result.

## Error mapping

| Condition | Required result |
|---|---|
| Zero/multiple active providers | Configuration error before model/framework work |
| Unsupported provider, empty pin, or runtime mismatch | Configuration/runtime error before model work |
| Unsupported `specify`/`clarify` | Visible blocked result with no model call |
| Missing previous native paths | Validation failure before implement |
| Escaping/secret-bearing implementation file | Unsafe failure; no success result |
| Implement question | Existing human-decision state; no validation/publish |
| Implement/model failure | Existing failure/blocked behavior; partial files remain inspectable |
| Retryable validation failure | Existing diagnosis → Spec Kit implement fix → re-validation |
| Transient/non-retryable validation failure | Existing validation-only retry or blocked result |
| Invalid saved planning handoff | Visible failure/blocked before implement, validation, or publish |
| Validation pass | Existing GitHub publish path only |

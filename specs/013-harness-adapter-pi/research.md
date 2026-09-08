# Research: Pi Harness Adapter

**Feature**: `013-harness-adapter-pi` | **Date**: 2026-09-08

This research resolves the implementation choices against the feature
specification, the constitution, the locked harness architecture, and the
current `personalAgent/` execution path. No unresolved clarification remains.

## 1. Replace the stage boundary with a run boundary

**Decision**: Reuse the current provider boundary module and replace its
stage-oriented context/result API with a provider-neutral harness start/result
contract. The contract carries one work attempt, not `plan`, `tasks`, or
`implement` lifecycle names. `AgentExecutor` exposes one harness-start method;
the orchestrator never calls a framework stage.

The current `external_framework.py`, `speckit.py`, and the external branches in
`orchestrator.py` are the smallest existing seams to replace. The old
`execute_framework`, `execute_step`, `_run_external_planning`, and
`PLANNING_COMPLETE` continuation path are removed from the live path rather
than wrapped as a second route. Generic validation helpers may remain in the
boundary module when they validate requests/results instead of sequencing
Spec Kit.

**Rationale**: The current feature 012 path already has worktree, artifact,
provider identity, overlay, and publish controls, but it exposes exactly the
stage machine this feature must remove. Moving those checks to one request and
one result preserves the safety work without preserving the wrong ownership
model.

**Alternatives considered**:

- Keeping `plan`/`tasks`/`implement` and adding a Pi shortcut — leaves two
  competing Spec Kit machines and violates the locked architecture.
- Adding a second orchestrator for Pi — duplicates task, recovery, human, and
  publication state.
- Passing raw Pi SDK objects through Hermes — couples orchestration to the
  first harness and makes replacement cross-cutting.

## 2. Keep Pi SDK details behind one adapter-owned port

**Decision**: Add a Pi-specific adapter/runtime port in the provider module.
The production adapter translates the generic request into the installed Pi
SDK's task/playbook invocation and translates its terminal response back to the
generic result. Pi SDK types, client construction, playbook flags, and model
mapping stay inside that adapter. The generic Hermes package remains
stdlib-only; the concrete Pi SDK runtime is supplied by the configured
preinstalled runtime or injected port, and the fixture uses a stand-in.

The adapter owns the complete Spec Kit playbook: specify, clarify stop and
resume, one continue gate, plan, tasks, conditional analyze, and the
implement/converge loop. The adapter exposes no method for an individual
Spec Kit stage. A missing, mismatched, or unavailable Pi runtime returns a
visible `failed` result before work begins.

**Rationale**: This repository has no installed Pi SDK module and the
constitution forbids an unapproved dependency. A narrow injected port makes
the real SDK integration testable without leaking SDK types into Hermes or
requiring a second runtime in the control plane. Runtime provisioning remains a
deployment concern, just as the current preinstalled Spec Kit assets were.

**Alternatives considered**:

- Importing a Pi SDK package directly from every Hermes layer — violates the
  adapter boundary and adds an unapproved dependency.
- Reimplementing the Pi agent loop in Python — violates the architecture and
  duplicates the harness.
- Calling individual Spec Kit scripts from Hermes — recreates the removed
  stage machine.

## 3. Use a closed, provider-neutral start/result schema

**Decision**: Define frozen, typed records with these shapes:

- `HarnessStartRequest`: task/project identity and safe task context, prepared
  worktree and feature branch, repository context, accepted playbook identity,
  required positive timeout, named model-profile reference, safety limits,
  operator flags, and bounded resume/diagnostic context.
- `HarnessResult`: exactly one of `completed`, `failed`, `needs_human`, or
  `stuck`; safe reason and next action; worktree-relative native artifact
  paths; worktree-relative produced changes; optional output reference;
  whole-run retry guidance; safe questions; and bounded resume context.

Artifact and change paths are relative to the prepared worktree in the
serialized result. Boundary validation resolves them only for inspection and
rejects absolute paths, traversal, symlinks, non-regular files, unreadable
files, secrets, or writes outside the worktree. The only accepted playbook in
this version is `speckit-orchestrate`; requests naming another playbook are
rejected before the adapter is invoked.

**Rationale**: The schema is large enough to support human parking,
diagnostics, timeout/retry decisions, and inspectable native files, while
remaining independent of Pi SDK types and internal Spec Kit stage names.

**Alternatives considered**:

- Reusing `ExternalFrameworkResult` with `success`/`failure`/`blocked` —
  cannot represent the required normalized harness outcomes or distinguish a
  human gate from a failed run.
- Returning absolute provider paths — leaks machine layout and weakens the
  worktree trust boundary.
- Returning a free-form JSON blob — makes persistence and secret validation
  ambiguous.

## 4. Resume human decisions through the same whole-run boundary

**Decision**: A Pi question or clarify/skip gate returns `needs_human` and
  stops before later playbook work. Hermes stores the safe question batch,
  documented skip assumptions/choice report, the continue decision, and the
  bounded resume context on the existing `WorkflowRecord`/overlay. A resume
  calls the same harness start boundary with that context; it never calls a
  stage.

Skip is an operator flag on the initial request. When Pi reports the
specify/clarify questions under skip, Hermes self-answers using the documented
assumptions, emits the choice report through the existing messaging seam, and
requires exactly one continue confirmation before resuming. Ordinary
clarification answers and the continue decision follow the existing human
decision/resume mechanism. Pi never receives an operator chat channel.

**Rationale**: Human authority, restart recovery, and decision persistence
remain in Hermes while Pi retains ownership of its internal stage cursor.
Reusing the existing record avoids a second database and preserves partial
native files.

**Alternatives considered**:

- Letting Pi ask the operator directly — breaks the control-plane authority
  boundary.
- Turning each question into a Hermes Spec Kit stage — recreates the old
  machine.
- Storing resume state in a new Pi or Hermes database — violates the
  single-record/storage constraint.

## 5. Treat timeout and stuck attempts as orchestration inputs

**Decision**: Require a positive wall-clock timeout in every start request.
The adapter passes a deadline/stop signal to the Pi runtime and maps expiry
to `failed`; it never maps timeout to `completed`. Timeout failures consume
one whole-run attempt. A `stuck` result is retried only when its result says
the same stuck point is recoverable, with no more than three whole harness
attempts. The third failed attempt parks for a human and no fourth automatic
run starts.

The adapter has no retry loop. Hermes increments and persists whole-run
attempts, carries the previous reason/diagnostic context into a new start
request, and applies the existing validation-recovery budget after a
completed harness result.

**Rationale**: The timeout is a trust-boundary safety limit, while attempt
count and escalation are orchestration responsibilities. Keeping retry policy
outside Pi prevents hidden retries and preserves restart semantics.

**Alternatives considered**:

- Defaulting a missing timeout — permits an unbounded harness process.
- Retrying inside Pi — hides attempts from Hermes and can exceed the human
  escalation budget.
- Treating a timeout as success with partial files — can trigger validation
  and publication on an incomplete run.

## 6. Preserve existing validation, Git, and publication seams

**Decision**: A `completed` harness result only moves Hermes to the existing
  project validation phase. Validation still runs from the prepared worktree;
  only a pass reaches `_begin_github`/`_run_github`, the existing feature
  branch push, and create-or-update pull request. A validation failure that
  needs workspace changes starts another whole harness run with diagnostic
  context. Hermes never calls a Pi implement stage or publishes from the
  adapter.

Existing `execute_role` support remains only for the existing validation and
  diagnosis responsibilities; it is not a fallback execution path for
  Spec Kit. The live constructor requires a configured harness adapter.

**Rationale**: This is the smallest change to the proven safety boundary.
Validation and GitHub behavior already enforce protected branches, no
pre-validation publication, recovery classification, and notices.

**Alternatives considered**:

- Letting Pi validate or publish — violates Hermes ownership and bypasses
  existing checks.
- Rebuilding validation/recovery around Pi — duplicates the control plane.
- Falling back to the old Hermes stage path when Pi fails — violates the
  removal decision and hides runtime failures.

## 7. Handle legacy short-path records explicitly

**Decision**: On startup/reclaim, records showing the removed Hermes Spec Kit
  phases or a historical `PLANNING_COMPLETE` checkpoint are parked for a human
  with a clear migration reason. Hermes does not finish them on the old
  machine, auto-rewrite their history, or auto-start Pi. New eligible tasks
  always prepare a worktree and start the generic harness path.

The old stage entry points are deleted from live dispatch and recovery. A
compatibility rejection may remain at a public boundary only to return a
visible unsupported-operation error before any stage call.

**Rationale**: This honors the clarified migration behavior and prevents a
  partial old run from silently changing execution semantics after rollout.

**Alternatives considered**:

- Resuming old plan/tasks state through Pi — auto-rewrites history and loses
  the required human review point.
- Leaving the old path behind a feature flag — preserves a forbidden fallback.
- Silently deleting old records — loses inspectable task history.

## 8. Verify with disposable Pi fixtures and existing checks

**Decision**: Replace the stage-oriented Spec Kit fixture checks with a
  `PiRuntime` stand-in that records its internal playbook order while Hermes
  observes exactly one start/result call. Add fixtures for successful runs,
  conditional analyze, implement/converge repetition, clarify/skip/continue,
  timeout, malformed/unsafe results, unavailable runtime, stuck-attempt
  escalation, validation recovery, restart, and publish gating.

Use temporary git repositories/worktrees, a read-only AiNative fixture only
for validation/diagnosis where required, `MemoryGitHost`, in-memory messaging,
and no live credentials. Run focused pytest suites, the full pytest suite,
ruff, and every command in `quickstart.md`.

**Rationale**: These checks prove the cross-cutting contract without live
  GitHub, live Pi credentials, production repositories, or writes to AiNative.

**Alternatives considered**:

- Testing the operator's Hermes home or live Pi runtime — unsafe and
  non-repeatable.
- Keeping only the old planning tests — would not prove the new one-run
  boundary.
- Adding a new testing dependency — unnecessary.

## Resolved technical context

| Topic | Decision |
|---|---|
| Language | Python 3.12 (`>=3.12,<3.14`) through the existing uv package |
| Generic contract | One typed start request and one normalized result |
| First adapter | Pi SDK adapter with SDK/runtime details private to its module |
| Playbook | Pi-owned `speckit-orchestrate`; no Hermes stage API |
| Model routing | Named profile reference in Hermes; Pi maps it privately |
| Storage | Existing `WorkflowRecord` and atomic overlay plus task worktree |
| Recovery | Existing Hermes validation recovery plus bounded whole-run attempts |
| Publication | Existing Hermes GitHub/PR path only after validation |
| Dependencies | No new Python dependency; runtime/SDK supplied by adapter deployment |
| Tests | pytest and ruff with disposable repositories and stand-ins |

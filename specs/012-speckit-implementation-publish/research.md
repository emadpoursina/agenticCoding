# Research: Spec Kit Implementation and Publish

**Feature**: `012-speckit-implementation-publish` | **Date**: 2026-09-07

Phase 0 resolves the implementation choices against the clarified feature
spec, the constitution, the delivered external-framework planning slice, and
the current `personalAgent/` code. No unresolved clarification remains.

## 1. Extend the delivered provider boundary

**Decision**: Extend `ExternalFrameworkContext`, `ExternalFrameworkResult`,
`AgentExecutor.execute_framework`, and `SpecKitAdapter` for `implement`.
Keep `github-spec-kit` as the only active provider and preserve the same
identity and runtime revision for plan, tasks, implement, and recovery fixes.

**Rationale**: The planning slice already validates provider selection,
runtime manifests, worktree containment, model calls, native artifacts, and
overlay metadata. A second builder abstraction would duplicate those trust
boundaries and violate the least-code and single-framework constraints.

**Alternatives considered**:

- Copying or creating an AiNative `builder` — violates AiNative's read-only
  boundary and makes the live roster an accidental implementation API.
- Adding a second implementation worker or orchestrator — duplicates existing
  state, recovery, and human-decision controls.
- Calling a framework-owned CLI/model runtime — breaks the requirement that
  Hermes's configured model service remains the model boundary.

## 2. Materialize implementation through the existing model service

**Decision**: `SpecKitAdapter` sends one structured `implement` request to
the existing `ModelService` using the configured implementation assignment.
The runtime applies the response's file map only below the inspected task
worktree, optionally creates a local commit through existing safe Git rules,
and returns normalized provider metadata. It never pushes, opens/updates a
pull request, merges, deploys, or starts another model runtime.

**Rationale**: `ModelResponse` already supports bounded file materialization
and an explicit local-commit flag. Reusing that response keeps implementation
and recovery hermetic in tests and avoids a new dependency or tool loop.
Containment and secret checks must be shared with the existing executor
write guard rather than trusting provider-returned paths.

**Alternatives considered**:

- Letting the model write arbitrary files — unsafe at the worktree trust
  boundary.
- Running `git push` or `gh pr` inside the adapter — bypasses the
  orchestrator-owned publish contract.
- Adding a new implementation client or dependency — unnecessary and makes
  model routing/provider selection drift possible.

## 3. Preserve native artifacts as the implementation handoff

**Decision**: Pass the exact validated native `plan` and `tasks` paths in the
external context and preserve them in the combined workflow result. Add
validation and diagnostic summaries as structured implementation context.
Validation/tester receives the same native paths through its existing context
seam; it does not read or require Hermes `PLAN.md` or `TASKS.md` aliases.

**Rationale**: The native paths are the only authoritative handoff in the
spec. Passing paths, rather than copying their text into competing files,
prevents a second task store and lets the implementation and validation
steps inspect the same worktree state.

**Alternatives considered**:

- Reading `PLAN.md` from the current executor — it is not present on the
  external live path and would reintroduce a competing canonical artifact.
- Copying native content into a new Hermes record/file — duplicates source of
  truth and can diverge from the files the provider actually consumed.
- Passing unvalidated provider paths — permits worktree escape or stale
  artifacts during recovery/resume.

## 4. Keep the checkpoint distinct from full-run completion

**Decision**: New full runs append a `PLANNING_COMPLETE` checkpoint after
native plan/tasks, keep the workflow active and the single-task slot held,
then continue in the same worktree to `implement`. Historical terminal
`PLANNING_COMPLETE` records remain compatible and are resumed only when a
named or next-ready selection validates their saved handoff.

**Rationale**: The existing planning slice uses `PLANNING_COMPLETE` as a
free-slot terminal state, while this feature requires the same label to
remain visibly distinct from PIV-complete without stopping a new full run.
A checkpoint step plus explicit legacy-resume handling preserves both
semantics without inventing a second task board or terminal success state.

**Alternatives considered**:

- Treating the checkpoint as `COMPLETED` — confuses planning with validated
  implementation and violates the success-state distinction.
- Freeing the slot for every new run — allows another task to start while
  the current task has not implemented or validated.
- Rerunning plan/tasks on resume — can replace valid native artifacts and
  loses the saved handoff guarantee.

## 5. Reuse the existing validation and recovery state machine

**Decision**: After successful implement, call the current validation path.
For a retryable validation failure, retain the existing
`diagnosis → fix → re-validation` order, but route the workspace-fixing
step to external `implement`. Diagnosis continues through the existing
validation/diagnostic role. Transient and non-retryable classifications keep
their current validation-only or blocked behavior.

**Rationale**: Recovery budgets, human-decision parking, overlay persistence,
and publish gating already live in `PivOrchestrator`. Only the worker used for
the workspace fix changes; a new adapter-local retry machine would create
competing attempt counts and recovery semantics.

**Alternatives considered**:

- Reusing the AiNative `builder` role for fixes — forbidden in the live
  methodology and inconsistent with the active provider.
- Retrying inside `SpecKitAdapter` — hides failures from Hermes and can
  exceed the existing recovery budget.
- Rebuilding validation/recovery for external implementation — duplicate
  state and risks publishing after an incomplete check.

## 6. Resume saved planning handoffs fail closed

**Decision**: A saved terminal planning record is eligible only when its
provider id/version, framework revision, worktree path, feature branch,
setup marker, and native `plan`/`tasks` files match the currently active
runtime and task. A named or next-ready selection uses that worktree and
continues at `implement` without calling plan/tasks. Missing, malformed,
escaping, unreadable, secret-bearing, or drifted handoffs become a visible
failure/blocked result before any implementation, validation, or publish.

**Rationale**: Overlay state is a trust boundary and can outlive a process or
runtime image. Strict validation prevents guessed paths, provider drift, and
silent reconstruction from stale state.

**Alternatives considered**:

- Trusting the saved path because it was produced locally — restart state
  can be edited, stale, or outlive its runtime.
- Recreating a missing plan/tasks file — fabricates the source of truth.
- Silently rerunning planning with the current provider — hides provider
  drift and violates the no-rerun handoff requirement.

## 7. Keep publish exactly where it is

**Decision**: After validation passes, reuse `_begin_github` and `_run_github`
with the existing `GitHost` contract: ensure a history-preserving commit
only when needed, push the feature branch, create/update one PR against the
configured default branch, require number and URL, and emit `pr_created`.

**Rationale**: GitHub integration already enforces protected branches,
forbidden actions, retry classification, PR identity, and notices. The
feature changes only the upstream producer of worktree changes.

**Alternatives considered**:

- Letting Spec Kit publish — violates the builder-never-publish boundary.
- Adding a second PR client — can create duplicate PRs and bypass existing
  auth/permission handling.
- Publishing after implementation before validation — violates the explicit
  validation gate.

## 8. Verify with disposable offline fixtures

**Decision**: Extend the existing focused pytest fixtures with a
scout-plus-validation AiNative fixture, pinned Spec Kit runtime stand-in,
disposable worktree, stand-in model, and simulated GitHub/messaging seams.
Run focused tests, the full suite, ruff, and the documented quickstart.

**Rationale**: The feature must prove call order, isolation, recovery, and
publish boundaries without live GitHub, Telegram, model credentials, or
writable AiNative. Existing fixtures already provide these seams and preserve
regression coverage for the older in-process PIV path.

**Alternatives considered**:

- Live credentials and repositories in the gate — unsafe and non-repeatable.
- A new test framework — unnecessary dependency and duplicated fixtures.
- Removing old full-chain fixtures — loses regression coverage for legacy
  injected orchestrator behavior.

## Resolved technical context

| Topic | Decision |
|---|---|
| Language | Python 3.12 (`>=3.12,<3.14`) via the existing uv package |
| Provider | One active `github-spec-kit` provider |
| Runtime | Build-time pinned Spec Kit assets with exact manifest revision |
| Model execution | Existing configured `ModelService`; planning vs implementation slots |
| Workspace | Existing task worktree and feature branch only |
| State | Existing `WorkflowRecord` and atomic overlay |
| Recovery | Existing classification, budget, decisions, and retry order |
| Publish | Existing orchestrator-owned `GitHost` sequence |
| Tests | pytest + ruff with disposable fixtures and stand-ins |

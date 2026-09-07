# Implementation Plan: Spec Kit Implementation and Publish

**Branch**: `012-speckit-implementation-publish` | **Date**: 2026-09-07 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/012-speckit-implementation-publish/spec.md`

**Note**: `tasks.md` is produced by the next Spec Kit phase and is not part
of this plan run.

## Summary

Extend the already-selected `github-spec-kit` provider from native planning
to native implementation. The live workflow will consume the validated
`plan` and `tasks` paths from the same task worktree, call Spec Kit
`implement` through Hermes's existing model service, then enter the existing
validation/recovery and orchestrator-owned GitHub publish paths. The
orchestrator remains the only owner of task state, recovery, commits that
are required for publish, branch pushes, pull requests, and notices.

The new run path records `PLANNING_COMPLETE` as a checkpoint step while
keeping the slot occupied and continuing into implementation. Historical
planning-only records remain resumable only after strict provider, runtime,
worktree, branch, and native-artifact validation; an invalid handoff fails
closed before implementation, validation, or publish.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via the existing `uv`
package in `personalAgent/`

**Primary Dependencies**: Existing stdlib-only control plane, `ModelService`,
`AgentExecutor`, `PivOrchestrator`, `WorkspaceManager`, `ProjectRegistry`,
`AiNativeAdapter`, `MemoryGitHost`/`LiveGitHost`, and the preinstalled pinned
Spec Kit runtime. No new Python dependency.

**Storage**: Existing native Hermes `kanban.db` read model, one atomic
`overlay.json` execution record, the existing task worktree and feature
branch, and provider-native `specs/<feature>/` artifacts. No second task
store or implementation workspace.

**Testing**: pytest 9.1.1 and ruff 0.16.5. Extend the focused offline
contract suite in
`personalAgent/tests/test_external_framework_planning.py`, add live-style
implementation/recovery assertions where appropriate, then run the complete
pytest suite and `uv run ruff check src tests`.

**Target Platform**: Host pytest on macOS/Linux and the existing
`hermes-agent:local` Docker image with the Spec Kit runtime provisioned at
image build time.

**Project Type**: In-process Python control-plane library plus the existing
worker/CLI dispatcher; not a new service and not a framework-owned worker.

**Performance Goals**: One blocking sequence per task:
`scout → plan → tasks → implement → validation → publish`. Preserve the
existing single-task slot and retry budgets; the adapter adds no retry loop
or concurrency.

**Constraints**: Exactly one active pinned external provider; the active
runtime identity and revision must match before model work; implementation
and recovery writes stay below the prepared task worktree; AiNative,
enrolled project roots, runtime source, control-plane state, and sibling
worktrees remain read-only; native plan/task paths remain canonical; no
publish before validation passes; no merge, deploy, protected-branch push,
force-push, or automatic consequential decision.

**Scale/Scope**: One V0 task slot, one active `github-spec-kit` provider,
one `implement` lifecycle step, existing bounded recovery, one feature
branch, and one create-or-update pull request.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | The clarified feature spec is complete and this plan follows constitution → specify → plan → tasks → implement. |
| II. Least Code (Ponytail) | PASS | Reuses the current provider boundary, executor, worktree, overlay, validation/recovery, GitHub, and messaging seams; no second builder or workflow is introduced. |
| III. Platform-native | PASS | Hermes remains the control plane and native Kanban remains the task source; Spec Kit artifacts stay native in the existing worktree. |
| IV. Trust-boundary tests | PASS | Saved handoffs, provider/runtime identity, artifact paths, model output files, validation outcomes, and publish boundaries receive fixture checks. |
| V. Human authority | PASS | The adapter never publishes, merges, approves as a human, deploys, pushes a protected branch, or answers consequential questions. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Implementation uses the existing model service and build-time runtime assets only. |
| Secrets / isolated Hermes home | PASS | Existing environment/configuration supplies credentials; records and artifacts reject or redact secrets. |
| Model routing | PASS | Plan/tasks use the configured planning assignment; implement and recovery fixes use the configured implementation assignment. No model/provider is hardcoded. |
| Surgical edits | PASS | Changes stay in the current adapter, executor, orchestrator, persistence validation, focused fixtures, and delivery documentation. |

## Project Structure

### Documentation (this feature)

```text
specs/012-speckit-implementation-publish/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── external-framework-implementation.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks), not created here
```

### Source Code (`personalAgent/`)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── external_framework.py  # lifecycle context/result and handoff validation
│   ├── speckit.py             # pinned plan/tasks/implement adapter
│   ├── executor.py            # model slots and safe framework/file context
│   ├── orchestrator.py        # checkpoint, implementation, recovery, validation, publish
│   ├── persist.py             # strict saved-handoff deserialization checks
│   ├── runtime.py             # live construction and CLI result handling
│   └── __init__.py            # public exports/version
├── tests/
│   ├── test_external_framework_planning.py
│   ├── test_piv_orchestrator.py
│   ├── test_restart_recovery.py
│   ├── test_live_piv_bridge.py
│   └── fixtures/
│       ├── ainative/          # scout + validation fixture, no planner/builder
│       ├── ainative-full/     # legacy in-process PIV regression fixture
│       ├── speckit-runtime/   # pinned runtime manifest/setup stand-in
│       └── projects/standard/ # disposable managed project
├── config/
│   └── default.yaml
├── docker/
│   ├── Dockerfile
│   └── speckit-runtime/
├── README.md
├── CHANGELOG.md
└── pyproject.toml
```

**Structure Decision**: Keep the existing flat adapter/control-plane package.
`external_framework.py` owns provider-neutral lifecycle and trust validation;
`speckit.py` owns the one provider's native implementation materialization;
`executor.py` supplies the configured model and safe worktree context;
`orchestrator.py` sequences the checkpoint, implementation, validation,
recovery, and GitHub phases. No builder is added to AiNative, and no new
database, worker, or publish path is created.

## Implementation Design

### 1. Extend the stable external-framework contract

- Keep the closed lifecycle names `specify`, `clarify`, `plan`, `tasks`, and
  `implement`; make only `plan`, `tasks`, and `implement` executable in this
  slice.
- Extend `ExternalFrameworkContext` with the native handoff and recovery
  information needed by implementation: validated prior artifact paths,
  validation summary, diagnostic summary, and the selected model assignment.
- Keep `ExternalFrameworkResult` explicit and provider-neutral. A successful
  implementation result records only validated provider-native worktree
  artifacts (changed files or another provider-owned implementation output);
  failure/blocked results contain no guessed artifacts.
- Add one validation path for saved planning handoffs. It must verify the
  exact active provider/version/revision, expected task worktree and feature
  branch, setup marker, readable regular `plan` and `tasks` files, containment,
  and secret-free metadata before any implementation call.

### 2. Route model execution by lifecycle

- Preserve `ModelService.complete` as the only model call surface.
- Keep plan/tasks on the configured `planning` model assignment.
- Select the configured `implementation` assignment for initial implementation
  and retryable recovery fixes; do not allow the adapter to select a model.
- Extend the safe model context so validation/tester execution receives the
  native plan/task paths and implementation context without reading or
  creating `PLAN.md` or `TASKS.md`.
- Materialize model-requested implementation files only under the inspected
  task worktree. Reject absolute paths, traversal, symlinks, writes into
  AiNative/enrolled/runtime/control-plane/sibling locations, and
  secret-bearing content. A provider may create a local commit through the
  existing safe Git rules, but it cannot push or open/update a pull request.

### 3. Extend `SpecKitAdapter` and its pinned runtime

- Allow `PinnedSpecKitRuntime.execute_step` and `SpecKitAdapter.execute` to
  handle `implement`; retain visible blocked results for `specify` and
  `clarify`.
- For implement, pass the exact prior native plan/task paths and safe
  diagnostic/validation context to the existing model service, apply returned
  files through the worktree containment guard, optionally preserve an
  existing local commit request, and return normalized provider metadata.
- Reuse matching `.specify` setup and the current runtime manifest. Do not
  install, download, launch Cursor/Claude Code, invoke another model client,
  or create a second feature directory.
- Keep partial implementation files for inspection/recovery while returning
  failure when the provider/model does not explicitly report success.

### 4. Continue the orchestrator after the planning checkpoint

- Replace the planning-only live branch with one external workflow path:
  `scout → plan → tasks → checkpoint → implement`.
- Record `PLANNING_COMPLETE` as a `StepRecord` and preserve the combined native
  handoff in `WorkflowRecord.external_result`, but keep a new full run in an
  active implementation state so the slot remains occupied.
- On successful implement, enter the existing validation path. Preserve the
  handoff in the validation context and keep validation pending until checks
  pass.
- Keep framework questions in the existing human-decision state. Resume the
  exact incomplete framework step with the same worktree, identity, and
  artifact paths; do not answer the question automatically.
- Preserve old terminal `PLANNING_COMPLETE` records for compatibility. When a
  named or next-ready run selects one, validate the saved handoff, reclaim/use
  the same worktree, skip plan/tasks, and continue at implement. Invalid or
  incomplete records fail closed before any implementation, validation, or
  publish call.

### 5. Reuse validation, recovery, and GitHub publish

- Keep project checks and the existing validation/tester seam unchanged.
- For retryable validation failures, preserve the current bounded order:
  `diagnosis → Spec Kit implement fix → re-validation`.
- Diagnosis remains the existing validation/diagnostic role. The live path
  must never call an AiNative `builder`; the implementation-fix request uses
  `execute_framework("implement", ...)` with native paths, diagnostic report,
  and last validation result.
- Preserve current transient and non-retryable behavior: validation-only retry
  or blocked outcome as already classified, with no unauthorized implement.
- On validation pass, call the unchanged `_begin_github` / `_run_github`
  sequence: history-preserving commit when needed, feature-branch push,
  create-or-update one PR against the configured default branch, validate
  number and URL, and emit the existing `pr_created` notice.
- Keep GitHub unreachable for implementation, diagnosis, recovery, and any
  pre-validation failure.

### 6. Fixtures, persistence, and delivery surfaces

- Extend the scout-only fixture with the existing validation role needed for
  recovery tests while keeping `specs-planner` and `builder` absent.
- Add stand-in responses for implement success, implementation question,
  model failure, partial files, retryable recovery, transient validation,
  non-retryable validation, and publish/update behavior.
- Round-trip the combined native handoff and implementation outcome through
  the existing overlay. Reject malformed/escaping/secret-bearing saved paths
  during resume rather than guessing or silently restarting planning.
- Update the package exports/version, `personalAgent/CHANGELOG.md`, root
  documentation/version history, operator config, Docker/runtime notes, and
  quickstart commands to describe the full live path and the legacy-handoff
  distinction. Do not document live credentials in git.

## Phase 0 / Phase 1 Outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contract | [contracts/external-framework-implementation.md](./contracts/external-framework-implementation.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Post-design Constitution Check (PASS)

The design extends the existing external-framework boundary rather than
creating a second builder, worker, task store, recovery machine, validation
path, or GitHub publisher. Native plan/task artifacts and implementation
writes remain in the one task worktree; AiNative remains read-only; saved
handoffs are validated at the trust boundary; and human merge/deploy
authority remains unchanged. No unresolved clarification remains.

## Implementation Notes for `/speckit-tasks`

- Keep all provider execution and model calls offline-testable through the
  injected `ModelService` and disposable runtime fixture.
- Make task dependencies explicit: contract/data model before adapter;
  adapter and executor before orchestration; orchestration before recovery
  routing; safety fixtures before documentation/version updates; full pytest
  and ruff last.
- Do not add `PLAN.md`, `TASKS.md`, a second task list, a second workspace,
  a builder role, a provider-local retry loop, or a publish call.
- Preserve legacy fixture coverage for the old in-process PIV path while
  making the configured live path fail closed when the external provider or
  matching runtime is absent.

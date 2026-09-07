# Implementation Plan: External Framework Planning Adapter

**Branch**: `011-external-framework-planning` | **Date**: 2026-09-07 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/011-external-framework-planning/spec.md`

**Note**: This plan is design-only. `tasks.md` is produced by the next
Spec Kit phase.

## Summary

Add a provider-neutral external-framework boundary to `personalAgent/` and a
V0 GitHub Spec Kit adapter. The live workflow keeps AiNative `scout` for
discovery, then invokes the pinned Spec Kit runtime for native plan and task
generation through Hermes's existing configured model service. All bootstrap
and artifacts stay in the already-prepared task worktree. The orchestrator
records the native paths and provider identity in its existing overlay,
returns a distinct `PLANNING_COMPLETE` outcome, frees the single-task slot,
and does not run implementation, validation, GitHub, merge, or deployment.

## Technical Context

The design below is scoped to the existing `personalAgent/` control plane.

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via the existing `uv`
package in `personalAgent/`

**Primary Dependencies**: Existing stdlib-only control plane,
`ModelService`, `ProjectRegistry`, `WorkspaceManager`, and
`AiNativeAdapter`. No new `pyproject.toml` dependency. Docker image
provisions the pinned Spec Kit `v1.0.1` runtime at build time.

**Storage**: Existing read-only Hermes `kanban.db`, existing JSON execution
overlay, and the task's existing git worktree. No new database, task table,
or framework state store.

**Testing**: pytest 9.1.1 and ruff 0.16.5; one focused
`tests/test_external_framework_planning.py` with disposable git/worktree,
runtime, methodology, model, and board fixtures, followed by the existing
full suite and style check.

**Target Platform**: Host pytest on macOS/Linux and the existing
`hermes-agent:local` Docker image. The runtime source is preinstalled in the
image and addressed through a configured environment-variable name.

**Project Type**: In-process Python library plus the existing worker/CLI
dispatcher; not a new service or framework-owned process.

**Performance Goals**: One blocking sequence of discovery, plan, and tasks;
no throughput or concurrency increase. Provider operations do not add their
own retry loop.

**Constraints**: One active provider; exact pinned version and runtime
revision; no per-run install/download/external API; all writes under the
prepared worktree; AiNative remains read-only; no `PLAN.md`/`TASKS.md`
aliases; existing PIV, overlay, retry, GitHub, protected-branch, and
human-decision controls remain authoritative.

**Scale/Scope**: One V0 task slot, one active `github-spec-kit` provider,
two executed lifecycle steps (`plan`, `tasks`), and future lifecycle names
reserved by the stable contract.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | Clarified spec is complete; this plan follows the required research/design order. |
| II. Least Code (Ponytail) | PASS | Reuses existing executor, model service, workspace, overlay, and orchestrator; adds only the provider boundary and Spec Kit implementation required by the spec. |
| III. Platform-native | PASS | Hermes remains the control plane; native task board, worktree, overlay, retries, GitHub, and AiNative read-only rules remain in place. |
| IV. Trust-boundary tests | PASS | Configuration, runtime identity, worktree paths, artifact files, secrets, and normalized results receive focused fixture checks. |
| V. Human authority | PASS | No merge, protected push, deployment, or automatic answer to framework questions; only disposable/offline fixtures are used in checks. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Spec Kit is an image/runtime asset, not a `personalAgent` Python dependency. |
| Secrets / isolated Hermes home | PASS | Credentials remain in existing runtime configuration; no secret enters framework files, overlay, logs, or docs. |
| Model routing | PASS | Model assignment comes from Hermes configuration and is passed into the adapter; no provider/model is hardcoded. |
| Out-of-scope list | PASS | No second worker, queue, database, editor config, AiNative modification, merge, or deploy. |
| Surgical edits | PASS | Add two focused modules and make narrow executor/orchestrator/runtime/persist integrations. |

## Project Structure

### Documentation (this feature)

```text
specs/011-external-framework-planning/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── external-framework-planning.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks), not created here
```

### Source Code (`personalAgent/` only)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── external_framework.py  # identities, context/result, config, registry
│   ├── speckit.py             # pinned runtime and Spec Kit adapter
│   ├── executor.py            # framework context/model-service seam
│   ├── orchestrator.py        # discovery → plan → tasks → planning complete
│   ├── persist.py             # round-trip normalized framework result
│   ├── runtime.py             # live provider validation and visible outcome
│   └── __init__.py            # public exports/version
├── tests/
│   ├── test_external_framework_planning.py
│   └── fixtures/
│       ├── ainative/          # fixture-only scout/tester; no live AiNative edits
│       └── speckit-runtime/   # pinned manifest/setup/template stand-in
├── config/
│   └── default.yaml           # active provider and runtime env-name example
├── docker/
│   └── Dockerfile             # build-time Spec Kit v1.0.1 provisioning
├── README.md                  # operator configuration/check/artifact guidance
└── CHANGELOG.md               # implementation release entry
```

**Structure Decision**: Keep the package flat like the existing adapters.
`external_framework.py` owns the stable boundary; `speckit.py` owns the only
V0 provider. The executor creates validated context using existing
project/workspace/model seams. The orchestrator retains sequencing, state,
slot, retry, and human authority. The Dockerfile provisions the runtime
without adding it to the Python package or copying framework agents into
AiNative.

## Complexity Tracking

> No constitution violations require justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | The provider boundary and separate planning terminal state are required by FR-003/FR-005/FR-019 and reuse existing control-plane machinery. |

## Implementation design

### Provider and runtime boundary

1. Parse and validate the `external_framework.providers` list and
   `runtime.path_env` using the existing config parser.
2. Require exactly one active `github-spec-kit` entry and a non-empty
   version pin.
3. Load the pinned runtime manifest and require exact provider id/version and
   a non-empty revision.
4. Build a provider registry that returns `SpecKitAdapter` for the active
   identity and rejects all other active ids.
5. Keep lifecycle names provider-neutral (`specify`, `clarify`, `plan`,
   `tasks`, `implement`) while allowing only `plan` and `tasks` in V0.

### Hermes model-service integration

1. Add `ExternalFrameworkContext` as a model context alongside the existing
   AiNative `AssembledContext`.
2. Reuse the configured planning model assignment and `ModelService`; do not
   create a second client, runtime, model slot, or agent execution path.
3. Supply Spec Kit runtime instructions and structured task/project/workspace
   context without reading `specs-planner` or `builder`.
4. Materialize only the native paths returned by the provider runtime, then
   validate files and contents before constructing a success result.

### Orchestration and state

1. Preserve discovery through the configured AiNative `scout`.
2. When the live adapter is active, replace only the planning branch:
   `discovery → external plan → external tasks`.
3. Route questions through existing `HUMAN_DECISION_REQUIRED` handling and
   failures through existing visible failure/block/recovery rules.
4. Store the normalized result in the existing `WorkflowRecord` overlay,
   including native paths, provider version, and framework revision.
5. Add `PLANNING_COMPLETE` as a terminal/free state distinct from
   `COMPLETED` and `PR_CREATED`; leave validation pending and never enter
   implementation or validation.
6. Print `planning complete` from the existing CLI for that outcome. No new
   dispatcher, scheduler, or notification event is introduced.

### Isolation and runtime provisioning

1. Use the already inspected `{workspace_root}/{project_id}/{task_id}` copy;
   never prepare a second worktree.
2. Bootstrap matching Spec Kit setup only below that copy; reuse matching
   setup and reject mismatches. Leave setup in place after the run.
3. Validate every returned native artifact path against the worktree and
   reject missing/unreadable/escaping/secret-bearing results.
4. Extend the Docker image build with a pinned `v1.0.1` runtime and manifest.
   Task execution performs no install, download, or external framework API
   request.

### Verification and documentation

The focused test must prove provider rejection before model work, runtime
revision matching, scout-before-framework ordering, no live planner lookup,
bootstrap/reuse isolation, native artifact paths, path/secret rejection,
planning-only completion, free-slot behavior, and zero implementation/
validation/publish calls. Then run the complete pytest and ruff checks.

Update `personalAgent/README.md`, `personalAgent/config/default.yaml`,
`personalAgent/CHANGELOG.md`, the package version in `__init__.py`, and the
root changelog at implementation time with the active-provider configuration,
runtime pin, fixture commands, native artifact behavior, and credentials that
remain outside git.

## Post-design Constitution Check (PASS)

The generated research, data model, contract, and quickstart keep Hermes as
the sole control plane, use no new Python dependency or task store, preserve
AiNative read-only behavior, and leave no unresolved clarification. Native
Spec Kit setup and artifacts are confined to the task worktree. The only
new terminal state is an explicit planning-only outcome and does not weaken
human merge/deploy authority.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contract | [contracts/external-framework-planning.md](./contracts/external-framework-planning.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Keep `tasks.md` out of this plan run.
- Live construction requires one active provider and a matching pinned
  runtime. Historical injected `MemoryTaskBoard` fixtures may continue to
  exercise the old full PIV path; no production live fallback to AiNative
  planning is allowed.
- The external result is the only handoff for native plan/task paths. Do not
  add `PLAN.md`, `TASKS.md`, `kanban.db` writes, or a second task store.
- `PLANNING_COMPLETE` must free the slot while remaining distinguishable from
  build-and-check completion.
- Tests must use a runtime fixture and stand-in model; never use the live
  AiNative mount, operator board, GitHub, or production credentials.
- Image provisioning and documentation/changelog/version updates are part of
  implementation, not this plan artifact phase.

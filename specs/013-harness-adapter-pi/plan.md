# Implementation Plan: Pi Harness Adapter

**Branch**: `013-harness-adapter-pi` | **Date**: 2026-09-08 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/013-harness-adapter-pi/spec.md`

**Architecture source of truth**:
`scratch/HarnessAdapterArchitecture.md`

## Summary

Replace Hermes' live `scout → Spec Kit plan → tasks → PLANNING_COMPLETE →
implement` path with one provider-neutral harness start/result boundary.
Hermes will prepare and protect the task worktree, start exactly one Pi
adapter run per work attempt, park/resume human decisions, validate the
completed work, and use the existing GitHub publication path. The Pi adapter
will own the complete Spec Kit playbook and its internal stage state, while
returning only normalized statuses, safe native artifact paths, changes,
questions, diagnostics, and retry guidance.

The implementation reuses the current executor, workspace, overlay,
validation/recovery, messaging, and GitHost seams. It replaces the
stage-oriented external-framework contract and removes its live orchestrator
branches rather than adding a second route. Pi SDK details stay inside a
private adapter/runtime port; no new Python dependency or Pi type enters the
generic Hermes contract.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) through the existing `uv`
package in `personalAgent/`

**Primary Dependencies**: Existing stdlib-only Hermes package,
`AgentExecutor`, `ModelService` for existing validation/diagnosis roles,
`WorkspaceManager`, `ProjectRegistry`, atomic overlay persistence,
`MemoryGitHost`/`LiveGitHost`, and an adapter-owned preinstalled/injected Pi
SDK runtime. No new Python dependency.

**Storage**: Existing native Hermes Kanban read model, one
`WorkflowRecord`/`overlay.json`, and the prepared task worktree/feature
branch. Native Spec Kit files and safe harness resume context remain in the
worktree and existing task record respectively. No second database, queue, or
event stream.

**Testing**: pytest 9.1.1 and ruff 0.16.5. Add focused offline contract and
Pi fixture checks, update live bridge/restart/orchestrator checks, then run
the complete `uv run pytest` suite and `uv run ruff check src tests`.

**Target Platform**: Host macOS/Linux checks and the existing
`hermes-agent:local` Docker deployment with a configured Pi runtime. Fixture
tests use disposable local git repositories and injected stand-ins.

**Project Type**: In-process Python control-plane library plus the existing
worker/CLI dispatcher; not a new service, worker, queue, or framework-owned
control plane.

**Performance Goals**: One blocking harness invocation per work attempt with
a required wall-clock timeout. No live event-stream or concurrency target;
existing single-task slot and validation/publish retry budgets remain.

**Constraints**: The generic request/result must contain no Pi SDK types,
Cursor model slugs, provider client settings, stage script, transcript,
private reasoning, token, or secret. Writes stay in the prepared task
worktree and feature branch; the harness cannot push, publish, merge, deploy,
write AiNative, or write a sibling worktree. Missing/mismatched runtime,
missing timeout, unsafe paths, unknown playbook, and malformed results fail
closed. The old Hermes stage machine cannot remain as fallback or recovery.

**Scale/Scope**: One active Pi adapter and one accepted `speckit-orchestrate`
playbook in V1; one task slot; one result per run; bounded whole-run retries;
existing project validation and one create-or-update pull request.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | Clarified spec, locked architecture, and this plan precede implementation. |
| II. Least Code (Ponytail) | PASS | Reuses the current executor, worktree, overlay, validation, messaging, and GitHub seams; adds only the requested one-run boundary and Pi adapter. |
| III. Platform-native | PASS | Native Kanban remains read-only task source, the existing worktree remains canonical, and no second database/queue/control plane is introduced. |
| IV. Trust-boundary tests | PASS | Request/result, timeout, worktree, artifact, secret, resume, legacy-record, validation, and publication boundaries receive disposable fixture checks. |
| V. Human authority | PASS | Hermes owns questions, skip/continue, parking, validation, GitHub publication, merge/deploy restrictions, and escalation; Pi has no operator chat. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Pi SDK is isolated behind an adapter-owned injected/preinstalled runtime port; Hermes adds no Python dependency. |
| Secrets / isolated Hermes home | PASS | Safe metadata is redacted/rejected and credentials remain outside git and the task record. |
| Model routing | PASS | Hermes passes a named profile reference; Pi privately maps it. Cursor model slugs and Pi client settings do not enter the generic contract. |
| Surgical edits | PASS | Replace the stage seam and its tests/config/docs; retain existing validation, recovery, worktree, messaging, and GitHub implementations. |

## Project Structure

### Documentation (this feature)

```text
specs/013-harness-adapter-pi/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── harness-execution.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks), not created here
```

### Source Code (`personalAgent/`)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── external_framework.py  # provider-neutral harness request/result and trust checks
│   ├── pi.py                  # Pi SDK adapter and private runtime translation
│   ├── executor.py            # request assembly, model profiles, validation/diagnosis seam
│   ├── orchestrator.py        # one-run lifecycle, human parking, validation, recovery, publish
│   ├── persist.py             # safe harness result/resume and legacy-record deserialization
│   ├── runtime.py             # live constructor and generic terminal output
│   └── __init__.py            # public exports/version
├── tests/
│   ├── test_harness_adapter.py
│   ├── test_piv_orchestrator.py
│   ├── test_restart_recovery.py
│   ├── test_live_piv_bridge.py
│   ├── test_import.py
│   └── fixtures/
│       ├── ainative/          # read-only validation/diagnosis stand-in only
│       ├── ainative-full/     # existing non-live regression fixture where retained
│       ├── pi-runtime/        # Pi SDK/playbook stand-in and native artifact fixtures
│       └── projects/standard/ # disposable managed project
├── config/default.yaml        # named harness/profile and runtime configuration
├── docker/Dockerfile          # build-time/runtime wiring, no per-run install
├── docker-compose.yml         # Pi runtime environment path, credentials remain external
├── README.md
├── CHANGELOG.md
└── pyproject.toml
```

**Structure Decision**: Keep the flat `hermes_kanban` package and existing
single control-plane seams. `external_framework.py` is reused as the
provider-neutral boundary but no longer contains lifecycle-step APIs.
`pi.py` is the only Pi-specific translation layer. The old `speckit.py`
stage adapter and `speckit-runtime` stage fixture are deleted and replaced by
the Pi runtime fixture; no source is copied into AiNative.

## Implementation Design

### 1. Replace the provider-neutral lifecycle API

- In `personalAgent/src/hermes_kanban/external_framework.py`, replace
  `ExternalFrameworkContext`/`ExternalFrameworkResult` lifecycle semantics
  with `HarnessStartRequest`, `HarnessResult`, `HarnessArtifact`,
  `ResumeContext`, and `HarnessAdapter`.
- Keep only generic validation helpers: identity, task/project/worktree,
  feature branch, timeout, playbook, model-profile, safety limits, relative
  artifact/change paths, bounded safe text, and secret detection.
- Close result status to `completed`, `failed`, `needs_human`, and `stuck`.
- Reject any request that names an individual Spec Kit stage. Preserve a
  visible compatibility error only if a caller still reaches an old direct
  entry point; it must not call a provider.
- Replace the current `external_framework` configuration loader with a
  harness selection loader that accepts exactly one active `pi` adapter and
  exactly `speckit-orchestrate`, validates the configured runtime marker, and
  exposes only a named model-profile reference to Hermes.

### 2. Implement the Pi adapter without leaking Pi types

- Add `personalAgent/src/hermes_kanban/pi.py` with a private `PiSdkPort`
  protocol/runtime wrapper and `PiHarnessAdapter.start`.
- Translate one generic request into one Pi SDK run, including the private
  Pi model/profile mapping, deadline, worktree safety policy, and the
  `speckit-orchestrate` playbook identity.
- Keep the complete playbook inside the adapter/runtime: specify, clarify
  stop, one continue gate, plan, tasks, conditional analyze, and alternating
  implement/converge until converged or stuck. Do not expose its stage cursor
  to Hermes.
- Stop the run at the requested deadline and map timeout to `failed`.
  Translate Pi questions to `needs_human`, SDK/runtime startup failures and
  unsafe operations to `failed`, and stuck playbook outcomes to `stuck`.
- Map only safe, worktree-relative native artifact/change/output paths into
  `HarnessResult`; retain partial native files for inspection but never claim
  successful completion after a failed/timeout run.
- Never call GitHub, push, merge, deploy, protected/default branch, AiNative,
  or another worktree. Do not add adapter-local retries.

### 3. Start one run from the executor

- In `personalAgent/src/hermes_kanban/executor.py`, add a single
  `start_harness` operation that validates the selected task/project/worktree,
  creates the provider-neutral request, selects the named harness profile,
  and calls `HarnessAdapter.start` exactly once.
- Remove the live use of `execute_framework` and any lifecycle-step-to-model
  assignment routing. Existing `execute_role` remains for validation and
  diagnosis only.
- Keep model credentials/model IDs private to the existing validation service
  and Pi runtime configuration. Do not serialize or pass Cursor model slugs
  through the generic request.

### 4. Replace orchestrator stage sequencing with result handling

- In `personalAgent/src/hermes_kanban/orchestrator.py`, remove
  `_run_external_planning`, `_run_external_implementation`, per-stage
  external branches, and `PLANNING_COMPLETE` as a live checkpoint.
- Make a new task run select/validate the task, prepare the worktree, mark
  execution started/running, and invoke `start_harness` once.
- Map `completed` to execution-finished then the existing validation path.
  Map `failed` to visible failure, `needs_human` to existing decision
  parking, and `stuck` to Hermes whole-run retry/escalation.
- Keep only orchestration phases/states in the record: execution, human,
  validation, publishing, completed/failed/stuck. Do not add or retain
  Hermes checkpoints for specify, clarify, plan, tasks, analyze, implement,
  converge, or `PLANNING_COMPLETE`.
- Resume a human decision or retry by creating another complete generic
  start request with persisted answers/assumptions/diagnostics. Never invoke a
  single Pi stage.
- Preserve `_after_validation`, `_start_recovery_cycle`, `_revalidate`,
  `_begin_github`, and `_run_github` ownership boundaries. A validation
  recovery needing workspace edits starts another whole harness run; a
  validation pass is still the only route to GitHub.
- At startup/reclaim, detect historical old-stage and
  `PLANNING_COMPLETE` records, park them with a migration reason, and do not
  finish, rewrite, or auto-start Pi for them.

### 5. Persist normalized results and resume context

- In `personalAgent/src/hermes_kanban/persist.py`, round-trip
  `HarnessResult`, relative native artifacts, changes, output reference,
  retry guidance, and `ResumeContext` through the existing atomic overlay.
- Validate paths against the current task worktree during load, reject
  secrets/transcripts/tokens/SDK metadata, and preserve partial native files
  without treating them as success.
- Keep old overlay parsing only long enough to identify and park removed
  stage records. Do not silently resume old planning handoffs or guess new
  artifact paths.

### 6. Update runtime, fixtures, and delivery surfaces

- Update `personalAgent/src/hermes_kanban/runtime.py` and `__main__` output
  to report generic execution, human, stuck, failed, validation, and PR
  outcomes; remove the planning-only success message.
- Update `personalAgent/src/hermes_kanban/__init__.py`, `pyproject.toml`,
  package version, and both changelogs according to the existing semver
  convention.
- Replace the stage-oriented
  `personalAgent/tests/test_external_framework_planning.py` and
  `tests/fixtures/speckit-runtime/` with Pi runtime stand-ins and
  `test_harness_adapter.py`. Update the orchestrator, restart, live bridge,
  and import tests for one request/result and legacy migration.
- Cover successful full playbook, optional analyze, repeated
  implement/converge, human clarify/skip/continue, timeout, unavailable
  runtime, malformed/unsafe results, no-forbidden-write snapshots,
  three-attempt stuck escalation, validation recovery, restart, and
  validation-gated simulated PR.
- Update `personalAgent/config/default.yaml`, `README.md`,
  `docker-compose.yml`, and `docker/Dockerfile` to describe the named model
  profile, Pi runtime provisioning/path, native artifact locations,
  human-decision behavior, offline fixtures, and credentials outside git.
  Remove documentation/configuration that presents Hermes Spec Kit stages or
  the old runtime as a live fallback.

## Phase 0 / Phase 1 Outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contract | [contracts/harness-execution.md](./contracts/harness-execution.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Dependency and Execution Order

### Phase dependencies

1. **Foundation**: generic request/result types, config/runtime validation,
   safety/path validators, and overlay schema. This blocks all workflow work.
2. **Pi adapter**: private Pi SDK port, one-run playbook invocation, status
   mapping, deadline enforcement, and fixture runtime. Depends on the
   foundation.
3. **Hermes execution**: executor request assembly and orchestrator result
   handling. Depends on both contract and adapter.
4. **Human/recovery/persistence**: resume decisions, skip/continue, stuck
   budget, validation recovery, restart, and legacy parking. Depends on the
   one-run workflow.
5. **Publication/docs/quality**: existing validation-to-PR integration,
   runtime/CLI/config/docs, changelog/version, focused tests, full tests, and
   quickstart verification. Depends on the behavior above.

### Safe parallelism

- Contract/data-model tests and the Pi fixture runtime can be prepared in
  parallel after the paths are agreed.
- `persist.py` serialization tests and Pi adapter unit tests can proceed in
  parallel once the result dataclasses exist.
- Documentation/config preparation and fixture snapshot helpers can proceed in
  parallel with adapter work, but must not describe the old stage path.
- Orchestrator edits, executor edits, and their corresponding integration
  tests remain serialized per file to avoid conflicting state-machine changes.
- Focused test suites and Ruff can run in parallel after implementation;
  the full suite and quickstart verification are final gates.

### Implementation notes for `/speckit-tasks`

- Tests precede each matching behavior change and use injected Pi/runtime,
  model, GitHub, messaging, and disposable-worktree seams.
- Native `spec.md`, `plan.md`, and `tasks.md` paths are evidence returned by
  the Pi result, never Hermes aliases or a second task list.
- Timeout validation precedes adapter invocation; result validation precedes
  validation and publication.
- Whole-run harness retry is distinct from existing validation-fix recovery,
  and neither is implemented inside the Pi adapter.
- No task may add an AiNative planner/builder, a Hermes `/speckit-orchestrate`
  command, a second database, a live event stream, or a publish call.

## Post-design Constitution Check (PASS)

The design keeps the current Hermes control-plane seams and moves only
execution ownership across the requested harness boundary. Pi-specific
translation is isolated, the generic contract is status/path/secret checked,
timeouts and retries are bounded, human authority and GitHub publication
remain in Hermes, native files stay in the one task worktree, and old
stage records are parked instead of silently migrated. No constitution
violation or unresolved clarification remains.

## Complexity Tracking

No constitution violations require an exception or additional abstraction.

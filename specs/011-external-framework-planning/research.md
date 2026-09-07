# Research: External Framework Planning Adapter

**Feature**: `011-external-framework-planning` | **Date**: 2026-09-07

Phase 0 resolves the technical choices against the clarified feature spec,
the constitution, the existing `personalAgent/` package, and the installed
Spec Kit assets. No `[NEEDS CLARIFICATION]` remains.

## 1. Reuse the existing control-plane seams

**Decision**: Keep `AiNativeAdapter` for AiNative roles only and add one
provider-neutral external-framework seam beside it. Reuse
`ProjectRegistry`, `WorkspaceManager`, `AgentExecutor`'s configured
`ModelService`, overlay persistence, and `PivOrchestrator` state/decision
handling. Do not add another orchestrator, worker, queue, task database, or
publish path.

The current live planning path resolves `settings.role_agents["planning"]`
(`specs-planner`) through AiNative and writes `PLAN.md`. The new live path
must bypass that lookup when an active external framework is configured:
`scout` through `AiNativeAdapter`, then external `plan`, then external
`tasks`, then stop. Existing injected `MemoryTaskBoard` PIV fixtures may keep
their historical full-chain behavior as a test seam; the production
`build_live_orchestrator` path is fail-closed and requires the external
framework selection.

**Rationale**: This is the smallest change that satisfies the live gap while
keeping the already-tested workspace, model, retry, overlay, GitHub, and human
decision controls authoritative.

**Alternatives considered**:

- Copying `specs-planner` or `builder` into AiNative — violates the read-only
  methodology boundary and hides the missing live capability.
- Replacing `PivOrchestrator` with a framework-owned runner — duplicates
  control-plane safety and recovery.
- Changing every historical fixture to a framework workflow — creates
  unrelated churn and removes useful regression coverage for the existing
  in-process PIV chain.

## 2. Stable provider-neutral contract

**Decision**: Add a small `external_framework.py` contract with:

- `FrameworkIdentity(id, version)`;
- `ExternalFrameworkContext`, carrying lifecycle step, task/project context,
  prepared worktree, active identity, model assignment, discovery summary,
  previous native artifacts, and an optional human decision;
- `ExternalFrameworkResult`, carrying explicit `success`/`failure`/`blocked`,
  provider identity, exact runtime revision, native artifact paths, questions,
  and next action;
- configuration validation and a registry that selects exactly one active
  provider.

The adapter accepts lifecycle names for `specify`, `clarify`, `plan`, `tasks`,
and `implement`, but V0 executes only `plan` and `tasks`. Unsupported steps
fail visibly rather than being silently mapped to another operation.

**Rationale**: The same context/result shape can support later lifecycle
steps without making this feature a one-off planner. Paths are structured
artifacts, not a replacement `PLAN.md`/`TASKS.md` convention.

**Alternatives considered**:

- A plan-only helper — cannot carry the later lifecycle boundary required by
  FR-019.
- Returning raw model responses — leaks transcript/reasoning concerns and
  leaves callers to reinterpret provider failures.
- Provider-specific types in the orchestrator — couples Hermes to Spec Kit
  and makes a future provider change cross-cutting.

## 3. Spec Kit runtime and model execution

**Decision**: V0 registers `github-spec-kit` and pins version `1.0.1` in
configuration. The Hermes image provisions the matching Spec Kit release at
image-build time under a runtime path, with a manifest containing provider
id, version, and the exact release revision. Runtime configuration supplies
only the environment-variable name for that path. A missing runtime, version
match, or revision fails before a model call.

The `SpecKitAdapter` consumes the pinned runtime's provider-neutral templates,
setup assets, and artifact rules. It invokes Hermes's existing configured
`ModelService` twice (lifecycle steps `plan` and `tasks`) and never launches
Cursor, Claude Code, a framework-owned model client, or an external planning
API. The model request uses a framework context, not an AiNative planner
agent. The runtime may materialize the native feature input required by its
plan command from the already-structured task/project/discovery context; that
input is framework-owned and is not a Hermes canonical plan or task list.

The runtime manifest is the only source for `framework_revision`; the adapter
does not invent a revision from the configured version string.

**Rationale**: Spec Kit `v1.0.1` is the installed repository integration
version (`.specify/integrations/speckit.manifest.json`) and its native
workflow expects a feature spec before plan and tasks. Image-build
provisioning satisfies “preinstalled and pinned” without adding
`specify-cli` to `personalAgent/pyproject.toml` or downloading during a
task. The existing model service remains the sole model executor.

**Alternatives considered**:

- Per-project `uv`/pip installation — violates FR-007 and makes runtime
  behavior depend on project files.
- Calling `specify` with a coding-agent integration — launches or emits
  editor/agent-specific machinery and cannot use Hermes's model service as
  the sole executor.
- Treating `1.0.1` as the revision — cannot prove the exact runtime snapshot.

## 4. Configuration and selection boundary

**Decision**: Extend the caller-supplied YAML with one `external_framework`
  block:

```yaml
external_framework:
  providers:
    - id: github-spec-kit
      version: 1.0.1
      active: true
  runtime:
    path_env: HERMES_SPECKIT_RUNTIME
```

The live constructor validates that exactly one provider has `active: true`,
that its id is supported, its version is non-empty, and its runtime manifest
matches. Zero active providers, multiple active providers, unsupported active
ids, empty pins, and unavailable/mismatched runtimes fail before workspace
framework work or model calls. The selected identity is shared by both
`plan` and `tasks`; there is no per-step provider choice.

**Rationale**: A list with an explicit `active` flag makes zero and multiple
active-provider cases representable at the trust boundary while preserving
future provider registrations. Environment-variable indirection keeps
machine paths out of committed config.

**Alternatives considered**:

- One scalar `provider` field — cannot express the required multiple-active
  rejection case cleanly.
- Selecting by role — permits plan/tasks provider drift and violates FR-002.
- Silent defaulting to Spec Kit — hides missing configuration and makes the
  no-active edge unsafe.

## 5. Bootstrap and isolation

**Decision**: `SpecKitAdapter` receives the already inspected prepared
  worktree; it never calls `prepare_workspace` and never creates a second
  workspace. If the worktree lacks the provider's setup marker, it copies
  only the pinned provider setup bundle into that worktree. If setup exists,
  it verifies provider/version/revision and reuses it. It rejects a mismatched
  setup rather than overwriting it.

All source and destination paths are resolved and checked. Writes are allowed
only below the task worktree; the enrolled project root, control-plane repo,
AiNative mount, runtime source, and sibling worktrees are outside the write
set. Setup files remain after a successful or partial run. Native plan/task
paths returned by the runtime must also resolve inside the same worktree and
must be readable regular files before a success result is built.

**Rationale**: Existing workspace preparation already supplies the one
isolated location. Keeping setup files makes a later lifecycle step able to
reuse the same native framework state, as required by clarification.

**Alternatives considered**:

- Bootstrap in the enrolled root then copy artifacts — violates isolation and
  creates a second planning workspace.
- Delete setup after planning — breaks later lifecycle reuse.
- Trust provider-returned absolute paths — permits writes or reads outside the
  task boundary.

## 6. Workflow completion and recovery

**Decision**: Add a distinct `PLANNING_COMPLETE` terminal workflow state.
After discovery succeeds, the orchestrator calls external `plan`; if that
result succeeds, it calls external `tasks`. A question parks through the
existing human-decision path. A failure or blocked result flows through the
existing visible failure/block path; the adapter does not add retries or
answer questions. On two successful native artifacts, the orchestrator stores
the normalized result in the existing overlay record, emits a safe
“planning complete” outcome, and writes the overlay as `free`. It does not
run implementation, validation, GitHub, merge, or deployment.

The stored result preserves provider metadata and native paths for later
steps. A resumed planning decision reuses a validated plan artifact when one
already exists; otherwise it restarts only the incomplete provider step. The
existing heartbeat, overlay, slot, and recovery rules remain the only
recovery machine.

**Rationale**: `COMPLETED`/`PR_CREATED` describe the existing build-and-check
workflow. A separate terminal state makes the requested visible outcome and
free-slot behavior unambiguous without pretending validation or PIV is done.

**Alternatives considered**:

- Reusing `COMPLETED` — conflates planning-only with build-and-check.
- Returning while leaving the slot occupied — prevents the required next task.
- Retrying inside the adapter — duplicates Hermes's retry/decision ownership.

## 7. Fixture checks and delivery surfaces

**Decision**: Add one focused pytest module with:

- a disposable git project/worktree;
- a live-style AiNative fixture containing `scout` but no required planner;
- a pinned Spec Kit runtime fixture and stand-in model service;
- configuration rejection, bootstrap/reuse, path-safety, native artifact,
  order, planning-complete, and no-publish assertions.

Run `uv run pytest tests/test_external_framework_planning.py`, the complete
suite, and `uv run ruff check src tests`. Update the package README,
operator config example, Docker image provisioning, and package changelog at
implementation time. No live GitHub, model credentials, Kanban board,
production repository, or writable live AiNative mount is part of the gate.

**Rationale**: These checks prove the cross-cutting contract at the trust
boundary without weakening or replacing the existing tests.

**Alternatives considered**:

- Testing against the operator's Hermes home or live AiNative — not
  hermetic and risks writes.
- Adding a new test framework or runtime dependency — unnecessary.

## 8. Resolved technical context

| Topic | Decision |
|---|---|
| Language | Python 3.12 (`>=3.12,<3.14`) via existing uv package |
| Runtime dependency | Build-time pinned Spec Kit `v1.0.1` assets; no Python dependency |
| Storage | Existing overlay and task worktree; no board writes or new database |
| Model execution | Existing configured Hermes `ModelService` |
| Tests | pytest + ruff; disposable fixtures and stand-ins |
| Target | Host checks and the existing `hermes-agent:local` image |
| Performance | One blocking discovery + plan + tasks sequence; no throughput target |
| Scope | One active provider, two lifecycle calls, one V0 task slot |

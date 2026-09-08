# Implementation Plan: Live Harness Adapter Gaps

**Branch**: `014-live-harness-gaps` | **Date**: 2026-09-08 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/014-live-harness-gaps/spec.md`

**Architecture source of truth**:
`scratch/HarnessAdapterArchitecture.md`

## Summary

Close the live wiring gaps without changing the generic Hermes-to-harness
boundary. `PiHarnessAdapter` will run the container-visible project Pi program
as a separate `pi --mode rpc` child in the task worktree, send one JSON
`prompt` command, privately consume Pi's JSONL run to settlement, extract one
structured result, and stop the child after settlement or timeout. The
existing fake Pi remains the offline test double.

The plan also centralizes strict timeout parsing so the checked-in `1800`
configuration loads, and adds a durable acknowledgement transition for parked
legacy short-path records. Acknowledgement clears the legacy marker without
starting Pi; the next Hermes process then reclaims the task through the generic
harness path. No second harness, database, Hermes event channel, SDK import, or
legacy fallback is introduced.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) through the existing `uv`
package in `personalAgent/`

**Primary Dependencies**: Existing stdlib-only Hermes package,
`PiHarnessAdapter`, `HarnessStartRequest`, `HarnessResult`, the subset YAML
reader, `subprocess`, and the existing workspace/orchestrator/persistence
seams. No new Python or Pi SDK dependency.

**Storage**: Existing `WorkflowRecord` and atomic `overlay.json`; native Pi
artifacts remain in the prepared task worktree. Add only the small durable
`legacy_acknowledged` transition field.

**Testing**: pytest 9.1.1 and ruff 0.16.5. Keep fake-Pi unit/integration
fixtures; add process transport, timeout/config, Docker wiring, and
legacy-acknowledgement checks. Run focused checks, then `uv run pytest` and
`uv run ruff check src tests`.

**Target Platform**: Linux Hermes Docker container for the live proof, with
macOS/Linux offline development checks. The Pi executable must be runnable
inside the container; host-only availability is invalid.

**Project Type**: In-process Python control-plane library and existing
dispatcher/worker, with one external child process used as the execution
harness.

**Performance Goals**: One blocking child per work attempt, one JSON prompt
command, one extracted result, and bounded wall-clock timeout. Pi's internal
event stream does not cross the Hermes boundary and concurrency does not
change.

**Constraints**: Reuse the existing generic boundary and adapter. Keep writes
inside the current task worktree and feature branch. Reject marker-only
runtimes, malformed/extra output, unsafe paths, secrets, invalid timeout
values, and protected/default branches. Do not add an upper timeout cap. Do
not import the Pi TypeScript SDK or revive the removed Hermes stage machine.

**Scale/Scope**: One active Pi adapter, one `speckit-orchestrate` playbook, one
task slot, one process/result per attempt, existing whole-run retry budget, and
existing validation/publication ownership.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research: PASS

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | The clarified feature spec, locked architecture, and parent artifacts precede implementation. |
| II. Least Code (Ponytail) | PASS | Reuses the existing contract, adapter, fake runtime, overlay, and orchestration seams; adds only the missing process/config/state behavior. |
| III. Platform-native | PASS | Uses a native child process and existing worktree/overlay; adds no database, queue, or control plane. |
| IV. Trust-boundary tests | PASS | Process output, timeout, runtime availability, config values, paths, secrets, and restart state receive focused checks. |
| V. Human authority | PASS | Legacy work stays parked until acknowledgement; Hermes retains human decisions, validation, and publication. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Uses Python standard library subprocess/JSON/process cleanup. |
| Secrets and isolated Hermes home | PASS | Job/result data remains bounded and secret-free; credentials stay outside git and the task record. |
| Surgical edits | PASS | Changes are limited to the adapter/runtime loader, config parsing, persistence/orchestrator transition, Docker wiring, fixtures, docs, and changelog. |

## Project Structure

### Documentation (this feature)

```text
specs/014-live-harness-gaps/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── harness-execution.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2 (/speckit-tasks), not created here
```

### Source Code

```text
personalAgent/
├── src/hermes_kanban/
│   ├── external_framework.py  # timeout/runtime validation and generic records
│   ├── pi.py                  # private subprocess RPC transport and mapping
│   ├── executor.py            # shared timeout settings/request construction
│   ├── orchestrator.py        # legacy ack transition and generic reclaim
│   └── persist.py             # overlay field round-trip and safety checks
├── tests/
│   ├── test_harness_adapter.py
│   ├── test_piv_orchestrator.py
│   ├── test_restart_recovery.py
│   ├── test_legacy_stage_removal.py
│   ├── test_live_piv_bridge.py
│   └── fixtures/pi-runtime/runtime.py
├── config/default.yaml
├── docker/Dockerfile
├── docker-compose.yml
└── CHANGELOG.md
```

**Structure Decision**: Keep the existing flat `hermes_kanban` package and
single control-plane seams. The private process transport lives behind
`PiHarnessAdapter`; it is not a second adapter or public protocol. The fake
runtime remains injected in tests. Docker provisions or mounts a
container-runnable Pi executable beside its identity marker.

## Implementation Design

### 1. Validate an executable runtime, not only a marker

- Extend `HarnessRuntime`/`load_harness_runtime` to resolve the Pi executable
  from the configured runtime directory/manifest or executable setting.
- Require the marker to identify Pi and a runnable executable to exist.
- Preserve the marker-only failure as a visible startup failure.
- Update `Dockerfile`, compose, runtime manifest, and operator documentation
  so a real project Pi launcher can be baked into the image or mounted
  read-only. The live check must execute `pi --mode rpc` inside the container.

### 2. Put one-shot RPC process handling behind the existing adapter

- Add a private process-backed implementation of the existing runtime port in
  `pi.py`; do not expose subprocess or Pi-specific types through the generic
  records.
- Build one JSON `prompt` command from the existing request, including
  task/worktree context, constraints, operator flags, resume context, and the
  structured-result instruction.
- Start `[pi, "--mode", "rpc"]` with `cwd=request.workspace_path`, write one
  prompt command, consume JSONL responses/events until settlement, and extract
  one structured assistant result.
- Reject rejected prompts, malformed RPC events, multiple/missing results,
  unknown statuses, unsafe paths, and secret-bearing metadata through the
  existing result validator.
- On settlement/result or timeout, terminate/kill and wait for the child. Map
  timeout and startup/transport failures to `failed`. Leave retry decisions to
  Hermes.
- Keep injected fake runtime behavior unchanged for offline tests.

### 3. Normalize timeout configuration once

- Add a strict positive-finite coercion helper in `external_framework.py`.
- Use it from `load_harness_config` and `ExecutionSettings.from_config`.
- Accept numeric strings from the subset YAML reader, including `1800`.
- Reject booleans, blank/missing, zero, negative, non-numeric, and non-finite
  values without adding a maximum.
- Add a default-config load check using a fixture runtime marker/executable.

### 4. Clear the legacy marker only after acknowledgement

- Add `legacy_acknowledged: bool = False` to `WorkflowRecord` and round-trip it
  through `persist.py`, defaulting old overlays to false.
- Keep startup parking unchanged for unacknowledged historical records.
- In the existing legacy decision path, clear `legacy_migration_reason`, mark
  acknowledgement, clear the decision, preserve worktree/history, and leave
  the record queued. Do not call Pi in the acknowledgement method.
- Make legacy detection ignore retained old steps only when the durable
  acknowledgement marker is true.
- Let the next process reclaim the queued execution through
  `start_harness`; make replayed acknowledgement safe and non-duplicating.

### 5. Verify the live boundary and delivery surfaces

- Add focused fake/process fixture checks for one job/result, cwd, process
  cleanup, timeout, malformed/extra output, marker-only runtime, and result
  mapping.
- Add config fixtures for numeric values, numeric strings, invalid values, and
  checked-in default loading.
- Add park/ack/restart checks for both unacknowledged and acknowledged records.
- Keep contract leakage, isolation, validation-gating, and existing fake-Pi
  checks.
- Update README, Docker files, and both changelogs with the actual delivered
  behavior and semver version.

## Dependency and Execution Order

1. **Boundary/runtime foundation**: executable runtime validation, shared
   timeout coercion, and `WorkflowRecord` persistence field. This blocks
   process and restart behavior.
2. **Process adapter**: private one-shot JSON transport, result mapping, child
   cleanup, and process fixtures. Depends on the generic records/validators.
3. **Hermes restart transition**: legacy acknowledgement and new-process
   generic reclaim. Depends on the persisted field and existing orchestrator
   behavior.
4. **Docker/config/docs**: actual runtime provisioning/mount, default config
   proof, README, and changelogs. Depends on the transport contract.
5. **Quality gates**: focused tests, Ruff, full pytest, and the disposable
   Docker live proof.

Safe parallelism is limited to independent test/config/documentation work
after the shared field and transport contract are agreed. Changes to
`pi.py`, `orchestrator.py`, and `persist.py` remain serialized because they
share lifecycle and result state. The Docker proof is final because it
depends on all runtime wiring.

## Phase 1 Acceptance and Verification

- `load_harness_config` accepts the checked-in timeout and numeric strings, and
  rejects every specified invalid form before starting Pi.
- A marker-only runtime fails before execution; a real container-visible
  `pi --mode rpc` process runs in the task worktree with one job and result.
- Results are mapped through the existing `HarnessResult`; leftover processes
  are stopped after result or timeout.
- Offline tests still use the fake runtime and no Pi SDK import exists.
- Unacknowledged legacy records remain parked; acknowledged records clear the
  marker and start the generic path only after a new process reclaim.
- Focused tests and Ruff pass, followed by the full quality gates and Docker
  live proof using a disposable project.

## Post-design Constitution Check: PASS

The design uses the existing adapter and control-plane records, keeps all
process input/output at a validated trust boundary, and introduces no new
dependency or state store. Pi remains a separate process and owns the
playbook; Hermes retains human authority, retries, validation, Git safety, and
publication. Legacy history is preserved, but acknowledgement is explicit and
cannot revive the removed stage machine. No unresolved clarification or
constitution violation remains.

## Complexity Tracking

No constitution violations require an exception or additional abstraction.

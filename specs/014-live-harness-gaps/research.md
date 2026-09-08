# Research: Live Harness Adapter Gaps

**Feature**: `014-live-harness-gaps` | **Date**: 2026-09-08

This research narrows the implementation to the three observed live gaps while
preserving the generic boundary and the locked decisions from feature 013.
There are no unresolved clarifications: skip assumptions are recorded in
`spec.md`.

## 1. Use a subprocess for the live Pi boundary

**Decision**: Keep `HarnessStartRequest`, `HarnessResult`, and
`PiHarnessAdapter`, but replace the production runtime behind the adapter with a
small private subprocess transport. It will execute the configured, container-
visible Pi program as:

```text
pi --mode rpc
```

with the task worktree as `cwd`. The transport writes exactly one JSON job
document to stdin and accepts exactly one JSON result document from stdout.
Offline tests continue injecting the existing fake runtime through the same
adapter port.

The runtime marker remains useful for version/revision identity, but it is not
itself executable. Runtime loading must resolve and verify an executable
alongside the marker (or a configured executable on `PATH`) before Hermes
starts a task. A marker-only directory therefore fails visibly before Pi
starts.

**Rationale**: The current `PiHarnessAdapter` invokes an in-process fixture
port and the Docker image copies only `manifest.json`, so a live run can never
reach the real Pi program. A subprocess keeps Hermes independent of the Pi
TypeScript SDK and matches the locked one-job/one-result boundary.

**Alternatives considered**:

- Treating `/opt/pi-runtime/manifest.json` as the runtime — it proves only
  metadata exists and was the live failure.
- Importing `@mariozechner/pi-coding-agent` into Python — violates the
  architecture and adds an unapproved SDK dependency.
- Adding a second harness implementation — duplicates the existing adapter
  boundary.
- Keeping a Hermes stage fallback — violates the locked removal decision.

## 2. Make process shutdown part of the one-result contract

**Decision**: The private process transport owns the child process lifecycle.
It starts one child, sends one job, reads one complete result, and then ends
the attempt. If the child is still running after a result, it is terminated
and, if necessary, killed and waited for. A timeout follows the same cleanup
path and maps to `failed`. Extra JSON, mixed output, malformed output, early
exit, and unknown statuses fail closed.

The adapter has no retry loop. Hermes continues to own whole-run retries and
human parking.

**Rationale**: The current thread-based fixture invocation cannot stop an
uncooperative runtime after one result, allowing later writes. Child cleanup
must be close to the transport so every caller receives the same safety
behavior.

**Alternatives considered**:

- Waiting indefinitely for normal process exit — violates the one-result
  contract and can hang a live task.
- Marking a result complete while leaving the child alive — permits continued
  worktree writes after Hermes has moved on.
- Retrying or restarting inside the adapter — hides attempts from Hermes.

## 3. Parse timeout values once, strictly

**Decision**: Add one shared positive-finite timeout coercion helper at the
configuration boundary. It accepts integers/floats and numeric strings such
as `1800`, rejects booleans, blank strings, non-numeric text, zero, negative,
and non-finite values, and does not add an upper bound. Use the helper in
`load_harness_config` and `ExecutionSettings.from_config`.

Add a focused check that loads the checked-in
`personalAgent/config/default.yaml` with the fixture runtime environment, plus
numeric-string and invalid-value fixtures.

**Rationale**: The repository's deliberate subset YAML parser returns an
unquoted scalar such as `1800` as text. The current loader only accepts numeric
Python objects, so the checked-in default is rejected before adapter startup.
A single helper prevents the two loaders from drifting.

**Alternatives considered**:

- Changing the YAML parser to infer numbers globally — broadens an intentionally
  small parser for one setting and risks changing unrelated configuration.
- Adding a new maximum — explicitly rejected by the feature clarification.
- Silently defaulting invalid values — would hide a trust-boundary error.

## 4. Persist explicit acknowledgement of legacy work

**Decision**: Keep legacy records parked until the existing human decision is
acknowledged. On acknowledgement, clear `legacy_migration_reason`, record an
explicit acknowledged marker on the existing workflow record, clear the human
decision, and leave the record queued for execution. Do not invoke Pi in that
acknowledgement call.

On the next Hermes process startup, the acknowledged record is reclaimed
through the generic execution phase. Historical stage steps remain inspectable,
but the acknowledged marker prevents `_is_legacy_record` from parking it
again. Replayed acknowledgement is a no-op or safe already-acknowledged
response and never starts a second harness run.

**Rationale**: Clearing only `legacy_migration_reason` is insufficient because
the existing legacy detector also inspects retained historical steps. A small
persisted acknowledgement bit preserves history while allowing exactly one
human-authorized transition to the new generic path.

**Alternatives considered**:

- Deleting old steps — rewrites history and removes useful review context.
- Auto-starting Pi during acknowledgement — violates the required human pause
  and makes restart semantics nondeterministic.
- Leaving the marker in place — causes every new process to park the task again.

## 5. Prove the live path in Docker without changing offline tests

**Decision**: Keep the fake `PiFixtureRuntime` for pytest. Add process-backed
fixture coverage for one job/result, cwd, cleanup, malformed output, timeout,
and marker-only failure. Update Docker provisioning/compose documentation so
the Hermes container receives a container-runnable real `pi` executable and
matching manifest, either from the image or a read-only runtime mount. The
live proof must invoke the real project `pi --mode rpc`; a protocol stub in
Docker is not sufficient.

The proof remains disposable and does not require live GitHub publication.

**Rationale**: Offline tests must remain credential-free and deterministic,
while the failure being closed is specifically the production process wiring.
The existing Docker image contains only a marker, so the deployment surface
must make executable availability explicit.

**Alternatives considered**:

- Replacing all tests with live Pi — adds credentials, network, and timing
  dependence without improving the contract checks.
- Using a protocol-only Docker stub as the live proof — does not prove the
  real project Pi can run inside Hermes.
- Installing the Pi SDK from Python — violates the no-SDK boundary.

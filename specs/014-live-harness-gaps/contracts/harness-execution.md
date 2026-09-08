# Contract: Live Harness Adapter Gaps

**Feature**: `014-live-harness-gaps`

This contract extends the existing generic harness contract from feature 013.
It does not add a second public harness API.

## Runtime availability

The configured runtime is usable only when all of the following are true:

1. the active adapter is `pi`;
2. the playbook is `speckit-orchestrate`;
3. the configured runtime marker is readable and matches `adapter_id`,
   `version`, and `revision`;
4. a container-visible executable resolves to the project Pi program;
5. that executable can be started with `--mode rpc`.

`manifest.json` alone is not an executable runtime. If the marker exists but
the Pi executable is missing or not runnable, Hermes returns a visible
`failed` startup outcome and never invokes the removed legacy path.

The executable may be baked into the Hermes image or supplied through a
read-only mount. A Pi binary available only on the Mac host does not satisfy
this contract.

## One-run process protocol

For each `HarnessStartRequest`, `PiHarnessAdapter` starts one separate child:

```text
pi --mode rpc
```

The child:

- runs with `cwd` equal to the validated task worktree;
- receives one JSON job document on stdin;
- returns one JSON result document on stdout;
- owns the complete Spec Kit playbook internally;
- has no Hermes operator chat channel;
- cannot publish, push, merge, deploy, write AiNative, or write another
  worktree.

The job contains the task projection, repository context, worktree-relative
context, safety constraints, named model-profile reference, operator flags,
and optional resume context. It does not contain a Pi SDK object, provider
credential, Cursor model slug, transcript, private reasoning, or a Hermes
stage list.

The transport accepts exactly one complete JSON result. A second result,
additional non-whitespace output, malformed JSON, early process exit, unknown
status, unsafe path, secret, or invalid human-question shape is rejected as a
failed run.

After the first complete result, Hermes ends the attempt. If the child is
still running, the adapter terminates it, escalates to kill if required, and
waits for it. Timeout uses the same cleanup path and maps to `failed`.

## Normalized result mapping

The adapter maps the process result to the existing `HarnessResult`:

| Pi result | Generic result | Hermes action |
|---|---|---|
| `completed` | `completed` | Run existing project validation. |
| `failed`, `error`, or startup/transport failure | `failed` | Retain inspectable artifacts; do not validate or publish. |
| `needs_human` or private `question` alias | `needs_human` | Park with safe questions; wait for the existing decision flow. |
| `stuck` | `stuck` | Apply existing whole-run retry budget. |
| timeout | `failed` | Stop child, retain artifacts, count one attempt. |

The result has one of the four closed statuses, bounded safe text, worktree-
relative artifact/change/output paths, and no provider/SDK/model leakage.
`completed` means only playbook completion; Hermes still owns validation and
later publication.

## Timeout configuration

`load_harness_config` and `ExecutionSettings.from_config` use the same strict
coercion:

- `1800`, `1800.0`, and `"1800"` become a positive finite `float`;
- booleans, blank strings, non-numeric strings, zero, negative, missing, and
  non-finite values fail before Pi starts;
- no upper bound is introduced.

The checked-in `personalAgent/config/default.yaml` must load with a fixture
runtime environment and expose `1800.0` to the adapter.

## Legacy parking and acknowledgement

At startup, a record from the removed Hermes short path is parked for a human
and no child process starts. The parked record retains its task, worktree,
native artifacts, and historical steps.

When the existing human decision acknowledges that record:

1. Hermes clears `legacy_migration_reason`;
2. Hermes sets the durable `legacy_acknowledged` marker;
3. Hermes clears the pending decision but preserves task/worktree context;
4. Hermes leaves the record queued for a later process/reclaim;
5. Hermes does not start Pi during acknowledgement.

The next Hermes process bypasses the legacy detector because the explicit
acknowledgement marker is present and starts the generic harness path once.
Replaying the acknowledgement is safe and does not start another run.

## Verification boundary

Focused checks must cover:

- real process invocation, exact `pi --mode rpc` arguments, task-worktree cwd,
  one JSON job, one JSON result, and leftover-process cleanup;
- marker-only runtime failure and missing/non-executable Pi;
- malformed, extra, unsafe, unknown, timeout, and human-needed results;
- numeric and numeric-string timeout loading, checked-in default loading, and
  invalid timeout rejection;
- legacy park → acknowledgement → new-process generic start, plus
  unacknowledged restart parking;
- existing fake-Pi offline execution, generic-contract leakage checks, and
  no validation/publication before a valid completed result.

The Docker live proof must use the real project `pi --mode rpc`. A protocol
stub is valid only for isolated offline transport tests, not for the live
proof.

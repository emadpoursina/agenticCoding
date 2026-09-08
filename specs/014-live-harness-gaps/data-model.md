# Data Model: Live Harness Adapter Gaps

**Feature**: `014-live-harness-gaps`

This feature keeps the existing generic harness entities and adds only the
process/runtime and legacy-acknowledgement data needed to close the live gaps.
No queue, Hermes event channel, task database, or second harness record is
added.

## Pi runtime

The runtime is the container-visible executable plus its identity marker.

| Field | Type | Rules |
|---|---|---|
| `runtime_path` | `Path` | Configured runtime directory or executable location visible inside the Hermes container. |
| `manifest_path` | `Path` | `manifest.json` used for adapter/version/revision identity. |
| `executable` | `Path` or command name | Must resolve to a runnable file or executable on `PATH`; a manifest alone is invalid. |
| `adapter_id` | `str` | Must be `pi`. |
| `version` | `str` | Required non-empty marker value. |
| `revision` | `str` | Required non-empty marker value. |

The runtime loader validates the marker and executable before any task
worktree is used. A host-only executable is not valid for a Docker run; the
same binary or launcher must be available inside the Hermes container.

## Pi RPC job

One private transport document sent to the Pi process.

| Field | Type | Rules |
|---|---|---|
| `task_id` | `str` | Matches the generic start request. |
| `task` | object | Bounded task title, description, expected result, acceptance criteria, priority, platform, notes, and dependencies. |
| `repository` | object | Repository identity and default branch; no credentials or control-plane handles. |
| `worktree` | object | The process receives the task worktree as `cwd`; the document identifies the relative work root only. |
| `playbook` | `str` | Exactly `speckit-orchestrate`; no individual stage names or stage list. |
| `constraints` | object | Worktree-only writes, feature branch only, no publication, no protected/default branch, and secret rejection. |
| `model_profile` | `str` | Provider-neutral named reference. Pi resolves it privately. |
| `operator_flags` | tuple of `str` | Bounded optional flags such as `skip`. |
| `resume_context` | `ResumeContext \| None` | Safe answers, assumptions, confirmation, and diagnostics. |

Hermes sends exactly one JSON `prompt` command for an attempt. Pi's JSONL
response/event stream remains private to the adapter; the process does not
receive a Hermes-owned Spec Kit stage sequence or operator chat channel.

## Pi RPC result

One private transport document returned by the Pi process.

| Field | Type | Rules |
|---|---|---|
| `status` | `str` | Maps to exactly one generic status: `completed`, `failed`, `needs_human`, or `stuck`; `question`, `blocked`, and `error` may be private aliases only. |
| `reason` | `str` | Required bounded safe explanation. |
| `next_action` | `str` | Safe follow-up action when needed. |
| `artifacts` | sequence | Worktree-relative native artifact paths only. |
| `changes` | sequence | Worktree-relative changed paths only. |
| `output_reference` | `str \| None` | Optional readable worktree-relative output reference. |
| `retryable` | `bool` | Whole-run retry guidance; no adapter retry loop. |
| `questions` | sequence | Required and safe when status maps to `needs_human`. |
| `resume_context` | `ResumeContext \| None` | Safe data needed for a later whole-run request. |

Hermes extracts one structured result from the final assistant message only.
A rejected prompt, malformed RPC event, second structured result, missing
final result, unknown status, unsafe paths, or secret-bearing metadata becomes
a visible `failed` result and cannot reach
validation or publication.

## Harness attempt

The existing `HarnessStartRequest` and `HarnessResult` remain the public
provider-neutral records. One attempt has:

- exactly one generic request;
- one `pi --mode rpc` child process;
- exactly one accepted result;
- a positive finite timeout;
- a cleanup outcome showing that the child is no longer running.

After the first result or timeout, the child is terminated, killed if needed,
and waited for. Partial native files remain available for inspection, but a
timeout or failed result cannot become `completed`.

## Workflow legacy acknowledgement

The existing `WorkflowRecord` remains the sole persistence record.

| Field | Type | Rules |
|---|---|---|
| `legacy_migration_reason` | `str \| None` | Existing marker set while a historical short-path record is parked. Cleared only after human acknowledgement. |
| `legacy_acknowledged` | `bool` | New durable transition marker. Defaults to `False` for old overlays and is set only by the acknowledgement path. |
| `state` | existing orchestration state | Acknowledgement leaves the record queued for a later generic execution reclaim; it does not start Pi in the same call. |
| `decision` | existing decision or `None` | Cleared after acknowledgement. |
| `workspace_path` / `workspace_branch` | existing fields | Preserved for the later generic run. |
| `steps` | existing history | Preserved, including legacy steps, for inspection. |

Legacy detection remains active when `legacy_acknowledged` is false. An
acknowledged record is not re-parked merely because its retained history still
contains old stage names. A repeated acknowledgement is safe and does not
create a second attempt or human transition.

## Configuration value

`harness.timeout_seconds` is normalized to `float` at load time.

Validation rules:

- accepts positive finite integers, floats, and numeric strings;
- rejects booleans, missing values, blank strings, zero, negative values,
  non-numeric text, and non-finite values;
- imposes no new maximum;
- is applied before the Pi child starts.

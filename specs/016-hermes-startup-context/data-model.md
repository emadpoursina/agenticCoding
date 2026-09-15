# Data Model: Hermes Startup Context Files

**Feature**: `016-hermes-startup-context`

This feature adds in-memory startup state and diagnostic metadata. It does
not add a database, overlay schema, task field, worktree file, or hidden
memory store. Registered source files remain the canonical source of truth.

## Startup context registration

**Entity**: `StartupContextRegistration`

| Field | Type | Rules |
|---|---|---|
| `role` | literal string | Exactly one of `hermes_instructions`, `system`, or `user`. |
| `configured_path` | absolute path | The exact configured container path; never rewritten to a host path. |
| `resolved_path` | absolute path | The resolved readable regular file used for this run. |
| `revision` | SHA-256 hex string | Hash of the exact source bytes loaded at startup. |

The three roles are loaded in this order:

```text
hermes_instructions → system → user
```

The loader rejects a missing role, an extra role, a non-absolute/host-only
path, a missing path, a directory, an unreadable file, empty content, invalid
UTF-8, or two roles resolving to the same file. It does not inspect or print
content when reporting a failure.

## Startup context snapshot

**Entity**: `StartupContextSnapshot`

| Field | Type | Rules |
|---|---|---|
| `files` | ordered mapping of role to loaded file | Exactly three entries in registration order. |
| `text` | UTF-8 text | Retained only in process memory for Hermes startup, planning, and health/doctor use. |
| `registrations` | tuple of `StartupContextRegistration` | Metadata-only view; safe to record and report. |

The snapshot is attached to the live orchestrator only for the current
process. It is deliberately absent from `WorkflowRecord`, `BoardTask`,
`ExecutePayload`, `AssembledContext`, `HarnessStartRequest`, and
`HarnessResult`.

## Context precedence layer

**Entity**: `ContextPrecedenceLayer`

The fixed authority order is:

| Rank | Layer | Source |
|---:|---|---|
| 1 | `platform_safety` | Platform, security, and protected-operation rules |
| 2 | `hermes_instructions` | Registered `AGENTS.md` |
| 3 | `runtime_configuration` | Live deployment configuration |
| 4 | `system` | Registered `SYSTEM.md` |
| 5 | `project_instructions` | Managed project's own files and manifest |
| 6 | `user` | Registered `USER.md` |
| 7 | `current_task` | Current task request |

The resolver accepts one candidate per layer and returns the first applicable
candidate. Lower-ranked candidates cannot weaken a higher-ranked safety or
protected-operation rule.

## Startup diagnostic

**Entity**: `StartupDiagnostic`

| Field | Type | Rules |
|---|---|---|
| `ainative_root` | absolute path | Configured read-only methodology root. |
| `available_agents` | sorted tuple of strings | Names discovered from the configured AiNative agent root. |
| `configured_projects` | tuple of project identities | IDs/names only; no project file bodies. |
| `workspace_root` | absolute path | Existing configured workspace root. |
| `active_harness` | string | Active provider-neutral harness identity, initially `pi`. |
| `persistent_state_path` | absolute path | Existing overlay/persistent-state directory. |
| `context_registrations` | tuple of registrations | Role, exact path, and revision only. |

Its JSON/text rendering must not include the `text` field from the snapshot,
environment secret values, tokens, passwords, or private keys.

## Failure state

Startup validation is fail-closed:

```text
configured role/path
        │
        ├── valid regular readable non-empty file
        │       └── hash + decode → loaded snapshot
        │
        └── missing / unreadable / directory / duplicate / host-only
                └── safe startup error(role, exact path, reason)
```

There is no transition from failure to an auto-created file. The operator
must provision persistent `SYSTEM.md` and `USER.md` from the safe templates
before retrying startup.

## Operational-record invariant

Only `StartupContextRegistration` metadata may cross into a startup
diagnostic or future revision record. A body substring from any registered
file must not occur in:

- Kanban/task records;
- workflow overlay JSON;
- worktrees or managed project repositories;
- coding-job payloads or model messages; or
- any separate Hermes memory database.

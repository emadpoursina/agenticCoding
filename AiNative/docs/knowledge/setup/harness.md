# Harness

Part 1 of the [agentic system](../../systems/agentic-system.md). The harness is
the runtime that runs managed-project work.

## Current runtime

The live install is the **Hermes agent**, configured by the `personalAgent`
repository. Canonical runtime facts (container, mounts, identity, model
routing) live there, in `personalAgent/SYSTEM.md`, and in the operator's
private Hermes home. This file does not duplicate them.

What matters to methodology:

- Hermes runs in Docker and reads AiNative **read-only** from
  `/opt/data/mnt/AiNative`.
- Coding work happens in the task workspace at `/opt/data/mnt/workspace`.
- The install provides native `hermes kanban` (board, tasks, links, dispatch)
  and `hermes project` (named workspaces) commands. **No worker loop is wired
  yet**: no projects are enrolled and only the `default` profile exists.

## Target worker model

When the [feature loop](../../systems/feature-loop.md) is wired, Hermes owns
the harness and starts **one worker session per agent state**:

- Each worker receives one step, its inputs, and a compact report contract.
- The worker exits after that step; Hermes owns transitions and recovery.
- Project `validation_commands` run in the tester state, not as an
  orchestrator-side shortcut.
- Human gates and publish decisions remain with the operator. Workers do not
  push, merge, or deploy.
- Project rules and validation live in the project's `AGENTS.md` and
  `.ainative/project.yaml`; AiNative stays read-only methodology.

Runtime mechanics (process model, profiles, worktrees, model routing) are
defined by Hermes, not here.

## Related

- [feature-loop.md](../../systems/feature-loop.md) — target state graph and card paths
- [new-project.md](./new-project.md) — repo enrollment and bootstrap handoff
- [tmux.md](../commands/tmux.md) — terminal session shortcuts, if needed

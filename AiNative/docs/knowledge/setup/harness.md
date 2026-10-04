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
- Human gates and ship decisions remain with the operator. Workers do not
  push, merge, or deploy.
- Project rules and validation live in the project's `AGENTS.md` and
  `.ainative/project.yaml`; AiNative stays read-only methodology.

Runtime mechanics (process model, profiles, worktrees, model routing) are
defined by Hermes, not here.

## Gate ownership (one gate per concern)

Three gates touch "is it ready?" at different levels. Each concern has exactly
one owner; a gate never re-implements another gate's checks.

| Gate | Level | Owns | Report |
|---|---|---|---|
| [hermes-readiness.sh](./hermes-readiness.sh) | Install | Can Hermes run? mounts, keys, DBs, config, CLI reachable, GitHub access | `PASS`/`FAIL`/`GAP`/`NOTE`, `ONBOARDING:`/`STEP3:` |
| `ready-check.sh` (`speckit-ready` skill) — read through [agents/ready/](../../agents/ready/) | Per flow | Branch state, Spec Kit layout, `.specify/ready.yml` | `READY: ok\|blocked`, `FLOW_ID`/`BRANCH`/`CHECKS`/`FIXES` |
| [task-groomer](../../agents/task-groomer/) | Per card | Card shape and dispatch-readiness | Card fields + `hermes kanban create` proposal |

Rules that prevent future confusion:

- `hermes-readiness.sh` checks a target project only for *sanity* (it is a git
  repo, origin reachable, worktree works). It does **not** check Spec Kit
  layout or branch state — the ready gate decides those per card.
- The ready gate does **not** check mounts, keys, DBs, or container runtime —
  the install gate decides those.
- task-groomer does **not** run environment checks.
- Never add a check to two gates. If a new check is needed, ask which level it
  belongs to (install / flow / card) and add it in exactly one place.

## Related

- [harness.md](./harness.md) — what the harness is; canonical runtime facts live in `personalAgent/SYSTEM.md`
- [hermes-readiness.sh](./hermes-readiness.sh) — the install-gate readiness check: run it on the Mac for host + container, or inside the container as Hermes. Prints `PASS`/`FAIL` (step-2 onboarding gates), `GAP` (step-3 gates), and `ONBOARDING:` / `STEP3:` verdicts. Branch/layout checks belong to the ready gate, not here (see [gate ownership](#gate-ownership-one-gate-per-concern)).
- [feature-loop.md](../../systems/feature-loop.md) — target state graph and card paths
- [new-project.md](./new-project.md) — repo enrollment and bootstrap handoff
- [tmux.md](../commands/tmux.md) — terminal session shortcuts, if needed

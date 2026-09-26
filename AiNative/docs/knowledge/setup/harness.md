# Harness

For enrolled projects, **Hermes** is the control plane and **Pi** is the
worker runtime. This is part 1 of the [agentic system](../../systems/agentic-system.md).

## Runtime contract

- The native Hermes Kanban board is the work queue.
- Hermes prepares an isolated task worktree and starts one new Pi session per
  agent state.
- Each Pi session receives one step, its inputs, and a compact report
  contract. It exits after that step; Hermes owns transitions and recovery.
- Project `validation_commands` run in the tester state, not as an
  orchestrator-side shortcut.
- Human gates and publish decisions remain with the operator. Workers do not
  push, merge, or deploy.
- `/ainative` is read-only methodology. Project rules and validation live in
  the project's `AGENTS.md` and `.ainative/project.yaml`.

## Related

- [feature-loop.md](../../systems/feature-loop.md) — state graph and card paths
- [new-project.md](./new-project.md) — repo enrollment and bootstrap handoff
- [tmux.md](../commands/tmux.md) — terminal session shortcuts, if needed

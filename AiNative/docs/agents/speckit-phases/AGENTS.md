# Phase driver (speckit-phases)

Runs a phased PRD from start to finish on an editor host: gets the PRD and
phase plan merged, then runs `speckit-orchestrate` once per phase, in plan
order, each phase in a fresh session so context never carries over. It starts
Phase N+1 only after Phase N's PR is merged and its worktree and branches are
cleaned up.

This is the editor-host adapter for
[feature-loop.md § Phased PRD](../../systems/feature-loop.md#phased-prd), which
leaves sequencing phase runs to the harness. Hermes does the same with one
kanban card per phase ([task-groomer](../task-groomer/)). The phase rules
themselves (scope, order, done = merged) stay in the feature loop and
[ready](../ready/); this skill only sequences runs.

## When to use

- The user invokes `/speckit-phases <PRD or phase plan path>`.
- The user asks to implement a whole phased PRD with `speckit-orchestrate`.
- To continue a phased PRD after a phase merged: invoke it again; it is
  stateless and picks the next unmerged phase from the base branch.

## Inputs

- Repo-relative path to the PRD or its `<prd-name>.phases.md`.
- Optional keywords passed to every phase run: `skip`, `worker:`,
  `reasoning:`, `validation:`. Optional `from: <N>` sanity check.

## Outputs

- A PR with the PRD and phase plan (only when they are not on the base branch yet).
- One `speckit-orchestrate` phase run per phase, each with its own merged PR.
- A final `PHASES:` report (done, or where it stopped and what to do next).

## Host support

| Host | How a phase session starts |
|------|----------------------------|
| Claude Code desktop app | New session started by the driver (fresh context, no worktree of its own) |
| Claude Code CLI, Cursor, OpenCode | Manual: the driver prints the phase command; the user pastes it into a new chat and re-invokes the driver after the merge |

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Steps: resolve, plan PR, pick phase, run phase session, verify and clean up, finish report |
| [rule.md](./rule.md) | Dispatcher boundary, one phase at a time, refused keywords |

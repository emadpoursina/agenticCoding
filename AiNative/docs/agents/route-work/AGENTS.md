# Route work

Stage 1 of the feature loop, right after `ready` ([feature-loop.md](../../systems/feature-loop.md)).
Decides the path (`feature` | `change` | `job`). Does not do the work. Does not write files, specs, or code.

Canonical source: AiNative `docs/agents/route-work/` (promoted from Cursor `route-work` 2026-09-25,
generalized to AiNative-first + Pi enrollment). Host symlink: `~/.cursor/skills/route-work/SKILL.md`.

## When to use

- Hermes dispatches the `route` state after `ready: ok`.
- Cursor `/speckit-orchestrate` launches the route stage.

## Inputs

- `REPO_ROOT` — target git repository (after `ready`: the feature `WORKTREE`)
- `FLOW_ID` — opaque run id minted by the parent
- `TASK_DESCRIPTION` — user/card task verbatim
- `REQUESTED_PATH` — `feature`, `change`, `job`, or `none`
- `REQUESTED_SKILL` — skill name the user named, or `none`

## Outputs

Compact report (parent parses it):

- `ROUTE: feature|change|job`, `SKILL`, `SKILL_PATH`, `WHY`

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Decide rules + job-skill resolution order |
| [rule.md](./rule.md) | Constraints specific to this agent |

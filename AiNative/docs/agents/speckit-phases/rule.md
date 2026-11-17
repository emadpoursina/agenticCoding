# Rules — Phase driver (speckit-phases)

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md` ([agents.md](https://agents.md/) format).

## Must

- Read which phases are merged from the phase plan **on the base branch**
  (filled `**Spec:**` line), never from the working copy or from memory.
- Fetch and fast-forward the local base branch before picking a phase; ready
  never fetches.
- Run exactly one phase at a time, in plan order, each in a fresh session (or,
  in manual mode, a fresh chat the user opens).
- Start a phase session without a worktree of its own; ready owns the phase
  worktree.
- Verify a phase report against git before moving on: PR `MERGED`, `**Spec:**`
  line filled on base, worktree and branches gone.
- Pass `skip`, `worker:`, `reasoning:`, and `validation:` through unchanged.

## Must not

- Run any feature-loop stage, write `spec.md` / `plan.md` / `tasks.md` / code,
  or edit the PRD or phase plan (the plan PR commits them unchanged; only each
  phase's `specify` step fills its `**Spec:**` line).
- Merge any PR: not the plan PR (the human merges it), not a phase PR
  (`speckit-orchestrate` merges after UAT pass).
- Start a phase while another phase's branch or PR is open, or start a phase
  ready would block.
- Accept `keep-local` / `no-ship`, `path:`, `skill:`, or `phase:`.
- Commit to or reset the base branch, or remove a worktree with uncommitted
  changes, or use `--force` on cleanup.
- Poll a phase session; wait for its report.

## Stop conditions

- No phase plan for the PRD → tell the user to run `/prd-writer` in phase-plan mode.
- Base branch ambiguous, or the local base cannot fast-forward.
- Spec Kit prerequisites or `gh` login missing.
- Plan PR open and not merged (waiting).
- A phase reports `parked` or `blocked`, or its report does not match git.
- Another phase's branch or PR is open.
- `from: <N>` does not match the next unmerged phase.

## Related enforcement

- Phase order is enforced by [ready § Phase order](../ready/SKILL.md#phase-order-required-when-phase_ref-is-set) whatever this driver does.
- Each phase run: [speckit-orchestrate](../speckit-orchestrate/SKILL.md) with `phase: <plan-path>#<N>`.

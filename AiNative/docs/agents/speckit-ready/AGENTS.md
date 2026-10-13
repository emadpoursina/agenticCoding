# Spec Kit ready

Per-card pre-flight gate. Confirms git state, Spec Kit layout (Pi enrollment
canonical), and optional `.specify/ready.yml` checks; creates or reuses a git
worktree for the feature branch; returns `READY: ok|blocked`.

Canonical source: AiNative `docs/agents/speckit-ready/` (promoted from Cursor
`speckit-ready` 2026-10-07). Hermes per-card gate `ready/` shares the same
skill body and script; see [`../ready/`](../ready/).

## When to use

- First state of every card run, before `route`.
- Re-run after `READY: blocked` is fixed.

## Inputs

- `REPO_ROOT`, `FLOW_ID`, `FEATURE_DESCRIPTION`

## Outputs

- `READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `WORKTREE`, `CHECKS`, `FIXES`

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Gate procedure (branch, layout, project checks) |
| [rule.md](./rule.md) | Constraints specific to this agent |
| [scripts/ready-check.sh](./scripts/ready-check.sh) | Executable gate (do not reimplement) |
| [scripts/ready-check.selftest.sh](./scripts/ready-check.selftest.sh) | Script self-test |

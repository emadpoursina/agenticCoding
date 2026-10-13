# Spec Kit orchestrator (Cursor parent)

Cursor parent implementation of the feature-loop graph
([feature-loop.md](../../systems/feature-loop.md)): `ready` → `route`, then
one of `feature` / `change` / `job`, with shared ship/UAT.

Canonical source: AiNative `docs/agents/speckit-orchestrate/` (promoted from
Cursor `speckit-orchestrate` 2026-10-13). The Hermes parent implements the
same graph via `personalAgent` dispatch; neither copies the graph, both link
`feature-loop.md`. Workers are stage-dumb in both runtimes (Cursor `Task` or
Pi via `pi-harness` here; Pi workers under Hermes there).

## When to use

- User invokes `/speckit-orchestrate` or asks to run the full Spec Kit flow in Cursor.

## Inputs

- User args verbatim (`skip`, `path:`, `skill:` keywords), `FLOW_ID` (minted),
  `WORKTREE` (from `ready`).

## Outputs

- Per-stage compact reports; final pipeline report + PR URL + walkthrough (UAT-ready).

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Control flow, model registry, pipeline, stuck policy |
| [rule.md](./rule.md) | Parent-vs-worker boundary |

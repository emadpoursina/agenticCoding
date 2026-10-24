# Spec Kit orchestrator (parent dispatcher)

Parent implementation of the feature-loop graph
([feature-loop.md](../../systems/feature-loop.md)): `ready` → `route`, then
one of `feature` / `change` / `job`, with shared ship/UAT.

Canonical source: AiNative `docs/agents/speckit-orchestrate/` (promoted from
Cursor `speckit-orchestrate` 2026-10-13). Symlinked into Cursor
(`~/.cursor/skills/speckit-orchestrate/`) and OpenCode
(`~/.config/opencode/skill/speckit-orchestrate/`); the Hermes parent
references the same graph via `personalAgent` dispatch rather than copying
it — all link `feature-loop.md`. Workers are stage-dumb in every runtime
(host Task, Pi via `pi-harness`, or Antigravity SDK via `antigravity-harness`
here; the same worker backends under Hermes there).
Model values are never pinned here; each runtime resolves them per run (see
SKILL.md Model resolution).

## When to use

- User invokes `/speckit-orchestrate` (Cursor) / skill `speckit-orchestrate`
  (OpenCode) or asks to run the full Spec Kit flow; Hermes references the
  same graph for dispatch.

## Inputs

- User args verbatim (`skip`, `path:`, `skill:` keywords), `FLOW_ID` (minted),
  `WORKTREE` (from `ready`).

## Outputs

- Per-stage compact reports; final pipeline report + PR URL + walkthrough (UAT-ready).

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Control flow, model resolution (runtime-owned, no pinned values), pipeline, stuck policy |
| [rule.md](./rule.md) | Parent-vs-worker boundary |

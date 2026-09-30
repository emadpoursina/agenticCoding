# Change

Small code-edit worker for the target Hermes `change` path
([feature-loop.md](../../systems/feature-loop.md), Card paths section).
Edits the worktree to match the card and reports
`STATUS`, `SCOPE`, `SUMMARY`. Stops with `SCOPE: feature`
when the card is really a feature.

> **Status: target methodology — not wired into the current install.**
> The current Hermes install has no worker loop running; see
> [feature-loop.md](../../systems/feature-loop.md).

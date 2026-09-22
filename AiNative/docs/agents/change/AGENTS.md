# Change

Small code-edit worker for the Hermes `change` path
([feature-loop.md](../systems/feature-loop.md), Card paths section).
Edits the worktree to match the card and reports
`STATUS`, `SCOPE`, `SUMMARY`. Stops with `SCOPE: feature`
when the card is really a feature.

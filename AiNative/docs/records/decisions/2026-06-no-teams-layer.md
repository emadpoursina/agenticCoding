# ADR-002: Remove teams layer from Engineering OS

**Date:** 2026-06-06
**Status:** Accepted
**Supersedes:** ADR-001 (partial — teams layer only)

## Context

ADR-001 included `docs/teams/` for per-team overrides (board URL, approvers, stack). This repo is a personal engineering OS, not a multi-team monorepo. A dedicated teams folder added structure without use — local context belongs in each project repo or `scratch/`.

## Decision

Remove the `docs/teams/` layer entirely. Universal workflows stay in `docs/systems/`. Project-specific notes (board link, approvers, stack) live in the project repository or `scratch/`, promoted to reference only when a pattern is universal.

## Consequences

**Enables:**

- Simpler navigation — one less layer to maintain
- Clear boundary: this repo = universal OS; project repos = local context

**Trade-offs:**

- No canonical place in this repo for "which board does team X use" — intentional

## Rejected alternatives

- **Keep empty teams/ as placeholder** — violates "remove layers that add no value"
- **Single teams/README template** — same friction as a folder; project repos are the right home

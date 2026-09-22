# ADR: Three explicit card paths

**Date:** 2026-09-22
**Status:** Accepted

## Context

The live feature loop runs every Kanban card through the same graph, from
ready through publish. After enroll, the operator wants every action on the
board, including a PRD, project bootstrap, and a small edit. Running the
full graph for those is the wrong cost. Prompt-only routers are a poor fit:
the same sentence can be a one-line fix or a redesign.

## Decision

- The card carries an explicit path: `feature`, `change`, or `job`.
- A missing path is `feature`. Hermes does not classify from card prose.
- `feature` is the existing graph in `docs/systems/feature-loop.md`.
- `change` is `ready` → one worker → `tester`. No spec, plan, critic, UAT,
  pr-review, or publish.
- `job` is one worker for a named skill. It may park for a human. It does
  not enter the feature graph and it does not publish. The first jobs are
  writing a PRD and bootstrapping the repo from that PRD.
- A `change` or `job` worker that finds the card is really a feature stops
  and reports that. It does not promote itself.

## Consequences

- Small edits and setup work can be cards without paying for the full loop.
- The operator must set the path when creating the card. A wrong path is a
  human mistake, fixed by stopping, not by a silent upgrade.
- Hermes still has one board and one worker per agent state. This decision
  does not add a second task store.
- The code still runs only `feature` until a later Hermes change reads the
  path. This ADR does not implement that change.

## Rejected alternatives

- Two paths only, with PRD and bootstrap as `change` cards. Those are not
  code edits, so they would distort the short code path.
- An automatic classifier on the card text. The opening sentence does not
  carry enough information, and a wrong guess skips review on a real feature.

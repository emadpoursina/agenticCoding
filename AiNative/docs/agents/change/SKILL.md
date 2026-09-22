---
name: change
description: Small code edit already specified by the Kanban card. Edit the worktree to match the card, then report STATUS/SCOPE/SUMMARY. Use for the Hermes change path only.
---

# Change

One worker for the Hermes `change` path (`ready` → `change` → `tester`).
Edit the worktree to match the card. Do not look for `tasks.md`.
Do not run specify, plan, critic, UAT, pr-review, or publish.

## What to do

1. Read the card problem, expected result, and acceptance criteria.
2. Make the smallest edit that satisfies the card.
3. If the card is really a feature (needs a spec, plan, or review), stop
   and report `SCOPE: feature`. Do not promote yourself onto the feature graph.

## Compact report

Return exactly:

- `STATUS: ok|blocked`
- `SCOPE: ok|feature`
- `SUMMARY`

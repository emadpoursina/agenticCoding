---
name: change
description: Small code edit already specified by the Kanban card. Edit the worktree to match the card, then report STATUS/SCOPE/SUMMARY. Target methodology for the Hermes change path only; not wired into the current install.
---

# Change

One worker for the target Hermes `change` path (`ready` → `change` → `tester`);
not wired into the current install. Edit the worktree to match the card. Do not
look for `tasks.md`. Do not run specify, plan, critic, UAT, pr-review, or
ship. Workers never commit, push, or open PRs — the parent does that after
operator approval.

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

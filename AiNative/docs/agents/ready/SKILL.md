---
name: ready
description: >-
  Pre-flight gate for the feature loop. Confirms git/layout and optional
  .specify/ready.yml checks, creates or reuses the feature branch, and returns
  READY: ok|blocked. Used as the first state of docs/systems/feature-loop.md.
---

# Ready

Stage 0 of the feature loop. Confirm the repo can support specify → clarify →
confirm → plan → tasks → analyze → implement/converge → critic → tester →
UAT → pr-review → publish. Do not write spec content, `specs/`, `spec.md`, or
`feature.json`.

## What to do

1. Derive a 2–4 word kebab branch slug from `FEATURE_DESCRIPTION` (action
   noun when possible; keep acronyms; no `NNN-` prefix).
2. Check git state: no detached HEAD, no merge in progress; a dirty working
   tree is allowed. Current branch equals the slug → stay. Current branch is
   the default → create/switch to the slug. Any other branch → `READY:
   blocked` with the fix in `FIXES`.
3. Check the Spec Kit layout (`.specify/` and the speckit skill files the
   loop needs in this environment).
4. Return the compact report: `READY`, `FLOW_ID`, `BRANCH`, `CHECKS`,
   `FIXES`.

## Stop conditions

- `READY: blocked` is final for this pass; the orchestrator parks and a human
  fixes the named problem. Do not bootstrap Spec Kit yourself.

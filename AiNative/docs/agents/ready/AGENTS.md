# Ready

Ready is the pre-flight gate at the start of the live feature loop
([feature-loop.md](../systems/feature-loop.md)). Ready confirms the repo can
support the loop before the first Spec Kit session starts: git state, Spec
Kit layout, and the feature branch. Ready never writes spec content, never
starts `specs/`, and never publishes.

## When to invoke

- The orchestrator (Cursor `/speckit-orchestrate` or Hermes) starts a new
  feature loop. Ready is the first state.
- Re-run Ready after `READY: blocked` is fixed. A stable `READY: blocked`
  stops the run; the orchestrator parks it.

## Inputs

- `REPO_ROOT` — the target git repository (for Hermes: the isolated task
  worktree)
- `FLOW_ID` — opaque run id minted by the parent
- `FEATURE_DESCRIPTION` — the task's feature description

## Output

Compact report (the parent parses it, never worker prose):

- `READY: ok|blocked`
- `FLOW_ID`
- `BRANCH`
- `CHECKS`
- `FIXES`

## Model behavior

- Derive a 2–4 word kebab branch slug from the feature description.
- Confirm git state (no detached HEAD, no merge in progress) and the Spec
  Kit skill layout.
- Report exactly the compact report fields. No narrative.

---
name: handoff
description: >-
  Capture current session state to a resumable handoff file and resume from one.
  Use when user says handoff, hand off, pick this up later, continue in a new
  session, or passes work to another agent.
---

# Handoff

Two modes, one file format. `capture` writes `REPO_ROOT/.agent/handoff/<slug>.md`.
`resume` reads it and continues. Agent-to-agent fields stay compatible with
[agent-handoff-template.md](../../systems/agent-handoff-template.md).

Default dir is gitignored (`.agent/`). Never commit handoff files unless the
user explicitly asks.

## Mode dispatch

- User says `handoff`, `hand off`, `save state`, `pick this up later` → `capture`.
- User pastes a handoff path or says `resume`, `continue from handoff`, `pick up <slug>` → `resume`.
- User names another agent (`next_agent: X`, `hand to tester`) → `capture` with that `next_agent`, plus a copy-paste `Next Prompt` block.

Ask one question max when ambiguous (capture vs resume). Otherwise proceed.

## Capture

1. Resolve `REPO_ROOT` = git top-level (`git rev-parse --show-toplevel`).
   `DIR = REPO_ROOT/.agent/handoff`. `mkdir -p DIR`.
2. Slug: 2–4 word kebab from task + `-YYYYMMDD-HHMM` (e.g. `auth-refresh-20261015-0254`).
   If user gave a slug, use it. Never overwrite without asking — bump timestamp.
3. Gather facts (read-only, no code edits):
   - `git -C REPO_ROOT branch --show-current` and `git -C REPO_ROOT status --short`
   - `git -C REPO_ROOT diff --stat` (unstaged + staged, no full diff in file)
   - Worktree: `git worktree list` only if relevant; record `WORKTREE = REPO_ROOT` normally.
   - FLOW_ID / BRANCH / FEATURE_DIR if a speckit run is active; else `n/a`.
   - Files touched: from status + diff stat, max 20 paths with one-line note each.
4. Ask user only for what you cannot observe: goal in one sentence, done criteria,
   open TODOs, blockers. If user says `skip` or gives nothing, write `Unknown — assumed from context` and continue. Do not block on answers.
5. Write `DIR/<slug>.md` in the template below. Keep it under ~150 lines.
   Facts over prose. File paths with `file:line` where it matters.

### Handoff file template

```markdown
---
task: <one-line goal>
status: in_progress | blocked | complete
branch: <branch or n/a>
worktree: <absolute path>
timestamp: YYYY-MM-DDTHH:MMZ
next_agent: <agent/skill name or human>
---

## Goal
<1–3 sentences: what we were doing and why>

## Current State
<What works now, what was just finished. Bullets.>

## Files Touched
- `path/to/file:line` — <what changed>
- (from `git diff --stat`: paste stat, not full diff)

## Decisions Made
- <choice + one-line why>

## Assumptions
- <what was assumed, not verified>

## Open TODOs
- [ ] <remaining work, ordered>

## Blockers / Flags
- <what stops progress, or None>

## Next Prompt
```text
Resume from .agent/handoff/<slug>.md. <one explicit instruction for next agent:
what to do first, done criteria, what NOT to redo>
```

## Validation
- [ ] Output is self-contained
- [ ] Next agent knows first action without asking
- [ ] Blockers flagged
```

6. Report exactly:

```text
HANDOFF: captured
FILE: <absolute path>
NEXT: <one-line instruction for the next agent>
```

Also print the `Next Prompt` block so the user can copy-paste cross-machine.

## Resume

1. Resolve path: absolute path, or `REPO_ROOT/.agent/handoff/<slug>.md`.
   If slug is ambiguous, list `DIR/*.md` (newest 10) and ask which. If file
   missing, stop and say so — do not invent state.
2. Read the whole file. Verify:
   - `branch` exists (`git branch --show-current` / `git branch --list`).
     If different branch, say so and stay on current branch — do not switch
     without asking.
   - Touched files still exist; note any that moved or vanished.
3. Report exactly:

```text
HANDOFF: resumed
FILE: <absolute path>
GOAL: <from file>
STATE: <2-sentence summary of Current State + TODOs count>
BLOCKERS: <from file or none>
```

4. Then do the first Open TODO (or the file's Next Prompt instruction)
   without waiting for further confirmation.

## Rules (summary, full list in rule.md)

- Capture never edits code; resume never redoes completed work without reason.
- Handoff files stay in `.agent/handoff/` and stay uncommitted by default.
- Next Prompt must be copy-paste runnable in a fresh session with no prior context.

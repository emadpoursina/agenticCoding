# Rules — Handoff

## Must

- Resolve `REPO_ROOT` via git top-level; default dir is `REPO_ROOT/.agent/handoff/`.
- Keep handoff files gitignored (`.agent/`); never commit, push, or PR them
  unless the user explicitly asks.
- Capture is read-only: gather via `git status --short`, `git diff --stat`,
  file reads. No code edits during capture.
- Keep handoff file under ~150 lines; paste `diff --stat`, never full diff.
- `Next Prompt` must be copy-paste runnable in a fresh session with zero prior
  context (file path + first action + done criteria + what NOT to redo).
- Resume verifies branch and file existence and reports drift before acting.
- Stay compatible with [agent-handoff-template.md](../../systems/agent-handoff-template.md)
  fields (`status`, `next_agent`, decisions/assumptions/blockers).

## Must not

- Overwrite an existing handoff file without asking; bump timestamp instead.
- Switch branches or worktrees during resume without asking.
- Redo completed work listed under Current State without stating why.
- Invent goal, TODOs, or blockers the file and workspace do not support.
- Write handoff files outside `.agent/handoff/` unless the user names a path.

## Stop conditions

- Resume slug matches zero or multiple files — list newest 10, ask which, stop.
- Handoff file missing or unreadable — stop, do not invent state.
- Current branch differs from file's `branch` — report, stay put, ask before switching.
- User answers `skip` on capture questions — record as assumed, finish, do not block.

## Boundary

Handoff owns state capture and restore only. It does not plan, implement,
review, or ship. After resume reports `HANDOFF: resumed`, the underlying task
skill owns the work.

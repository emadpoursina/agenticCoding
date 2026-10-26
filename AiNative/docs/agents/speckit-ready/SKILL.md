---
name: speckit-ready
description: >-
  Pre-flight gate for /speckit-orchestrate. Confirms git/layout and optional
  .specify/ready.yml checks, creates or reuses a git worktree for the feature
  branch, and returns READY: ok|blocked. Use when orchestrate launches the
  ready stage.
disable-model-invocation: true
---

# Spec Kit ready

Stage 0 of `/speckit-orchestrate`. Confirm the repo can support specify →
clarify → plan → tasks → analyze → implement/converge. Do not write spec
content, `specs/`, `spec.md`, or `feature.json`.

## Inputs (from the parent prompt)

- `REPO_ROOT` — target git repository
- `FLOW_ID` — opaque run id minted by the parent
- `FEATURE_DESCRIPTION` — user args after `/speckit-orchestrate`

## What to do

1. Derive a 2–4 word kebab **branch slug** from `FEATURE_DESCRIPTION`:
   - Action-noun when possible; keep acronyms (`OAuth2`, `API`, `JWT`).
   - No `NNN-` prefix. Examples:
     - "I want to add user authentication" → `user-auth`
     - "Implement OAuth2 integration for the API" → `oauth2-api-integration`
     - "Create a dashboard for analytics" → `analytics-dashboard`
     - "Fix payment processing timeout bug" → `fix-payment-timeout`
2. Run this skill's script (do not reimplement checks in ad-hoc shell):

   `<AINATIVE>/docs/agents/speckit-ready/scripts/ready-check.sh <REPO_ROOT> <FLOW_ID> <slug>`
   (host symlink: `$HOME/.cursor/skills/speckit-ready/scripts/ready-check.sh`;
   Hermes mount: `/opt/data/mnt/AiNative/docs/agents/speckit-ready/scripts/ready-check.sh`)

3. Return the script's stdout as the compact report. Do not wrap it.

## Rules the script enforces

### Git branch (required)

- Fail on detached HEAD or merge-in-progress.
- Resolve the base branch in this order:
  1. `SPECKIT_BASE_BRANCH` for a one-run override.
  2. This repository's local Git setting `speckit.baseBranch` (set with
     `git -C <repo> config speckit.baseBranch <branch>`).
  3. `refs/remotes/origin/HEAD`, when available.
  4. If no `origin/HEAD` exists, a unique remote `*/HEAD` target.
  5. If no remote `*/HEAD` target exists, a unique existing branch among
     `main`, `master`, `develop`, and `development` (local or remote-tracking).
- Never guess when multiple remote HEADs or base candidates exist, or when the
  base cannot be resolved. Block with a fix explaining how to set
  `speckit.baseBranch`.
- The detected base and the conventional names `main`, `master`, `develop`,
  and `development` are protected. If the current checkout is already on the
  derived slug and the slug is not protected, reuse `REPO_ROOT` itself as the
  worktree.
- When on a protected branch, add or reuse a git worktree for `<slug>` at
  `$(dirname REPO_ROOT)/.speckit-worktrees/$(basename REPO_ROOT)/<slug>`;
  never `git checkout` or `git switch` the current tree onto the slug. Reuse
  an existing worktree that already has `<slug>` checked out (`git worktree
  list`) before adding a new one. A dirty protected checkout is allowed — do
  not block on it, since the current tree is left untouched.
- If the current checkout is on a different, non-protected branch (not the
  base and not the slug), block rather than repurposing it.
- If creating or adding the worktree fails, block and report the actionable
  Git fix. Never modify or commit to the protected base branch.

### Spec Kit layout (required)

`REPO_ROOT/.specify/` exists, and the Pi enrollment prompts exist
(canonical — `specify init --integration pi`):

- `.pi/prompts/speckit.specify.md`
- `.pi/prompts/speckit.clarify.md`
- `.pi/prompts/speckit.plan.md`
- `.pi/prompts/speckit.tasks.md`
- `.pi/prompts/speckit.analyze.md`
- `.pi/prompts/speckit.implement.md`
- `.pi/prompts/speckit.converge.md`

Legacy fallbacks (honored, not canonical): `.cursor/skills/speckit-*/SKILL.md`
(Cursor enrollment) or `.opencode/commands/speckit.*.md` (retired Opencode
enrollment). The `ready-check.sh` script accepts any of the three layouts.

### Worker runtime (required)

Check only the backend this run will use (do not require both):

1. `SPECKIT_WORKER` for a one-run override.
2. This repository's local Git setting `speckit.worker`
   (`git -C <repo> config speckit.worker pi|antigravity`).
3. Default `antigravity`.

Aliases for Antigravity: `antigravity`, `agy`, `google-antigravity`.

- **pi** — `pi` is on PATH (`SPECKIT_PI_BIN` overrides the binary name).
- **antigravity** — `agy` is on PATH and authenticated (`agy models` exits 0).
  SDK import is neither required nor sufficient. Do not require the `agy` TUI.
  FIXES tell the operator to install/put `agy` on PATH or authenticate the CLI
  (never `pip install google-antigravity`).

The compact report includes `WORKER: pi|antigravity` and a
`worker-runtime` check line.

### Project checks (optional file)

If `.specify/ready.yml` is absent, skip (not a failure). If present, only:

- `tcp` — `host` + `port` reachable
- `http` — URL returns `expect_status` (default 200) within ~3s
- `file_exists` — path exists relative to repo root
- `env_var_set` — named environment variable is non-empty

No per-check shell from YAML. The **only** YAML-declared command Ready runs is
the optional top-level `setup:` string (see below). Honor `required` vs
`optional`. Malformed YAML is
a required failure. Unknown `check` type is a required failure for that item.

### Worktree local files (optional)

If the project commits a `.worktreeinclude` at the repository root (
gitignore-syntax allow-list of ignored/untracked paths), then when Ready
**adds** a new feature worktree (both the existing-branch and new-branch
paths), and only when no other required check has already failed, it copies
the matching untracked-or-ignored files from `REPO_ROOT` into the new
worktree via
`git ls-files --others --ignored --exclude-from=.worktreeinclude -z` piped to
`rsync -a --from0 --files-from=- ./ "$wt_path/"` (layout preserved; symlinks
are copied as symlinks, not dereferenced). Missing `.worktreeinclude`, an
empty file, or zero matches is a no-op, not a failure. Ignored files that do
not match are never copied. Ready never symlinks `node_modules`, `.venv`, or
`.env` back to the source checkout.

If `.specify/ready.yml` declares a top-level `setup:` command string, Ready
runs it after the copy (including a zero-file copy), only in a newly added
worktree, with that worktree as cwd, bounded at 10 minutes
(`SPECKIT_READY_SETUP_TIMEOUT_SEC` overrides the bound for self-tests only).
Missing `setup:` is a no-op. Non-zero exit or timeout is a required failure.
Reuse of an existing worktree (or the current checkout already on the slug)
overwrites nothing and runs neither the copy nor `setup:`. Copy or setup
failure on a worktree added in this run removes that worktree before
reporting `READY: blocked`, so the next run adds it fresh; reused worktrees
are never removed. `checks:` types stay `tcp` | `http` | `file_exists` |
`env_var_set` — no per-check shell.

CHECKS lines when a feature worktree was selected (new or reuse; omitted when
no worktree was selected):

- `[required] worktree-copy: pass|fail` — `copied N files` |
  `skipped (no .worktreeinclude)` | `skipped (reused worktree)` |
  `skipped (other required checks failed)` | `fail — <tool/io error, no
  paths>`. Copied paths and contents never appear in output.
- `[required] worktree-setup: pass|fail` — `ran` | `skipped (no setup:)` |
  `skipped (reused worktree)` | `skipped (other required checks failed)` |
  `fail — exit N` | `fail — timed out after 10 minutes`. Command
  stdout/stderr never appear in output; FIXES may name the command and exit
  status or timeout.

### Gate

Run all checks in one pass. Any required fail → `READY: blocked` and `FIXES:`
(one actionable line per required failure). Optional fails appear under
`CHECKS` only. Do not retry stable fails (missing file, unsafe branch state,
unresolved base branch). `tcp` /
`http` may be retried once if the first attempt looks transient.

## Report

```text
READY: ok | blocked
FLOW_ID: <flow_id>
BRANCH: <branch-name-created-or-reused>
WORKER: pi | antigravity
WORKTREE: <absolute feature worktree path>
CHECKS:
- [required] git-branch-state: pass|fail — <note>
- [required] speckit-layout: pass|fail — <note>
- [required] worker-runtime: pass|fail — <note>
- [required] worktree-copy: pass|fail — <outcome; "copied N files" when copied, never paths>
- [required] worktree-setup: pass|fail — <outcome; never command stdout/stderr>
FIXES:
- <only when blocked>
```

No `FEATURE_DIR`. `BRANCH` is the git branch name only; specify owns the spec
directory independently. `WORKTREE` is printed only on `READY: ok`: the
absolute path of the feature worktree, or `REPO_ROOT` itself when the
checkout was already on `<slug>`. Notes say the worktree was created or
reused, not "checked out".

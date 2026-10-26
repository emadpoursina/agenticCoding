# Data model: Ready worktree local files

No database. State is files plus the in-process Ready gate.

## Worktree include list

- **Identity**: committed file `.worktreeinclude` at the source checkout root (`REPO_ROOT`).
- **Fields**: gitignore-syntax patterns (allow-list).
- **Validation**: absence is a no-op, not a failure. Empty file or no matches → copy transfers zero files (setup may still run).
- **Selection rule**: only untracked-or-ignored paths matching the file, via `git ls-files --others --ignored --exclude-from=.worktreeinclude`. Tracked files are not part of this transfer.

## Source checkout

- **Identity**: tree where Ready was invoked (`REPO_ROOT` after `pwd -P`).
- **Role**: origin of copied local files; `ready.yml` `checks:` still run here (not retargeted into the worktree).

## Feature worktree

- **Identity**: isolated git worktree at `$(dirname REPO_ROOT)/.speckit-worktrees/$(basename REPO_ROOT)/<slug>`, or `REPO_ROOT` when already on the slug.
- **Fields / flags (in-script)**:
  - `worktree_path` — absolute destination (today).
  - `worktree_added_this_run` — true only if this process successfully ran `git worktree add` (existing or new branch). False on reuse.
- **Transitions**:
  - `absent` → `added` (new `git worktree add`) → optional `copy` → optional `setup` → `ready-ok`.
  - `added` → copy/setup fail → `removed` (unregister) → `READY: blocked`.
  - `existing` (reuse) → skip copy/setup → unchanged local files.
  - `added` + other required check already failed → skip copy/setup → worktree remains (today’s lifetime).

## Setup command

- **Identity**: optional top-level `setup:` string in `.specify/ready.yml`.
- **Fields**: command string; cwd = new worktree; bound 600s (test override `SPECKIT_READY_SETUP_TIMEOUT_SEC`).
- **Validation**: absent → skip. Non-zero or timeout → required failure. Not a `checks:` item; `checks:` types stay `tcp` | `http` | `file_exists` | `env_var_set`.

## Compact Ready report

- **Fields** (unchanged set): `READY`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE` (ok only), `CHECKS`, `FIXES`.
- **New CHECKS entities**: copy outcome + file count; setup outcome. No copied paths, no file contents, no setup stdout/stderr.
- **FIXES**: one actionable line per required failure, including copy/setup (may name command and exit/timeout, not output).

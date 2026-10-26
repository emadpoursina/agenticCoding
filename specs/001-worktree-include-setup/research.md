# Research: Ready worktree local files

## Decision: Extend both identical `ready-check.sh` copies after other required checks

**Rationale**: Copy and setup must run only after a successful **new** `git worktree add`, and only when no other required check has already failed (FR-017). Today the script adds or reuses the worktree first, then layout, `ready.yml` checks, worker, then report (`AiNative/docs/agents/ready/scripts/ready-check.sh` ~211–296, ~298–370, ~379–649, ~651–729, ~732–792). Insert copy/setup immediately before the report, gated on a `worktree_added_this_run` flag set only on the two successful `git worktree add` paths (existing-branch ~265–268, new-branch ~275–278). Reuse of an existing worktree (~260–263) and reuse of the current checkout (~225–227) leave the flag unset.

The two scripts are byte-identical today (`ready/` and `speckit-ready/`). FR-012 requires they and their self-tests stay in lockstep: edit one, copy to the other.

**Alternatives considered**: Copy immediately after `worktree add` — rejected; would write secrets into a tree this run will report blocked. A new helper script — rejected; twins already are the executable gate and SKILL.md forbids reimplementing checks in ad-hoc shell.

## Decision: Use the specified git + rsync pipeline without `--exclude-standard`

**Rationale**: FR-002 names `git ls-files --others --ignored --exclude-from=.worktreeinclude -z` piped to `rsync -a --from0 --files-from=- ./ "$wt_path/"`. Measured on macOS git + openrsync:

- Allow-listed ignored files (`.env`, `keep.me`) appear.
- Ignored files not in the include list (`secret.local`) do not.
- Untracked files not matching the include list do not.
- Adding `--exclude-standard` **adds** non-matching ignored files — that would violate FR-003.

macOS `/usr/bin/rsync` (openrsync protocol 29) supports `--from0` and `--files-from`. `rsync -a` preserves symlink nodes (does not dereference). Absent `.worktreeinclude` → skip copy (FR-004). Count files by counting NUL records from `ls-files`; CHECKS prints the count, never paths (FR-010, FR-011). If `rsync` is missing or the copy returns non-zero, required fail + rollback (FR-008, FR-016). No APFS `cp -c` unless rsync is absent; spec allows it as an equivalent, default remains rsync.

**Alternatives considered**: `cp -R` / `ditto` — extra platform branches. Symlink `node_modules` / `.venv` / `.env` into the worktree — explicitly out of scope.

## Decision: One top-level `setup:` string; 10-minute timeout via Python `subprocess`

**Rationale**: Existing inline Python already parses `.specify/ready.yml` (~387–516). It currently skips unknown top-level keys until `checks:` (so `setup:` before `checks:` is ignored today) and **malforms** if `checks:` is missing. Extend that parser to:

- Capture optional top-level `setup:` (single command string, quotes stripped like other values).
- Keep `checks:` types unchanged (`tcp`, `http`, `file_exists`, `env_var_set` only).
- If `setup:` is present and `checks:` is absent, emit no check records and do not MALFORM (otherwise a setup-only file would be a new required failure, contradicting SC-004 / FR-006 spirit). Empty `checks:` list remains valid.

Do **not** confuse this with the unused per-item `type: setup` key already present in selftest fixtures (`ready-check.selftest.sh` ~167–178); the parser never reads `type`. Leave that key alone.

Run setup with cwd = new worktree. Bound with `python3` `subprocess.run(..., timeout=600, capture_output=True)` so CHECKS/FIXES never dump stdout/stderr (secrets). Non-zero or `TimeoutExpired` → required fail. GNU `timeout` is not assumed on macOS.

**Alternatives considered**: Arbitrary per-check `shell` type — forbidden by FR-007 and current SKILL (“No arbitrary shell from YAML”). This feature’s only YAML-declared command is top-level `setup:`.

## Decision: Rollback only worktrees added this run

**Rationale**: FR-016. On copy or setup failure when `worktree_added_this_run=1`, `git worktree remove --force -- "$wt_path"` (then clear `worktree_path`) before printing `READY: blocked`. Never remove a reused worktree or `REPO_ROOT`. Other required failures after add (layout, project checks, worker) keep today’s lifetime: worktree stays; copy/setup skipped.

**Alternatives considered**: Leave the failed tree in place for debugging — rejected; next Ready would reuse and skip copy/setup (the skip-mode clarification).

## Decision: CHECKS lines for copy and setup, including no-ops

**Rationale**: FR-010 and US3. Compact report fields stay `READY`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE`, `CHECKS`, `FIXES`. Parent (`speckit-orchestrate`) already parses these; adding CHECKS bullets is additive. Suggested notes (no paths):

- copy: `copied N files` | `skipped (no .worktreeinclude)` | `skipped (reused worktree)` | `skipped (other required checks failed)` | `fail — <tool/io, no paths>`
- setup: `ran` | `skipped (no setup:)` | `skipped (reused worktree)` | `skipped (other required checks failed)` | `fail — exit N` | `fail — timed out after 10 minutes`

Emit these whenever a worktree was selected (new or reuse). If branch/layout never produced a worktree, omit them (nothing to copy).

**Alternatives considered**: Printing copied paths for operator debug — rejected; secrets.

## Decision: Docs twins + proving selftest; constitution is a stub

**Rationale**: FR-013/FR-014. Canonical docs: `AiNative/docs/agents/ready/{AGENTS,SKILL}.md` and `speckit-ready/` twins. `feature-loop.md` is context only. `.specify/memory/constitution.md` is still the unfilled Specify template; project gates that actually bind Ready are SKILL/rule.md (gate-only, no spec writes, no ship, no arbitrary YAML shell except this spec’s `setup:` carve-out).

Proving check lives in both `ready-check.selftest.sh` copies: temp repo, `.gitignore` two files, `.worktreeinclude` lists one, Ready creates a worktree, matched `.env` present, unmatched ignored file absent. Additional cases (not extra files): setup fail removes the new worktree; reuse does not overwrite; timeout can be a short internal bound in test via an env override **only if** documented as test-only — prefer a setup command `exit 1` for fail/rollback and skip a 10-minute sleep. Timeout behavior is specified; a unit of the python timeout helper is enough if a full 600s test is unreasonable. Prefer: test the timeout path with `SPECKIT_READY_SETUP_TIMEOUT_SEC` defaulting to 600, used only by selftest with a tiny value. Spec does not forbid a test hook; if we avoid env hooks, document timeout as proven by the python `timeout=` argument and do not add a 10-minute selftest. **Chosen**: default 600 in code; selftest may export a small `SPECKIT_READY_SETUP_TIMEOUT_SEC` to prove the timeout FIXES line without sleeping 10 minutes. Production Ready does not need the var.

**Alternatives considered**: Separate sibling test file — allowed by spec; keep in selftest to match “twin self-tests stay in sync.”

## Constitution tension (ANALYZE)

Ready SKILL today: “No arbitrary shell from YAML.” Spec FR-007: setup is the **only** YAML-declared command; checks stay non-shell. Plan treats this as a documented exception, not a new per-check shell type. Compact-report contract is shared with the orchestrator parent. Twin-script sync is a cross-folder invariant.

## Open questions

None remaining for implementation. Skip-mode clarifications are in `spec.md`.

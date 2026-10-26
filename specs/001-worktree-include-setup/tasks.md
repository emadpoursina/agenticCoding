---
description: "Task list for Ready worktree local files"
---

# Tasks: Ready worktree local files

**Input**: Design documents from `/specs/001-worktree-include-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Spec FR-013 and each story’s Independent Test require runnable checks in `ready-check.selftest.sh` (no live network). Write those cases so they fail before the matching script change, then implement.

**Organization**: Tasks are grouped by user story. Edit `AiNative/docs/agents/ready/` first; copy byte-identical twins in Polish (FR-012). Do not invent `.worktreeinclude` or `setup:` for repos that omitted them. Do not write spec content, start `specs/`, or ship.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Agent scripts + docs (not an application):

```text
AiNative/docs/agents/ready/scripts/ready-check.sh
AiNative/docs/agents/ready/scripts/ready-check.selftest.sh
AiNative/docs/agents/ready/AGENTS.md
AiNative/docs/agents/ready/SKILL.md
AiNative/docs/agents/speckit-ready/   # identical script twins + docs twins
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stay inside existing Ready/speckit-ready files; no new packages or helper scripts

- [X] T001 Confirm the four existing script/doc twin paths in `AiNative/docs/agents/ready/` and `AiNative/docs/agents/speckit-ready/` match plan.md (no new directories, no new dependencies)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Worktree lifecycle flag and the single insert point before the compact report so copy/setup can run only after a new add

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `worktree_added_this_run=0` next to `worktree_path=""` in `AiNative/docs/agents/ready/scripts/ready-check.sh` and set it to `1` only on the two successful `git worktree add` paths (existing-branch ~265–268 and new-branch ~275–278); leave it `0` on current-checkout reuse (~225–227) and existing-worktree reuse (~260–263)
- [X] T003 Insert a copy/setup section immediately before the Report block (~731) in `AiNative/docs/agents/ready/scripts/ready-check.sh`: if `worktree_path` is empty, omit copy/setup entirely; if a worktree was selected but `worktree_added_this_run` is `0` or any other required check already failed (`branch_fail`, `layout_fail`, `project_required_fail`, `worker_fail`), skip both copy and setup (FR-017 / data-model: reused trees and “other required fail after add” never copy or run setup)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - New worktrees receive listed local files (Priority: P1) 🎯 MVP

**Goal**: After a successful new `git worktree add`, copy untracked-or-ignored paths allowed by committed `.worktreeinclude` (gitignore-syntax allow-list) from `REPO_ROOT` into the new worktree, preserving relative layout and symlink nodes; skip when the include file is absent

**Independent Test**: Temp repo ignores two files, lists only one in `.worktreeinclude`, Ready creates a new worktree, only the listed file appears (FR-013 / SC-002)

### Tests for User Story 1

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T004 [US1] Add the proving selftest in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh`: gitignore `.env` and a non-matching ignored file; committed `.worktreeinclude` lists only `.env`; run Ready so it creates a new worktree; assert the matched `.env` exists at the same relative path in that worktree and the unmatched ignored file is absent
- [X] T005 [US1] Add a selftest case in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` that omits `.worktreeinclude` and asserts Ready still succeeds without copying extra ignored files (absence is a no-op, not a failure)
- [X] T006 [US1] Add a selftest case in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` where another required check has already failed after a new worktree add: copy must not run (listed local files must not appear in that worktree)

### Implementation for User Story 1

- [X] T007 [US1] When `worktree_added_this_run=1`, other required checks passed, and `$REPO_ROOT/.worktreeinclude` exists, list matches with `git ls-files --others --ignored --exclude-from=.worktreeinclude -z` (do not add `--exclude-standard`) and copy with `rsync -a --from0 --files-from=- ./ "$worktree_path/"` from `REPO_ROOT` in `AiNative/docs/agents/ready/scripts/ready-check.sh`; preserve symlink nodes (do not dereference); never create new `node_modules` / `.venv` / `.env` links back to the source checkout; count NUL records for CHECKS (never print copied paths)
- [X] T008 [US1] If `.worktreeinclude` is absent, skip copy and continue in `AiNative/docs/agents/ready/scripts/ready-check.sh` (empty include or no matches: transfer zero files, not a failure)
- [X] T009 [US1] If `rsync` is missing or copy returns non-zero, set Ready blocked with an actionable FIXES line (tool/io only, no paths) in `AiNative/docs/agents/ready/scripts/ready-check.sh` and `git worktree remove --force` the worktree added this run, then clear `worktree_path` (never remove a reused worktree or `REPO_ROOT`)

**Checkpoint**: User Story 1 is independently testable via the proving selftest

---

## Phase 4: User Story 2 - Optional post-create setup, without touching reused trees (Priority: P2)

**Goal**: Optional top-level `setup:` in `.specify/ready.yml` runs only in a newly added worktree (cwd = that tree, 600s bound); failure blocks Ready and rolls back that new tree; reuse never overwrites locals or re-runs setup

**Independent Test**: Declared setup that fails → `READY: blocked`, FIXES line, newly added worktree gone so a later Ready can add fresh; reuse of an existing worktree does not overwrite an extra local file and does not run setup

### Tests for User Story 2

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T010 [US2] Add a selftest in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` with `setup: exit 1`: Ready is `blocked`, FIXES names the failed setup (command/exit, not stdout/stderr), and the worktree added this run is unregistered/gone
- [X] T011 [US2] Add a selftest in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` that reuses an existing feature worktree whose extra local file was changed: that file is not overwritten and setup does not run
- [X] T012 [US2] Add a selftest in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` that exports a tiny `SPECKIT_READY_SETUP_TIMEOUT_SEC` with a hanging setup command and asserts `READY: blocked` plus a FIXES line for timeout (default production bound remains 600s; do not sleep 10 minutes)
- [X] T013 [US2] Add a selftest in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` for a setup-only `.specify/ready.yml` (top-level `setup:` and no `checks:` block): file is valid (not MALFORM); setup still runs on a newly created worktree even when copy transferred zero files

### Implementation for User Story 2

- [X] T014 [US2] Extend the inline Python parser in `AiNative/docs/agents/ready/scripts/ready-check.sh` to capture optional top-level `setup:` as a single command string (quotes stripped like other values); if `setup:` is present and `checks:` is absent, emit no check records and do not MALFORM; empty `checks:` list remains valid; `checks:` types stay `tcp` | `http` | `file_exists` | `env_var_set` only (no per-check shell; leave unused fixture `type: setup` ignored)
- [X] T015 [US2] After a successful copy (including a no-op copy) on a newly added worktree with no other required failures, run `setup:` in `AiNative/docs/agents/ready/scripts/ready-check.sh` with cwd = the new worktree via `python3` `subprocess.run(..., timeout=..., capture_output=True)` so CHECKS/FIXES never dump command stdout/stderr; timeout default 600s, overridable only by `SPECKIT_READY_SETUP_TIMEOUT_SEC`; missing `setup:` or missing `.specify/ready.yml` skips setup (not a failure)
- [X] T016 [US2] On setup non-zero exit or `TimeoutExpired`, set `READY: blocked` with a FIXES line naming the command and exit or timeout (not output) in `AiNative/docs/agents/ready/scripts/ready-check.sh`, then `git worktree remove --force` only if `worktree_added_this_run=1`

**Checkpoint**: User Stories 1 and 2 both work independently (copy-only projects and setup-fail rollback)

---

## Phase 5: User Story 3 - Operators see copy/setup outcome without leaked secrets (Priority: P3)

**Goal**: Compact report CHECKS/FIXES include copy and setup outcomes (copy: outcome plus file count, never paths); Ready AGENTS.md and SKILL docs for both twins mention `.worktreeinclude` and `setup:`

**Independent Test**: Inspect successful and failed Ready reports for CHECKS/FIXES; grep Ready agent docs for `.worktreeinclude` and `setup:`; confirm the two `ready-check.sh` copies stay equivalent

### Tests for User Story 3

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T017 [US3] Extend `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` so successful copy CHECKS include `worktree-copy` with a file count (e.g. `copied N files`) and never contain copied relative paths (including `.env` as a path in the copy note) or file contents; setup CHECKS never contain command stdout/stderr
- [X] T018 [US3] Extend `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` so skip notes exist for reused worktree, missing include, missing `setup:`, and other-required-fail skip, matching `specs/001-worktree-include-setup/contracts/ready-report.md`

### Implementation for User Story 3

- [X] T019 [US3] Emit `[required] worktree-copy` and `[required] worktree-setup` CHECKS lines from `AiNative/docs/agents/ready/scripts/ready-check.sh` whenever a feature worktree was selected (new or reuse), using notes `copied N files` | `skipped (no .worktreeinclude)` | `skipped (reused worktree)` | `skipped (other required checks failed)` | `fail — <tool/io, no paths>` and `ran` | `skipped (no setup:)` | `skipped (reused worktree)` | `skipped (other required checks failed)` | `fail — exit N` | `fail — timed out after 10 minutes`; omit both lines when no worktree was selected; keep field set `READY`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE` (ok only), `CHECKS`, `FIXES`; `WORKTREE` stays omitted on blocked including after rollback
- [X] T020 [P] [US3] Document `.worktreeinclude` (gitignore-syntax allow-list of ignored/untracked paths copied into newly added worktrees) and optional `setup:` in `AiNative/docs/agents/ready/AGENTS.md`
- [X] T021 [P] [US3] Document `.worktreeinclude` and `setup:` (only YAML-declared command; `checks:` stay non-shell; 10-minute bound; reuse skips both) in `AiNative/docs/agents/ready/SKILL.md`, including the compact-report CHECKS bullets from `specs/001-worktree-include-setup/contracts/ready-report.md`
- [X] T022 [P] [US3] Document `.worktreeinclude` and `setup:` in `AiNative/docs/agents/speckit-ready/AGENTS.md` to the same operator facts as the ready twin
- [X] T023 [P] [US3] Document `.worktreeinclude` and `setup:` in `AiNative/docs/agents/speckit-ready/SKILL.md` to the same operator facts as the ready twin

**Checkpoint**: Operators can diagnose copy/setup from CHECKS/FIXES without leaked paths; docs mention both knobs

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Twin-script lockstep and quickstart validation

- [X] T024 Copy `AiNative/docs/agents/ready/scripts/ready-check.sh` onto `AiNative/docs/agents/speckit-ready/scripts/ready-check.sh` and `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` onto `AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh` so the pairs stay byte-identical (FR-012)
- [X] T025 Run both selftests and both `cmp` commands from `specs/001-worktree-include-setup/quickstart.md`; confirm `rg -n 'worktreeinclude|setup:'` hits all four AGENTS/SKILL files
- [X] T026 Confirm `AiNative/docs/agents/ready/scripts/ready-check.sh` still never writes spec content, never starts `specs/`, and never ships (FR-015)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; uses US1 copy insert point (setup runs after copy, including no-op copy)
- **User Story 3 (Phase 5)**: Depends on Foundational; CHECKS wiring should follow US1/US2 outcomes; doc tasks T020–T023 can start once the contract notes are known
- **Polish (Phase 6)**: Depends on desired user stories; twin `cp` after `ready/` script edits

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — no dependency on US2/US3
- **User Story 2 (P2)**: After Phase 2 — independently testable via setup-fail rollback even if copy transferred zero files; shares `ready-check.sh` with US1 so implement sequentially in one file
- **User Story 3 (P3)**: After Phase 2 — report/docs; script CHECKS lines share `ready-check.sh` with US1/US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Flag/gate (Phase 2) before copy before setup before CHECKS polish
- `ready/` scripts before speckit-ready byte copy (T024)
- Story complete before moving to next priority when staffing is sequential

### Parallel Opportunities

- T020–T023 (four doc files) can run in parallel
- Selftest cases T004–T006 can be authored together in one file sequentially (same file → not [P])
- US2 tests T010–T013 same file, sequential
- Do not parallelize edits to `ready-check.sh` across stories (same file)

---

## Parallel Example: User Story 3 docs

```bash
Task: "Document .worktreeinclude and setup: in AiNative/docs/agents/ready/AGENTS.md"
Task: "Document .worktreeinclude and setup: in AiNative/docs/agents/ready/SKILL.md"
Task: "Document .worktreeinclude and setup: in AiNative/docs/agents/speckit-ready/AGENTS.md"
Task: "Document .worktreeinclude and setup: in AiNative/docs/agents/speckit-ready/SKILL.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (proving copy selftest)
4. **STOP and VALIDATE**: `bash AiNative/docs/agents/ready/scripts/ready-check.selftest.sh`
5. Demo isolated worktree with listed locals

### Incremental Delivery

1. Setup + Foundational → flag and skip gate
2. User Story 1 → copy + proving check → MVP
3. User Story 2 → setup timeout/rollback/reuse skip
4. User Story 3 → CHECKS + docs
5. Polish → twin `cmp` + quickstart `rg`

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. One implementer owns `ready-check.sh` sequentially (US1 then US2 then CHECKS)
3. Another can draft T020–T023 docs in parallel once contracts are stable
4. T024 syncs speckit-ready scripts last

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec.md user stories
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group only if the operator asks
- Stop at any checkpoint to validate the story independently
- Avoid: printing copied paths, per-check YAML shell, symlink-back to source checkout, editing `feature-loop.md` (out of required doc scope)

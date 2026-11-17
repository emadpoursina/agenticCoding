---
name: speckit-phases
description: >-
  Runs every phase of a phased PRD in order, one speckit-orchestrate run per
  phase, each in a fresh session so no context carries over. Gets the PRD and
  phase plan merged first, then starts the next unmerged phase after the
  previous one's PR is merged and cleaned up. Use when the user invokes
  /speckit-phases with a PRD or phase plan path, or asks to implement a whole
  phased PRD with speckit-orchestrate.
disable-model-invocation: true
---

# Phase driver

This skill runs a phased PRD from start to finish on an editor host (Claude
Code, Cursor, OpenCode). It is that host's adapter for
[feature-loop.md § Phased PRD](../../systems/feature-loop.md#phased-prd),
which leaves the sequencing of phase runs to the harness. Hermes does the same
job with one kanban card per phase ([task-groomer](../task-groomer/SKILL.md)).

```text
step 0: PRD + phase plan merged into base
  → phase 1 session: /speckit-orchestrate phase: <plan>#1 … UAT pass → merged
  → cleanup check
  → phase 2 session (fresh context) … → merged → cleanup check
  → … until no phase has `**Spec:** none`
```

The driver is a dispatcher, one level above `speckit-orchestrate`. It never
runs a stage, never writes a spec, plan, or code, never merges a phase PR, and
never has more than one phase in flight.

The driver keeps no state of its own. Everything it needs is read from git:
the phase plan on the base branch says which phases are merged (a filled
`**Spec:**` line), and the phase branches and PRs say which one is in flight.
So it can stop at any point and pick up again by being invoked again.

## Input

`/speckit-phases <path> [keywords]`

- `<path>` — the PRD (`docs/prd/billing.md`) or its phase plan
  (`docs/prd/billing.phases.md`), repo-relative. A PRD path maps to the plan
  next to it: drop the `.md`, add `.phases.md`.
- Keywords passed through unchanged to every phase run: `skip`,
  `worker: …`, `reasoning: …`, `validation: …`
  ([speckit-orchestrate § Keywords](../speckit-orchestrate/SKILL.md#keywords)).
- **Refused keywords:** `keep-local` / `no-ship` (a phase that never merges
  blocks every later phase), `path:` and `skill:` (a phase run is always
  `feature`), and `phase:` (the driver picks the phase). Stop and say why.
- `from: <N>` — optional. Only a sanity check: the driver still starts the
  first unmerged phase, and stops if that is not N.

## Step 1 — Resolve

1. `REPO_ROOT` = `git rev-parse --show-toplevel`. Stop if the checkout has a
   merge or rebase in progress.
2. Resolve the base branch exactly as ready does
   ([ready § Git state](../ready/SKILL.md)): `SPECKIT_BASE_BRANCH`, then
   `git config speckit.baseBranch`, then `origin/HEAD`, then a unique remote
   HEAD, then a unique one of `main` / `master` / `develop` / `development`.
   Never guess; stop and ask when it is ambiguous.
3. `git -C <REPO_ROOT> fetch origin`, then fast-forward the local base branch
   to `origin/<base>` (`git -C <REPO_ROOT> merge --ff-only` when the base is
   checked out, else `git fetch origin <base>:<base>`). Ready reads the local
   base and never fetches, so a stale local base would block a phase whose
   predecessor is already merged. If the fast-forward is not possible, stop
   and report; never reset the base.
4. Resolve `PLAN` (the `.phases.md` path). If the file exists nowhere (not on
   disk, not on the base branch), stop: the PRD needs a phase plan first —
   tell the user to run `/prd-writer` in phase-plan mode on that PRD.
5. Check the speckit-orchestrate prerequisites once
   ([speckit-orchestrate § Prerequisites](../speckit-orchestrate/SKILL.md#prerequisites)):
   `.specify/` and the project Spec Kit prompts, plus a usable `gh` login.
   Missing → stop and list what is missing. Do not create them.

## Step 2 — Get the PRD and phase plan merged (step 0)

Ready blocks Phase 1 until the phase plan is on the base branch, and every
phase reads the PRD from there. Check `git cat-file -e <base>:<PLAN>` and the
same for the PRD the plan names.

- **Both on base, and the working copies match base** → go to Step 3.
- **Missing from base, or the working copy differs** → open the plan PR:
  1. Guards (stop on any failure): the only changed paths are the PRD and
     `PLAN`; no secrets; `origin` is the expected remote.
  2. Create branch `docs/<plan-slug>-plan` from the base (plan file name
     without `.phases.md`, kebab-cased), in a worktree under the same parent
     as ready's worktrees, or from `REPO_ROOT` when it is clean and on base.
     Never commit to the base branch.
  3. Copy in the two files, commit with Conventional Commits
     (`docs: add PRD and phase plan for <name>`), push, and open one PR with
     `gh pr create`. If an open PR for that branch exists, reuse it.
  4. Park: tell the user the PR URL and that Phase 1 starts once they merge
     it. The driver never merges this PR.
  5. On resume (the user says it is merged, or invokes the driver again):
     verify `gh pr view <PR> --json state` is `MERGED`, fast-forward the base,
     remove the plan worktree and the local and remote branch, then go to
     Step 3.

## Step 3 — Pick the next phase

Read `PLAN` **from the base branch** (`git show <base>:<PLAN>`), not from the
working copy.

1. `N` = the lowest `## Phase <N>` whose `**Spec:**` line is `none`.
2. No such phase → every phase is merged. Go to **Finish**.
3. Look for a phase run already in flight: branch `<plan-slug>-phase-<N>`
   ([ready's fixed phase slug](../ready/SKILL.md)) locally or on `origin`, or
   an open PR whose head is that branch.
   - In flight with an open PR → this phase is not done. Resume it in Step 4
     (same branch and PR; ready reuses the branch).
   - A branch or PR for a phase **other than** N exists and is not merged →
     stop and report it. Never start a second phase while another is open.
4. If `from: <N>` was given and does not match, stop and report both numbers.

## Step 4 — Run the phase in a fresh session

Each phase gets its own session so its stage reports, implement ↔ converge
loops, clarify questions, and UAT rounds never reach the next phase's context.
Inside that session `speckit-orchestrate` already runs every stage as a fresh
subagent or worker; the driver does not change that.

The phase session's opening message is exactly:

```text
/speckit-orchestrate phase: <PLAN>#<N> [pass-through keywords]
```

followed by this brief, as plain text after the command line:

```text
This is Phase <N> of <PLAN>, started by the phase driver. Run it to the end:
through UAT, the merge, and the post-merge cleanup (base synced, the phase
worktree and its local and remote branches removed). End your final report
with these lines:
PHASE: <N>
PHASE_STATUS: merged | parked | blocked
PR: <url or none>
CLEANUP: done | pending | n/a
REASON: <one line when parked or blocked, else none>
```

How to start it depends on the host:

- **Claude Code desktop app** — start a new session (the app's session-start
  tool), working directory `REPO_ROOT`, **without** a worktree of its own:
  ready creates the phase worktree, and a second one would split the work.
  Start it fresh (no fork of this conversation). Then wait for its report;
  do not poll it.
- **Any other host** (Claude Code CLI, Cursor, OpenCode), or when the
  session-start tool is not available or the new session did not run the
  command as the `speckit-orchestrate` skill → **manual mode**: print the
  opening message above in a code block and tell the user to paste it into a
  new chat in `REPO_ROOT`, then to invoke `/speckit-phases <path>` again here
  (or in any new chat) once that phase is merged. The driver is stateless, so
  re-invoking it continues from the next phase.

The user answers the phase's clarify questions and does its UAT **in the phase
session**, not here.

## Step 5 — After the phase reports

Read the report, then verify it against git. The report is a claim, not proof.

- `PHASE_STATUS: parked` or `blocked` → stop. Tell the user the phase, the
  reason, and that the fix happens in that phase's session (or by re-running
  `/speckit-orchestrate phase: <PLAN>#<N>` there). Do not start the next phase.
- `PHASE_STATUS: merged` → verify, in order:
  1. `gh pr view <PR> --json state` is `MERGED`.
  2. Fast-forward the local base (Step 1.3).
  3. Phase N's `**Spec:**` line on the base branch is filled and names a spec
     directory whose `spec.md` is on the base branch.
  4. **Cleanup:** the phase worktree is gone (`git worktree list`) and the
     branch `<plan-slug>-phase-<N>` is gone locally and on `origin`. If any is
     left, remove it here — only after checks 1–3 pass, only if the worktree
     has no uncommitted changes (otherwise stop and report the path), and
     never with `--force`.
  Any check 1–3 failing → stop and report what does not match.
- Then go back to **Step 3** for the next phase.

## Finish

When no phase has `**Spec:** none`, report:

```text
PHASES: done
PLAN: <PLAN>
MERGED: <N phases, with their PR URLs>
MVP: <the plan's "MVP complete after" phase, and whether it is merged>
DEFERRED: <count of Deferred items in the plan, or none>
```

On any stop, report instead:

```text
PHASES: waiting | parked | blocked
PLAN: <PLAN>
PHASE: <N, or "plan PR">
PR: <url or none>
REASON: <one line>
NEXT: <what the user does next, e.g. "merge the plan PR, then run /speckit-phases <path>">
```

`waiting` means the driver is parked on a human step (the plan PR merge, or a
phase session waiting on UAT). `parked` / `blocked` mean something needs
fixing first.

---
name: learn
description: >-
  Builds a time-boxed throwaway spike or demo that answers one question,
  parks for the operator's verdict and go/rework/kill decision, then writes
  a finding and a reference patch. Use when route-work sends a card with
  mode learn to the job path, or when an idea must be tried before it is built.
disable-model-invocation: true
---

# Learn

<!-- canonical: AiNative docs/agents/learn/ -->

Build to learn, not to earn ([scoping.md](../../systems/scoping.md)). Anything
past what answers the card's question is waste.

```text
STEP: build   → read card → build prototype → gather evidence → park (NEEDS_HUMAN)
STEP: finding → save patch → revert prototype → write finding → STATUS: ok → parent ships
```

The parent starts one worker per step and tells it which one. Do only the
named step. The two steps run in separate sessions: the operator's answers
arrive in the `finding` step's prompt.

## Inputs (from the parent prompt)

- `REPO_ROOT`, `FLOW_ID`, `BRANCH`
- `STEP` — `build` or `finding`
- `TASK_DESCRIPTION` — the card, verbatim
- `DEADLINE` — ISO 8601; the moment the appetite runs out
- `FINDING_SLUG` — `<YYYY-MM-DD>-<slug>`, fixed for both steps (the parent
  mints it from the card's start date and title)
- `STEP: finding` only: the build report and the operator's answers

## Read the card

Required sections: `## Mode` (`learn: spike` or `learn: demo`),
`## Question`, `## Appetite`, `## Exit Evidence`, `## Out of Scope`. If one
is missing, or the question has more than one answerable part, return
`STATUS: blocked` with `SUMMARY` naming the gap. Do not build.

## STEP: build

1. **Check the clock.** Run `date -u +%Y-%m-%dT%H:%M:%SZ`. If `DEADLINE` has
   passed, skip to step 5 with `BREAKER: tripped`.
2. **Plan the shortest path to the exit evidence.** Write it as three to five
   lines in your head, not a file. Everything in `## Out of Scope` is faked:
   hard-coded data, stubbed calls, no auth, no error handling.
3. **Build it in the worktree.** Edit tracked files when the question is about
   the existing app; add new files when it is not. Follow the repo's stack so
   the evidence means something. Do not write tests unless a test *is* the
   evidence.
4. **Gather the exit evidence.** Check the clock between pieces of work; stop
   when `DEADLINE` passes.
   - `spike`: run the prototype and capture the output that answers the
     question (command, output, numbers). Write the raw evidence to
     `.learn/<FINDING_SLUG>/evidence/` — this folder is scratch and is
     deleted in the `finding` step.
   - `demo`: make it runnable and write the exact steps a person follows to
     try it (command to start, URL or screen, what to do).
5. **Park once.** Return `STATUS: blocked` with `NEEDS_HUMAN` (see
   [Report](#report)). Never `STATUS: ok` on this step: on the `job` path
   `ok` ships, and nothing ships before the finding. `NEEDS_HUMAN` holds,
   in this order:
   - the question and your answer so far (`yes`, `no`, `yes, if …`, or
     `unanswered`), with the evidence in two or three lines
   - `demo` only: the steps to try it, and "Does this solve the problem for
     the person it is for?"
   - what the prototype faked
   - your recommendation (go / rework / kill) in one line, with the reason
   - "Decision: go, rework, or kill?"

Leave the prototype in the worktree; the `finding` step needs it.

## STEP: finding

1. **Save the prototype as a reference patch.** Include new files: mark them
   with `git add -N <paths>`, run
   `git diff --binary > docs/learn/<FINDING_SLUG>.patch`, then `git reset`.
   Exclude `.learn/` and the finding itself. If the patch is over 3000 lines,
   keep only the lines that carry the idea and note the cut in the finding.
2. **Revert the prototype.** Restore every tracked file the prototype changed
   (`git restore --source=HEAD --staged --worktree -- <paths>`), and delete
   every new file it added, plus `.learn/`. Use explicit paths; never a blanket
   `git clean`.
3. **Write the finding** at `docs/learn/<FINDING_SLUG>.md`
   (format below). The decision is the operator's answer, copied verbatim.
   If the operator did not decide, return `STATUS: blocked` and ask again.
4. **Verify the diff.** `git status --porcelain` must list exactly the finding
   and the patch. Anything else: fix it before reporting.

## Finding format

```markdown
# Learn: [Short title]

**Kind:** spike | demo
**Date:** [YYYY-MM-DD]
**Card:** [card id or title]
**Appetite:** [as written on the card] · **Used:** [time actually spent]
**Circuit breaker:** not tripped | tripped
**Decision:** go | rework | kill

## Question

[The card's question, verbatim]

## Answer

[yes | no | yes, if … | unanswered] — [one paragraph]

## Evidence

[What was run or shown, and what came out. For a demo, the person's verdict
in their words.]

## Faked

[Everything the prototype skipped or hard-coded. A future build must not
assume any of it works.]

## Surprises

[What we did not expect. "None." when empty.]

## Next

[go: what the build card or PRD should carry over — constraints, the shape
that worked. rework: the narrower question for the next learn card.
kill: why, in one sentence.]

**Prototype:** `<FINDING_SLUG>.patch` in this folder — reference only, never applied
```

## Report

```text
FLOW_ID: <flow_id>
STEP: build | finding
STATUS: ok | stuck | blocked   (build step: always blocked when parking)
KIND: spike | demo
ANSWER: yes | no | yes-if | unanswered
BREAKER: tripped | no
NEEDS_HUMAN: <the park text, build step only; otherwise none>
FINDING: <repo-relative path, finding step only; otherwise none>
DECISION: go | rework | kill | none
SUMMARY: <one or two sentences>
```

The parent ships after `STEP: finding` reports `STATUS: ok`: a single
commit, `docs(learn): record <kind> finding for <short title>`, on the
`job` path ([feature-loop.md § Card paths](../../systems/feature-loop.md#card-paths)).
On **go**, the operator opens a `build` card or a `prd-writer` job that
cites the finding; this worker never opens one.

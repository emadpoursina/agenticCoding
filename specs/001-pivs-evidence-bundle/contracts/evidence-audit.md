# Contract: pr-reviewer evidence audit

On-demand after Ship. Not a loop gate. Re-runnable on every pr-review pass after a fix push (FR-009).

## Inputs

- PR head SHA
- `specs/<flow>/evidence.md` from the PR worktree / local bundle (gitignored — reviewer uses the working tree or attached CI artifacts, not git history)
- Plan acceptance criteria and proof types
- PR CI results for the jobs that re-run Plan `validation_commands` (or documented equivalent)

## Checks (all required)

1. **Completeness** (verdict-aware): tester PASS → every acceptance criterion has a manifest row and the required artifact shape for its proof type. Tester FAIL → rows are required for every flow that was executed (with actual exit codes); unexecuted criteria are not "claimed proven" and are not flagged as claimed but unproven.
2. **SHA freshness**: each row’s commit SHA must equal current PR head. Mismatch → mark those rows **stale**.
3. **CI agreement**: on this head, CI re-ran `validation_commands` (or documented equivalent) and those jobs **succeeded**. Artifact bytes need not match local files.
4. **Claimed but unproven**: tester PASS (or claimed proven) when any of: missing manifest, missing required artifact, stale SHA, CI failed, CI skipped, CI unfinished.
5. **Merge gate:** stale and claimed-but-unproven are **Critical** (trouble ≥ 0.8, file:line on the manifest or PR `## Evidence` row, named trigger). They REQUEST CHANGES via the same gate as other findings. They are not a parallel blocker. Phase 1.5 BLOCKED is unchanged.

## Non-blocking / allowed

- Tester FAIL with a complete executed-flow manifest: Ship may still show `## Evidence`; pr-reviewer still blocks merge-quality claims that are unproven, but recording failed commands is required, not forbidden.
- Ship opened before CI finished: `## Evidence` may use named artifacts; until this head’s jobs succeed, PASS claims stay claimed but unproven.

## Docs that MUST state this

- `AiNative/docs/agents/pr-reviewer/` prompts (staged review)
- `AiNative/docs/systems/pr-review-system.md` overview

# Research: Agentic validation loop

Operator `skip` was active. Clarify answers already live in `spec.md` (Session 2026-10-26). No `[NEEDS CLARIFICATION]` remain. Constitution is an unfilled template (spec Assumptions).

## Decision: Validation is a parent-owned loop, not an optional afterthought

- **Decision**: After feature-path `CONVERGE_OUTCOME: converged`, the parent launches critic (Validation profile, fresh session), then tester only on critic PASS, then ship only on tester PASS (unless `keep-local`). After `SHIP: ok`, the parent launches pr-reviewer automatically. Job path never launches pr-reviewer. Change path stays tester-only (change `STEP: tester`), then ship, then automatic pr-review.
- **Rationale**: Today `speckit-orchestrate` ships immediately after `converged` / change tester PASS and treats pr-reviewer as on-demand. The spec’s done-when graph is `converge(converged) → critic → tester → ship → pr-review → uat`. Workers stay stage-dumb; only the parent sequences stages.
- **Alternatives considered**: Keep pr-reviewer on-demand (rejected by FR-003). Collapse critic into pr-reviewer (rejected by FR-016 / US6). Run critic on the change path (rejected by FR-025).

## Decision: LOOP_BACK is a parseable field; parent routing is exclusive

- **Decision**: Critic and PIVS tester compact reports keep PASS/FAIL (and tester `EVIDENCE`) and add `LOOP_BACK: implement | plan | none`. PASS always uses `none`. FAIL with only implement-target findings → converge then implement↔converge then critic→tester. FAIL with any plan-target finding → park (mixed report parks). Missing `LOOP_BACK` on FAIL: tester assertion/code failures → `implement`; explicit spec/plan contradiction → `plan`; still ambiguous → park.
- **Rationale**: Prose loop-back already exists in critic/tester rules (“Implement” vs “Plan”) but the parent cannot parse chat. A third field avoids inventing a new verdict enum.
- **Alternatives considered**: Parent infers target from finding text (fragile). Separate FIX loop that skips converge (forbidden by FR-007). Treat mixed FAIL as implement (rejected: plan-target wins).

## Decision: REQUEST CHANGES with zero Criticals is APPROVE for the loop

- **Decision**: Parent routes on Critical count, not the raw string `REQUEST CHANGES`. `CRITICAL_COUNT: 0` (Warnings/Suggestions only) → same as APPROVE: UAT park, no converge, no change retry. `CRITICAL_COUNT ≥ 1` → feature: converge with those Criticals as `$ARGUMENTS`; change: change worker + FINDINGS. BLOCKED (Phase 1.5) parks; not a REQUEST CHANGES retry.
- **Rationale**: Merge gate is already Critical-only (changelog 0.2.3). Looping on Warnings would contradict FR-019.
- **Alternatives considered**: Start a fix cycle on any REQUEST CHANGES (rejected in clarify). Auto-merge on APPROVE (forbidden).

## Decision: Same-PR ship is parent-owned reuse, not a second `gh pr create`

- **Decision**: First successful ship on a run opens the PR. After a post-review (or post-validator) validation PASS, the parent commits, pushes the same `BRANCH`, refreshes `## Walkthrough` / `## Evidence` on that PR, and keeps the same URL. Never open a second PR for the same run. Workers never ship.
- **Rationale**: Clarify chose “re-run parent ship with same-PR reuse.” Existing ship always `gh pr create`, which would fork the review surface.
- **Alternatives considered**: Worker-owned amend/push (forbidden). Close and reopen PR (loses review thread). Skip ship and ask the operator to push (breaks automatic re-review).

## Decision: Re-review uses existing `--extra` previous-report

- **Decision**: Parent saves the pr-reviewer report artifact from the last pass and relaunches pr-reviewer with that path as `--extra` (existing SKILL “Re-review”). No new review protocol.
- **Rationale**: FR-020. Avoid a second reviewer skill.
- **Alternatives considered**: Diff-only informal re-read (loses Critical tracking). Paste the previous report into chat without `--extra` (not the documented path).

## Decision: Converge fingerprint adds validator IDs without new source-ref kinds

- **Decision**: Keep converge source-refs as spec/plan/constitution only (`FR-###`, `US1/AC2`, `plan: …`, `Constitution …`). Validator IDs appear in task descriptions as `[tester: flow-2]`, `[critic: C1]`, `[pr-review: C1]`. `FINGERPRINT` is sorted source-refs plus sorted validator IDs (see contracts). Three attempts (original + two resumes) on an unchanged fingerprint parks. If converge reports `converged` while a validator FAIL is still open, the parent parks and does not re-enter critic/tester/pr-review.
- **Rationale**: FR-013 vs FR-014. Putting `[pr-review: C1]` in the source-ref slot would invent a fourth source-ref kind.
- **Alternatives considered**: New `FINDING_IDS:` compact field (extra parser surface). Treat validator IDs as source-refs (forbidden). Count every critic FAIL as a new stuck point (oscillates).

## Decision: Tiny converge `$ARGUMENTS` convention only

- **Decision**: Parent passes validator Criticals in the converge worker’s `$ARGUMENTS` as a FINDINGS list (id, severity, summary, suggested spec/plan source-ref). Converge prompt (`.pi/prompts/speckit.converge.md` when present) gets at most a short “when `$ARGUMENTS` lists validator Criticals…” paragraph: append remaining work, map to spec/plan/constitution source-refs, put validator ids in the description, include those ids in `FINGERPRINT`. No wholesale prompt rewrite. If the worktree has no converge prompt, the parent `$ARGUMENTS` text is still the contract; do not add a second converge skill.
- **Rationale**: FR-021.
- **Alternatives considered**: Parent appends `tasks.md` itself (forbidden). Feed Criticals to implement (forbidden). Copy converge into AiNative agents (out of scope).

## Decision: Documentation-only product surface; leftover “on-demand” outside the in-scope list stays

- **Decision**: Implement only the spec **In Scope** files (plus critic/tester `AGENTS.md` if those folders already document the compact report, matching 001). Changelog **0.4.0** in `AiNative/CHANGELOG.md` only. Host Cursor/OpenCode skills that symlink/mount AiNative change with the canonical files; do not maintain a divergent copy. Do not edit Hermes/`personalAgent`. Known leftovers that still say “pr-reviewer is on-demand, not a loop state”: `agentic-coding.md`, `agentic-system.md`, `docs/agents/README.md`, `prd-writer/SKILL.md`, and possibly `pr-reviewer/AGENTS.md` — **out of this spec’s file list**. Do not expand scope to “fix every mention.”
- **Rationale**: FR-021, FR-023, SC-009 applies to listed canonical files.
- **Alternatives considered**: Sweep the whole AiNative tree (YAGNI vs spec; spec file list wins during implement, but the list is explicit). Dual changelog at playground root (forbidden).

## Decision: ANALYZE after plan

- **Decision**: `ANALYZE: yes`. Compact-report fields, parent routing tables, fingerprint, same-PR ship, and critic vs pr-review split cut across feature-loop, orchestrate, critic, tester, pr-reviewer, change, and converge `$ARGUMENTS`.
- **Rationale**: Plan-stage rule: yes for cross-cutting contracts.
- **Alternatives considered**: Skip analyze (would miss field-name drift across eight surfaces).

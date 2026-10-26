# Implementation Plan: Agentic validation loop

**Branch**: `agentic-validation` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-agentic-validation/spec.md` (operator `skip`; decisions in spec **Clarifications**). Spec Kit feature directory: `specs/002-agentic-validation` (do not infer from git branch).

**Note**: Filled by `/speckit.plan`. Do not create `tasks.md` in this stage.

## Summary

Make feature-loop Validation agentic: after `CONVERGE_OUTCOME: converged` the parent runs critic → tester → ship → automatic pr-review → existing UAT. Implement-target FAILs and PR Criticals enter the existing converge loop (append-only `tasks.md`); plan-target and mixed FAILs park; zero-Critical REQUEST CHANGES routes as APPROVE; post-fix ship reuses the same PR. Change path stays tester-only with FINDINGS retries; job never runs pr-review. Documentation and parent dispatcher contracts in the spec in-scope list; changelog 0.4.0; no Hermes runtime, no new fix loop, no auto-merge.

## Technical Context

**Language/Version**: Markdown methodology + parent skill contracts (AiNative). No application runtime.

**Primary Dependencies**: None new. Reuse existing critic/tester/pr-reviewer/change/orchestrate skills and Spec Kit converge `$ARGUMENTS`.

**Storage**: Compact-report artifacts and previous pr-review markdown on disk for `--extra`; no new database. Spec dir from `.specify/feature.json`.

**Testing**: Post-implement validation via [quickstart.md](./quickstart.md) ripgrep checks and tabletop routing (SC-001–SC-009). Proof types for this feature: CLI/job and logic.

**Target Platform**: Spec Kit / speckit-orchestrate parent (Cursor Task / OpenCode / Hermes-linked docs). Workers: Validation profile for critic, tester, pr-reviewer.

**Project Type**: Methodology documentation cross-cutting Validation, Ship, and PR review.

**Performance Goals**: N/A (doc/skill edits). Stuck policy remains three attempts.

**Constraints**: Parent dispatcher-only (FR-017); workers stage-dumb and never write `tasks.md` (FR-015); no critic on change (FR-025); no job pr-review (FR-009); no auto-merge (FR-004); `.pi/prompts` except tiny converge `$ARGUMENTS` (FR-021); changelog only `AiNative/CHANGELOG.md` 0.4.0 (FR-023); FEATURE_DIR ≠ BRANCH (FR-024).

**Scale/Scope**: ~12 markdown files in AiNative + this feature’s contracts; no packages.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an **unfilled template**. No project-specific constitution gates apply. Spec FRs are the binding constraints.

| Gate | Status |
|------|--------|
| Library-first / TDD / CLI constitution examples | N/A — template not ratified; documentation/contracts only |
| New dependencies | Pass — none |
| Simplicity / YAGNI | Pass relative to constitution; **spec/tasks outrank YAGNI during implement** (FR-022): smallest diff that satisfies the spec, not a smaller product that leaves pr-review on-demand |
| Parent vs worker | Pass — parent routes; workers remain dumb |
| Hermes runtime | Pass — out of scope (FR-021) |

**Post-design re-check**: Pass. Entities are dispatcher/report fields; contracts are markdown. No runtime schema. Cross-cutting compact-report names require **ANALYZE: yes**.

## Project Structure

### Documentation (this feature)

```text
specs/002-agentic-validation/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── compact-reports.md
│   ├── parent-routing.md
│   └── same-pr-ship.md
└── tasks.md             # /speckit.tasks — not created in plan stage
```

### Source (implementation targets)

```text
AiNative/
├── CHANGELOG.md         # 0.4.0
└── docs/
    ├── systems/
    │   ├── feature-loop.md
    │   ├── validation-layer.md
    │   └── pr-review-system.md
    └── agents/
        ├── speckit-orchestrate/   # SKILL.md, rule.md
        ├── critic/                # SKILL.md, rule.md (+ AGENTS.md if it restates compact reports)
        ├── tester/                # SKILL.md, rule.md (+ AGENTS.md if needed)
        ├── pr-reviewer/           # SKILL.md, rule.md
        └── change/SKILL.md

# optional tiny edit only
.pi/prompts/speckit.converge.md   # $ARGUMENTS convention for validator Criticals
```

**Structure Decision**: Single AiNative documentation tree. Contracts live in this feature dir. Host skill mirrors that symlink/mount AiNative change with the canonical files; do not write a second copy. Do not edit `agentic-coding.md` / `agentic-system.md` / `docs/agents/README.md` unless a later spec expands the file list (known leftover “on-demand” wording — [research.md](./research.md)).

## Complexity Tracking

No constitution violations requiring justification.

---

## Execution plan

Work items ordered so compact-report and graph strings land first (parent parsers must not drift).

| ID | Work item | Primary files | FRs |
|----|-----------|---------------|-----|
| W1 | **Feature-loop graph + compact reports**: `converge(converged) → critic → tester → ship → pr-review → uat`; pr-review is a loop state after Ship; LOOP_BACK; converge fingerprint includes validator IDs; source-ref rule; FEATURE_DIR. | `feature-loop.md` | FR-001, FR-010, FR-013, FR-014, FR-016, FR-024 |
| W2 | **Orchestrate parent**: insert critic→tester before ship; automatic pr-review after `SHIP: ok`; routing table; same-PR ship; keep-local skips pr-review; Validation profile includes pr-reviewer; mermaid; change/job exceptions; mixed LOOP_BACK park; converged+open FAIL park. | `speckit-orchestrate/SKILL.md`, `rule.md` | FR-002–009, FR-011–012, FR-017–020, FR-025 |
| W3 | **Critic + PIVS tester**: compact `LOOP_BACK`; workers never write `tasks.md`; implementation review remains required before tester; feature-path only. | `critic/`, `tester/` | FR-010, FR-011, FR-015, FR-016 |
| W4 | **pr-reviewer**: parseable `VERDICT` / `CRITICAL_COUNT` header; loop-state (not on-demand-only on feature/change after Ship); re-review `--extra`; Critical-only merge gate unchanged; architecture/risk/evidence job. | `pr-reviewer/SKILL.md`, `rule.md`, `pr-review-system.md` | FR-003, FR-004, FR-016, FR-019, FR-020 |
| W5 | **Change path**: document no critic; FINDINGS retry for tester FAIL and Critical REQUEST CHANGES; same-PR ship; three-attempt stuck. | `change/SKILL.md`, orchestrate (W2) | FR-008, FR-025 |
| W6 | **Validation-layer copy**: critic→tester required; pr-review after Ship as loop state; keep critic vs pr-review split. | `validation-layer.md` | FR-001, FR-016, FR-018 |
| W7 | **Converge `$ARGUMENTS`**: tiny paragraph if `.pi/prompts/speckit.converge.md` exists; parent already passes Criticals. | converge prompt (optional), orchestrate prompt text | FR-005, FR-007, FR-014, FR-021 |
| W8 | **Changelog 0.4.0**. | `AiNative/CHANGELOG.md` | FR-023 |

**Blast radius**: Markdown / skill text. Readers: parent orchestrator, Validation workers, operators. No Hermes/`personalAgent` code. No new agents. No auto-merge.

**Agent boundaries**: Implement worker edits W1–W8. Parent already owns ship — document reuse. Converge remains the only writer of `tasks.md`.

**Reuse decision**: **In-repo** — extend existing graph and compact contracts. No new reviewer skill, no new fix loop.

**Known current-doc conflicts to resolve while implementing**:

- `feature-loop.md` / `validation-layer.md` / orchestrate mermaid: pr-reviewer “on-demand tool after Ship, not a loop state” and ship immediately after `converged` — replace on in-scope files.
- Orchestrate feature path never launches critic/tester today — insert them.
- Ship always `gh pr create` — add reuse when a run already has a PR.
- Critic/tester loop-back is prose only — add `LOOP_BACK`.
- Converge `FINGERPRINT` is source-refs only — append validator IDs without new source-ref kinds.
- Leftover on-demand wording outside the in-scope list: leave it (research).

---

## Acceptance criteria

Done-conditions for **this feature’s documentation deliverable**:

| ID | Criterion | Spec |
|----|-----------|------|
| AC-1 | Feature graph and orchestrate steps are `critic → tester → ship → pr-review → uat` after `converged`. | FR-001, FR-002, FR-003 |
| AC-2 | Critic and PIVS tester compact reports include `LOOP_BACK`; parent routing matches [parent-routing.md](./contracts/parent-routing.md). | FR-010, FR-011 |
| AC-3 | REQUEST CHANGES with Criticals → converge (feature) or FINDINGS (change); zero Criticals → UAT as APPROVE; BLOCKED parks. | FR-005, FR-006, FR-008, FR-019 |
| AC-4 | Same-PR ship documented; re-review uses `--extra` previous report. | FR-020 |
| AC-5 | Fingerprint includes validator IDs; source-refs stay spec/plan/constitution; validators never write `tasks.md`. | FR-013, FR-014, FR-015 |
| AC-6 | Change: no critic; job: no pr-review; keep-local: no ship/pr-review/UAT. | FR-009, FR-018, FR-025 |
| AC-7 | Critic implementation review still required before tester; pr-reviewer is architecture/risk/evidence after Ship. | FR-016 |
| AC-8 | `AiNative/CHANGELOG.md` has **0.4.0**. | FR-023 |
| AC-9 | [quickstart.md](./quickstart.md) checks pass. | SC-001–SC-009 |

## Test flows (for later critic/tester of this feature)

| ID | Flow | Proof | What it proves |
|----|------|-------|----------------|
| TF-1 | Graph string rg | CLI/job | SC-001, AC-1 |
| TF-2 | LOOP_BACK rg | CLI/job | SC-004, AC-2 |
| TF-3 | Routing + same-PR rg | CLI/job | SC-002, SC-003, AC-3, AC-4 |
| TF-4 | Fingerprint / source-ref rg | CLI/job | SC-006, AC-5 |
| TF-5 | Path isolation rg | CLI/job | SC-007, AC-6 |
| TF-6 | Critic vs pr-review rg | CLI/job | SC-008, AC-7 |
| TF-7 | Changelog 0.4.0 | CLI/job | SC-009, AC-8 |
| TF-8 | Tabletop routing | logic | SC-002–SC-007 |

## ANALYZE

**yes** — compact-report contracts, parent routing, fingerprint, and same-PR ship cut across feature-loop, orchestrate, critic, tester, pr-reviewer, change, and converge `$ARGUMENTS`; run speckit.analyze before large edits to catch field-name drift and leftover “on-demand-only” on in-scope files.

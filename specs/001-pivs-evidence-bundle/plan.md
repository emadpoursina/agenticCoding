# Implementation Plan: PIVS evidence bundle

**Branch**: `pivs-evidence-bundle` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-pivs-evidence-bundle/spec.md` (operator `skip`; decisions in spec **Clarifications**). Spec Kit feature directory: `specs/001-pivs-evidence-bundle`.

**Note**: Filled by `/speckit.plan`. Do not create `tasks.md` in this stage.

## Summary

Add commit-tied, acceptance-criterion–mapped **file evidence** to the PIVS loop without replacing PR + walkthrough + UAT. Plans declare a proof type per test flow; critic fails orphan criteria and non-Playwright UI labels; tester writes command-produced captures under `specs/<flow>/evidence/` plus a Markdown table at `specs/<flow>/evidence.md`; enrolled-project docs require PR CI to re-run `validation_commands` and upload bulky files as workflow artifacts (GitHub Actions example only); Ship adds PR `## Evidence` beside `## Walkthrough`; pr-reviewer audits completeness, SHA freshness vs PR head, and CI job success. Documentation-only in listed `AiNative/` paths — no new agents, loop states, dependencies, or Hermes runtime.

## Technical Context

**Language/Version**: Markdown documentation (AiNative methodology). No application runtime.

**Primary Dependencies**: None new (FR-012). UI proof references Playwright built-ins only (trace, video, screenshots).

**Storage**: Local `specs/<flow>/evidence.md` + `specs/<flow>/evidence/`; CI workflow artifacts for bulky files; both evidence paths gitignored.

**Testing**: Post-implement validation via [quickstart.md](./quickstart.md) ripgrep checks and tabletop prompt review (SC-001–SC-006). Proof types for this feature’s own flows: CLI/job and logic.

**Target Platform**: Spec Kit / speckit-orchestrate parent + PIVS workers (Cursor, OpenCode, Hermes-linked docs).

**Project Type**: Methodology documentation cross-cutting Plan, Validation, Ship, and on-demand pr-reviewer.

**Performance Goals**: N/A (doc edits). Git history stays small (no traces in commits).

**Constraints**: Workers never commit, push, or open PRs (FR-013); do not modify `agy-spawn.py` (FR-015); scope limited to the spec in-scope file list (FR-011); secrets redacted from API dumps (FR-013a); changelog only in `AiNative/CHANGELOG.md` (FR-014).

**Scale/Scope**: ~10 markdown files + changelog; contracts in this feature dir.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an **unfilled template** (placeholder principles, no ratified version). No project-specific constitution gates apply. Spec FRs are the binding constraints.

| Gate | Status |
|------|--------|
| Library-first / TDD / CLI constitution examples | N/A — template not ratified; this change is documentation-only |
| New dependencies | Pass — none (FR-012) |
| Simplicity / YAGNI | Pass — extend existing agent/system docs; no new agents, states, or evidence products |
| Workers ship | Pass — parent Ship only (FR-013) |
| `agy-spawn.py` | Pass — listed out of scope (FR-015) |

**Post-design re-check**: Pass. Entities are files and compact-report fields; contracts are markdown; no runtime schema or new parser in the parent.

## Project Structure

### Documentation (this feature)

```text
specs/001-pivs-evidence-bundle/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── evidence-manifest.md
│   ├── compact-reports.md
│   ├── plan-test-flow-proof.md
│   └── evidence-audit.md
└── tasks.md             # /speckit.tasks — not created in plan stage
```

### Source (implementation targets)

```text
AiNative/
├── CHANGELOG.md
└── docs/
    ├── systems/
    │   ├── feature-loop.md
    │   ├── validation-layer.md
    │   └── pr-review-system.md
    └── agents/
        ├── tester/                 # SKILL.md, rule.md, AGENTS.md
        ├── _skills/test-execution/SKILL.md
        ├── critic/                 # plan proof-type check
        ├── speckit-orchestrate/SKILL.md   # Ship / UAT
        └── pr-reviewer/            # prompts (+ overview in pr-review-system)
```

**Structure Decision**: Single AiNative documentation tree. Contracts live in the feature spec dir for implementer reference. No new packages, services, or enrolled-repo workflow files.

## Complexity Tracking

No constitution violations requiring justification.

---

## Execution plan

Work items ordered for compact-report parity first (FR-010) so later skills cannot drift.

| ID | Work item | Primary files | FRs |
|----|-----------|---------------|-----|
| W1 | **Feature-loop compact reports**: tester `EVIDENCE: <path>`; Ship `EVIDENCE: included\|none`; keep existing fields. | `feature-loop.md` | FR-010, FR-005, FR-008 |
| W2 | **Tester + test-execution**: manifest table, artifact dirs, full replace, FAIL still writes, `EVIDENCE` field, secrets redaction, loop-back full-bundle regenerate, optional fail-before pointer. | `tester/SKILL.md`, `tester/rule.md`, `tester/AGENTS.md`, `_skills/test-execution/SKILL.md` | FR-003–005, FR-003a–b, FR-004, FR-013a, FR-016 |
| W3 | **Plan + critic**: proof-type enum; blocking orphan / missing type / non-Playwright UI. | `critic/SKILL.md`, `critic/rule.md`, `critic/AGENTS.md` | FR-001, FR-002, FR-012 |
| W4 | **Validation layer + CI**: vendor-neutral PR CI re-run of `validation_commands`, Playwright capture for UI, workflow artifact upload, GitHub Actions **example snippet only**, gitignore both evidence paths, optional fail-before. | `validation-layer.md` (feature-loop may cross-link) | FR-006, FR-006a, FR-016 |
| W5 | **Ship / UAT**: PR `## Evidence` beside `## Walkthrough`; compact `EVIDENCE`; do not wait for CI. | `speckit-orchestrate/SKILL.md` | FR-007, FR-008, FR-013 |
| W6 | **pr-reviewer**: evidence audit (completeness, stale SHA, CI job success, claimed but unproven, re-run after fix push). | `pr-reviewer/prompts.md` (and skill/rules if they list stages), `pr-review-system.md` | FR-009 |
| W7 | **Changelog**: Keep a Changelog entry (recommend `0.3.0`). | `AiNative/CHANGELOG.md` | FR-014 |

**Blast radius**: Markdown only. Readers: parent orchestrator, Validation workers, operators. No Hermes/`personalAgent` code. Do not edit `agy-spawn.py`.

**Agent boundaries**: Implement worker edits W1–W7. Parent Ship already owns PR create — document only. pr-reviewer remains on-demand, not a loop gate.

**Reuse decision**: **In-repo** — extend existing tester/critic/Ship/pr-reviewer docs and feature-loop compact contracts. No new library or third-party evidence product.

**Known current-doc conflicts to resolve while implementing**:

- Tester re-verification says “re-run only the failed flows” — keep execution hint if useful, but evidence files must be a **full** regeneration (spec assumption **Replace on re-run**).
- Tester output is chat “Evidence:” prose — add on-disk bundle + compact `EVIDENCE:` path without dropping PASS/FAIL.
- Ship requires `## Walkthrough` only — add `## Evidence` without demoting walkthrough.

---

## Acceptance criteria

Done-conditions for **this feature’s documentation deliverable**:

| ID | Criterion | Spec |
|----|-----------|------|
| AC-1 | Tester and test-execution skills require `specs/<flow>/evidence/` captures and `specs/<flow>/evidence.md` Markdown table per `contracts/evidence-manifest.md`, including FAIL persistence and full regeneration. | FR-003, FR-003a–b, FR-004 |
| AC-2 | Tester compact report documents `EVIDENCE: <manifest path>` without removing PASS/FAIL. | FR-005 |
| AC-3 | Critic plan-review is a **blocking** fail for orphan criteria, missing proof type, or UI without Playwright. | FR-001, FR-002, FR-012 |
| AC-4 | Plan-stage guidance lists four proof types and artifact shapes. | FR-001 |
| AC-5 | `validation-layer.md` (and/or feature-loop) documents CI re-run, Playwright capture for UI, workflow uploads, gitignore of both evidence paths, GitHub Actions example, vendor-neutral rule. | FR-006, FR-006a |
| AC-6 | Ship mandates `## Evidence` next to `## Walkthrough` and `EVIDENCE: included\|none`; walkthrough stays mandatory. | FR-007, FR-008 |
| AC-7 | `feature-loop.md` compact-report section matches tester and Ship `EVIDENCE` fields. | FR-010 |
| AC-8 | pr-reviewer docs define evidence audit: stale SHA, CI disagreement (fail/skip/unfinished), missing artifacts → blocking “claimed but unproven”; re-runnable after fix pushes. | FR-009 |
| AC-9 | `AiNative/CHANGELOG.md` has a new entry; `agy-spawn.py` untouched. | FR-014, FR-015 |
| AC-10 | Secrets: API redaction + UI secret warning in tester/validation docs; evidence uncommitted. | FR-013a |
| AC-11 | Optional fail-before / pass-after is documented and not mandatory. | FR-016 |
| AC-12 | `quickstart.md` checks pass after implementation. | SC-001–SC-006 |

---

## Validation layer

### Critic (post-implement doc review of this change)

| Check | Type | PASS signal | FAIL signal |
|-------|------|-------------|-------------|
| FR coverage | Requirement trace | FR-001–FR-016 addressed in listed files | Orphan FR or files outside scope |
| Compact parity | Consistency | `EVIDENCE` fields align across feature-loop, tester, Ship | Mismatched names or values |
| Walkthrough preserved | Regression | UAT walkthrough still mandatory | Evidence replaces walkthrough |
| Scope | Guard | No `agy-spawn.py`, no new deps/states/agents | FR-011/012/015 violation |
| Secrets | Security | Redaction + warning present | API dumps documented without redaction |

**Heuristic risks**: Drift if Cursor/OpenCode skill copies are not the AiNative files (implement only listed AiNative paths). Manifest path vs branch name — implementers MUST use `.specify/feature.json` basename.

### Tester (this feature)

No application tests. **quickstart.md** is the executable script (**CLI/job**). Tabletop reads are **logic**.

| Flow | Role | PASS |
|------|------|------|
| QF-1 Compact parity | CLI/job | Quickstart §2 |
| QF-2 Manifest + secrets | CLI/job | §§3, 8 |
| QF-3 Proof type + critic | CLI/job | §4 |
| QF-4 Ship + pr-reviewer | CLI/job | §§5–6 |
| QF-5 CI + changelog + fail-before | CLI/job | §§7, 9–10 |

---

## Test flows

### TF-1: Compact-report parity (AC-7, AC-2, AC-6)

- **Maps to**: AC-7, AC-2, AC-6
- **Proof type**: CLI/job
- **Role**: system (doc cross-check)
- **Steps**: Run quickstart §2; compare `feature-loop.md` vs tester vs speckit-orchestrate for `EVIDENCE`.
- **Command(s)**: `rg -n 'EVIDENCE:' …` (quickstart §2)
- **Expected artifacts**: `specs/001-pivs-evidence-bundle/evidence/tf1-rg.txt` (transcript) after this feature ships; during implement, command exit 0 is the proof.
- **Expected**: Tester path form; Ship `included|none`; no dropped fields.

### TF-2: Evidence manifest contract in skills (AC-1, AC-10)

- **Maps to**: AC-1, AC-10
- **Proof type**: logic
- **Role**: unit
- **Steps**: Read tester + test-execution skills vs `contracts/evidence-manifest.md`.
- **Expected**: FR-003 columns; FR-003a–b; redaction of `Authorization`.

### TF-3: Critic plan gate (AC-3, AC-4)

- **Maps to**: AC-3, AC-4
- **Proof type**: logic
- **Role**: unit
- **Steps**: Tabletop — (a) Plan missing proof type on one AC; (b) UI label with non-Playwright commands.
- **Expected**: Blocking finding names the orphan criterion; UI case tells Plan to use CLI/job or logic.

### TF-4: Ship Evidence section (AC-6)

- **Maps to**: AC-6
- **Proof type**: logic
- **Role**: unit
- **Steps**: Read Ship / UAT procedure.
- **Expected**: `## Walkthrough` and `## Evidence` both mandatory; compact `EVIDENCE`; PR open does not wait for CI.

### TF-5: pr-reviewer stale SHA and CI agreement (AC-8)

- **Maps to**: AC-8
- **Proof type**: logic
- **Role**: system
- **Steps**: Tabletop — manifest at `S_old`, PR head `S_new`; then PASS claim with unfinished CI.
- **Expected**: Stale rows; unfinished CI is claimed but unproven; same rules on a second pass after a fix push.

### TF-6: Scope, CI docs, changelog (AC-5, AC-9, AC-11)

- **Maps to**: AC-5, AC-9, AC-11
- **Proof type**: CLI/job
- **Steps**: `git diff --name-only` against base; quickstart §§7, 9–10.
- **Expected**: No `agy-spawn.py`; gitignore both evidence paths; GitHub Actions example; optional fail-before; changelog entry.

### Edge / error paths (documentation)

- Tester FAIL: manifest still written (TF-2).
- Missing evidence on PASS: Ship `EVIDENCE: none`; pr-reviewer blocking (TF-4, TF-5).
- Change-path thin Plan: critic still requires proof types for listed criteria (TF-3).
- Accidental `git add` of evidence: ignore guidance in validation-layer (TF-6).

---

## Commit plan

Atomic Conventional Commits; implement worker does not commit unless the operator later asks the parent Ship. Suggested split:

| Commit | Scope | Contents |
|--------|-------|----------|
| 1 | `docs(loop): evidence compact-report fields` | W1 |
| 2 | `docs(tester): evidence bundle and secrets` | W2 |
| 3 | `docs(critic): proof-type plan gate` | W3 |
| 4 | `docs(validation): CI re-proof and gitignore` | W4 |
| 5 | `docs(orchestrate): ship evidence section` | W5 |
| 6 | `docs(pr-reviewer): evidence audit` | W6 |
| 7 | `docs(ainative): changelog for evidence bundle` | W7 |

Parent Ship may squash per loop policy.

---

## Phase artifacts (plan stage)

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/](./contracts/) |
| Quickstart | [quickstart.md](./quickstart.md) |

**Analyze stage**: **yes** — compact-report contracts and evidence-audit rules cut across feature-loop, orchestrate, tester, critic, and pr-reviewer; analyze before large edits to catch field-name drift.

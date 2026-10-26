# Quickstart: validating the PIVS evidence bundle docs

Runnable checks for the **documentation deliverable** (no production application code). Run from repository root after implementation.

## Prerequisites

- Git worktree on branch `pivs-evidence-bundle` (feature dir `specs/001-pivs-evidence-bundle`)
- `rg` (ripgrep)

## 1. In-scope file touch list

```bash
git diff --name-only origin/main...HEAD 2>/dev/null | sort
```

Expected includes subsets of:

- `AiNative/docs/systems/feature-loop.md`
- `AiNative/docs/systems/validation-layer.md`
- `AiNative/docs/systems/pr-review-system.md`
- `AiNative/docs/agents/tester/` (`SKILL.md`, `rule.md`, `AGENTS.md`)
- `AiNative/docs/agents/_skills/test-execution/SKILL.md`
- `AiNative/docs/agents/critic/`
- `AiNative/docs/agents/speckit-orchestrate/SKILL.md`
- `AiNative/docs/agents/pr-reviewer/` (prompts)
- `AiNative/CHANGELOG.md`

Must **not** include `AiNative/docs/agents/antigravity-harness/agy-spawn.py` (FR-015).

## 2. Compact-report parity (SC-004, FR-010)

```bash
rg -n 'EVIDENCE:' AiNative/docs/systems/feature-loop.md \
  AiNative/docs/agents/tester/ AiNative/docs/agents/_skills/test-execution/ \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md
```

**Pass**: Tester uses path form (`EVIDENCE: specs/<flow>/evidence.md` or equivalent). Ship uses `included|none`. Existing PASS/FAIL and `WALKTHROUGH` fields remain.

## 3. Manifest contract documented (FR-003, FR-003a–b)

```bash
rg -n 'evidence\.md|Acceptance criterion|specs/\*/evidence' \
  AiNative/docs/agents/tester/ AiNative/docs/agents/_skills/test-execution/ \
  specs/001-pivs-evidence-bundle/contracts/evidence-manifest.md
```

**Pass**: Table columns match FR-003; skills require captures under `specs/<flow>/evidence/`; FAIL still writes rows; each run replaces the bundle.

## 4. Proof type + critic gate (SC-003, FR-001, FR-002)

```bash
rg -n 'proof type|Playwright' AiNative/docs/agents/critic/
```

**Pass**: Critic plan review treats missing proof type / orphan criterion as **blocking**, and fails UI proof without Playwright commands.

## 5. Ship Evidence section (FR-007, FR-008, SC-005)

```bash
rg -n '## Evidence|EVIDENCE: included|## Walkthrough' \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md
```

**Pass**: Ship requires `## Evidence` beside mandatory `## Walkthrough`; compact report includes `EVIDENCE: included|none`.

## 6. pr-reviewer audit (SC-002, FR-009)

```bash
rg -n 'evidence audit|claimed but unproven|stale' \
  AiNative/docs/agents/pr-reviewer/ AiNative/docs/systems/pr-review-system.md
```

**Pass**: Completeness, SHA vs PR head, CI job success (not byte match), and re-check after fix pushes are documented as blocking when unproven.

## 7. CI + gitignore + vendor example (FR-006, FR-006a, SC-006)

```bash
rg -n 'validation_commands|workflow artifact|GitHub Actions|specs/\*/evidence' \
  AiNative/docs/systems/validation-layer.md AiNative/docs/systems/feature-loop.md
```

**Pass**: Vendor-neutral re-run requirement; recommended ignore of `specs/*/evidence/` **and** `specs/*/evidence.md`; one GitHub Actions snippet; no committed enrolled-repo workflow files.

## 8. Secrets (FR-013a)

```bash
rg -n 'Authorization|redact' AiNative/docs/agents/tester/ \
  AiNative/docs/systems/validation-layer.md AiNative/docs/agents/_skills/test-execution/
```

**Pass**: API dumps must redact credentials/`Authorization`; UI traces/screenshots warned as possible secrets.

## 9. Optional fail-before / pass-after (FR-016)

```bash
rg -n 'fail-before|merge-base' AiNative/docs/systems/validation-layer.md \
  AiNative/docs/agents/tester/ AiNative/docs/agents/_skills/test-execution/
```

**Pass**: Optional procedure documented; not required for every flow.

## 10. Changelog (FR-014)

```bash
head -25 AiNative/CHANGELOG.md
```

**Pass**: New SemVer entry describes the evidence-bundle documentation (recommend `0.3.0`).

## Tabletop: end-to-end story

1. Planner drafts test flows with proof types for each AC.
2. Critic rejects a plan missing a proof type, or labeling UI without Playwright.
3. Tester runs flows, writes `specs/<flow>/evidence/*` and `evidence.md`, redacts API tokens, emits `EVIDENCE: specs/<flow>/evidence.md`.
4. Ship copies the table into PR `## Evidence` (does not wait for CI), emits `EVIDENCE: included`.
5. pr-reviewer on a fix push flags stale SHA until tester re-runs; unfinished CI is claimed but unproven.

Expected outcome: operator can satisfy SC-001 from the PR without reading tester chat logs.

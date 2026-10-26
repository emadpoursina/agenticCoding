# Quickstart: validating the agentic validation loop docs

Runnable checks for the **documentation / dispatcher-contract** deliverable. Run from repository root after implementation. Proof types: CLI/job (ripgrep) and logic (tabletop). No production application.

## Prerequisites

- Worktree whose Spec Kit feature dir is `specs/002-agentic-validation` (read `.specify/feature.json`; do not infer from git branch `agentic-validation`)
- `rg` (ripgrep)

## 1. In-scope file touch list

```bash
git diff --name-only origin/main...HEAD 2>/dev/null | sort
```

Expected includes subsets of:

- `AiNative/docs/systems/feature-loop.md`
- `AiNative/docs/systems/validation-layer.md`
- `AiNative/docs/systems/pr-review-system.md`
- `AiNative/docs/agents/speckit-orchestrate/SKILL.md`
- `AiNative/docs/agents/speckit-orchestrate/rule.md`
- `AiNative/docs/agents/critic/` (`SKILL.md`, `rule.md`; `AGENTS.md` if compact-report text lives there)
- `AiNative/docs/agents/tester/` (`SKILL.md`, `rule.md`; same for `AGENTS.md`)
- `AiNative/docs/agents/pr-reviewer/SKILL.md` and `rule.md`
- `AiNative/docs/agents/change/SKILL.md`
- `AiNative/CHANGELOG.md` (0.4.0)

Must **not** require Hermes runtime files, `agy-spawn.py`, or a playground-root changelog. `.pi/prompts/speckit.converge.md` may appear only as a tiny `$ARGUMENTS` paragraph.

## 2. Feature graph (SC-001, FR-001, FR-003)

```bash
rg -n 'critic → tester → ship → pr-review → uat|on-demand-only|on-demand tool after Ship' \
  AiNative/docs/systems/feature-loop.md \
  AiNative/docs/systems/validation-layer.md \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md
```

**Pass**: Live graph and orchestrate mermaid/steps show critic → tester → ship → pr-review → uat on the feature path. Feature-loop and validation-layer no longer describe pr-reviewer as on-demand-only for that path. Job path still skips pr-review.

## 3. Compact-report LOOP_BACK (SC-004, FR-010, FR-011)

```bash
rg -n 'LOOP_BACK:' \
  AiNative/docs/systems/feature-loop.md \
  AiNative/docs/agents/critic/ \
  AiNative/docs/agents/tester/ \
  specs/002-agentic-validation/contracts/compact-reports.md
```

**Pass**: Critic and PIVS tester document `implement | plan | none`. PASS uses `none`. Mixed FAIL parks. Change-path tester skill has no `LOOP_BACK` requirement.

## 4. Parent routing + same-PR (SC-002, SC-003, FR-005, FR-008, FR-019, FR-020)

```bash
rg -n 'same-PR|CRITICAL_COUNT|keep-local|LOOP_BACK: plan' \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md \
  AiNative/docs/agents/speckit-orchestrate/rule.md \
  specs/002-agentic-validation/contracts/parent-routing.md \
  specs/002-agentic-validation/contracts/same-pr-ship.md
```

**Pass**: Orchestrate launches critic then tester after `converged`; pr-reviewer after `SHIP: ok`; zero-Critical REQUEST CHANGES routes as APPROVE; Criticals go to converge (feature) or FINDINGS (change); same-PR reuse; `keep-local` skips ship and pr-review.

## 5. Fingerprint + source-refs (SC-006, FR-013, FR-014, FR-015)

```bash
rg -n 'FINGERPRINT|source-ref|\[pr-review:|\[critic:|\[tester:' \
  AiNative/docs/systems/feature-loop.md \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md \
  specs/002-agentic-validation/contracts/compact-reports.md
```

**Pass**: Fingerprint includes validator IDs. Source-refs stay spec/plan/constitution. Validators never write `tasks.md`.

## 6. Path isolation (SC-007, FR-009, FR-025)

```bash
rg -n 'no critic|MUST NOT run pr-reviewer|STEP: tester' \
  AiNative/docs/agents/change/SKILL.md \
  AiNative/docs/agents/speckit-orchestrate/SKILL.md \
  AiNative/docs/systems/feature-loop.md
```

**Pass**: Change path: tester only, FINDINGS retry, no converge. Job: no pr-review.

## 7. Critic vs pr-review split (SC-008, FR-016)

```bash
rg -n 'implementation review|architecture, risk, and evidence' \
  AiNative/docs/agents/critic/ \
  AiNative/docs/agents/pr-reviewer/ \
  AiNative/docs/systems/validation-layer.md
```

**Pass**: Critic still required before tester on the feature path. pr-reviewer remains architecture/risk/evidence after Ship.

## 8. Changelog (SC-009, FR-023)

```bash
rg -n '^## \[0\.4\.0\]' AiNative/CHANGELOG.md
```

**Pass**: Keep a Changelog entry **0.4.0** for this work.

## 9. Tabletop (logic)

Walk [contracts/parent-routing.md](./contracts/parent-routing.md) against SC-002–SC-007. Expected:

1. Happy path: no extra operator prompt between `converged` and UAT except the existing UAT pass/fail.
2. REQUEST CHANGES with Criticals: converge before implement; same PR; `--extra` previous report.
3. REQUEST CHANGES with zero Criticals: UAT park, no converge.
4. Implement-target tester FAIL: next worker is converge; plan-target and mixed: park.
5. `converged` + open FAIL: park.
6. Same finding ID three times: park.
7. Change REQUEST CHANGES: no `tasks.md`; job ship: no pr-reviewer.

## Done

All rg checks pass and the tabletop matches the contract. Browser verification is N/A (docs only).

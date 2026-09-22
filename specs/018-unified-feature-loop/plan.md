# Implementation Plan: Unified feature loop (Hermes stages + Pi per step)

**Branch**: `018-unified-feature-loop` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-unified-feature-loop/spec.md`

## Summary

Replace Hermes (`personalAgent`) live execution — today one whole-playbook
Pi run (`speckit-orchestrate`) followed by a shell validation phase — with
a Hermes-owned overlay state machine whose graph is exactly the canonical
feature loop in `AiNative/docs/systems/feature-loop.md` (Ready → specify →
clarify → confirm → plan → tasks → optional analyze → implement ↔ converge
→ critic → tester → UAT → pr-review → publish). Every agent state starts a
**new** Pi session that knows only that step; `confirm`, `uat`, and
`publish` never start Pi. Human gates stay in Hermes via the existing
Telegram park/resume. Publish (commit/push/PR on the feature branch) happens
only after tester pass → UAT pass → pr-review PASS. The one-shot playbook,
whole-playbook resume, and `_run_validation` as the GitHub gate are removed
from the live path. Methodology stays in AiNative; Hermes docs **link** to
`/ainative/docs/systems/feature-loop.md`. Cursor `/speckit-orchestrate` is
untouched.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv (Hard Constraint)

**Primary Dependencies**: Existing Hermes stdlib-only stack (sqlite3 kanban,
subprocess Pi adapter, aiohttp/stdlib services). Ready agent = promoted
AiNative `docs/agents/ready/` (added in this change per FR-011, modeled on
`~/.cursor/skills/speckit-ready`). No new external dependencies.

**Storage**: Existing `kanban.db` (only task SoT) + overlay workflow records
(already persisted there — no second database). Spec Kit artifacts live in
the task worktree under `specs/<task-id>/`.

**Testing**: pytest + ruff (workspace default check tools). Existing hermetic
tests in `personalAgent/tests/` must keep passing; new tests use fixture Pi
runtimes (no network, no real Pi process).

**Target Platform**: Docker container `personal-agent` on the Mac host
(`~/.hermes/personal-agent` isolated home; `/ainative` read-only mount;
`/workspaces/<project>` enrolled projects).

**Project Type**: CLI/service orchestration control plane (no UI).

**Performance Goals**: Not latency-bound; one concurrent workflow slot as
today. Per-state Pi timeout from existing `harness.timeout_seconds`.

**Constraints**: No provider/model names hardcoded (model routing stays in
Hermes config per state). Pi never publishes. No protected-branch pushes.
No merge/deploy. AiNative read-only. Worktrees isolated per task.

**Scale/Scope**: Single-user personal install. Scope = `personalAgent` repo
only: `src/hermes_kanban/{orchestrator,executor,external_framework,pi,ainative}.py`,
`AGENTS.md`, `README.md`, `docs/context/SYSTEM.md`, tests; plus AiNative doc
pointers and `docs/agents/ready/` promotion (apply checklist §1), plus
supersede banners on specs 011/012/013/014 (§4).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Spec-First | PASS | This feature is itself the spec→plan→tasks flow; the runtime being built enforces Spec Kit order. |
| II. Least Code | PASS | Net deletion expected: one-shot playbook path, whole-playbook resume, `_run_validation` gate. State machine replaces the existing phase machine in `orchestrator.py`, not a new control plane. |
| III. Platform-Native | PASS | Reuses kanban.db, worktrees, Telegram park/resume, GitHub skills, existing Pi adapter. No second task DB. AiNative stays read-only; methodology linked, not copied (FR-010). |
| IV. Trust-Boundary Tests | PASS | Compact reports from Pi are external input → strict parsing at the boundary (existing `_coerce_response` pattern extended per-state). New hermetic tests: per-state session starts, prompt leakage, human park, converge loop, no-publish-before-pr-review. |
| V. Human Authority | PASS (strengthened) | Today's shell `_run_validation` gate is weaker than the constitution requires; this change puts critic → tester → UAT (human) → pr-review before any publish, and parks after pr-review for operator decision. Publish remains feature-branch-only PR, no merge. |

**Tension resolved by design**: FR-008 lets the *Pi tester* run project
`validation_commands` (agents executing shell commands). This stays within
Principle V because the tester runs inside the isolated feature worktree,
never pushes, and its PASS/FAIL is only one gate among critic/UAT/pr-review
before Hermes (the parent, not the agent) touches GitHub.

Post-design re-check: PASS — see Complexity Tracking.

**Complexity Tracking — dated, scoped constitution exception (Principle III):**

> 2026-09-21, human decision on the 018 Analyze critical finding: during this
> one-time development pass, editing AiNative **inside this repo**
> (`docs/agents/ready/` promotion, `docs/systems/feature-loop.md` one-line
> edit, live-pointer updates per the apply checklist) is an accepted
> development-time source fix while the system is being built. The AiNative
> read-only principle continues to apply at **Hermes runtime**: the
> `/ainative` mount stays read-only and running Hermes workers must not
> modify it. This exception is not permission for Hermes runtime to write
> AiNative.

**Decision note — encode-answers (no new product behavior):** clarify
answers are encoded by a **second clarify Pi session** (a new session with
the same `clarify` step id, answers carried in the resume context). It is
**not** a new LoopState; no `encode-answers` state exists on the graph.
T017 is aligned with this wording and with `contracts/state-graph.md`.

## Project Structure

### Documentation (this feature)

```text
specs/018-unified-feature-loop/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output — extended validation guide (pre-seeded from spec phase)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── state-graph.md       # States, transitions, stuck policy
│   ├── harness-request.md   # Per-step harness start request
│   └── compact-reports.md   # Parseable per-state report schemas
├── checklists/
│   └── requirements.md  # Spec-quality checklist (spec phase)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Single existing package — no new top-level projects.

```text
personalAgent/
├── AGENTS.md                        # Dispatcher text rewrite; link to /ainative/docs/systems/feature-loop.md
├── README.md                        # Same rewrite posture
├── docs/context/SYSTEM.md           # Reference copy; align with AGENTS.md
├── src/hermes_kanban/
│   ├── external_framework.py        # HarnessStartRequest: playbook id → step id + skill path; strict result validation
│   ├── pi.py                        # Pi adapter: one RPC run per agent state; per-state prompt (no later-step leakage)
│   ├── orchestrator.py              # Overlay state machine: ready…publish; human gates; converge loop; park policy
│   ├── executor.py                  # Remove role map (discovery/planning/implementation/validation), playbook config, _run_validation-as-gate; step-id dispatch; tester passes validation_commands
│   ├── ainative.py                  # Read-only adapter: resolve agent states (ready/critic/tester/pr-reviewer) to docs/agents/<name>/
│   └── github.py                    # Unchanged posture: feature-branch commit/push/PR only, after pr-review PASS
└── tests/
    ├── test_legacy_stage_removal.py # Extended: refuse whole-playbook jobs (SC-002)
    ├── test_piv_orchestrator.py     # Replaced by state-machine tests
    └── (new) test_feature_loop_states.py, test_prompt_isolation.py, test_human_gates.py, test_publish_gate.py
```

**Structure Decision**: Extend the existing `src/hermes_kanban` package in
place. The overlay phase machine already lives in `orchestrator.py`
(`current_phase`: execution/human/validation/github); it is generalized from
4 phases to the canonical state graph. No new modules beyond what the
per-step prompt/report parsing needs.

## Complexity Tracking

> No constitution violations to justify — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | | |

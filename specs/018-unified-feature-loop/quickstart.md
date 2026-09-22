# Quickstart — 018 (Hermes slice)

Hand this to an implementing agent. **Cursor is out of scope.**

1. Read `AiNative/docs/systems/feature-loop.md` — especially **Hermes
   runtime (what to build)**.
2. Read `spec.md` — apply checklist §2 only (personalAgent).
3. Link `/ainative/docs/systems/feature-loop.md` from `AGENTS.md`. Do
   not paste the graph into Hermes.
4. Remove live one-shot Pi playbook `speckit-orchestrate`.
5. Prove with fixture Pi: new session per agent state; no Pi for
   confirm, UAT, publish; critic→tester→UAT→pr-review before GitHub.

## Validation scenarios (run after implementation)

Prerequisites: `personalAgent` repo checkout, `uv` with Python 3.12,
existing hermetic test suite passing (`uv run pytest` in `personalAgent/`).
All scenarios use the fixture Pi runtime already injected by the tests —
no real Pi process, no network, no Docker, no Telegram.

### V1 — Per-state session starts (SC-001, US1)

Run the state-machine tests (`pytest tests/test_feature_loop_states.py`,
or the equivalent new tests). Fixture Pi records every start
(step id + session handle).

**Expected**: one recorded start per agent state — `ready`, `specify`,
`clarify`, `plan`, `tasks`, `implement`, `converge`, `critic`, `tester`,
`pr-review` — each with a **distinct** session handle; zero starts for
`confirm`, `uat`, `publish`. Order matches the graph. The clarify detour
(park → relay → new encode session) and the implement↔converge loop
(`tasks_appended` → fresh implement session) are covered here.

### V2 — No later-step leakage in prompts (FR-004, US1/AC3)

Run the prompt-isolation tests. For each recorded start, inspect the
prompt sent to the fixture runtime.

**Expected**: the prompt names only that step and its skill path; no
prompt instructs Pi to "then run clarify/plan/implement…". Any request
carrying a playbook id (`speckit-orchestrate`) or a non-agent state
(`confirm`/`uat`/`publish`) is refused outright (SC-002: 100% refusal).

### V3 — Human gates park and resume (US2)

Drive the fixture through clarify-with-questions, then `confirm`, then
tester-pass → `uat`.

**Expected**: record parks `HUMAN_DECISION_REQUIRED` on clarify; after
recorded answers a **new** Pi session encodes them and `confirm` still
runs before `plan` (including under operator `skip`). UAT presents a
feature-derived QA checklist and starts no Pi session.

### V4 — Critic before publish (US3, FR-007/FR-009)

Fixture converge reports `converged`; GitHub publish path is invoked
only after critic PASS → tester PASS → uat pass → pr-review PASS.

**Expected**: no commit/push/PR is attempted before pr-review PASS;
publish runs only on the feature branch. After pr-review completes
(PASS or FAIL) the record parks — no auto-loop into implement or
re-validation (FR-016).

### V5 — Legacy removal (FR-005, FR-012, SC-002)

Run the extended `tests/test_legacy_stage_removal.py`.

**Expected**: no live dispatch path accepts a whole-playbook job; config
no longer defines `harness.playbook`; in-flight `013` whole-playbook
overlay records park for a human instead of resuming the old machine;
`_run_validation` no longer unlocks GitHub.

### V6 — Docs agree (SC-003, US4)

```bash
grep -rn "speckit-orchestrate" personalAgent/AGENTS.md personalAgent/README.md
grep -rn "feature-loop" personalAgent/AGENTS.md
```

**Expected**: `AGENTS.md` links `/ainative/docs/systems/feature-loop.md`
and describes one Pi session per agent state; no live-path sentence says
execution is one Pi playbook or forbids Hermes-owned stages. Specs 011–
014 carry the supersede banner; Cursor `/speckit-orchestrate` is
untouched (`git status` shows no Cursor changes).

Full-suite gate: `uv run pytest && uv run ruff check .` passes in
`personalAgent/` (SC-004).

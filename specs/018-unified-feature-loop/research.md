# Phase 0 Research: 018-unified-feature-loop (Hermes slice)

Methodology SoT: `AiNative/docs/systems/feature-loop.md` (linked, never
copied). All NEEDS CLARIFICATION items from the spec's clarification session
are already resolved in `spec.md`; this file records the remaining
**technical** decisions needed before design.

## R1. How does the overlay state machine represent the canonical graph?

**Decision**: Generalize the existing overlay workflow record
(`orchestrator.py`: `current_phase` ∈ {execution, human, validation, github})
to carry the canonical state ids: `ready`, `specify`, `clarify`, `confirm`,
`plan`, `tasks`, `analyze`, `implement`, `converge`, `critic`, `tester`,
`uat`, `pr-review`, `publish`, plus the terminal/park states
(`HUMAN_DECISION_REQUIRED`, `BLOCKED`, `PR_CREATED`, `DONE`). Keep one
`WorkflowRecord` per task in `kanban.db` (overlay already persisted there).

**Rationale**: The graph lives in AiNative; Hermes owns only *current
state + advance/retry/park*. Reusing the record type avoids a migration and
keeps "one task database" (Principle III). Terminal transition table becomes
data (one dict), not scattered phase branches.

**Alternatives considered**:
- New state-machine module/database — rejected: second store, forbidden.
- Keep 4 phases and encode steps inside "execution" — rejected: cannot
  prove SC-001/SC-002 (per-state starts, refusal of whole-playbook).

## R2. Harness request: playbook id → per-step request

**Decision**: Replace `harness_playbook` ("speckit-orchestrate") with a
**step start**: `{step_id, skill_path, inputs, report_schema}`. 
`external_framework.py` drops the single `PLAYBOOK_ID` constant; request
validation refuses any request whose `step_id` is not on the canonical
graph, and `pi.py`'s RPC prompt names **only** that step and its skill path
(FR-004). Config `harness.playbook` is removed; `harness.timeout_seconds`
and `harness.model_profile` defaults stay.

**Rationale**: FR-002/FR-005/FR-014. The executor's existing one-request-
one-run transport (`pi.py` `_run_process`, one RPC prompt per process) is
already "new process per run" — the change is that the request is one step,
not a whole playbook, so each agent state naturally gets a fresh process.

**Alternatives considered**:
- Keep playbook id and pass a step hint inside the prompt — rejected: the
  prompt would still say "run the playbook"; leakage risk FR-004.
- Reuse Cursor Task slugs — rejected: Hermes has no Task runtime; models
  per step stay in Hermes config (Assumptions).

## R3. Whole-playbook removal posture (FR-005, FR-012, FR-014)

**Decision**: Same removal posture `013` used against the old short path:
- `speckit-orchestrate` disappears from `executor.py` defaults, config
  handling, resume/recovery paths, and prompt text.
- Resume after a human answer restarts **the named step** (or its successor
  for clarify-answers / confirm), never the whole flow.
- In-flight `013` whole-playbook overlay records are detected (old phase
  names / playbook id in record) and parked `HUMAN_DECISION_REQUIRED` with
  a "superseded by 018" diagnostic; they are not auto-migrated (Edge Case 1).
- `test_legacy_stage_removal.py` extended: any dispatch path given a
  whole-playbook job must refuse it (SC-002).

**Alternatives considered**: Auto-migrating parked runs onto the new graph —
rejected by spec (human must acknowledge).

## R4. `_run_validation` → tester inputs (FR-008)

**Decision**: Delete the shell gate. `ProjectContext.validation_commands`
become **inputs** on the tester step request; the Pi tester (AiNative
`docs/agents/tester/`) runs them inside the worktree and returns its
existing PASS/FAIL compact contract. Hermes parses only the report; it does
not execute the commands itself (explicit clarification).

**Rationale**: Tester runs *or includes* project checks — no parallel
parent "validation phase" that skips agents. `github.py` unlock condition
becomes: critic PASS ∧ tester PASS ∧ UAT pass ∧ pr-review PASS.

**Alternatives considered**: Keeping `_run_validation` as a fast pre-check —
rejected: it is the exact gate FR-005/FR-008 remove.

## R5. Ready agent resolution (FR-011)

**Decision**: Promote the Ready agent into AiNative as
`AiNative/docs/agents/ready/` (modeled on `~/.cursor/skills/speckit-ready`,
same folder contract as `critic/tester/pr-reviewer`: `AGENTS.md`/`SKILL.md`/
`rule.md`). Hermes resolves `ready` via the existing `AiNativeAdapter` like
any other AiNative agent. The "global speckit-ready" Hermes map-only option
is removed; `feature-loop.md` documents the single Ready agent (one-line
edit of the ready row's "global speckit-ready" mention).

**Rationale**: One Ready definition in AiNative; read-only adapter already
validates folder completeness (`IncompleteAgentError`). Runtime mount
`/ainative` stays read-only; the promotion is a development-time repo edit
in this workspace.

**Alternatives considered**: Keeping two Ready sources — rejected by
clarification.

## R6. Human gates and relays (FR-006, FR-015, FR-016)

**Decision**:
- `clarify` questions (`STATUS: blocked` + question queue) park as
  `HUMAN_DECISION_REQUIRED`; Hermes relays one question at a time over the
  existing Telegram path; after answers a **new** Pi session encodes them;
  `confirm` is then a parent↔human continuation (no Pi) before `plan`.
- `uat`: Hermes derives the QA checklist from the feature's test path
  (converge report / quickstart) and presents it; operator pass/fail. No Pi,
  no failure-state machine, no auto-loop.
- `pr-review` completion (PASS or FAIL) parks for operator decision; Hermes
  never auto-loops into implement/re-validation afterwards.

**Rationale**: Matches existing `_park_*` + Telegram machinery; context
stays small (US2).

**Alternatives considered**: UAT failure state machine — deferred by
clarification (V0 is simple human QA).

## R7. Converge loop and stuck policy

**Decision**: `converge` report `CONVERGE_OUTCOME` drives:
- `tasks_appended` (with new work) → start a **new** `implement` session;
- unchanged `FINGERPRINT` → stuck → park;
- `blocked` → park immediately.
Per-step retry budget: three attempts (original + two resumes), then park;
stable `READY: blocked` is never retried; missing spec/plan/tasks artifacts
are not retried. This is the `feature-loop.md` stuck policy verbatim —
linked, not restated, in Hermes docs.

**Rationale**: Existing bounded-retry recovery generalizes per state.

## R8. Compact reports (boundary parsing)

**Decision**: Extend `external_framework.py` result validation with the
per-state compact fields from `feature-loop.md` ("Compact reports" section):
Ready (`READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES`),
Spec Kit step reports (`STATUS: ok|stuck|blocked`, `ARTIFACTS`, `SUMMARY`,
plan adds `ANALYZE: yes|no`), implement (`IMPLEMENT_STATUS`, `TASKS_DONE`,
`TASKS_OPEN`, `BLOCKER`), converge (`CONVERGE_OUTCOME`, `FINDINGS`,
`FINGERPRINT`, `TASKS_APPENDED`), critic/tester/pr-reviewer (existing
PASS/FAIL contract). Malformed/missing fields = step failure (trust
boundary), same posture as today's `_coerce_response`.

**Rationale**: The parent parses reports, never chat prose (SC-002 posture;
Principle IV).

## R9. Model routing per state

**Decision**: Hermes `config.yaml` gains a per-step model-profile mapping
(ready/specify/…/pr-review) replacing the planning/implementation/validation
slots; provider/model names stay in config only (Hard Constraint). Unknown
step in the map → fail closed at startup.

**Alternatives considered**: Pulling Cursor Task slugs into the container —
rejected (Assumptions).

## R10. Docs linkage and supersede banners

**Decision**:
- `personalAgent/AGENTS.md`, `README.md`, `docs/context/SYSTEM.md`:
  dispatcher-only text; link `/ainative/docs/systems/feature-loop.md`;
  delete "one speckit-orchestrate playbook" and "do not restore
  Hermes-owned stages" lines.
- AiNative (development-time edits, apply checklist §1): point
  `agentic-coding.md`, `systems/README.md`, `docs/README.md`,
  `ENGINEERING-OS.md`, `piv-gate.mdc`, `ai-rules.mdc`, `cursor-rules.md`,
  `ai-rules-template.md` at the feature loop as live; mark PIV historical;
  `docs/agents/README.md` lists Ready/critic/tester/pr-reviewer as live;
  add `docs/agents/ready/`.
- Specs `011`, `012`, `013`, `014`: banner on live-path sections —
  superseded by 018 for execution shape. No scenario rewrites.
- Cursor `/speckit-orchestrate` and `/pi-harness`: untouched (FR-013).

**Rationale**: Original bug was three written loops; SC-003 requires no
contradictory live loop on the operator path.

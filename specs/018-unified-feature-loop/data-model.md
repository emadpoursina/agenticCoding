# Phase 1 Data Model: 018-unified-feature-loop (Hermes slice)

All entities live in the existing `personalAgent` package; persistence stays
in the overlay records of `kanban.db`. No new stores.

## Entities

### 1. LoopState (enum, data)

One node on the canonical graph in `AiNative/docs/systems/feature-loop.md`.
Hermes stores the id string only; the graph definition is linked, not copied.

- Values: `ready`, `specify`, `clarify`, `confirm`, `plan`, `tasks`,
  `analyze`, `implement`, `converge`, `critic`, `tester`, `uat`,
  `pr-review`, `publish`
- Plus non-graph record states already present: `QUEUED`, `RUNNING`,
  `RETRYABLE_FAILURE`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`, `PR_CREATED`,
  `DONE`

**Kind** (per state, from the linked table):
- `agent` → starts a new Pi session: ready, specify, clarify, plan, tasks,
  analyze, implement, converge, critic, tester, pr-review
- `human` → never starts Pi: confirm, uat
- `parent` → Hermes/GitHub only: publish

**Validation rules**:
- `step_id` on any harness request MUST be an `agent`-kind state; a request
  for `confirm`/`uat`/`publish` is invalid (FR-006).
- `analyze` runs only if the `plan` report returned `ANALYZE: yes`.

### 2. WorkflowRecord (existing, extended)

Overlay record for one Kanban task. Persisted in `kanban.db`.

| Field | Type | Change |
|---|---|---|
| `run_id` | str | unchanged |
| `state` | str | unchanged set (RUNNING/PARK/…) |
| `current_phase` | str | now a `LoopState` id (was execution/human/validation/github) |
| `current_worker` | str | step's agent (`ready`…`pr-reviewer`) or `""` for human/parent states |
| `steps` | tuple[StepRecord] | one StepRecord per **session start** (state + worker + summary) |
| `attempt` / retry budget | int | per-state: 3 attempts (original + two resumes), then park |
| `converge_fingerprint` | str \| None | last `FINGERPRINT` from converge; unchanged value ⇒ stuck |
| `uat_checklist` | list[str] \| None | feature-derived QA items presented at `uat` |
| `question_queue` | list[str] | clarify questions awaiting relay (existing park payload) |
| `playbook_id` | str | **removed** |

**State transitions** (advance edge from the linked graph; malformed report
or exhausted retries → park):

```text
ready → specify → clarify → confirm → plan → tasks → (analyze) → implement
implement ↔ converge            # tasks_appended → implement; fingerprint stuck → park
converge(converged) → critic → tester → uat → pr-review → publish
any state → HUMAN_DECISION_REQUIRED | BLOCKED
```

**Invariants**:
- No transition may skip critic, tester, uat, or pr-review before `publish`
  (FR-007/FR-009).
- After `pr-review` completes, next record state is a park — never
  `implement` or a re-run (FR-016).
- `publish` reached only with critic PASS ∧ tester PASS ∧ uat pass ∧
  pr-review PASS recorded in `steps`.

### 3. StepStartRequest (renamed/reshaped HarnessStartRequest)

What Hermes hands the Pi adapter. One instance per agent-state session.

| Field | Type | Notes |
|---|---|---|
| `step_id` | LoopState (agent kind) | validated against the graph |
| `skill_path` | str | AiNative `docs/agents/<name>/` for agent-kind states; Spec Kit skill path in the worktree for spec-kit states |
| `workspace_path` / `workspace_branch` | Path / str | isolated `feature/task-<id>` worktree (unchanged) |
| `model_profile` | str | resolved from config per step; never a literal model name |
| `timeout_seconds` | float | existing harness timeout |
| `inputs` | dict | step inputs on disk; tester includes `validation_commands` list (FR-008) |
| `operator_flags` | tuple[str] | e.g. `skip` (self-answer clarify; still confirm before plan) |
| `resume_context` | ResumeContext \| None | **per-step** resume only |

**Validation**: unknown `step_id`, non-agent state, missing skill path, or a
prompt/payload containing a later state's name as an instruction ⇒ rejected
at the boundary (FR-004, SC-002).

### 4. StepReport (per state)

Parseable compact report; the ONLY thing Hermes reads back.

| State(s) | Required fields |
|---|---|
| ready | `READY: ok\|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES` |
| specify, clarify, tasks, analyze | `FLOW_ID`, `ARTIFACTS`, `STATUS: ok\|stuck\|blocked`, `SUMMARY` |
| plan | above + `ANALYZE: yes\|no` |
| implement | `IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`, `SUMMARY` |
| converge | `CONVERGE_OUTCOME: converged\|tasks_appended\|blocked`, `FINDINGS`, `FINGERPRINT`, `TASKS_APPENDED`, `SUMMARY` |
| critic, tester, pr-reviewer | existing AiNative PASS/FAIL contract (parseable status required) |

Malformed/missing required fields ⇒ step failure (trust boundary), not
lenient defaults.

### 5. AgentDefinition (AiNative, read-only, existing)

Unchanged shape (`ainative.py`). Live resolution set becomes:
`ready` (promoted in this change), `critic`, `tester`, `pr-reviewer`.
`scout`, `plan-reviewer` stay optional/off-graph; `specs-planner`,
`builder` are not resolvable on the live path.

## Relationships

```text
KanbanCard 1─1 WorkflowRecord 1─* StepRecord (one per session start)
WorkflowRecord *─1 LoopState (current_phase)
StepStartRequest 1─1 StepReport (one Pi session per pair)
WorkflowRecord *─1 AgentDefinition (agent-kind states only)
```

## Migration / parking

Old `013` records (`current_phase` ∈ {execution, validation, github} or a
playbook id present) are detected at startup and parked
`HUMAN_DECISION_REQUIRED` with diagnostic "superseded by 018 — whole-
playbook run". No automatic conversion onto the new graph (FR-012).

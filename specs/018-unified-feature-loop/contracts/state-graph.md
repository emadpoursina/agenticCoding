# Contract: Hermes state graph (overlay state machine)

Owner: Hermes (`personalAgent/src/hermes_kanban/orchestrator.py`).
The graph itself is defined in `AiNative/docs/systems/feature-loop.md`
(§ Canonical state graph); this contract is only Hermes' runtime shape for
holding and advancing it.

## States and kinds

| step_id | kind | worker | Hermes behavior |
|---|---|---|---|
| `ready` | agent | AiNative `docs/agents/ready/` | preflight; `READY: blocked` parks (never retried) |
| `specify` | agent | Spec Kit skill (worktree) | new Pi session |
| `clarify` | agent | Spec Kit skill | questions → park → relay → **new** session encodes answers |
| `confirm` | human | — | one continuation; Hermes asks operator; no Pi (FR-006) |
| `plan` | agent | Spec Kit skill | parses `ANALYZE: yes\|no` |
| `tasks` | agent | Spec Kit skill | |
| `analyze` | agent | Spec Kit skill | only when plan said `ANALYZE: yes`; critical finding → park |
| `implement` | agent | Spec Kit skill | fresh session each pass |
| `converge` | agent | Spec Kit skill | loops with implement per outcome |
| `critic` | agent | AiNative `docs/agents/critic/` | required before tester |
| `tester` | agent | AiNative `docs/agents/tester/` | runs project `validation_commands` as inputs |
| `uat` | human | — | feature-derived QA checklist; operator confirms pass; no Pi (FR-006, FR-015) |
| `pr-review` | agent | AiNative `docs/agents/pr-reviewer/` | after UAT pass |
| `publish` | parent | Hermes + GitHub skills | commit/push/PR on feature branch only; no Pi (FR-006) |

## Transition table (advance edges)

```text
ready      → specify
specify    → clarify
clarify    → confirm          (after answers encoded; or self-answered under `skip`)
confirm    → plan             (operator continuation; `skip` still runs confirm)
plan       → tasks | analyze  (analyze iff plan report ANALYZE: yes)
tasks      → implement
implement  → converge
converge   → implement        (outcome tasks_appended with new work)
converge   → critic           (outcome converged)
converge   → park             (outcome blocked; or unchanged fingerprint = stuck)
critic     → tester           (retryable FAIL follows bounded retries)
tester     → uat              (pass)
uat        → pr-review        (operator confirms pass)
pr-review  → park             (PASS or FAIL — operator decides next; FR-016)
park       → publish          (operator approves after pr-review PASS; feature branch only)
```

## Guarantees

1. One Pi session per agent state; `confirm`, `uat`, `publish` never start
   Pi (FR-002, FR-006).
2. No whole-playbook dispatch exists; any such request is refused (FR-005,
   FR-014, SC-002).
3. Publish is reachable only through critic → tester → uat → pr-review PASS
   (FR-007, FR-009).
4. After pr-review, the machine parks; it never auto-loops (FR-016).
5. Stuck policy (per `feature-loop.md`, linked): 3 attempts per state, then
   park; stable `READY: blocked` and missing spec/plan/tasks artifacts are
   never retried.
6. In-flight `013` whole-playbook records park for a human (FR-012).

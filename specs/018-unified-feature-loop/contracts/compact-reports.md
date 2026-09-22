# Contract: Compact reports (Pi → Hermes, per state)

Owner: `personalAgent/src/hermes_kanban/external_framework.py` (strict
parsing), `pi.py` (RPC JSON). Shapes follow `AiNative/docs/systems/
feature-loop.md` § Compact reports (reusing `/speckit-orchestrate` report
shapes). Hermes parses these fields only — never worker chat prose.

## Common envelope

One JSON object as the final assistant message of the RPC run:

```json
{
  "status": "completed | failed | needs_human | stuck",
  "reason": "…",
  "report": { "<state-specific fields>" }
}
```

`status` maps as today (`question`→needs_human, `blocked`/`error`→failed on
the transport layer, etc.). Missing/extra envelope fields are rejected
(existing `_coerce_response` posture).

## State-specific `report` fields

| State | Required fields | Notes |
|---|---|---|
| ready | `READY: ok\|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES` | `blocked` parks; never retried |
| specify / clarify / tasks / analyze | `FLOW_ID`, `ARTIFACTS`, `STATUS: ok\|stuck\|blocked`, `SUMMARY` | clarify may return `questions: [...]` with blocked status |
| plan | above + `ANALYZE: yes\|no` | yes ⇒ analyze state runs |
| implement | `IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`, `SUMMARY` | |
| converge | `CONVERGE_OUTCOME: converged\|tasks_appended\|blocked`, `FINDINGS`, `FINGERPRINT`, `TASKS_APPENDED`, `SUMMARY` | unchanged `FINGERPRINT` ⇒ stuck ⇒ park |
| critic | existing AiNative critic PASS/FAIL contract | parseable status mandatory |
| tester | existing AiNative tester PASS/FAIL contract (+ ran `validation_commands` evidence) | commands were passed as inputs, run in-worktree |
| pr-reviewer | existing AiNative pr-review PASS/FAIL contract | PASS unlocks the publish park decision |

## Boundary rules

- Unknown fields in `report` for a state ⇒ malformed (fail, not ignore).
- A report missing required fields ⇒ step failure → retry/park policy.
- For critic/tester/pr-reviewer, narrative text without a parseable
  PASS/FAIL status is a failure ("parseable status, not only narrative").
- Hermes MUST NOT execute `validation_commands` as a substitute for, or in
  parallel to, the tester report (FR-008).

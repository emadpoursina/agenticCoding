# Contract: Per-step harness start request (Hermes → Pi adapter)

Owner: `personalAgent/src/hermes_kanban/external_framework.py` (validation),
`pi.py` (transport). Replaces the whole-playbook `HarnessStartRequest`.

## Shape

```json
{
  "step_id": "specify",
  "flow_id": "<flow_...>",
  "skill_path": "docs/agents/ready/ | .cursor/skills/speckit-specify/ ...",
  "workspace_path": "/workspaces/<project>/.worktrees/feature/task-<id>",
  "workspace_branch": "feature/task-<id>",
  "model_profile": "<name from config; never a provider/model literal>",
  "timeout_seconds": 1800.0,
  "inputs": {
    "task_id": "018-...",
    "validation_commands": ["uv run pytest", "uv run ruff check ."],
    "operator_flags": ["skip"]
  },
  "resume_context": null
}
```

## Rules

- `step_id` MUST be an agent-kind state on the canonical graph. Requests
  with `confirm`, `uat`, `publish`, or an unknown id are invalid (FR-006).
- `playbook_id` is gone. A request carrying a playbook id (e.g.
  `speckit-orchestrate`) is **refused**, not translated (FR-005, FR-014).
- `skill_path` resolves to exactly one skill/agent definition; the Pi prompt
  names **only** that step. If the prompt would instruct Pi to run a later
  state, the request is malformed (FR-004).
- One request ⇒ one new Pi process (`pi --mode rpc`), one compact report,
  then exit. Resume after a human answer resumes **this step only**
  (or its successor for clarify-answers/confirm) — never the whole flow.
- Safety constraints carried unchanged: write root = worktree, feature
  branch only, no publish/push/merge, no external writes, reject secrets.
- Tester requests carry the project's declared `validation_commands` as
  **inputs**; Hermes does not execute them itself (FR-008).

## Failure posture

Validation failures raise `HarnessValidationError` → step failure → normal
retry/park policy. No silent coercion of a playbook request into a step.

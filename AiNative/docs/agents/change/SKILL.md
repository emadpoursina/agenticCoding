---
name: change
description: >-
  Executes one small, already-specified code edit, then proves it with
  tests. Use when /speckit-orchestrate routes a task to the change path.
disable-model-invocation: true
---

# Change

<!-- canonical: AiNative docs/agents/change/ (promoted from Cursor change 2026-09-25). -->

The thin engineering path. No spec, plan, tasks, or converge loop. Validation is `STEP: tester` only (no critic, no `LOOP_BACK`).

```text
change → inspect → edit → tester → ship → pr-review → uat
```

The parent launches one worker per step and tells it which one:
`STEP: change` (inspect + edit) or `STEP: tester`. Do only the named step.
Validation remains `STEP: tester` only (no critic).

## Inputs (from the parent prompt)

- `REPO_ROOT`, `FLOW_ID`, `BRANCH`
- `STEP` — `change` or `tester`
- `TASK_DESCRIPTION` — user arguments verbatim
- `ATTEMPT` and prior tester findings, when this is a retry
- change report (`FILES`, `SUMMARY`), for the tester step

## Rules for the change path

- The change is already specified. If you have to decide what the behavior
  should be, it is not a change.
- Keep it small: the fewest files that satisfy the task. No new dependency,
  no new module, no public API, schema, or contract change.
- No architectural decisions. Follow the existing structure and style.
- Do not commit, push, open a pull request, or deploy.
- MUST NOT write `tasks.md` or run converge.
- Critic MUST NOT run on this path.
- On `keep-local`, tester still runs, but ship and pr-review are skipped (`SHIP: declined`).

If the task breaks any of these, stop and report `SCOPE: feature`. Do not
edit anything first. Do not promote yourself to the feature path.

## STEP: change

1. **Inspect** — read the files the task names and find the smallest place
   to make the change. Find the tests that cover that code.
2. **Edit** — make the change directly. Add or update a test when the change
   alters behavior and the project has tests for that area.
3. Run the relevant tests (not the whole suite unless it is quick) and fix
   what you broke.

On a retry, fix the tester findings you were given. Nothing else.

Report:

```text
FLOW_ID: <flow_id>
STATUS: ok | blocked | stuck
SCOPE: ok | feature
FILES: <files changed, or none>
TESTS: <commands run and result>
SUMMARY: <what changed and why; or why it is really a feature>
```

## STEP: tester

Fresh eyes. Do not edit source files.

1. Read the task and the change report. Read the diff (`git diff`).
2. Check the diff does what the task asked, and only that.
3. Run the relevant tests plus the project's lint/typecheck if it has one
   (use the commands the project documents in README, AGENTS.md,
   `package.json`, `pyproject.toml`, `Makefile`, or
   `.ainative/project.yaml` `validation_commands`).

Report:

```text
FLOW_ID: <flow_id>
TESTER: PASS | FAIL
TESTS: <commands run and result>
FINDINGS: <none, or one line each: file | problem | fix needed>
SUMMARY: <one paragraph>
```

Validation remains `STEP: tester` only (no critic, no `LOOP_BACK`).
On `TESTER: FAIL`, the parent retries the change worker with FINDINGS (three attempts then park). Never converge. Never append `tasks.md`. On `TESTER: PASS`, the parent ships unless `keep-local` was requested.

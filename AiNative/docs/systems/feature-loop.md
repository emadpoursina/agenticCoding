# Feature loop

Canonical live workflow for managed-project work. **Hermes** runs this graph
from the project's Kanban board. PIV agent definitions are stages on this
graph, not a second workflow.

Related: five-part model in [agentic-system.md](./agentic-system.md).
Historical PIV text: [agentic-coding.md](./agentic-coding.md) (do not use
it as the live stage list).

## Layers

One graph, one control-plane orchestrator, one worker runtime.

```text
AiNative feature-loop.md  ← the graph (this file)
        │
        └─ Hermes parent    ← personalAgent (Kanban / unattended)
              workers: one Pi session per agent state
```

Hermes owns state, dispatch, report checks, human relays, retries, and
publishing. A Pi worker executes only the one state Hermes assigned; it never
chooses the next state.

## Split of ownership

| Layer | Owns | Does not own |
|---|---|---|
| **AiNative** (this tree) | What the loop is. Which states exist. Which agent kind runs a state. Compact-report expectations. Human gates vs agent states. | Kanban, worktrees, Pi process, GitHub, Telegram, enrolled-project source. |
| **Spec Kit** (in the project) | How specify / clarify / plan / tasks / analyze / implement / converge write native artifacts. | The graph. Skip/confirm/UAT policy. Publish. |
| **Hermes parent** (`personalAgent`) | Kanban, current state, isolated task worktree, one worker per state, report checks, retries, human gates, Telegram, GitHub publish. | Following stage skills in-process; one-shot “run all of Spec Kit.” |
| **Pi worker** | Execute the **one** step Hermes named. Read that skill. Write artifacts. Return a compact report. Exit. | The flow. Next state. Skip/confirm/UAT policy. Publish. Merge. AiNative writes. |

## Agent and skill sources

To Hermes, each agent state is a named skill, artifacts, and a compact
report.

1. **AiNative agents** — folders under `docs/agents/`. Live required: Ready,
   critic, tester, and pr-reviewer. Other agents may be used by an explicitly
   named job or remain optional.
2. **Spec Kit** — project skills, normally stored under
   `.cursor/skills/speckit-{specify,clarify,plan,tasks,analyze,implement,converge}/SKILL.md`.
   Hermes/Pi reads these files as skill inputs; this does not require a Cursor
   runtime, command, or symlink.

Hermes maps each state to a skill path and starts **one** worker. It does not
run skills in-process.

## Executor rule

```text
Hermes: what state? → start a new Pi worker for that step only
Pi: do the step → compact report → exit
Hermes: check → next state, retry, or park for a human
```

- **New Pi process every agent state.** Never one process that runs Ready
  through converge.
- Worker prompts are stage-dumb: worktree, step name, skill path, inputs
  on disk, report schema. If the prompt says “then run clarify,” the
  playbook has leaked back in.
- Hermes never writes `spec.md`, `plan.md`, `tasks.md`, or application code
  from the parent process because “context is already loaded.”

## Hermes runtime

- Kanban is the only task source of truth. Hermes uses one concurrent slot,
  an isolated `feature/task-<id>` worktree, read-only `/ainative`, and the
  existing Telegram park/resume and GitHub PR paths.
- Hermes records internal states in its overlay; the board contains work
  cards, not cards for `ready`, `plan`, `tester`, or other internal stages.
- Every agent state starts one new Pi process with a one-step request and a
  compact report contract. Pi never publishes, pushes, merges, or deploys.
- A Feature Card uses the `task-generator` profile. After planning produces
  `tasks.md`, Hermes creates child Task Cards on the same board. Each child
  is independently executable by an `executor`; the parent stays open until
  all children are complete and feature-level validation passes.
- The feature-level critic/tester and operator gates belong to the parent
  Feature Card, not its child cards. UAT is an operator step in the current
  graph; its exact triggering and board presentation remain under active
  policy work.
- Keep project rules in `AGENTS.md` and project validation commands in
  `.ainative/project.yaml`. Hermes links to this file rather than copying
  the graph into its dispatcher instructions.

Do not rebuild Telegram or add a second task database. In-flight 013
whole-playbook overlays stay parked until a human acknowledges them.

## Card paths

After a project is enrolled, every unit of work is a Kanban card. The card
names its path. Hermes does not infer the path from the title or body.
A missing path is `feature`.

| Path | When | Graph |
|---|---|---|
| `feature` | A desired product outcome that needs a spec, plan, and review | The graph below; planning creates child Task Cards |
| `change` | A small code edit already specified by the card | `ready` → one worker → `tester` |
| `job` | Work that is not a code change (write a PRD, bootstrap from a PRD) | One worker for the named skill. It may park for a human. After the worker reports `STATUS: ok` it parks for the operator's publish decision: approval commits, pushes the job branch, and opens a pull request; decline completes without publishing. It does not enter the feature graph |

A `change` or `job` worker that finds the card is really a feature stops
and reports that. It does not promote itself onto the feature graph.

`change` does not run specify, clarify, confirm, plan, tasks, analyze,
implement/converge, critic, UAT, pr-review, or publish. `tester` runs the
project `validation_commands`. `ready` on a `change` is branch preflight
only.

## Canonical state graph

This graph is the `feature` path. Orchestrator-specific **edges** (not extra loops):

- **Hermes:** pick the Kanban card, isolate its worktree, surface human
  gates on the existing operator path, and publish to GitHub only after
  required reviews pass and the operator approves.

```text
ready
  → specify → clarify → confirm
  → plan → tasks → [analyze]
  → implement ↔ converge
  → critic → tester
  → uat
  → pr-review
  → publish
```

| State | Kind | Worker? | Notes |
|---|---|---|---|
| `ready` | AiNative [`docs/agents/ready/`](../agents/ready/) (promoted; the single Ready definition) | yes | Git/layout/branch preflight. Not scout. `READY: blocked` stops the run. |
| `specify` | Spec Kit | yes | |
| `clarify` | Spec Kit | yes | Questions return to the parent. Parent asks the operator. A **new** worker encodes answers. |
| `confirm` | parent ↔ human | **no** | One continuation before plan. Not an agent. |
| `plan` | Spec Kit | yes | No extra plan-approval gate. |
| `tasks` | Spec Kit | yes | |
| `analyze` | Spec Kit | yes | Only if plan returned `ANALYZE: yes`. Read-only. Critical finding = park. |
| `implement` | Spec Kit | yes | Parent loops with converge. Fresh worker each pass. |
| `converge` | Spec Kit | yes | `tasks_appended` (new work) → implement again. Unchanged fingerprint → stuck. Only `converged` exits the loop. |
| `critic` | AiNative | yes | Adversarial review of spec/plan/implementation. Required. After converge; not a “finish” report. |
| `tester` | AiNative | yes | Prove the flows. Project `validation_commands` run **here**, not as a parallel parent phase. Required. |
| `uat` | parent ↔ human | **no** | Operator exercises the feature (use converge/quickstart test path). Pass/fail confirmation; exact trigger/presentation policy is being refined. |
| `pr-review` | AiNative | yes | After UAT pass. |
| `publish` | parent / GitHub | **no** | Hermes commits/pushes and opens a PR on the feature branch only after operator approval; workers never publish. |

**Default publish order** (until explicitly changed): pr-review the
**branch**, then Hermes opens the PR. Do not open a PR and then treat
review as optional comments.

`skip` is an **operator flag**, not a skipped specify/clarify state.
Workers self-answer; the parent still shows the choice report and still
does `confirm` before plan.

## Compact reports

The parent parses these report fields; it does not scrape worker chat prose.

Ready: `READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES`.

Specify/clarify/plan/tasks/analyze: `FLOW_ID`, `ARTIFACTS`,
`STATUS: ok|stuck|blocked`, `SUMMARY`. Plan also: `ANALYZE: yes|no`.

Implement: `IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`,
`SUMMARY`.

Converge: `CONVERGE_OUTCOME: converged|tasks_appended|blocked`,
`FINDINGS`, `FINGERPRINT`, `TASKS_APPENDED`, `SUMMARY`.

Critic / tester / pr-reviewer: keep each agent’s existing PASS/FAIL
contract; the parent must get a parseable status, not only narrative.

## Stuck policy

Per step, three attempts (original + two resumes) then park.
Do not retry a stable `READY: blocked`.
Do not retry missing `spec.md` / `plan.md` / `tasks.md`.
`CONVERGE_OUTCOME: blocked` parks immediately.
Human questions are not stuck; they are `confirm` / clarify relay / `uat`.

## What this is not

- Scout → 5/10/20 questions → plan-reviewer → wait for plan approval →
  implement → critic → tester as the **live** path.
- One Pi identity that runs the whole Spec Kit playbook in a single session.
- A classifier that picks `feature` / `change` / `job` from card prose.
  The path is a field on the card.
- Hermes implementing Spec Kit stages in-process.
- Converge substituting for critic/tester/UAT.
- Duplicating this document into Hermes. Hermes **links** here
  (`/ainative/docs/systems/feature-loop.md`) and describes only
  dispatcher behavior.

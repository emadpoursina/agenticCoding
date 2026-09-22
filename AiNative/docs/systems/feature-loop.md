# Feature loop

Canonical live workflow for a full feature. This replaces homemade PIV as
the **loop every orchestrator runs**. PIV agents still exist; they are
states on this graph, not a second machine.

Related: five-part model in [agentic-system.md](./agentic-system.md).
Historical PIV text: [agentic-coding.md](./agentic-coding.md) (do not use
it as the live stage list).

**Apply slice:** change **Hermes** (`personalAgent`) to this graph. Cursor
`/speckit-orchestrate` already runs the parent pattern in the IDE; do
not edit it in the Hermes implementation pass.

## Layers

One graph. Two orchestrators. Worker backends are swappable.

```text
AiNative feature-loop.md     ← the graph (this file)
        │
        ├─ Cursor parent     ← /speckit-orchestrate (you in the IDE)
        │     workers: Cursor Task  OR  Pi via /pi-harness
        │
        └─ Hermes parent     ← personalAgent (Kanban / unattended)
              workers: Pi only
```

`/speckit-orchestrate` is **not** a third loop and **not** a Spec Kit
skill. It is the Cursor **parent**: same job as Hermes (state, dispatch,
check report, human relay, stuck policy). Do not copy this graph into
that skill; the skill may only add Cursor mechanics (Task slugs, Pi
fallback, `FLOW_ID`, chat relay).

`/pi-harness` is **not** an orchestrator. It is one **worker backend**:
spawn Pi, keep events on disk, return `report.json`. Hermes has its own
Pi adapter. A worker never learns the next state.

## Split of ownership

| Layer | Owns | Does not own |
|---|---|---|
| **AiNative** (this tree) | What the loop is. Which states exist. Which agent kind runs a state. Compact-report expectations. Human gates vs agent states. | Kanban, worktrees, Pi process, GitHub, Telegram, enrolled-project source. |
| **Spec Kit** (in the **project**) | How specify / clarify / plan / tasks / analyze / implement / converge write native artifacts. | The graph. Skip/confirm/UAT policy. Publish. |
| **Orchestrator** | Current state. Start/stop **one worker per agent state**. Check the report. Advance, retry, or park. Human gates. | Following any stage skill itself. One-shot “run all of Spec Kit.” |
| **Cursor parent** | `/speckit-orchestrate` in this chat. Chooses Task vs Pi per stage. Relays questions in the parent thread. Repo is usually the current workspace. | Writing spec/plan/tasks or implementing in the parent. |
| **Hermes parent** | `personalAgent`. Kanban, isolated `feature/task-<id>` worktree, Telegram park, GitHub publish. Always Pi. | Cursor Task. Running skills in-process. |
| **Worker** (Task or Pi) | Execute the **one** step the parent named. Read that skill. Write artifacts. Compact report. Exit. | The flow. Next state. Skip/confirm/UAT. Publish. Merge. AiNative writes. |

## Two agent kinds

Same thing to the orchestrator: a named state, a skill, artifacts, a
compact report.

1. **AiNative** — folders under `docs/agents/`. Live required: Ready
   (`docs/agents/ready/`, promoted), critic, tester, pr-reviewer.
   Optional later (not V0): scout, plan-reviewer.
2. **Spec Kit** — project skills
   `.cursor/skills/speckit-{specify,clarify,plan,tasks,analyze,implement,converge}/SKILL.md`.

The parent maps a state to a skill path and starts **one** worker. It
does not in-process run the skill.

## Executor rule

```text
Parent: what state? → start a new worker for that step only
Worker: do the step → compact report → exit
Parent: check → next state, retry, or park for a human
```

- **New worker every agent state** (new Cursor Task, or new Pi spawn via
  pi-harness / Hermes Pi adapter). Never one process that runs Ready
  through converge.
- Worker prompts are stage-dumb: worktree, step name, skill path, inputs
  on disk, report schema. If the prompt says “then run clarify,” the
  playbook has leaked back in.
- The parent never writes `spec.md`, `plan.md`, `tasks.md`, or
  application code because “context is already loaded.”

### Cursor worker choice

`/speckit-orchestrate` already: Luna-named stages prefer Cursor Task
(`gpt-5.6-luna-xhigh`); if that slug is missing, spawn Pi with
`/pi-harness`. Grok-named stages (`analyze`, `converge`) stay Task
(`cursor-grok-4.6-medium`); no silent model swap. Hermes has no Task
runtime, so every Hermes agent state is Pi.

Critic, tester, and pr-reviewer on Cursor use the same rule: one new
worker each (Task or Pi), AiNative skill path, compact PASS/FAIL. Do not
run them in the parent chat. **Hermes never uses Cursor Task.**

## Hermes runtime (what to build)

Keep: Kanban as only task SoT, one concurrent slot, isolated
`feature/task-<id>` worktree, read-only `/ainative`, Telegram
park/resume, GitHub feature-branch PR, no merge/deploy, Pi never
publishes.

**Add**

- Promoted Ready agent `docs/agents/ready/` (the single Ready definition).
- Overlay **state machine** with the graph below (`ready` … `publish`), with the graph below (`ready` … `publish`),
  not `execution` then shell `validation` then GitHub.
- Harness request = **one step id** + skill path + compact report. **New
  Pi process per agent state.**
- First state **Ready** (the promoted AiNative `docs/agents/ready/`).
- Spec Kit states as Hermes states, including implement↔converge and
  fingerprint stuck.
- **critic → tester → UAT → pr-review** then publish. Tester runs
  project `validation_commands`.
- `AGENTS.md` **links** this file; dispatcher text only.

**Remove** (live path only)

- One-shot Pi playbook `speckit-orchestrate` (whole specify…converge in
  one `pi --mode rpc`).
- Config treating `playbook: speckit-orchestrate` as “run the flow.”
- Resume that **restarts the whole playbook** after one human answer.
- `_run_validation` (project checks) as the gate that unlocks GitHub
  without critic/tester/UAT/pr-review.
- `AGENTS.md` line forbidding Hermes-owned stages / requiring one
  playbook.
- Live use of leftover roles `scout` / `specs-planner` / `builder`.
  Do not restore those agents.

Do not copy this graph into Hermes. Do not rebuild Telegram or a second
task DB. Park in-flight 013 whole-playbook overlays for a human.

## Card paths

After a project is enrolled, every unit of work is a Kanban card. The card
names its path. Hermes does not infer the path from the title or body.
A missing path is `feature`.

| Path | When | Graph |
|---|---|---|
| `feature` | Product work that needs a spec, a plan, and review | The graph below |
| `change` | A small code edit already specified by the card | `ready` → one worker → `tester` |
| `job` | Work that is not a code change (write a PRD, bootstrap from a PRD) | One worker for the named skill. It may park for a human. It does not enter the feature graph and it does not publish |

A `change` or `job` worker that finds the card is really a feature stops
and reports that. It does not promote itself onto the feature graph.

`change` does not run specify, clarify, confirm, plan, tasks, analyze,
implement/converge, critic, UAT, pr-review, or publish. `tester` runs the
project `validation_commands`. `ready` on a `change` is branch preflight
only.

## Canonical state graph

This graph is the `feature` path. Orchestrator-specific **edges** (not extra loops):

- **Hermes:** pick Kanban card, isolate worktree, Telegram for human
  gates, GitHub after pr-review.
- **Cursor:** current repo / branch from Ready, human gates in this
  chat, publish only if you asked (otherwise stop after pr-review with
  the test path).

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
| `uat` | parent ↔ human | **no** | Operator exercises the feature (use converge/quickstart test path). Pass/fail confirmation. |
| `pr-review` | AiNative | yes | After UAT pass. |
| `publish` | parent / GitHub | **no** | Hermes: commit/push/PR on the feature branch. Cursor: only if the operator asked; workers never publish. |

**Default publish order** (until explicitly changed): pr-review the
**branch**, then Hermes opens the PR. Do not open a PR and then treat
review as optional comments.

`skip` is an **operator flag**, not a skipped specify/clarify state.
Workers self-answer; the parent still shows the choice report and still
does `confirm` before plan.

## Compact reports

Reuse the `/speckit-orchestrate` report shapes. The parent parses these;
it does not scrape worker chat prose.

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
- One Pi identity `speckit-orchestrate` that runs the whole Spec Kit
  playbook (Hermes 013). The Cursor **command** `/speckit-orchestrate` is
  the parent, not that playbook.
- A classifier that picks `feature` / `change` / `job` from card prose.
  The path is a field on the card.
- Parent implementing Spec Kit stages in-process (Cursor or Hermes).
- `/pi-harness` owning skip/confirm/converge looping.
- Converge substituting for critic/tester/UAT.
- Duplicating this document into Hermes. Hermes **links** here
  (`/ainative/docs/systems/feature-loop.md`) and describes only
  dispatcher behavior.

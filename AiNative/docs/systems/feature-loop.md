# Feature loop

Target workflow for managed-project work. **Hermes** is the control plane and
the project's Kanban board holds the work. PIVSA agent definitions are stages on
this graph, not a second workflow.

> **Status: target methodology — not wired into the current install.**
> The current Hermes install has no worker loop running. Runtime mechanics are
> owned by Hermes (`personalAgent`), not by this file. See
> [harness.md](../knowledge/setup/harness.md) and the
> [fresh-Hermes rebuild ADR](../records/decisions/2026-09-fresh-hermes-rebuild.md).

Related: five-part model in [agentic-system.md](./agentic-system.md).
Historical PIV text: [agentic-coding.md](./agentic-coding.md) (do not use
it as the live stage list).

## Layers

One graph, one control-plane orchestrator, one worker runtime.

```text
AiNative feature-loop.md  ← the graph (this file)
        │
        └─ Hermes parent    ← control plane (board / dispatch / gates)
              workers: one worker session per agent state
```

Hermes owns state, dispatch, report checks, human relays, retries, and
shipping. A worker executes only the one state Hermes assigned; it never
chooses the next state.

## Split of ownership

| Layer | Owns | Does not own |
|---|---|---|
| **AiNative** (this tree) | What the loop is. Which states exist. Which agent kind runs a state. Compact-report expectations. Human gates vs agent states. | Board runtime, worktrees, worker process, GitHub, messaging, enrolled-project source. |
| **Spec Kit** (in the project) | How specify / clarify / plan / tasks / analyze / implement / converge write native artifacts. | The graph. Skip/UAT policy. Ship. |
| **Hermes parent** (`personalAgent`) | Board, current state, isolated task worktree, one worker per state, report checks, retries, human gates, messaging, GitHub ship. | Following stage skills in-process; one-shot “run all of Spec Kit.” |
| **Worker** | Execute the **one** step Hermes named. Read that skill. Write artifacts. Return a compact report. Exit. | The flow. Next state. Skip/UAT policy. Ship. Merge. AiNative writes. |

## Agent and skill sources

To Hermes, each agent state is a named skill, artifacts, and a compact
report.

1. **AiNative agents** — folders under `docs/agents/`. Target required states: Ready,
   route-work, critic, and tester. `pi-harness` is the Pi worker backend; `antigravity-harness` is the
   Google Antigravity CLI worker backend; `claude-harness` is the Claude Code CLI worker backend; `cursor-harness` is the Cursor TypeScript SDK (`@cursor/sdk`) worker backend. Ready selects one via
   `SPECKIT_WORKER` / `speckit.worker` (default `antigravity`) and checks that
   runtime only. All require `--model` (no harness default). `scout` (read-only brief / Repo Q&A)
   and `legacy-system-assessment-agent` (standalone assessment) are on-hand tools
   Hermes may call whenever it needs them — not loop states, not tied to one
   step. `pr-reviewer` is an automatic loop state after Ship on feature and change paths (and on-hand for ad-hoc reviews).
   `speckit-orchestrate` is the Cursor parent implementation of this same
   graph (Cursor `Task` workers or Pi fallback); the Hermes parent implements
   the same graph via dispatch. Other agents run only as an explicitly named `job`.
2. **Spec Kit** — project prompts stored in the enrolled project by
   `specify init --integration pi` (`.pi/prompts/speckit.*.md`; Pi is the only
   integrated runtime). Hermes reads
   these files as skill inputs; this does not require an editor runtime,
   command, or symlink. Legacy Cursor (`.cursor/skills/`) and retired Opencode
   (`.opencode/commands/`) layouts are honored as fallbacks by the `ready` gate
   only. Pi has built-in MCP support since 1.0, so tool-using prompts
   (`taskstoissues`, etc.) work without an adapter.

Hermes maps each state to a skill path and starts **one** worker. It does not
run skills in-process.

## Executor rule

```text
Hermes: what state? → start a new worker for that step only
Worker: do the step → compact report → exit
Hermes: check → next state, retry, or park for a human
```

- **New worker session every agent state.** Never one process that runs Ready
  through converge.
- Worker prompts are stage-dumb: worktree, step name, skill path, inputs
  on disk, report schema. If the prompt says “then run clarify,” the
  playbook has leaked back in.
- Hermes never writes `spec.md`, `plan.md`, `tasks.md`, or application code
  from the parent process because “context is already loaded.”

## Runtime ownership

Runtime mechanics are **not** defined in AiNative. Hermes owns them; this
install's live configuration lives in `personalAgent` (Compose, image,
environment) and `$HERMES_DATA_ROOT/state` (SOUL, `config.yaml`, and the
context files Hermes writes for itself). The current
install provides the native `hermes kanban` and `hermes project` commands but
no worker loop is wired, so do not describe the loop as running.

The target runtime must satisfy these constraints:

- The Kanban board is the only task source of truth; do not add a second task
  database.
- One isolated task worktree per active card, read-only AiNative
  (`/opt/data/mnt/AiNative`), and the operator's human park/resume path for
  questions and gates.
- Every agent state starts one new worker session with a one-step request and
  a compact report contract. Workers never ship, push, merge, or deploy.
- A Feature Card is planned by a planning role. After planning produces
  `tasks.md`, Hermes creates child Task Cards on the same board. Each child
  is independently executable; the parent stays open until all children are
  complete and feature-level validation passes.
- The feature-level critic/tester and operator gates belong to the parent
  Feature Card, not its child cards. UAT starts after Ship: the operator
  exercises the shipped PR using the walkthrough in the PR body; its exact
  triggering and board presentation remain under active policy work.
- Keep project rules in `AGENTS.md` and project validation commands in
  `.ainative/project.yaml`. Hermes links to this file rather than copying
  the graph into its dispatcher instructions.

Do not add a second task database.

## Card paths

After a project is enrolled, every unit of work is a Kanban card. `path`
is an optional card field. When the card names a path, Hermes honors it.
When it does not, Hermes runs `route` after `ready` to decide the path
from the task — the same route-work as `speckit-orchestrate`
(`REQUESTED_PATH` honored when present, inferred from the task when
absent). The groomer omits `## Path` unless the human explicitly wrote
`feature|change|job`; that omission is the normal case. Absent path never
means a default — it means machine-infer by `route-work`.

| Path | When | Graph |
|---|---|---|
| `feature` | A desired product outcome that needs a spec, plan, and review | The graph below (`ready → route → specify → clarify → plan → tasks → [analyze] → implement ↔ converge → critic → tester → ship → pr-review → uat → adjust`); planning creates child Task Cards |
| `change` | A small code edit already specified by the card | `ready` → `route` → one worker → `tester` → `ship` → `pr-review` → `uat` → `adjust` (no critic, no converge, no `tasks.md`) |
| `job` | Work that is not a code change (write a PRD, bootstrap from a PRD, run a `learn` card to a finding) | `ready` → `route` → one worker for the named skill. It may park for a human. Workers never ship. After the named skill reports `STATUS: ok` the parent automatically ships (commit, push branch, open PR; `keep-local` opts out); after named skill `STATUS: ok` → ship (or declined); MUST NOT run pr-reviewer; UAT is not a job-path stage. The job path skips **pr-review and UAT only**: after ship the card stays open until the human merges its PR; the parent then verifies `MERGED`, syncs the base branch, removes the worktree and branches, and only then completes, so cards with `parents=[job card]` release on merge. The job path has **no per-card Adjust** — one worker, a ship, and a human merge give no spec/plan/critic/tester evidence — while job cards still report friction and still carry a `## Metrics` block so the weekly roll-up sees them. It does not enter the feature graph |

Downstream stages MUST use `FEATURE_DIR` / `.specify/feature.json` (basename e.g. `002-agentic-validation`) and MUST NOT infer the spec directory from git `BRANCH` (`agentic-validation` may differ).

No worker on any path ships. Every path ends the same way: once validation
passes, the parent commits, pushes the branch, and opens a PR automatically,
with no confirmation prompt. The PR is the review surface; on feature and
change paths, the operator's UAT pass on the open PR is the single merge approval,
and the parent then merges. The job path skips pr-review and UAT only: after
ship the card stays open until the human merges its PR; the parent completes
only after verifying `MERGED`, syncing the base branch, and removing the
worktree and branches. `keep-local` opts a run out of shipping.

PR CI independently re-proves validation and evidence stays out of git —
see the CI re-proof and evidence-hygiene guidance in
[validation-layer.md](./validation-layer.md).

A `change` or `job` worker that finds the card is really a feature stops
and reports that. It does not promote itself onto the feature graph.

**Mode.** The paths above are `build` mode: they ship decided behavior. A
card whose *what* is not decided yet belongs in `learn` mode (a time-boxed
`spike` or `demo` whose code is never merged and whose only shipped output
is a finding). A card with `## Mode: learn: spike|demo` routes to `job` with
the [`learn`](../agents/learn/SKILL.md) skill: a `build` step that parks once
for the operator's verdict and decision (`STATUS: blocked`, never `ok`, so
nothing ships early), then a `finding` step whose `STATUS: ok` ships a PR
holding only the finding and a reference patch. See
[scoping.md](./scoping.md).

`change` does not run specify, clarify, plan, tasks, analyze,
implement/converge, or critic. `tester` runs the
project `validation_commands`. `ready` on a `change` is branch preflight
only.

### Phased PRD

A PRD too big for one `feature` run gets a **phase plan**: a separate file
next to the PRD, named `<prd-name>.phases.md` (`PRD.md` → `PRD.phases.md`).
The PRD itself is never restructured, so a PRD written with any tool can be
phased, as long as it is a file in the repo. `prd-writer` writes the plan,
either right after writing the PRD or in phase-plan mode for an existing PRD.
Format and rules:
[prd-writer § Phase plan](../agents/prd-writer/SKILL.md#phase-plan).

Each phase is one `feature` run through the graph below, in plan order:

- **Naming the phase.** A phase run's task input carries
  `phase: <plan-path>#<N>` (e.g. `phase: PRD.phases.md#2`) and nothing about
  how to build it. The plan and the PRD own the *what*; `plan.md` / `tasks.md`
  own the *how*. A design copied into the task input goes stale the moment
  implement diverges from it, and then two sources of truth disagree. A task
  input with a `phase:` line is always a `feature`.
- **Scope.** `specify` specs only Phase N's scope. Later phases and deferred
  items are out of scope; earlier phases are existing behavior. Phase N's exit
  criteria become acceptance scenarios in `spec.md`.
- **Order.** Phase N starts only after Phase N−1's PR is merged into the base
  branch. Phase 1 starts only after the phase plan is merged (in an empty
  repo, after the bootstrap PR too). The proof lives on the base branch: each
  phase's `specify` step writes its spec directory into that phase's
  `**Spec:**` line on the phase branch, so the line reaches the base branch
  only when the phase's PR merges. `ready` reads it there and blocks a phase
  whose predecessor is not merged (`phase-order` check,
  [ready](../agents/ready/SKILL.md#phase-order-required-when-phase_ref-is-set)).
  How a harness sequences phase runs is the harness's business; the `ready`
  check holds either way.
- **Done.** A phase is done only when **its PR is merged**, not at `ship` and
  not at a UAT pass. The same rule as every other unit of work (see
  [After onboarding](../knowledge/setup/new-project.md#after-onboarding)).
- **MVP.** A merged phase is not a releasable product. The plan's
  `MVP complete after:` line names the phase that completes the MVP; an MVP
  usually spans several phases.

## Canonical state graph

This graph is the `feature` path. Orchestrator-specific **edges** (not extra loops):

- **Hermes:** pick the Kanban card, isolate its worktree, surface human
  gates on the operator path, and ship to GitHub once required checks pass
  (automatic; `keep-local` opts out).

```text
ready → route
  → specify → clarify
  → plan → tasks → [analyze]
  → implement ↔ converge
  → critic → tester
  → ship
  → pr-review
  → uat
  → adjust
```

Graph string: `ready → route → specify → clarify → plan → tasks → [analyze] → implement ↔ converge → critic → tester → ship → pr-review → uat → adjust`

| State | Kind | Worker? | Notes |
|---|---|---|---|
| `ready` | AiNative [`docs/agents/ready/`](../agents/ready/) (promoted; the single Ready definition; Cursor stage name `speckit-ready`) | yes | Git/worktree/layout preflight. Not scout. `READY: blocked` stops the run. Returns `WORKTREE` on `ok`. Phase run: also blocks until the previous phase is merged ([Phased PRD](#phased-prd)). |
| `route` | AiNative [`docs/agents/route-work/`](../agents/route-work/) (same as `speckit-orchestrate` route stage) | yes | Decides `feature \| change \| job`. Honors card `path` when present; infers from the task when absent. `ROUTE: job` with no usable skill stops. |
| `specify` | Spec Kit | yes | Phase run: specs only that phase's scope and fills its `**Spec:**` line in the phase plan ([Phased PRD](#phased-prd)). |
| `clarify` | Spec Kit | yes | Questions return to the parent. Parent asks the operator. A **new** worker encodes answers. |
| `plan` | Spec Kit | yes | No extra plan-approval gate. |
| `tasks` | Spec Kit | yes | |
| `analyze` | Spec Kit | yes | Only if plan returned `ANALYZE: yes`. Read-only. Critical finding = park. |
| `implement` | Spec Kit | yes | Parent loops with converge. Fresh worker each pass. Size-gated before the build stage is created: see [Build size gate](#build-size-gate). |
| `converge` | Spec Kit | yes | `tasks_appended` (new work) → implement again. Unchanged fingerprint → stuck. Only `converged` exits the loop. |
| `critic` | AiNative | yes | Adversarial review of spec/plan/implementation. Required. After converge; not a “finish” report. |
| `tester` | AiNative | yes | Prove the flows. Project `validation_commands` run **here**, not as a parallel parent phase. Required. |
| `ship` | parent / GitHub | **no** | Parent commits everything, pushes the branch, and opens a PR with a step-by-step human walkthrough in the PR body. Automatic once validation passes (feature: critic PASS then tester PASS; change: tester PASS; job: `STATUS: ok`); `keep-local` opts out; workers never ship, on any path. |
| `pr-review` | AiNative | yes | Staged PR review (`pr-reviewer`). Required loop state after `ship` on feature and change paths (host Task, Validation profile, fresh session). Evaluates architecture, risk, and evidence. APPROVE or REQUEST CHANGES with zero Criticals routes to UAT park; REQUEST CHANGES with Criticals routes back to converge (feature) or change worker (change). Job path skips pr-review. |
| `uat` | parent ↔ human | **no** | Operator exercises the shipped PR using the walkthrough. Pass/fail confirmation; exact trigger/presentation policy is being refined. |
| `adjust` | AiNative [`docs/agents/adjust/`](../agents/adjust/) | yes | One step, fresh worker session under the Validation profile on the same executor rule as every other state ([validation-layer.md#model-selection](./validation-layer.md#model-selection)). Runs after `uat`/merge and on blocked/parked/killed/abandoned cards. Output is proposals only; never gates or delays merge or card completion. Three attempts then park with the park recorded as a follow-up item on a completed card. |

**End-of-path rule (all paths):** workers never commit, push, or open PRs.
The parent does that in `ship` automatically once validation passes; on feature
and change paths, the operator then reviews the PR (UAT). A UAT pass makes the
parent merge it (merge commit, after checking mergeability, required checks, and
that the head matches the validated head). Adjust's trigger is the card reaching
a terminal state — merged, or closed without a merge — so no new card state is
required; Adjust runs as its own worker after the merge or terminal close and never
gates the merge or card completion.

**Job path:** it skips pr-review and UAT only. After ship the card stays open
until the human merges its PR; the parent then verifies `MERGED`, syncs the base
branch, removes the worktree and branches, and only then completes — so cards
with `parents=[job card]` release on merge, never on an open PR.

## PIVSA mapping

The loop above is the detailed form of PIVSA:

* **Plan** = `ready → route → specify → clarify → plan → tasks → [analyze]`
* **Implementation** = `implement ↔ converge`
* **Validation** = `critic → tester`
* **Ship** = `ship → pr-review → uat` (pr-review is an automatic loop state after Ship on feature and change paths; the job path skips pr-review and UAT only) → merge (parent step, after UAT pass on feature and change; on the job path the card completes after the human merges and the parent verifies `MERGED`, syncs the base branch, and removes the worktree and branches)
* **Adjust** = `adjust`, runs after the merge on feature and change paths and on cards that never merge (blocked, parked, killed, abandoned); never gates the merge or card completion

**Default ship order** (until explicitly changed): critic PASS then tester PASS, then parent
ships the **branch** (commit, push, open PR with walkthrough) automatically,
with no confirmation prompt; `keep-local` opts out. After `SHIP: ok`, pr-reviewer runs automatically. Do not open a PR and then
treat the walkthrough as optional. Merge is a parent step taken after the operator's UAT pass on
feature and change paths; on the job path the human merges the open PR and the parent completes on
`MERGED`.

`skip` is an **operator flag**, not a skipped specify/clarify state.
Workers self-answer; the parent still shows the choice report and goes
straight to plan.

## Compact reports

The parent parses these report fields; it does not scrape worker chat prose.

### Friction grammar

Every worker compact report ends with a friction line — grammar:

`FRICTION: <target-class> | <one-sentence observation> | <evidence-reference>`

The clean-run form is exactly `none` (no pipes, no trailing text), and omitting the line is a report defect; the line is required, its content is not. An absent line on an older or partial artifact means **unknown**, never "no friction".

- `<target-class>` is one of exactly four values: `project-rules` (the managed project's `AGENTS.md`), `project-config` (the managed project's `.ainative/project.yaml`), `ainative` (an AiNative skill or system doc), `harness` (a harness adapter).
- `<one-sentence observation>` is one sentence with no `|` character (use `/` instead), stating what slowed the step down or forced a guess.
- `<evidence-reference>` is something the parent can open (card id, artifact path, report id, metric).

The line never changes a verdict, loop-back, gate, or merge. The `ready` report contract subsumes `docs/agents/speckit-ready/SKILL.md` (its step 3 returns the script stdout as the ready report, with the line appended as the last line). Contract item 12 (job skills) covers job skills that document their own report (`server-setup`, `prd-writer`, `project-bootstrapper`, `proposal-writer`, `learn`). The `ship` line is emitted by the **parent** (ship is a parent step).

Ready: `READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `CHECKS`, `FIXES`, and a FRICTION line — grammar above (emitted by the ready worker, appended as the last line after the unwrapped `ready-check.sh` stdout).

Route: `ROUTE: feature|change|job`, `SKILL`, `SKILL_PATH`, `WHY`, and a FRICTION line — grammar above.

Specify/clarify/plan/tasks/analyze: `FLOW_ID`, `ARTIFACTS`, `STATUS: ok|stuck|blocked`, `SUMMARY`, and a FRICTION line — grammar above. Plan also: `ANALYZE: yes|no`.

Implement: `IMPLEMENT_STATUS`, `TASKS_DONE`, `TASKS_OPEN`, `BLOCKER`, `SUMMARY`, and a FRICTION line — grammar above.

Converge: `FLOW_ID`, `CONVERGE_OUTCOME: converged|tasks_appended|blocked`, `FINDINGS`, `FINGERPRINT: <sorted source-refs> | <sorted validator-ids or "none">`, `PHASE_APPENDED`, `TASKS_APPENDED`, `BLOCKER`, `SUMMARY`, and a FRICTION line — grammar above. Source-refs in FINDINGS / appended tasks remain spec/plan/constitution only (`FR-###`, `US#/AC#`, `plan: …`, `Constitution …`). Validator IDs appear in the task description only (`[tester: flow-2]`, `[critic: C1]`, `[pr-review: C1]`); MUST NOT invent PR-review source-refs.

Critic: `FLOW_ID`, `CRITIC: PASS | FAIL`, `LOOP_BACK: implement | plan | none`, `FINDINGS: <none, or one line each: ID | severity | file:line | summary>`, `SUMMARY`, and a FRICTION line — grammar above. PASS ⇒ `LOOP_BACK: none`. FAIL mixed implement+plan ⇒ emit `plan` (parent parks). Worker MUST NOT write `tasks.md` or launch tester/ship.

Tester: `FLOW_ID`, `TESTER: PASS | FAIL`, `LOOP_BACK: implement | plan | none`, `EVIDENCE: specs/<flow>/evidence.md`, `FINDINGS: <none, or one line each: flow-id | problem | fix needed>`, `SUMMARY`, and a FRICTION line — grammar above. PASS ⇒ `none`. Assertion/code failures default to `implement` when omitted. `<flow>` is the Spec Kit feature directory basename from `feature.json`, not `BRANCH`.

Change-path tester (`change` SKILL `STEP: tester`): `FLOW_ID`, `TESTER: PASS | FAIL`, `TESTS`, `FINDINGS`, `SUMMARY`, and a FRICTION line — grammar above (validation remains `STEP: tester` only; no critic, no `LOOP_BACK`; FAIL retries the change worker with FINDINGS, three attempts then park; never converge, never `tasks.md`).

pr-reviewer (after `SHIP: ok`, feature and change only): `FLOW_ID`, `VERDICT: APPROVE | REQUEST CHANGES | BLOCKED`, `CRITICAL_COUNT: <integer>`, `CRITICALS: <none, or one line each: ID | file:line | trigger | summary>`, `REPORT: <path>`, `SUMMARY`, and a FRICTION line — grammar above. Merge gate remains Critical-only (Warning/Suggestion never change `VERDICT`). `VERDICT: REQUEST CHANGES` with `CRITICAL_COUNT: 0` is routed as APPROVE for the loop. Worker MUST NOT ship, merge, write `tasks.md`, or dispatch converge/implement.

Ship: `SHIP: ok|blocked|declined`, `PR: <PR URL, or none>`, `WALKTHROUGH: <included|none|blocked>`, `EVIDENCE: included|none`, `SUMMARY`, and a FRICTION line — grammar above (emitted by the parent). After a first `SHIP: ok`, later passes on the same run MUST reuse `PR` (same URL). `SHIP: declined` only for `keep-local`. `SHIP: blocked` does not launch pr-reviewer.

Adjust: `FLOW_ID`, `ADJUST: ok|no-findings|blocked`, `EVIDENCE_USED`, `LEARNINGS`, `PROPOSALS`, `ARTIFACT`, `SUMMARY`, and a FRICTION line — grammar above.

Job skills: whatever report the named skill defines (`STATUS: ok|stuck|blocked`, `SUMMARY`, files changed at minimum), and a FRICTION line — grammar above.

## Per-card metrics

The one home for a card's numbers is on the card itself, in a `## Metrics` block. It is appended **by the parent** when the card reaches its terminal state (`merged`, `blocked`, `parked`, `killed`, `abandoned`), before Adjust is dispatched. One block per card; a re-opened card keeps its block and appends a new one with the new `closed_at`. Read by Adjust (baseline input 1) and by the weekly roll-up. Never written by a worker.

### Block wire format

```markdown
## Metrics

- path: feature | change | job
- terminal: merged | blocked | parked | killed | abandoned
- closed_at: 2026-11-26T14:03:11Z
- loops: loops.converge=<n|n/a> loops.critic=<n|n/a> loops.tester=<n|n/a> loops.pr_review=<n|n/a>
- uat: uat.outcome=<pass|fail|not_run> | uat.rounds=<n> | uat.reasons=<comma list or none>
- uat_notes: "<operator's own words, quoted, or none>"
- tokens: input=<n|unknown> output=<n|unknown> total=<n|unknown>
- cost_usd: <number|unknown>
- wall_time_active: <2h14m|unknown>
- boundary: sessions from ready dispatch to the last dispatch before <terminal>; excludes human park time; cost unavailable when the harness or provider does not report it
```

### Field rules

- `path`: Required; the card's routed path (`feature`, `change`, or `job`).
- `terminal`: Required; `merged` requires a UAT pass on the merged head (feature/change).
- `closed_at`: ISO-8601 UTC timestamp; **anchors the roll-up week** — a card belongs to the week this timestamp falls in.
- `loops.<stage>`: Count of **return dispatches caused by that stage**:
  - `converge` = `tasks_appended` re-entry into implement
  - `critic` = FAIL loop-back (to implement or plan)
  - `tester` = FAIL loop-back (to implement or plan; change path: FAIL → re-run change worker)
  - `pr_review` = REQUEST CHANGES
- Loop-back counting rules:
  - One count = one parent-observed **return dispatch** caused by that stage.
  - Retries under the stuck policy (attempt 2 or 3 of the same verdict-less dispatch) are not loop-backs.
  - A stage that runs twice and FAILs twice in one card counts 2.
  - `0` only when the stage ran and returned a non-looping verdict (`PASS`, `converged`, `APPROVE`).
  - `n/a` when the path lacks the stage or it never ran before the card closed. Never `0` for an absent stage.
  - **Job path mapping**: the job path skips validation entirely, so all four loop-back fields are recorded as `n/a`: `loops.converge=n/a`, `loops.critic=n/a`, `loops.tester=n/a`, `loops.pr_review=n/a`, with `uat.outcome=not_run`. The block is still written so job cards feed the roll-up.
  - `uat.rounds` is not a loop-back field; UAT failures are recorded in `uat.rounds` and `uat.reasons` (each reason may carry its round, e.g. `wrong-behavior@r2`).
- `uat.outcome`: `pass`, `fail`, or `not_run` (`not_run` for job cards and cards that closed before ship).
- `uat.rounds`: Rounds attempted (0 when `not_run`).
- `uat.reasons`: Required when `uat.outcome` is `fail`. Closed-set ids, each optionally carrying its round (`wrong-behavior@r2`).
- `uat_notes`: Verbatim operator words; required when `reasons` includes `other`.
- `tokens`: Cumulative across the card's worker sessions, or `unknown`. Never `0` as a stand-in for missing.
- `cost_usd`: As reported by the harness report, or `unknown`.
- `wall_time_active`: Sum of worker session durations; excludes human park and UAT idle time.
- `boundary`: One line; states what is covered and what is unavailable today.

### Closed UAT failure reason set

| Id | Means |
|---|---|
| `missing-feature` | A promised behavior is absent |
| `wrong-behavior` | Behavior differs from the walkthrough |
| `broken-ui` | Page/control broken, layout or interaction failure |
| `error-crash` | Error, exception, or 5xx on the happy path |
| `missing-evidence` | PR walkthrough or evidence does not let the operator verify |
| `env-setup` | Could not exercise it (config, data, credentials, port) |
| `scope-mismatch` | Shipped more or less than the card asked |
| `docs-wrong` | Documented step or claim is wrong |
| `other` | None of the above — `uat_notes` required |

### Derivation rules (no transcripts)

All fields are derivable from board dispatch history plus worker compact reports:
- `loops.*`: derived from parent dispatch history and stage verdicts (`CONVERGE_OUTCOME`, `CRITIC`, `TESTER`, `VERDICT`).
- `uat.*`: derived from the UAT exchange on the card.
- `tokens`, `cost_usd`, `wall_time_active`: derived from harness per-session reporting and dispatch timestamps. Where unavailable, `unknown` is recorded with the boundary stated.
- `path`, `terminal`, `closed_at`: card fields at close.

### Before/after comparison rule for accepted changes

To evaluate whether an accepted Change card produced a measurable improvement:
- Compare `loops.*`, `uat.reasons`, `wall_time_active`, and `cost_usd` on the same path, per stage.
- Evaluation window: the 5 cards before the Change card's merge versus the 5 cards after it on the same path (skipping weeks where a different change landed).
- Always print the sample size (`n=`).
- Exclude stages recorded `n/a` from the sample rather than averaging them as zero.
- No comparison may require transcripts.

## Weekly Adjust roll-up

A weekly cross-card aggregation that finds recurring friction, unaccepted proposals, and stage friction across cards. It is an ordinary Kanban card on the board, not an in-process step: visible, skippable, and run by the same `adjust` skill in `STEP: rollup` mode.

### Scheduling and ownership

- **Cadence:** One card per **ISO-8601 week** (Monday 00:00 → Sunday 23:59 **UTC**, key `YYYY-Www`, e.g. `2026-W48`).
- **Owner:** Filed by the **control plane** (Hermes parent) no later than the first business day after the week closes. AiNative defines the cadence and artifact shape; scheduling is harness-owned.
- **Card shape:** `## Path: job`, `## Skill: adjust`, `STEP: rollup`, `## Week: <YYYY-Www>`.
- **Week membership:** A card belongs to the week its `## Metrics` `closed_at` timestamp falls in (anchored on terminal state, not when Adjust ran or the PR opened). A late or resumed Adjust run never moves a card between weeks, and no card is counted twice.
- **Skip semantics:** The operator may skip or delete the roll-up card without affecting any other card in the loop. The next roll-up reports the skipped week in its `gaps:` line with no back-fill or catch-up run.
- **Empty weeks:** If a week produces no terminal cards or Adjust runs, the ranking is empty and `gaps:` explicitly notes the empty week. No findings are ever invented.
- **Delivery and PR/ship handling:** Like other `job` path cards, the roll-up runs on a fresh short-lived branch (e.g. `adjust/rollup-<YYYY-Www>`) cut from the current base. The parent commits the written artifact `.ainative/adjust/<YYYY>-W<ww>-rollup.md` and opens a PR titled `Adjust roll-up: <YYYY-Www>` against the base branch for human review and merge. If no findings survived or the card is skipped, no PR is opened.

### Artifact shape and sections

The roll-up writes its artifact to `.ainative/adjust/<YYYY>-W<ww>-rollup.md`. It contains:

1. **Header:** inputs count (Adjust runs, cards with metrics by path), week key, and UTC boundary.
2. **Friction by target (ranked):** targets ranked by accumulated friction, with every line displaying the observation count and the distinct-card count (e.g. `7 observations, 5 cards`).
3. **Recurring, not accepted:** findings seen across weeks whose Change card remains unapproved or pending (`finding key`, `first week`, `weeks seen`, `change card`, `state`). Listed once; never re-filed.
4. **Stage numbers:** per-stage loop-back averages and UAT failure share per path. Every figure displays sample size (`n=`), and stages recorded `n/a` are excluded from the sample rather than averaged as zero.
5. **Gaps:** explicit listing of evidence gaps, including skipped roll-up weeks, cards predating friction reporting (treated as unknown), `unknown` cost/token metrics, and small samples.
6. **Proposals:** new proposals follow the same shape and rejection rules as per-card runs; consult [adjust/rule.md](../agents/adjust/rule.md) for the recurrence threshold and merge-target test (gate-ownership rule). Cross-week sightings count toward distinct cards.

The roll-up cannot block, delay, or reorder any other card.

## Build size gate

Runs before a build stage (`implement ↔ converge`) is created for a feature.
A build stage has a fixed iteration budget. A feature that exceeds it fails
mid-run, and retrying does not recover, because the remaining work no longer
fits in one stage.

1. **Count.** Count the open tasks (`- [ ]`) in the feature's `tasks.md` and
   note the user story each one belongs to. Tasks that belong to no story
   (setup, foundational) are their own group.
2. **Split when** the open count is **more than 15**, or the open tasks span
   **more than one user story**.
3. **Multi-story phases never run as one stage.** A phase spanning more than
   one user story is never dispatched as a single build stage. A
   single-story phase at or under 15 open tasks may run as one stage.
4. **Setup and foundational group.** Tasks with no story form their own stage,
   placed before the first story stage. If that group exceeds 15 tasks, split
   it by section.
5. **Stage shape.** Each story stage covers one user story's exit criteria,
   and names the previous stage as its prerequisite. Stages run in sequence.
   The first stage has no prerequisite.
6. **Restate inheritance.** Each stage restates in writing the shared decisions
   from `plan.md` and the working tree it inherits (branch, worktree, and the
   files earlier stages changed). A stage must not depend on context from the
   stage before it that is not written down in those inputs.

## Stuck policy

Per step, three attempts (original + two resumes) then park.
Do not retry a stable `READY: blocked`.
Do not retry missing `spec.md` / `plan.md` / `tasks.md`.
`CONVERGE_OUTCOME: blocked` parks immediately.
Human questions are not stuck; they are clarify relay / `uat`.

## What this is not

- Scout → 5/10/20 questions → plan-reviewer → wait for plan approval →
  implement → critic → tester as the **target** path.
- One worker identity that runs the whole Spec Kit playbook in a single session.
- Treating card `path` as required. `path` is optional; when absent
  `route` after `ready` decides `feature` / `change` / `job` from the
  task (honoring `REQUESTED_PATH` when present, machine-inferring when absent).
- Hermes implementing Spec Kit stages in-process.
- Converge substituting for critic/tester/ship.
- Duplicating this document into Hermes. Hermes **links** here
  (`/opt/data/mnt/AiNative/docs/systems/feature-loop.md`) and describes only
  dispatcher behavior.

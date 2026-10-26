---
name: speckit-orchestrate
description: >-
  Runs ready, routes the task (feature, change, or job), then runs that path
  when the user invokes /speckit-orchestrate or asks to “run the full speckit
  flow”.
disable-model-invocation: true
---

# Spec Kit orchestrator

This skill owns the control flow: ready, route, then one of three paths. It is
standalone and must not assume any project-specific workflow beyond the
project's Spec Kit skills and the global skills it names.

```text
ready → route-work ─┬─ feature → specify … converge → critic → tester → ship* → pr-review → UAT
                    ├─ change  → change → tester → ship* → pr-review → UAT
                    └─ job     → named skill → ship* (no pr-review, no UAT)
```

Graph string: `ready → route → specify → clarify → plan → tasks → [analyze] → implement ↔ converge → critic → tester → ship → pr-review → uat`

\* `ship` is automatic once validation passes; `keep-local` (alias `no-ship`) opts out. Merge is
manual and outside this loop.

Only **feature** uses the heavy Spec Kit machinery. **change** and **job** are
thin.

## Keywords

Treat these as command keywords when they appear in the user's `/speckit-orchestrate`
arguments or in a later reply during specify or clarify. Match case-insensitively.

- **skip** — A lone word `skip` counts; so do `skip questions` and
  `skip specify`. The user does not want to answer specify/clarify questions.
  Do not present the clarification question loop. Tell the specify and clarify
  workers not to ask; they document assumptions or pick recommended options and
  write those into the spec. After clarify, show the worker's **choice report**
  (what was chosen and why), then continue to plan. Do not treat `skip` as
  permission to skip plan, tasks, implement, or converge. `skip` has no effect
  on ship: ship is automatic after validation passes (see **Ship / UAT**).
- **keep-local** — A lone word `keep-local` (alias `no-ship`) opts this run out
  of shipping. After validation passes the parent leaves the work uncommitted
  in `WORKTREE`, emits `SHIP: declined`, and skips automatic pr-review and UAT.
  It is the only way to suppress the automatic ship; the default is to ship.
  Committing the work locally afterward is the operator's job.
- **path: feature|change|job** — the user chose the path. Pass it to route-work
  as `REQUESTED_PATH`; route-work must honor it.
- **skill: <name>** — the skill a job must use. Pass it to route-work as
  `REQUESTED_SKILL`.
- **worker: <pi-model>** — per-profile override for the Worker profile only
  (`implement`, `converge`, `change`, `job`). Accepts `provider/model`,
  `provider/model:thinking`, or full Pi flags (`--provider <p> --model <m>
  [--thinking <t>]`). Example: `worker: my-provider/my-exec-model`.
  Validated by launching Pi; never applied to Reasoning or Validation
  stages.
- **reasoning: <task-slug>** — per-profile override for the Reasoning profile
  only (`ready`, `route`, `specify`, `clarify`, `plan`, `tasks`, `analyze`;
  plan-reviewer when used = Reasoning, same model as plan). Must be a slug
  from the runtime's allowed Task model list. Example:
  `reasoning: my-reviewer-slug`. Never applied to Worker or Validation
  stages.
- **validation: <task-slug>** — per-profile override for the Validation profile
  only (`critic`, `tester`, `pr-reviewer`). Must be a slug from the runtime's allowed Task
  model list. Example: `validation: my-validator-slug`. Never applied to
  Worker or Reasoning stages.

## Parent vs worker (hard)

While this skill is running it outranks `pi-handoff`, `plan-orchestrator`, and
changelog/version bootstrap. Do not leave this pipeline to spawn Pi except for
worker stages (those stages are Pi-first). Do not run plan-orchestrator, or add
versioning the spec/tasks did not ask for. `pi-harness` has no default model —
worker stages MUST pass explicit `--provider` / `--model` / `--thinking`
resolved per run from **Model resolution** below (never a skill-pinned value).

The parent is a dispatcher. It MUST NOT execute ready, route, specify, clarify,
plan, tasks, analyze, implement, converge, change, critic, tester, pr-reviewer,
or a job skill itself: not by following those skills in this session, not by
writing their artifacts, not by running `ready-check.sh`, not by editing code
in-place because context is already loaded.

Never omit `model`. Never pass `inherit` on Task launches. Ban
`inherit` for every reasoning- or validation-stage Task in this pipeline.

For reasoning stages the parent MUST launch a foreground `generalPurpose` Task
(`run_in_background: false`) with the **resolved** reasoning model from
**Model resolution** below (user override else runtime default — never a
skill-pinned slug, never `inherit`). Validation stages use the same host Task
launch with the **resolved** validation model, in a fresh session. For worker
stages the
parent MUST spawn the resolved worker backend (`pi-harness` or
`antigravity-harness`) with the resolved worker model flags; do not launch a
Task for those stages.

## flow_id

Before launching ready, mint an opaque `FLOW_ID` of the form
`flow_<timestamp>_<short-rand>`. Inject `FLOW_ID` into every worker prompt
(ready and all later stages). Every compact report MUST include a `FLOW_ID:`
line; parse it. This is prompt-scaffold only — do not edit project speckit
skills to teach them `flow_id`.

## Skill path resolution (AiNative-first)

`<AINATIVE>` is the AiNative repo root. Canonical source is always
`<AINATIVE>/docs/agents/<name>/SKILL.md`. Resolve hosts as:

| Host | Path (same file) |
| --- | --- |
| AiNative canonical | `<AINATIVE>/docs/agents/<name>/SKILL.md` |
| Cursor host | `~/.cursor/skills/<name>/SKILL.md` → canonical (symlink) |
| OpenCode host | `~/.config/opencode/skill/<name>/SKILL.md` → canonical (symlink) |
| Hermes worker | `/opt/data/mnt/AiNative/docs/agents/<name>/SKILL.md` (read-only mount) |

AiNative-owned skills below are named by their canonical `<AINATIVE>` path;
never assume the host `~/.cursor/...` spelling inside a worker prompt — pass
the canonical path and let the runtime resolve its symlink/mount. Spec Kit
project prompts are different: they live in the target repo at
`REPO_ROOT/.pi/prompts/speckit.<step>.md` (canonical), with
`REPO_ROOT/.cursor/skills/speckit-<step>/SKILL.md` as legacy fallback only.
`pr-generate/template.md` is the one exception: Cursor-only
(`~/.cursor/skills/pr-generate/`), not an AiNative agent — see Ship / UAT.

## Model resolution (runtime-owned, no pinned values)

This skill pins no provider, model, or thinking flag. Concrete values are
resolved per run from the runtime, per
`docs/systems/agentic-system.md` §2 Model: the active harness's Model Selection Config owns provider
and model selection; card profiles name execution profiles, not providers. Do
not put provider names or credentials in cards or in this skill.

Profiles (stage kinds, not model IDs):

| Profile | Stages |
| --- | --- |
| Reasoning | `ready`, `route`, `specify`, `clarify`, `plan`, `tasks`, `analyze` (host Task: Cursor `generalPurpose` Task, OpenCode subagent equivalent, or Hermes worker session). plan-reviewer when used = Reasoning, same model as plan. |
| Worker | `implement`, `converge`, `change`, `job` (Pi via `pi-harness` or Antigravity SDK via `antigravity-harness`) |
| Validation | `critic`, `tester`, `pr-reviewer` (host Task or equivalent, fresh session, validation model — distinct from plan/implement) |

Which profile fits which job is the authority of `docs/systems/agentic-system.md`
§2 Model; this skill only resolves concrete values per profile.

Resolution order for each profile, per run (each keyword/env affects only its own
profile — `worker:` never affects Reasoning or Validation stages, `reasoning:`
and `validation:` never affect Worker stages):

1. **Invocation keywords** — `worker: <pi-model>` sets the Worker profile
   only; `reasoning: <task-slug>` sets the Reasoning profile only;
   `validation: <task-slug>` sets the Validation profile only. Validate before
   use (Pi must launch; Task slug must be in the runtime's allowed list).
   Invalid value for that profile → STOP for that profile, say what was rejected
   and list what the runtime allows. Do not guess, do not cross-apply.
2. **Env override** — `SPECKIT_WORKER_MODEL` (Pi flags or `provider/model[:thinking]`,
   worker only), `SPECKIT_REASONING_MODEL` (Task slug, reasoning only),
   `SPECKIT_VALIDATION_MODEL` (Task slug, validation only). Same validation
   as keywords. Env beats runtime defaults but loses to invocation keywords.
3. **Runtime default** — otherwise use the runtime's configured default **per profile**:
   - Hermes: per-profile `config.yaml` model + card profile (`hermes kanban set-model`,
     `default` profile fallback). Keys live in Hermes
     (`$HERMES_DATA_ROOT/state/config.yaml`); this skill never invents them —
     read what `hermes config get model.*` / `hermes profile list` reports.
   - Cursor: reasoning = session default Task model (must be in the allowed Task
     model list); validation = a different allowed Task model for the session
     (fresh session for critic/tester); worker = operator-confirmed Pi provider/model (env or last
     working Pi flags). Set them independently in the session before invoking.
   - OpenCode: reasoning/validation = the configured subagent model for this
     session (validation distinct from reasoning);
     worker = same Pi provider/model mechanism as Cursor (Pi is external to
     both editors).
   Pass `--thinking` only when that profile's resolved source specifies it;
   never invent it.
4. **Unresolved** — if a profile has no usable value from 1–3, STOP before
   launching that profile and ask the operator for that profile's value only. Never
   invent a nearby slug, never reuse another profile's model.

## Worker SDK (Pi or Antigravity SDK)

Worker stages run in an external coding agent. The backend is the Worker
execution's `provider` (`SDK pi` vs `SDK antigravity`) — not a separate
decision. Resolve **one** provider per run (do not require both to be
installed). For Cursor/OpenCode that provider value lives in:

1. `SPECKIT_WORKER` (`pi` or `antigravity`; aliases `agy`, `google-antigravity`).
2. `git config speckit.worker` in the target repo.
3. Default `antigravity`.

Ready already reports `WORKER:` and `worker-runtime` as the echo of the
resolved provider. Honor that value for every later Worker-profile stage in
the same run.

- **pi** — follow `pi-harness`. Pass resolved `--provider` / `--model` /
  `--thinking`. `--cwd` is `WORKTREE` after ready.
- **antigravity** — follow `antigravity-harness` (`agy-spawn.py` wrapping official
  headless `agy -p`). Pass `--model` (required). Spawn only via `agy-spawn.py`;
  never exec `agy -p` directly, do not launch `agy` TUI, do not use npm `antigravity-sdk`.
  `--cwd` is `WORKTREE` after ready.

Do not swap backends mid-run because spawn failed. Same fallback rules as
the model: retry once only if the runtime defines a distinct fallback.

## Model access and fallback

The resolved value is always the first choice. Never invent nearby slugs.

**Worker stages** (`implement`, `converge`, `change`, `job`): spawn via the
resolved **Worker backend** (`pi-harness` or `antigravity-harness`). You stay in control; that agent is the worker. Give
it the same worker prompt this skill
would have given a Task (repo root, skill path, skip, report format,
`FLOW_ID`, `BRANCH` and `WORKTREE` when known); for any stage after ready, run
the worker with `--cwd` set to `WORKTREE`. Pass the resolved `--model` (and
Pi `--provider` / `--thinking` when the backend is Pi). Then continue from
the worker's compact report.

If the resolved worker launch cannot be used — binary missing, provider/auth
failure, spawn reject, or the launch fails because of the model — do not
improvise another backend or model. Retry once only if the runtime defines a
distinct fallback value for that profile. The fallback may use a different
executionMode: if it specifies HOST, run the stage as a host Task (or host
equivalent) with the fallback model, using the same worker prompt and report
contract. If the primary partially executed the
stage before becoming unavailable, do not blindly rerun through the fallback:
inspect artifacts and side effects first and retry only when safe; otherwise stop
and report execution status and remaining work. If there is no runtime fallback, or
that fallback also fails, STOP (this is not a stuck retry of the primary).
Wait for the user to fix it.

**Reasoning stages** (`ready`, `route`, `specify`, `clarify`, `plan`, `tasks`,
`analyze`): launch a Task with the resolved Reasoning-profile model. Check the session's allowed Task model list
before launch. If the resolved value is missing from the list, Task rejects it, or the
launch fails because of the model, do not invent another slug: launch once
more only if the runtime defines a distinct fallback model. If there is no
runtime fallback, or the fallback also cannot be used, STOP
immediately. Do not continue to the next stage and do not count this as a
stuck retry. Wait for the user to fix it.

**Validation stages** (`critic`, `tester`, `pr-reviewer`): launch a fresh foreground host
Task with the resolved validation model — never continue a plan or implement
session. Same rules as reasoning stages: check the allowed Task model list,
never invent a slug, retry only a runtime-defined distinct fallback, and STOP
(that profile, not a stuck retry) if both the resolved value and the fallback
fail. Wait for the user to fix it.

Then tell the user, in plain language:

- which stage stopped
- which model slug or Pi flags were required
- what failed (no access, could not open, rejected slug, or worker report)
- the available slugs, if known

Do **not**: run any stage in the parent; pass or omit `inherit` on Tasks;
switch to Auto, Composer, Fast, or any nearby slug; retry the same
exact-slug or same Pi flags after a model-access failure; or keep a
reasoning- or validation-stage pipeline going so the user never sees the problem. Pi is the
worker runtime for worker stages is the resolved backend (Pi or Antigravity
SDK). Reasoning and validation stages
stay on the host Task mechanism (never Pi, never in-parent).

The parent MAY only: mint `FLOW_ID`, check prerequisites, dispatch workers,
parse reports, honor the keywords, relay a worker's queued questions to the
user one at a time (relay only; do not score or write the answer into files),
show the clarify choice report, run the pre-push guards, execute the automatic
ship (commit, push, PR) once validation passes unless the operator passed
`keep-local`, park feature/change runs for UAT, enforce stuck policy, and write
the finish report. Ship and UAT are parent-only
operations; workers remain ship-dumb on every path. It MAY read
worker reports, `git diff --stat`, and `quickstart.md` for that report. It MUST NOT read the
stage skills (AiNative `<AINATIVE>/docs/agents/...` or project Spec Kit prompts
`REPO_ROOT/.pi/prompts/speckit.*.md`, legacy `REPO_ROOT/.cursor/skills/speckit-{specify,clarify,plan,tasks,analyze,implement,converge}/SKILL.md`)
in order to perform those stages.

## Prerequisites

Before launching a worker, verify (AiNative-first; hosts resolve via symlink/mount per **Skill path resolution** above):

- Canonical AiNative skills (source of truth):
  - `<AINATIVE>/docs/agents/speckit-ready/SKILL.md`
  - `<AINATIVE>/docs/agents/speckit-ready/scripts/ready-check.sh`
    (Hermes: `/opt/data/mnt/AiNative/docs/agents/speckit-ready/scripts/ready-check.sh`)
  - `<AINATIVE>/docs/agents/route-work/SKILL.md`
  - `<AINATIVE>/docs/agents/change/SKILL.md` (covers `STEP: change` and `STEP: tester`)
  - `<AINATIVE>/docs/agents/pi-harness/SKILL.md` (Pi worker backend)
  - `<AINATIVE>/docs/agents/antigravity-harness/SKILL.md` (Antigravity SDK worker backend; required when `WORKER: antigravity`)
- The target repository contains `.specify/`
- `REPO_ROOT/.pi/prompts/speckit.specify.md` (Pi enrollment, canonical)
- the sibling project prompts needed for clarify, plan, tasks, analyze, implement, and
  converge (legacy fallback: `REPO_ROOT/.cursor/skills/speckit-*/SKILL.md`)

If a global skill/script is missing, or the repository is not a Spec Kit
project, stop and tell the user what is missing. Do not create the missing
project structure. Do not require a project-local `speckit-ready`.

## Pipeline

> Path resolution: AiNative skills resolve per **Skill path resolution**
> above (canonical `<AINATIVE>/docs/agents/<name>/SKILL.md`). Project Spec
> Kit prompts resolve to `REPO_ROOT/.pi/prompts/speckit.<step>.md`
> (canonical), with `REPO_ROOT/.cursor/skills/speckit-<step>/SKILL.md` as
> legacy fallback. Every bare `speckit-<step>` path below means the project
> Pi prompt first, Cursor legacy second — never an AiNative path (Spec Kit
> stages are not AiNative agents).

```mermaid
flowchart TD
  ready[ready] -->|READY blocked| haltReady[halt with FIXES]
  ready --> route[route-work]
  route -->|feature| specify[specify]
  route -->|change| change[change]
  route -->|job| job[named skill]

  specify --> clarify[clarify]
  clarify -->|questions relayed, answers encoded| plan[plan]
  clarify -->|skip: choice report shown| plan
  plan --> tasks[tasks]
  tasks --> analyze{analyze?}
  analyze -->|yes| analyzeRun[analyze]
  analyze -->|no| impl[implement]
  analyzeRun --> impl
  impl --> conv[converge]
  conv -->|tasks_appended| impl
  conv -->|converged| critic[critic]
  critic -->|PASS| tester[tester]
  critic -->|FAIL: LOOP_BACK implement| conv
  critic -->|FAIL: LOOP_BACK plan| haltCritic[park: plan misunderstanding]
  tester -->|PASS| featureShip[ship: commit, push, PR]
  tester -->|FAIL: LOOP_BACK implement| conv
  tester -->|FAIL: LOOP_BACK plan| haltTester[park: plan misunderstanding]
  featureShip -->|ok| featureReview[pr-reviewer]
  featureShip -->|keep-local / declined| featureDone[finish report]
  featureShip -->|blocked| featureShipHalt[halt: ship blocked]
  featureReview -->|APPROVE / zero Criticals| featureUat[UAT park]
  featureReview -->|REQUEST CHANGES: Criticals| conv
  featureReview -->|BLOCKED| haltReview[park: Phase 1.5 blocked]
  featureUat -->|pass| featureDone
  featureUat -->|fail| featureHalt[halt with findings]

  change -->|SCOPE feature| haltScope[stop: needs feature path]
  change --> changeTester[tester]
  changeTester -->|FAIL| change
  changeTester -->|PASS| changeShip[ship: commit, push, PR]
  changeShip -->|ok| changeReview[pr-reviewer]
  changeShip -->|keep-local / declined| changeDone[finish report]
  changeShip -->|blocked| changeShipHalt[halt: ship blocked]
  changeReview -->|APPROVE / zero Criticals| changeUat[UAT park]
  changeReview -->|REQUEST CHANGES: Criticals| change
  changeReview -->|BLOCKED| haltChangeReview[park: Phase 1.5 blocked]
  changeUat -->|pass| changeDone
  changeUat -->|fail| changeHalt[halt with findings]

  job -->|questions| job
  job --> publish[ship: commit, push, PR]
  publish -->|ok| jobDone[job report]
  publish -->|keep-local / declined| jobDone
  publish -->|blocked| jobShipHalt[halt: ship blocked]
```

### Shared start

1. **Ready** — launch a `generalPurpose` worker with the resolved Reasoning-profile
   model. Tell it to follow the AiNative
   `<AINATIVE>/docs/agents/speckit-ready/SKILL.md` (not a project copy). Pass
   `REPO_ROOT`, `FLOW_ID`, and `FEATURE_DESCRIPTION` (user args verbatim).
   Ready runs against the original `REPO_ROOT` and never checks out the
   feature branch in the current worktree. Instead, it creates or reuses a
   dedicated git worktree for the feature branch (or reuses the current
   checkout when it is already on the feature branch). Nothing after ready
   runs unless the report says `READY: ok`. On `READY: blocked`, halt and
   show `CHECKS` + `FIXES`. If `READY: ok`, keep `BRANCH` **and** `WORKTREE`
   from the report; `WORKTREE` is the absolute path of the feature worktree
   (or `REPO_ROOT` itself when the checkout was already on the feature
   branch). A `READY: ok` report without a `WORKTREE:` line is unparseable —
   treat it under the stuck policy.

   From here on, every later stage (route, specify, …, change, job) must
   receive `WORKTREE` as its `REPO_ROOT`. If `WORKTREE` differs from the
   original `REPO_ROOT`, the parent MUST call cursor-app-control
   `move_agent_to_root` with that path **before** route and all later
   stages; skip the move when the two paths are the same.
2. **Route** — launch a `generalPurpose` worker with the resolved reasoning
   model. Tell it to follow
   `<AINATIVE>/docs/agents/route-work/SKILL.md`. Pass `REPO_ROOT` (the feature
   `WORKTREE` from ready), `FLOW_ID`,
   `TASK_DESCRIPTION` (user args verbatim), `REQUESTED_PATH`, and
   `REQUESTED_SKILL` (`none` when absent). Tell the user the route and `WHY`
   in one line, then take that path. For `ROUTE: job`, if `SKILL` is `none` or
   `SKILL_PATH` does not exist, stop and tell the user which skill is missing.

### Feature path

3. **Specify** — launch a `generalPurpose` worker with the resolved Reasoning-profile
   model. Tell it to follow the project's
   `REPO_ROOT/.pi/prompts/speckit.specify.md` exactly (legacy fallback:
   `REPO_ROOT/.cursor/skills/speckit-specify/SKILL.md`). Include `FLOW_ID`,
   `BRANCH`, and `WORKTREE` from ready, and pass `WORKTREE` as the
   worker's `REPO_ROOT`. When this prompt includes `FLOW_ID` + `BRANCH` +
   `WORKTREE`, **that instruction outranks the specify skill's
   `before_specify` hook for branch/worktree creation only**. Do not invoke
   git-extension branch create/switch: ready already created or reused the
   branch and its worktree. Still create the spec dir, `spec.md`, and
   `feature.json` as the skill says.
   Downstream stages use `FEATURE_DIR` / `feature.json` from specify; never
   infer the spec directory from `BRANCH`. It must make and document
   reasonable assumptions instead of waiting for its own clarification table;
   clarification happens in the clarify stage. If **skip** is active, tell the
   worker not to ask the user anything and to record assumptions in the spec.
   If the specify worker still presents questions, the parent MUST NOT wait on
   the user for those: answer them as assumptions and tell the worker to
   finish. The parent MUST NOT write `spec.md`.
4. **Clarify** — launch a `generalPurpose` worker with the resolved Reasoning-profile
   model, same rules as specify. Tell it to follow the
   project's `REPO_ROOT/.pi/prompts/speckit.clarify.md` exactly (legacy fallback:
   `REPO_ROOT/.cursor/skills/speckit-clarify/SKILL.md`). The parent
   MUST NOT write `spec.md`.

   **Default:** the worker must not wait inside the Task for answers. It
   returns the question queue (max 5) with `STATUS: blocked`. The parent asks
   the user those questions one at a time (relay only). After the last answer,
   resume or relaunch the worker with the answers so it encodes them into the
   spec.

   **If skip is active** (user said `skip` in arguments, during specify, or
   as the reply when questions would start): tell the worker not to ask. It
   builds the same question queue the skill would have asked (max 5), picks
   the recommended option using the skill's own recommendation rules, and
   writes those answers into the spec. The worker includes this in `SUMMARY`;
   the parent only displays it:

   ```text
   ## Choices I made (skip)

   For each question:
   - Q: <the question>
   - Chose: <option letter or short answer>
   - Why: <one or two sentences>
   ```

   **When clarify completes, go straight to plan.** Do not ask the user to
   confirm, do not wait for "continue", and do not pause after the choice
   report. There is no continuation gate in this run.
5. **Plan** — launch a `generalPurpose` worker with the resolved Reasoning-profile
   model (spawn like route; plan is a Reasoning-profile stage, not a Pi worker stage).
   It follows `REPO_ROOT/.pi/prompts/speckit.plan.md`
   (legacy fallback: `REPO_ROOT/.cursor/skills/speckit-plan/SKILL.md`)
   and returns the plan artifacts plus `ANALYZE: yes|no` and a one-line
   reason. Use `yes` for cross-cutting contracts, constitution tension, or
   many unknowns; use `no` for a small, local change. The parent MUST NOT
   write plan artifacts.
6. **Tasks** — launch a `generalPurpose` worker with the resolved Reasoning-profile
   model to follow `REPO_ROOT/.pi/prompts/speckit.tasks.md`
   (legacy fallback: `REPO_ROOT/.cursor/skills/speckit-tasks/SKILL.md`).
   The parent MUST NOT write `tasks.md`.
7. **Analyze** — only when plan returned `ANALYZE: yes`, launch a
   `generalPurpose` worker with the resolved reasoning model to follow
   `REPO_ROOT/.pi/prompts/speckit.analyze.md` (legacy fallback:
   `REPO_ROOT/.cursor/skills/speckit-analyze/SKILL.md`). This is read-only. Treat a
   critical finding as stuck and stop to ask the user; do not edit artifacts
   automatically. The parent MUST NOT perform the analysis.
8. **Implement ↔ converge** — start the loop with the resolved worker backend (`pi-harness` or `antigravity-harness`, resolved Worker-profile
   flags) for both implement and converge. Never launch these two workers in
   parallel. Continue until converge returns `CONVERGE_OUTCOME: converged`.
   `tasks_appended` with genuinely new tasks starts another implementation
   pass. Do not request user confirmation. The parent MUST NOT implement
   application code or append converge tasks itself.
9. **Critic** — after `CONVERGE_OUTCOME: converged`, launch a fresh host Task with
   the resolved Validation-profile model in a fresh session. Follow
   `<AINATIVE>/docs/agents/critic/SKILL.md`. Critic performs adversarial review
   of spec/plan/implementation before tests run. Critic implementation review is
   required.
   - `CRITIC: PASS` (`LOOP_BACK: none`) → proceed to tester.
   - `CRITIC: FAIL` with `LOOP_BACK: implement` → launch converge with `$ARGUMENTS`
     containing `VALIDATOR_CRITICALS` (the critic Criticals; parent MUST NOT feed
     validator Criticals directly to implement). Converge appends tasks to
     `tasks.md`, then parent loops `implement ↔ converge`, then relaunches critic.
   - `CRITIC: FAIL` with `LOOP_BACK: plan` (or mixed implement+plan) → park. Do not
     re-run critic/tester/pr-review until a human unparks.
   - Missing `LOOP_BACK` on FAIL: treat assertion/code failures as `implement`,
     explicit spec/plan contradictions as `plan`, else park.
   - If converge returns `CONVERGE_OUTCOME: converged` while a validator FAIL is
     still open → park (do not treat as validation PASS; do not re-run
     critic/tester/pr-review).
   Worker MUST NOT write `tasks.md` or launch tester/ship.
10. **Tester** — after `CRITIC: PASS`, launch a fresh host Task with the resolved
    Validation-profile model in a fresh session. Follow
    `<AINATIVE>/docs/agents/tester/SKILL.md`. Tester executes test flows and
    persists the evidence bundle at `specs/<flow>/evidence.md` (where `<flow>` is
    the Spec Kit feature directory basename from `.specify/feature.json`, never
    `BRANCH`).
    - `TESTER: PASS` (`LOOP_BACK: none`) → proceed to Ship (or if `keep-local` /
      `no-ship` is active, emit `SHIP: declined`, skip ship, automatic pr-review,
      and UAT, and finish).
    - `TESTER: FAIL` with `LOOP_BACK: implement` → launch converge with `$ARGUMENTS`
      = `VALIDATOR_CRITICALS`. Converge appends tasks, parent loops
      `implement ↔ converge`, then runs critic → tester.
    - `TESTER: FAIL` with `LOOP_BACK: plan` (or mixed) → park.
    - Missing `LOOP_BACK` on FAIL: defaults to `implement` for assertion/code failures.
    Worker MUST NOT write `tasks.md` or launch ship.
11. **Ship** — after tester PASS:
    - If `keep-local` (alias `no-ship`) is active: emit `SHIP: declined`, skip ship,
      skip automatic pr-review, skip UAT, and finish.
    - Otherwise, execute the automatic ship procedure below (commit, push `BRANCH`, PR).
    - On `SHIP: blocked`, halt with the blocker; do not launch pr-reviewer; MUST NOT
      infer `keep-local` from blocked ship.
    - On `SHIP: ok`, proceed automatically to PR review.
12. **PR review** — after `SHIP: ok`, launch `pr-reviewer` automatically as a loop
    state (host Task, Validation-profile model, fresh session). Follow
    `<AINATIVE>/docs/agents/pr-reviewer/SKILL.md`. `pr-reviewer` evaluates
    architecture, risk, and evidence on the opened PR (automatic loop state on this
    path, not on-demand).
    Parent routes on the compact header:
    - `VERDICT: APPROVE`, or `VERDICT: REQUEST CHANGES` with `CRITICAL_COUNT: 0` →
      route as APPROVE for the loop; park for operator UAT pass/fail (does not
      complete the run; merge stays human).
    - `VERDICT: REQUEST CHANGES` with `CRITICAL_COUNT ≥ 1` → parent feeds Criticals
      to converge as `$ARGUMENTS = VALIDATOR_CRITICALS` (parent MUST NOT feed validator
      Criticals directly to implement). Converge appends tasks →
      `implement ↔ converge` loop → `critic` → `tester` → same-PR ship →
      `pr-reviewer` re-review with `--extra @<previous-review>.md`.
    - `VERDICT: BLOCKED` (Phase 1.5 architecture block) → park (not a REQUEST CHANGES retry).
    Worker MUST NOT ship, merge, write `tasks.md`, or dispatch converge/implement.
13. **UAT** — after PR review APPROVE (or zero Criticals), park for operator UAT.
    - UAT pass: complete the run.
    - UAT fail: halt with findings (v1 does not auto-loop UAT).

### Change path

3. **Change** — spawn the resolved worker backend (`pi-harness` or `antigravity-harness`) with the resolved worker
   flags. Tell it to follow `<AINATIVE>/docs/agents/change/SKILL.md`
   with `STEP: change`. Pass `REPO_ROOT` (the feature `WORKTREE` from
   ready), `FLOW_ID`, `BRANCH`, `TASK_DESCRIPTION`, and `ATTEMPT`. On
   `SCOPE: feature`, stop and tell the user the task needs the feature path
   (re-run with `path: feature`). Do not switch paths on your own.
4. **Tester** — launch a fresh `generalPurpose` worker with the
   resolved validation model (fresh session; never the change worker's model). Tell it to follow the same skill with
   `STEP: tester` (no critic, no `LOOP_BACK`), and pass the change report. On `TESTER: FAIL`, launch a new
   change worker with the `FINDINGS` and the next `ATTEMPT`, then test again.
   This counts toward the change step's 3-attempt stuck limit (never converge, never `tasks.md`).
5. **Ship** — after `TESTER: PASS`, run the shared **Ship / UAT**
   procedure below automatically (no confirmation prompt).
   - If `keep-local` (alias `no-ship`) was passed: emit `SHIP: declined`, skip ship and pr-review, and finish.
   - On `SHIP: blocked`, halt with the blocker; do not launch pr-reviewer; MUST NOT infer `keep-local` from blocked ship.
   - On `SHIP: ok`, proceed automatically to PR review.
6. **PR review** — launch `pr-reviewer` automatically as a loop state (host Task, Validation profile, fresh session).
   - `VERDICT: APPROVE` or `REQUEST CHANGES` with `CRITICAL_COUNT: 0` → UAT park.
   - `REQUEST CHANGES` with `CRITICAL_COUNT ≥ 1` → retry change worker with FINDINGS (no `tasks.md`, no converge) → tester → same-PR ship → re-review.
   - `BLOCKED` → park.
7. **UAT** — operator exercises the PR: UAT pass completes; UAT failure halts with findings.

### Job path

3. **Job** — spawn the resolved worker backend (`pi-harness` or `antigravity-harness`) with the resolved worker
   flags. Tell it to read `SKILL_PATH` from route-work and
   follow it exactly, with the user args verbatim as the task input, and
   pass `REPO_ROOT` (the feature `WORKTREE` from ready). Tell it to write
   outputs inside `REPO_ROOT` and not to commit, push, or open a pull
   request. If the skill needs answers from the user, the worker returns
   `STATUS: blocked` with a question queue; relay the questions one at a time
   and resume or relaunch the worker with the answers. If the worker reports
   the task is really a code change, stop and tell the user; do not switch
   paths on your own.
4. **Ship** — after named skill `STATUS: ok`, run the shared **Ship / UAT** procedure
   below automatically (no confirmation prompt), unless the operator passed
   `keep-local` (alias `no-ship`). For jobs, after named skill `STATUS: ok` → ship (or declined); MUST NOT run pr-reviewer; UAT is not a job-path stage.
5. **Complete** — report the skill used, the artifacts, and the PR URL when
   published.

## Ship / UAT (parent only; job skips UAT)

Feature enters this procedure after `TESTER: PASS` (following `CRITIC: PASS`); change
enters after `TESTER: PASS`; job enters after `STATUS: ok`.

**Ship is automatic and asks no confirmation.** Once the path's validation
gate passes, the parent commits, pushes, and opens a PR. The PR *is* the
review surface: the operator reviews the concrete diff and walkthrough, not the
intent beforehand. Merge is never part of this loop — the parent never merges
anything, on any path. Human judgment keeps exactly two gates: UAT on the open
PR, and merge (outside the loop).

Opt out with the `keep-local` keyword (alias `no-ship`, see **Keywords**): when present, skip
ship, emit `SHIP: declined`, skip automatic pr-review and UAT, and finish.

**Pre-push guards — all must hold before pushing; otherwise `SHIP: blocked`:**

- Path validation passed (feature: critic PASS then tester PASS; change:
  `TESTER: PASS`; job: `STATUS: ok`).
- `BRANCH` is a topic branch, never a protected base branch (`main`, `master`,
  `develop`, `development`, or another protected name).
- The remote is the project's expected `origin`.
- No obvious secret material is staged (`.env`, credential files, keys). If
  found, stop and report rather than push.

**Ship action (First ship vs same-PR ship):**

1. **First ship of the run:**
   - Commit and push from `WORKTREE` on `BRANCH` using Conventional Commits. Run Git as `git -C <WORKTREE>`.
   - Never commit to or push the protected base branch.
   - Restamp the local tester manifest (`specs/<flow>/evidence.md`) with the pushed commit SHA (`git rev-parse HEAD`), re-running any HEAD-sensitive validation commands (such as section 1 touch list) on the pushed SHA so captures match that head, leaving the restamp uncommitted per validation-layer evidence hygiene (`specs/*/evidence.md` and `specs/*/evidence/` in `.gitignore`).
   - Create a PR with `gh pr create`. Do not invent a second PR.
   - The PR body must follow the host PR template when present (Cursor-only:
     `~/.cursor/skills/pr-generate/template.md`, not an AiNative agent) and always
     include a mandatory `## Walkthrough` section with step-by-step human
     instructions. Source the walkthrough from plan test flows, `quickstart.md`,
     and the implement summary. Once a PR exists, the walkthrough is required, not
     optional — it is what the operator reviews.
   - The PR body must also include a mandatory `## Evidence` section alongside
     `## Walkthrough`, sourced from the tester manifest `specs/<flow>/evidence.md`
     (where `<flow>` is the Spec Kit feature directory basename from `.specify/feature.json`): publish that
     acceptance-criterion table (restamped to the pushed commit SHA without making a SHA-only follow-up commit), inline small PNG/JPEG screenshots that exist
     locally, and reference bulky captures (traces, videos) by the documented CI
     workflow artifact name (or the URL when CI has already produced it). Do not
     wait for CI to finish before opening the PR. With no usable manifest
     (missing, empty, or invalid), still include `## Walkthrough` and report
     `EVIDENCE: none`. Evidence never replaces the walkthrough.
   - Emit `SHIP: ok` with `PR: <url>`.

2. **Reuse (same-PR ship):**
   When `PR` is already set for this run (or `gh pr view --head <BRANCH>` shows an open PR created by this run):
   - Commit pending work on `BRANCH` in `WORKTREE` using Conventional Commits (same secret and pre-push guards).
   - Push `BRANCH` via `git -C <WORKTREE> push origin <BRANCH>` (normal push; do not force-push unless existing ship policy already requires it).
   - Restamp the local tester manifest (`specs/<flow>/evidence.md`) with the pushed commit SHA (`git rev-parse HEAD`), re-running any HEAD-sensitive validation commands (such as section 1 touch list) on the pushed SHA so captures match that head, leaving the restamp uncommitted per validation-layer evidence hygiene.
   - Refresh the existing PR body: keep the same PR URL; update `## Walkthrough` and publish that table in PR `## Evidence` without making a SHA-only follow-up commit.
   - Do **not** call `gh pr create` (MUST NOT open a second PR; do not invent a second PR).
   - Emit `SHIP: ok` with the **same** `PR:` URL.
   - Re-review after reuse: launch `pr-reviewer` against that PR URL with `--extra @<previous-review>.md` pointing at the previous review report artifact (`REPORT` from the prior compact header).

After the parent completes the ship action, emit:

```text
SHIP: ok | blocked | declined
PR: <PR URL, or none>
WALKTHROUGH: <included | none | blocked>
EVIDENCE: <included | none>
SUMMARY: <what shipped, why it was kept local, or what blocked>
```

`EVIDENCE: included` means the PR body carries a usable `## Evidence` from
the manifest (allowed even when the tester verdict was FAIL); `EVIDENCE: none`
means no usable manifest (missing, empty, or invalid). It is added — the
existing `SHIP`, `PR`, `WALKTHROUGH`, and `SUMMARY` fields stay.

After `SHIP: ok`, for feature and change paths, the parent launches `pr-reviewer`
automatically as a loop state. After PR review completes with APPROVE
(or zero Criticals), the parent parks for operator UAT:

- **A — UAT pass:** complete the pipeline.
- **B — UAT fail:** halt with the findings. In v1, do not loop back to
  implement.

Do not run UAT or pr-reviewer after a job ship, nor after `SHIP: blocked` or `SHIP: declined`.
A ship failure is `SHIP: blocked`, not an implicit keep-local decision; report
the blocker and stop (MUST NOT infer `keep-local` from blocked ship). `SHIP: declined` means only the `keep-local` (alias `no-ship`) opt-out.
Workers do not commit, push, create PRs, write walkthroughs, or perform UAT on
any path.

## Worker launches

Required `model` on every worker (always pass the resolved value; never omit
it; never pass `inherit` on Tasks). Resolve the value per run from **Model
resolution (runtime-owned, no pinned values)** above:

| Stage | Profile / spawn |
| --- | --- |
| ready, route, specify, clarify, plan, tasks, analyze | **Reasoning** — host Task with `model` = resolved Reasoning-profile model (plan-reviewer, when used, pinned to the same model as plan) |
| implement, converge, change, job | **Worker** — resolved backend (`pi-harness` or `antigravity-harness`) with resolved `--model` (fallback may specify HOST: host Task with fallback model) |
| critic, tester, pr-reviewer | **Validation** — host Task with `model` = resolved Validation-profile model, fresh session (distinct from Reasoning/Worker when available) |

Pass the resolved values exactly as resolved. If the resolved value for that
profile cannot be used, use the runtime's distinct fallback for that profile if one
exists; otherwise stop. If both the resolved value and the runtime fallback
fail, stop. Never substitute an invented slug or Pi model outside the
resolution order above.

Reasoning- and validation-stage workers must be a foreground `generalPurpose` Task with
`run_in_background: false` (or the host equivalent: OpenCode subagent /
Hermes worker session with the resolved reasoning or validation model;
validation always in a fresh session). Worker stages must run as the resolved backend via `pi-harness` or `antigravity-harness`.
Do not create or retain per-command agents.
Each worker starts with empty context, so include all of the following in its
prompt:

- `FLOW_ID`
- repository root — for every stage after ready this is the feature
  `WORKTREE` from ready, not the original `REPO_ROOT` — plus `BRANCH` and
  `FEATURE_DIR` when known (do not treat `BRANCH` as the spec directory)
- the user's arguments verbatim, including whether **skip** is active
  (if it is, the specify and clarify workers must not ask the user; document
  assumptions or pick recommended options)
- the current iteration or attempt number
- the relevant prior report (implement/converge summary, change report,
  tester findings)
- the relevant open tasks and findings
- the skill file to read and follow exactly (AiNative-first per **Skill path resolution**; hosts resolve via symlink/mount):
  - ready: `<AINATIVE>/docs/agents/speckit-ready/SKILL.md`
  - route: `<AINATIVE>/docs/agents/route-work/SKILL.md`
  - critic: `<AINATIVE>/docs/agents/critic/SKILL.md`
  - tester: `<AINATIVE>/docs/agents/tester/SKILL.md` (or change-path tester via `<AINATIVE>/docs/agents/change/SKILL.md` plus `STEP: tester`)
  - pr-reviewer: `<AINATIVE>/docs/agents/pr-reviewer/SKILL.md`
  - change / tester: `<AINATIVE>/docs/agents/change/SKILL.md` plus `STEP`
  - job: the `SKILL_PATH` from route-work (already AiNative-first resolved)
  - feature stages: the project's `REPO_ROOT/.pi/prompts/speckit-<step>.md`
    (legacy fallback: `REPO_ROOT/.cursor/skills/speckit-<step>/SKILL.md`)
- specify after ready: the `FLOW_ID` + `BRANCH` + `WORKTREE` precedence rule
  for `before_specify` (branch/worktree creation only)

Tell each worker to return its compact report in the format below (ready,
route, change, and tester use the formats in their own skills). Workers read
specification, plan, and task files from disk; do not paste those files into
their prompts.

Ready returns:

```text
READY: ok | blocked
FLOW_ID: <flow_id>
BRANCH: <branch-name-created-or-reused>
WORKTREE: <absolute feature worktree path, or REPO_ROOT when already on the branch>
CHECKS:
- [required] git-branch-state: pass|fail — <note>
- [required] speckit-layout: pass|fail — <note>
FIXES:
- <only when blocked>
```

Route returns:

```text
FLOW_ID: <flow_id>
ROUTE: feature | change | job
SKILL: <skill name, or none>
SKILL_PATH: <absolute path, or none>
WHY: <one or two sentences>
```

Feature stages and job return:

```text
FLOW_ID: <flow_id>
ARTIFACTS: <paths produced or updated>
STATUS: ok | stuck | blocked
SUMMARY: <one paragraph>
```

Implement returns:

```text
FLOW_ID: <flow_id>
IMPLEMENT_STATUS: completed | partial | failed | blocked
TASKS_DONE: <ids or "unknown">
TASKS_OPEN: <ids or "none">
BLOCKER: <none or one paragraph>
SUMMARY: <what was implemented; files touched; tests and result>
```

Converge returns:

```text
FLOW_ID: <flow_id>
CONVERGE_OUTCOME: converged | tasks_appended | blocked
FINDINGS: <none, or one line per finding: ID | gap-type | severity | source-ref | remaining work>
FINGERPRINT: <sorted source-refs> | <sorted validator-ids or "none">
PHASE_APPENDED: <none or "Phase N">
TASKS_APPENDED: <none or new task IDs>
BLOCKER: <none or one paragraph>
SUMMARY: <counts checked; gap-type counts; whether tasks.md was written>
```

- Source-refs in FINDINGS / appended tasks: spec/plan/constitution only (`FR-###`, `US#/AC#`, `plan: …`, `Constitution …`).
- Validator IDs appear in the task description only (`[tester: flow-2]`, `[critic: C1]`, `[pr-review: C1]`); MUST NOT invent PR-review source-refs.
- `$ARGUMENTS` when the parent sends validator Criticals:
  ```text
  VALIDATOR_CRITICALS:
  - source: critic|tester|pr-review
    id: C1
    summary: <one line>
    suggested_source_ref: FR-### or US#/AC#
  ```

Critic returns:

```text
FLOW_ID: <id>
CRITIC: PASS | FAIL
LOOP_BACK: implement | plan | none
FINDINGS: <none, or one line each: ID | severity | file:line | summary>
SUMMARY: <one paragraph>
```

- PASS ⇒ `LOOP_BACK: none`.
- FAIL ⇒ `LOOP_BACK: implement` or `plan`. If findings mix both targets, emit `plan` (parent parks).
- Finding `ID` values are validator finding IDs (`C1`, …).
- Worker MUST NOT write `tasks.md` or launch tester/ship.

Tester returns:

```text
FLOW_ID: <id>
TESTER: PASS | FAIL
LOOP_BACK: implement | plan | none
EVIDENCE: specs/<flow>/evidence.md
FINDINGS: <none, or one line each: flow-id | problem | fix needed>
SUMMARY: <one paragraph>
```

- PASS ⇒ `LOOP_BACK: none`.
- FAIL ⇒ same LOOP_BACK rules as critic. Assertion/code failures default to `implement` when omitted.
- `<flow>` is the Spec Kit feature directory basename from `.specify/feature.json`, not `BRANCH`.

pr-reviewer returns:

```text
FLOW_ID: <id>
VERDICT: APPROVE | REQUEST CHANGES | BLOCKED
CRITICAL_COUNT: <integer>
CRITICALS: <none, or one line each: ID | file:line | trigger | summary>
REPORT: <path to the full markdown report>
SUMMARY: <one paragraph>
```

- `VERDICT: REQUEST CHANGES` with `CRITICAL_COUNT: 0` is routed as APPROVE for the loop.
- `BLOCKED` is Phase 1.5 only.
- Merge gate remains Critical-only (Warning/Suggestion never change `VERDICT`).
- Re-review: parent passes previous `REPORT` via `--extra @<previous-review>.md`.
- Worker MUST NOT ship, merge, write `tasks.md`, or dispatch converge/implement.

## Stuck policy

Track failures per step and iteration. A worker crash, empty or unparseable
report, unresolved implement failure, `TESTER: FAIL` after a change retry, or
repeated converge fingerprint is stuck. Retry the same step up to three
attempts total: the original attempt plus two resume or relaunch attempts
carrying the failure text and an instruction to fix it and finish. After the
third attempt, halt and ask the user. A repeated fingerprint is the same stuck
point even if the iteration number changed. An unchanged fingerprint across
original + two resumes parks.

Ready and route worker crash or empty/unparseable report may use that
3-attempt retry. Do **not** retry a stable `READY: blocked` (required check
failed the same way a second time would: missing file, unsafe branch state,
ambiguous/unresolved base branch, malformed `ready.yml`).

Do not retry these cases:

- `READY: blocked` for a stable required-check failure — show `FIXES` and wait
- `ROUTE: job` with no usable skill — say which skill is missing and wait
- `SCOPE: feature` from a change worker — tell the user and wait
- missing `spec.md`, `plan.md`, or `tasks.md`
- a checklist gate where the user has not answered yes/proceed/continue
- a constitution or policy block requiring a human decision
- a worker explicitly asking the user a question it cannot answer
  (**exception:** specify/clarify questions while **skip** is active — tell
  the worker to self-answer and finish; do not halt. **exception:** a clarify
  or job worker that returned `STATUS: blocked` with a question queue — the
  parent relays those questions to the user, then resumes the worker with the
  answers; that is not stuck)
- a Reasoning- or Validation-profile stage resolved model and its runtime fallback both remain unavailable,
  inaccessible, or could not be opened (see **Model access and fallback**)
- a Worker-profile stage resolved Pi flags and runtime fallback both failed (Pi missing, provider
  or auth failure, job hung, or unusable report)
- `LOOP_BACK: plan` (or mixed implement+plan) from critic or tester — park
- `CONVERGE_OUTCOME: converged` while a validator FAIL is still open — park immediately (do not continue critic/tester/pr-review)

For these cases, stop immediately and tell the user the prerequisite,
decision, or model problem required.

Treat `CONVERGE_OUTCOME: blocked` as an immediate stop (park immediately). Treat
`CONVERGE_OUTCOME: tasks_appended` as progress only when it adds new remaining
work; an unchanged fingerprint follows the stuck policy (three unchanged attempts park). Only
`CONVERGE_OUTCOME: converged` is a successful exit.

During the loop, keep updates short: iteration number, implement status,
converge outcome, and finding count. On `CONVERGE_OUTCOME: converged`, state
that the feature satisfies the specification, plan, and tasks, give the number
of iterations, then launch critic; launch tester only after critic PASS; ship
only after tester PASS (unless `keep-local`); launch pr-reviewer automatically
after `SHIP: ok`; and park for UAT only after pr-reviewer APPROVE or zero
Criticals. On a stop, state the failed step, attempt count,
worker report, actions already tried, and what the user must do next.

Do not handle constitution, checklist, taskstoissues, or other commands outside
this pipeline.

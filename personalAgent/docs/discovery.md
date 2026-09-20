# Discovery — Hermes 0.20 as installed

Written during project bootstrap (2026-08-28). Inspected the **running machine and `hermes-agent:local` image**, not upstream docs. Implementation must follow this install.

## Where things live

| Thing | Path / value |
|---|---|
| This repo (confirmed) | `/Users/emad/Projects/playground/agenticCoding/personalAgent` |
| Isolated Hermes home (confirmed) | `~/.hermes/personal-agent` |
| Existing live Hermes (do not mount for V0) | `~/.hermes` |
| AiNative | `/Users/emad/Projects/playground/agenticCoding/AiNative` @ `a747a8f` |
| Image | `hermes-agent:local` (created 2026-08-27), Hermes **0.20.3 / 0.20.6** |
| Image workdir | `/opt/hermes`, `HERMES_HOME=/opt/data` |
| Official compose | `network_mode: host`, `command: ["gateway", "run"]`, `~/.hermes:/opt/data` |
| 9router | container `9router` on `:20128` (OpenAI-compatible; API key required) — optional, not required |

`personalAgent` did not exist at the spec path. `/Users/emad/Projects/playground/personalAgent` is an empty `config/` stub and was **not** reused.

The spec's sample compose (`MODEL_NAME=NousResearch/Hermes-2-Pro-Llama-3-8B`, port `8001:8000`) does **not** match this install. Use the 0.20 gateway image.

## Hermes capabilities already present

Do not rebuild these. Adapter/orchestrator only where the native mechanism is missing.

**Kanban** (`~/.hermes/kanban.db` schema — same engine will init in the isolated home):

- Tasks: status, priority, assignee, body, tenant, session
- Dependencies: `task_links`
- Claims: `claim_lock`, `claim_expires`, `worker_pid`
- Heartbeat: `last_heartbeat_at`
- Retries / circuit breaker: `consecutive_failures`, `max_retries`, `last_failure_error`
- History: `task_runs`, `task_events`, `task_comments`, `task_attachments`
- Workspace: `workspace_kind`, `workspace_path`, `branch_name`, `project_id`
- Workflow stubs: `workflow_template_id`, `current_step_key` (v1 kernel stores them; dispatcher does not route on them yet)
- Per-task: `skills`, `model_override`, `provider_override`, `reasoning_effort`, `goal_mode`
- Blocks: `block_kind`, `block_recurrences` (dependency vs human-blocked vs triage loop limit)
- Telegram: `kanban_notify_subs`

**Projects** (`projects.db`): `projects`, `project_folders`, `discovered_repos`.

**Messaging**: Telegram is a first-class Hermes platform plugin (`platform_toolsets.telegram: hermes-telegram`). Gateway already exists. Extend events; do not add a second bot.

**GitHub**: skills under `~/.hermes/skills/github/` (`github-pr-workflow`, `github-issues`, `github-auth`, …).

**Workers**: dispatcher spawns workers with claim locks, heartbeats, failure limits, optional Ralph-style `goal_mode`.

## Live model config (existing `~/.hermes`, not this project's home)

- Provider: OpenRouter
- Default model: `deepseek/deepseek-v4-flash-0731`
- Confirmed product decision: configure models **inside Hermes**; optional `OPENAI_BASE_URL` + `OPENAI_API_KEY` for any OpenAI-compatible API. Do not hardcode 9router.

## AiNative (read-only dependency)

Agents are documentation/instruction folders (`AGENTS.md` + `SKILL.md` + `rule.md`), not executable processes. Cursor commands are a human harness. The adapter must turn agent definitions into Hermes worker prompts.

Current agents: critic, plan-reviewer, pr-reviewer, project-bootstrapper, scout, specs-planner, task-groomer, tester, prd-writer.

`specs-planner` uses specs.md FIRE. This control-plane **repo** is not installing specs.md (owner decision). Managed projects may still use whatever methodology AiNative defines.

## Gaps V0 still has to build

Hermes does not already provide:

- AiNative discovery/load/versioning adapter
- Project context loading from repo manifests / conventions
- PIV orchestrator (plan → implement → validate with no plan-approval gate)
- Git safety wrapper (never push main/master; never share dirty worktrees)
- PR creation as an orchestrator-owned GitHub boundary (builder must not push)
- Structured execution-state overlay if native fields are insufficient
- Lesson capture classified as PROJECT_SPECIFIC / GLOBAL_AINATIVE / TRANSIENT (proposals only)
- Fixture repo + failure-injection tests
- Isolated worktree layout under configurable `WORKSPACE_ROOT`

## Sibling projects (do not merge)

- `jobHunter/docker-compose.yml` — isolated `~/.hermes/jobhunter`, `nousresearch/hermes-agent:latest`, gateway ports 8642/9119
- `northStar/hermes-openproject` — different product: OpenProject is task SoT; Python 3.12 + uv + Spec Kit

## Decisions made during bootstrap

- Repo: `agenticCoding/personalAgent`
- Hermes home: isolated `~/.hermes/personal-agent`
- Models: Hermes-native config; optional OpenAI-compatible env
- Planning framework for this repo: not specs.md (owner will add another)
- Language: Python 3.12 + uv (matches Hermes and the OpenProject sibling)
- No second database
- No feature code in the scaffold commit

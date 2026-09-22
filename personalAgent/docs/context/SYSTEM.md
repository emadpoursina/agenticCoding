# Hermes runtime environment

> **Reference copy** for this repository. Hermes does **not** load this file
> at startup. The live file is private:
> `/opt/data/hermes-context/SYSTEM.md`
> (on the Mac: `/Users/emad/.hermes/personal-agent/hermes-context/SYSTEM.md`).
> `SYSTEM.example.md` remains the blank starter template.
> Keep secrets out of both copies.

This file describes the current Hermes install on this Mac, as seen from
inside the Docker container named `hermes-personal-agent`. It is environment
only. Hermes identity and operating rules live in `AGENTS.md`. Operator
preferences live in `USER.md`.

Use the **container paths** below. Do not guess. Do not use Mac home paths
such as `/Users/emad/...` in container commands.

Live settings in Compose, environment, and `/opt/data/config.yaml` win if
they disagree with this file.

Keep secrets in the mounted environment (`.env` and Hermes config). Never
put passwords, API keys, tokens, or private keys here.

Hermes loads this live file at startup. Do not copy its body into Kanban,
overlay records, task worktrees, or project repositories. Check registration
with:

```text
python -m hermes_kanban --config /opt/personal-agent/config/default.yaml --doctor
```

## This install

- Host computer: macOS (Darwin), user home `/Users/emad`
- Time zone: Pacific Time (`America/Los_Angeles`)
- Hermes runs in Docker, container `hermes-personal-agent`, image `hermes-agent:local`
- Hermes version seen in the running container: **0.21.0**
- Hermes private data on the Mac: `/Users/emad/.hermes/personal-agent`
- That folder is mounted in the container as `/opt/data` (`HERMES_HOME`)
- This file’s container path: `/opt/data/hermes-context/SYSTEM.md`
- Operator preferences (same folder): `/opt/data/hermes-context/USER.md`
- Do **not** write to `/Users/emad/.hermes` (the older default Hermes home).
  This project uses the isolated `personal-agent` home only.
- Hermes instructions (identity): `/opt/personal-agent/AGENTS.md`

## Container paths Hermes should use

| Purpose | Container path |
| --- | --- |
| Hermes app / this package (read-only) | `/opt/personal-agent` |
| Hermes instructions | `/opt/personal-agent/AGENTS.md` |
| Hermes Kanban config | `/opt/personal-agent/config/default.yaml` |
| Hermes private data | `/opt/data` |
| This file | `/opt/data/hermes-context/SYSTEM.md` |
| Operator preferences | `/opt/data/hermes-context/USER.md` |
| Hermes model/runtime config | `/opt/data/config.yaml` |
| Kanban database | `/opt/data/kanban.db` |
| Project registry | `/opt/data/projects.db` |
| Pi agent data | `/opt/data/pi-agent` |
| GitHub CLI config (when used) | `/opt/data/.config/gh` |
| AiNative methodology (read-only) | `/ainative` |
| AiNative agent definitions | `/ainative/docs/agents/` |
| Task workspaces | `/workspaces` |
| Enrolled project `ich-mag-dich` | `/workspaces/ich-mag-dich` |
| Hermes overlay / operational state | `/var/lib/hermes-kanban` |
| Pi coding harness runtime | `/opt/pi-runtime` |
| Official Hermes install inside the image | `/opt/hermes` |
| SSH agent socket (no private keys in the image) | `/run/host-services/ssh-auth.sock` |

## Host-to-container mounts

Hermes code must use the container side. The Mac side is listed only so
paths are not mixed up.

| On the Mac | Inside the container | Notes |
| --- | --- | --- |
| `/Users/emad/.hermes/personal-agent` | `/opt/data` | Private Hermes home, read-write |
| `/Users/emad/Projects/playground/agenticCoding/personalAgent` | `/opt/personal-agent` | This project, read-only |
| `/Users/emad/Projects/playground/agenticCoding/AiNative` | `/ainative` | Methodology, read-only |
| `/Users/emad/Projects/playground/agenticCoding/personalAgent/workspaces` | `/workspaces` | Task workspaces, read-write |
| Docker volume `personalagent_hermes-overlay` | `/var/lib/hermes-kanban` | Overlay state, not a Mac folder |
| Docker Desktop SSH helper | `/run/host-services/ssh-auth.sock` | Agent forwarding only |

## Settings (no secrets)

- Active coding harness: **pi** (`HERMES_PI_RUNTIME=/opt/pi-runtime`)
- Pi version seen in the container: **0.84.3**
- Live workflow: the feature loop (see `/ainative/docs/systems/feature-loop.md`; one new Pi session per agent state)
- Workspace root: `/workspaces`
- AiNative is read-only. Never write into `/ainative`.
- GitHub: SSH agent forwarding; optional `GH_TOKEN` from the environment,
  not from this file. Do not push `main`/`master`. Do not merge unless
  asked. Do not copy private keys into the image.
- Web UI (on the Mac): http://localhost:9119 (port 9119 in the container).
  Sign-in details stay in `.env`, not here.
- Optional OpenAI-compatible endpoint is configured via environment
  (`OPENAI_BASE_URL`). Do not store keys in this file.
- Named model profile inside Hermes config: `DeepSeekFlash` (provider
  `custom`). Treat live Hermes config as authority for models.
- Telegram notifications are enabled in the Kanban config. Connection
  details stay in Hermes private config, not here.
- Python package path: `PYTHONPATH=/opt/personal-agent/src`

## Approved limits

- One coding job at a time (`max_concurrent_tasks: 1`)
- Up to 3 retries
- Harness timeout: 1800 seconds
- Do not modify AiNative automatically
- Do not deploy, merge protected branches, or place trades
- Do not auto-create missing `SYSTEM.md` or `USER.md`

## Known agents (AiNative, read-only)

Available under `/ainative/docs/agents/`:

critic, plan-reviewer, pr-reviewer, prd-writer, project-bootstrapper,
scout, task-groomer, tester, template

`project-bootstrapper` is an AiNative agent folder, not a Hermes skill
unless it is later installed as one. Discover the live roster with
`--doctor`; do not search Hermes skill roots for these names.

## Operator notes to complete later

- [ ] Any extra folders that should be treated as off-limits besides
      `/ainative` and the default Hermes home at `~/.hermes`
- [ ] Any extra enrolled projects besides `ich-mag-dich`

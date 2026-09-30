# Hermes runtime environment

> **Reference copy** for this repository. Hermes does **not** load this file
> at startup. The live container's identity is `/opt/data/SOUL.md`.
> The private Hermes home on the Mac is `~/.hermes-personal-coding`.
> `SYSTEM.example.md` remains the blank starter template.
> Keep secrets out of both copies.

This file describes the current Hermes install on this Mac, as seen from
inside the Docker container `hermes-personal-coding`. It is environment
only. Identity and operating rules live in `AGENTS.md` and `/opt/data/SOUL.md`.
Operator preferences live in `USER.md`.

Use the **container paths** below. Do not guess. Do not use Mac home paths
such as `/Users/emad/...` in container commands.

Live settings in Compose, environment, and `/opt/data/config.yaml` win if
they disagree with this file.

Keep secrets in the mounted environment (`.env` and Hermes config). Never
put passwords, API keys, tokens, or private keys here.

## This install

- Host computer: macOS (Darwin), user home `/Users/emad`
- Time zone: Pacific Time (`America/Los_Angeles`)
- Hermes runs in Docker: container `hermes-personal-coding`, image
  `hermes-personal-coding:local` (built from `nousresearch/hermes-agent:latest`
  plus `gh`)
- Official Hermes install inside the image: `/opt/hermes`
- Hermes version seen in the running container: **0.21.0**
- Identity file Hermes loads at startup: `/opt/data/SOUL.md`
- Hermes private data on the Mac: `/Users/emad/.hermes-personal-coding`,
  mounted as `/opt/data` (`HERMES_HOME`)
- Model/runtime config: `/opt/data/config.yaml`
- Default model: `muse-spark-1.3-contributor` (provider `opencode-go`,
  base URL `https://opencode.ai/zen/go/v1`). Live config is authority.
- No managed/enrolled project is registered yet.
- No worker loop runs here; the native `hermes kanban` and
  `hermes project` CLIs exist but are unused until a project is enrolled.

## Container paths Hermes should use

| Purpose | Container path |
| --- | --- |
| Hermes private home (`HERMES_HOME`) | `/opt/data` |
| Hermes identity | `/opt/data/SOUL.md` |
| Model/runtime config | `/opt/data/config.yaml` |
| Kanban database | `/opt/data/kanban.db` |
| Project registry | `/opt/data/projects.db` |
| AiNative methodology (read-only) | `/opt/data/mnt/AiNative` |
| Task workspace (read-write) | `/opt/data/mnt/workspace` |
| Official Hermes install | `/opt/hermes` |
| Container `HOME` | `/opt/data/home` |
| Git config (read-only) | `/opt/data/home/.gitconfig` |
| SSH keys (read-only) | `/opt/data/home/.ssh` |

## Host-to-container mounts

Hermes code must use the container side. The Mac side is listed only so
paths are not mixed up.

| On the Mac | Inside the container | Notes |
| --- | --- | --- |
| `/Users/emad/.hermes-personal-coding` | `/opt/data` | Private Hermes home, read-write |
| `/Users/emad/hermes-workspace-personal-coding` | `/opt/data/mnt/workspace` | Task workspace, read-write |
| `/Users/emad/Projects/playground/agenticCoding/AiNative` | `/opt/data/mnt/AiNative` | Methodology, read-only |
| `/Users/emad/.ssh` | `/opt/data/home/.ssh` | Read-only |
| `/Users/emad/.gitconfig` | `/opt/data/home/.gitconfig` | Read-only |

## Settings (no secrets)

- AiNative is read-only. Never write into `/opt/data/mnt/AiNative`.
- Do coding work in `/opt/data/mnt/workspace` and its project directories.
  Do not write elsewhere unless Emad explicitly asks.
- Web UI (on the Mac): http://localhost:9119 (dashboard port 9119; the
  gateway is published on 8642). Sign-in details stay in `.env`, not here.
- GitHub over the read-only SSH mount; any token comes from the environment,
  not from this file.
- The managed-project feature-loop methodology is documented in AiNative
  (`/opt/data/mnt/AiNative/docs/systems/`); it is not wired into this install.

## Approved limits

- Work only inside `/opt/data/mnt/workspace` unless Emad explicitly asks.
- Do not modify AiNative.
- Do not commit secrets, copy SSH private keys into images, or print
  credentials.
- Do not push `main` / `master`, merge, deploy, or place trades unless Emad
  clearly asked for that specific action.

# Hermes Kanban

Operational control plane: Hermes runs Kanban, workspaces, GitHub, and Telegram. [AiNative](https://github.com/emadpoursina/AiNative) stays an external read-only methodology. Each managed software project keeps its own source of truth.

This repo is the environment scaffold and live Hermes PIV bridge. Native
Kanban remains the only task source; the package reads `kanban.db` read-only
and reuses the existing orchestrator, GitHub, and Telegram seams.
Card-body creation and editing belong to upstream Hermes Kanban; this
repository does not add a second writer or specifier. The upstream
specifier/groomer must preserve the exact `## Priority` heading with a value
of `P0`, `P1`, `P2`, or `P3`, plus `## Problem`, `## Expected Result`, and the
existing `## Platform`, `## Acceptance Criteria`, `## Technical Notes`, and
`## Dependencies` headings. This bridge rejects missing or invalid priority
instead of inventing fields.

Canonical plan: [`docs/v0-implementation-plan.md`](docs/v0-implementation-plan.md). Discovery of the live Hermes 0.20 install: [`docs/discovery.md`](docs/discovery.md).

## Stack

| Layer | Choice |
|---|---|
| Runtime | Docker Compose + existing `hermes-agent:local` (Hermes **0.20**) |
| Adapter language | Python 3.12 (`>=3.12,<3.14`) via uv |
| Task SoT | Hermes native Kanban (`kanban.db`) — no second task DB |
| Project registry | Hermes `projects.db` + config-backed operational settings |
| Methodology | AiNative mounted read-only at `/ainative` |
| Models | Named profiles mapped privately by Pi |
| Chat | Existing Hermes Telegram gateway (do not rebuild) |
| GitHub | SSH agent forwarding plus verified github.com host keys; `gh` via `GH_TOKEN` when provided |
| Tests | pytest + ruff |

## Project identity

The control plane keys every artifact by the operational project id in
`config/default.yaml` (`id: ich-mag-dich`). Hermes Kanban stores each card's
`project_id` as the native `projects.db` internal id (`p_…`) instead. Declare
the native id(s) as aliases so both forms resolve to the same project:

```yaml
projects:
  - id: ich-mag-dich
    name: emadpoursina/ich-mag-dich
    repository: github.com/emadpoursina/ich-mag-dich
    location: /workspaces/ich-mag-dich
    default_branch: master
    kanban_project_ids:
      - p_f1577341
```

Read the native id once, inside the container:

```bash
docker exec hermes-personal-agent \
  sqlite3 /opt/data/projects.db "select id, slug from projects;"
```

The bridge reads the native Kanban database read-only, translates a card's
native id to the operational id at the board boundary, and never writes
`projects.db` or `kanban.db`. On Hermes 0.21 the database is resolved per
enrolled project (`kanban/boards/<id>/kanban.db`), falling back to the
legacy single-`kanban.db` layout; `HERMES_KANBAN_DB` overrides both. An
undeclared id stays fail-closed: `--task` reports it, and `--next-ready`
names it instead of returning a bare "no ready task". `--doctor` lists each
project's declared aliases.

## Layout

```
src/hermes_kanban/   # live bridge, orchestrator, adapters, and dispatcher
tests/
config/              # operational defaults + Hermes config example
docs/
scratch/             # gitignored working notes
docker-compose.yml
```

## Local setup

```bash
cp .env.example .env          # edit host paths / optional OpenAI-compatible env
mkdir -p "$HOME/.hermes/personal-agent" ./workspaces
cp config/hermes.yaml.example "$HOME/.hermes/personal-agent/config.yaml"
# Put API keys in $HOME/.hermes/personal-agent/.env — never in git

uv python install 3.12
uv sync --extra dev
uv run pytest
```

Fill `HERMES_UID` / `HERMES_GID` in `.env` from `id -u` and `id -g`.

## Docker

```bash
docker compose up -d      # start
docker compose logs -f    # inspect logs
docker compose restart    # restart
docker compose down       # stop
```

Rebuild the Hermes image this stack uses (`hermes-agent:local`) from the official image:

```bash
docker build -t hermes-agent:local -f docker/Dockerfile .
docker compose up -d --force-recreate
```

Hermes web UI: [http://localhost:9119](http://localhost:9119) after `docker compose up -d`. Sign in with `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` / `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` from `.env` (see `.env.example`).

Hermes home is isolated at `~/.hermes/personal-agent`. The default `~/.hermes` board and Telegram state are not mounted.

Compose forwards the host SSH agent (`SSH_AUTH_SOCK`) into `hermes-personal-agent`. Do not copy private keys into the image and do not add a key volume.

The Hermes image includes a container-runnable Pi runtime and the configured
DeepSeekFlash OpenAI-compatible profile. Set the endpoint and key only in the
local `.env`:

```bash
OPENAI_BASE_URL=http://host.docker.internal:20128/v1
OPENAI_API_KEY=<local-api-key>
docker build -t hermes-agent:local -f docker/Dockerfile .
docker compose up -d --force-recreate
docker exec hermes-personal-agent pi --version
docker exec hermes-personal-agent pi --list-models 9router
```

The runtime is baked into the image, so a Pi installation that exists only on
the Mac is not used.

github.com SSH host keys live in `docker/ssh/github_known_hosts` (public keys from GitHub’s docs). The image and boot script install them so they survive container recreate. Do not use `ssh-keyscan` at start and do not set `accept-new`.

Optional GitHub CLI login: export `GH_TOKEN` on the host or set it in local `.env` (never in git). Compose passes it only from that value; the boot script logs `gh` in when it is non-empty. Rebuild `hermes-agent:local` after Dockerfile or boot-script changes.

## Startup context

Hermes validates three exact container paths before handling commands:

- `/opt/personal-agent/AGENTS.md` — versioned Hermes guidance
- `/opt/data/hermes-context/SYSTEM.md` — persistent runtime instructions
- `/opt/data/hermes-context/USER.md` — persistent operator preferences

The repository includes a blank starter at
`docs/context/SYSTEM.example.md` and `docs/context/USER.example.md`. Copy
them manually into the host directory mounted at `/opt/data`, then complete
the instructions.

A filled, non-secret **reference** of this machine’s `SYSTEM.md` is also in
`docs/context/SYSTEM.md` so it can be read in Git. Hermes still loads only
the private live file at `/opt/data/hermes-context/SYSTEM.md`.

```bash
mkdir -p "$HERMES_HOME/hermes-context"
cp docs/context/SYSTEM.example.md "$HERMES_HOME/hermes-context/SYSTEM.md"
cp docs/context/USER.example.md "$HERMES_HOME/hermes-context/USER.md"
```

Keep passwords and keys out of every copy. Hermes does not search fallback
paths or create missing files. Check the registration and safe revisions with:

```bash
docker exec hermes-personal-agent \
  python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --doctor
```

Live github.com proof (operator-named or disposable **non-critical** repo only; not required for pytest):

1. One-time: confirm fingerprints in `docker/ssh/github_known_hosts` match [GitHub’s SSH key fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints) (`ssh-keygen -lf docker/ssh/github_known_hosts`).
2. Set `SSH_AUTH_SOCK` in `.env` (Docker Desktop: `/run/host-services/ssh-auth.sock`; Linux: the host agent socket path). Optionally set `GH_TOKEN` the same way (host export or local `.env`). Recreate the container.
3. Handshake: `docker exec -it hermes-personal-agent ssh -T git@github.com`
4. If `GH_TOKEN` was provided: `docker exec -it hermes-personal-agent gh auth status`
5. Fetch the disposable remote from inside the container, then push **only** a feature branch (`git push origin HEAD:refs/heads/feature/...`). Never push `main`/`master`.

## Tests

```bash
uv run pytest
uv run ruff check src tests
```

## Dispatcher and live checks

The one dispatcher entry is available to an already-started Hermes worker and
to a shell. Compose mounts this package at `/opt/personal-agent` and sets
`PYTHONPATH=/opt/personal-agent/src`.

```bash
export HERMES_HOME="$HOME/.hermes/personal-agent"
python -m hermes_kanban --config /path/to/default.yaml --task TASK_ID
python -m hermes_kanban --config /path/to/default.yaml --next-ready
python -m hermes_kanban --config /path/to/default.yaml \
  --resume PROJECT_ID TASK_ID OPTION
```

The worker may set `HERMES_KANBAN_TASK` after Hermes claims a card. The
dispatcher allows that claimed `running` card only for the matching task id;
next-ready never starts parked or running cards.

## Harness execution

Hermes starts one generic harness run per work attempt. The default
configuration selects Pi and the `speckit-orchestrate` playbook:

```yaml
harness:
  adapters:
    - id: pi
      active: true
      runtime_path_env: HERMES_PI_RUNTIME
  playbook: speckit-orchestrate
  model_profile: default
  timeout_seconds: 1800
```

The runtime manifest must identify `adapter_id`, `version`, `revision`, and
the executable. Hermes starts that executable once as `pi --mode rpc` in the
task worktree, sends one JSON `prompt` command, privately consumes Pi's JSONL
responses/events until settlement, and extracts one structured result. The
checked-in timeout accepts positive finite numbers and numeric strings, with no
new maximum.

Pi owns the complete playbook: specify, clarify/continue, plan, tasks,
conditional analyze, and implement/converge. Native
`specs/<task-id>/spec.md`, `plan.md`, and `tasks.md` files stay in the
isolated task worktree. Hermes stores only the normalized result and safe
resume context on its existing overlay record. Pi has no operator chat,
publish, push, merge, deploy, or AiNative write access.

### Kanban worker contract

The process spawned by the Kanban gateway is only the bridge into this
control plane. With `HERMES_KANBAN_TASK` set, it must run:

```bash
python -m hermes_kanban --config /opt/personal-agent/config/default.yaml
```

That command starts Pi. The worker must not edit the managed project, run
implementation tests as a substitute for Pi, commit, push, open a pull
request, or mark the card complete from direct edits. If the command fails,
the worker reports the failure and stops; it must not fall back to coding the
card itself.

Questions return as `needs_human`. Hermes records answers, skip assumptions,
and the one continuation confirmation, then starts another whole harness run.
Three recoverable stuck attempts park for a human. A `completed` harness
result still requires the existing project validation before Hermes can
commit, push a feature branch, or create/update a pull request. Historical
records from the removed stage machine are parked and never auto-start Pi.
A human acknowledgement clears the legacy marker without starting Pi; the
next Hermes process then reclaims the task through the generic harness path.

The live smoke command is fail-closed. It requires an explicit disposable
`owner/name` that matches both the GitHub remote and the enrolled project
name, plus exactly one task selector, before any push or pull request:

```bash
python -m hermes_kanban --config /path/to/default.yaml \
   --smoke --repo owner/name --next-ready
# or: --smoke --repo owner/name --task TASK_ID
```

`--next-ready` is limited to eligible cards belonging to that validated
disposable project; it never searches other enrolled projects.

Automated checks stay hermetic and do not use GitHub, Telegram, a live model,
or the operator board:

```bash
uv run pytest tests/test_live_piv_bridge.py
uv run pytest tests/test_harness_adapter.py
uv run pytest tests/test_legacy_stage_removal.py
uv run pytest
uv run ruff check src tests
```

External credentials remain outside git: GitHub SSH agent forwarding, the
already-connected Hermes Telegram token/home chat, and the model-provider key.
The configured Pi runtime is provisioned at image build time or injected by
the offline fixture; task execution never installs or downloads a Python
dependency. Model and GitHub credentials remain outside git.
The bridge adds no worker, scheduler, Telegram event kind, task database, or
AiNative write path.

## V0 out of scope

- Obsidian, automatic merge, production deploy, concurrent workers
- Autonomous modification of AiNative

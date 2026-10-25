# agenticCoding

Workspace repo for an **AI-native engineering setup**: a personal engineering operating system (`AiNative/`) plus the Docker runtime that executes it (`personalAgent/`).

The methodology lives in docs; the runtime reads it. Neither is an application — there is no build step and no test suite to install.

```text
agenticCoding/
├── AiNative/        # Engineering OS — systems, agents, knowledge, records (docs)
├── personalAgent/   # Hermes agent runtime — Docker Compose, image, env
├── .agent/          # Runtime artifacts (handoffs, Pi run logs) — gitignored
└── README.md        # this file
```

---

## AiNative/ — the engineering OS

A structured, Git-versioned repository of knowledge, decisions, and operational patterns. Full spec: [AiNative/ENGINEERING-OS.md](./AiNative/ENGINEERING-OS.md). Overview: [AiNative/README.md](./AiNative/README.md).

Four doc layers, one decision each:

| Layer | Path | Contents |
|-------|------|----------|
| **Systems** | `AiNative/docs/systems/` | How you work — PR review, release management, agentic system, feature loop |
| **Agents** | `AiNative/docs/agents/` | Per-task AI agents (`AGENTS.md`, `SKILL.md`, `rule.md`) + shared `_skills/` |
| **Knowledge** | `AiNative/docs/knowledge/` | Evergreen reference — commands, setup, architecture patterns, snippets |
| **Records** | `AiNative/docs/records/` | Dated, append-only memory — debugging notes, ADRs, postmortems, evaluations |

Start at [AiNative/docs/README.md](./AiNative/docs/README.md) — it is a retrieval index ("when you need X, go to Y").

### Agents

Reusable agent definitions in `AiNative/docs/agents/` — orchestration (`speckit-orchestrate`, `route-work`, `task-groomer`), review (`pr-reviewer`, `plan-reviewer`, `critic`, `tester`), scaffolding (`prd-writer`, `project-bootstrapper`, `ready`), and harness adapters (`pi-harness`, `antigravity-harness`). Each agent folder ships `AGENTS.md` (behavior), `SKILL.md` (trigger/discovery), and often `rule.md`.

They are mirrored into Cursor as slash commands in `AiNative/.cursor/commands/` and symlinked into host harnesses via `AiNative/docs/knowledge/setup/link-host-skills.sh`.

### Checks

```bash
# Validate every relative link in the markdown docs (exits non-zero on breakage)
node AiNative/scripts/check-doc-links.mjs

# Install gate: can Hermes run? (mounts, keys, config, CLI, GitHub access)
bash AiNative/docs/knowledge/setup/hermes-readiness.sh [target-project]
```

### Rituals

| Ritual | When | Action |
|--------|------|--------|
| Capture | During work | Write raw notes in `AiNative/scratch/` (gitignored except its README) |
| Friday review | Weekly, 15 min | Promote notes to the right layer, update stale knowledge, delete junk |
| Event response | Bug / decision / incident | Debug note, ADR, or postmortem in `docs/records/` |

---

## personalAgent/ — the runtime

The live **Hermes agent** install: a Docker Compose service (`hermes-personal-coding`) that runs the agent gateway and reads AiNative **read-only** at `/opt/data/mnt/AiNative`. Coding work happens in `/opt/data/mnt/workspace`; all agent state lives under `HERMES_DATA_ROOT` (outside this repo).

Runtime docs: [AiNative/docs/knowledge/setup/harness.md](./AiNative/docs/knowledge/setup/harness.md).

### Run it

```bash
cd personalAgent
cp .env.example .env          # then fill in DASH_PASS / DASH_SECRET / GITHUB_TOKEN
docker compose up -d --build
```

| Port | Service |
|------|---------|
| `8642` | Hermes gateway |
| `9119` | Dashboard (basic auth) |

Notes:

- **HTTPS-only GitHub auth** — the container rewrites SSH remotes to HTTPS and authenticates with `gh auth git-credential`; no `~/.ssh` is mounted.
- `.env` and image pins are gitignored; only `.env.example` is tracked.
- Verify an install with `hermes-readiness.sh` (see above).

---

## Repository conventions

- **No monorepo tooling** — plain Git, no workspace manager, no build.
- **Conventional commits** — `type(scope): subject` (e.g. `docs(agents): ...`, `fix(ready): ...`).
- **Gitignored by design**: `.agent/` (runtime artifacts), `AiNative/scratch/*` (raw capture), all `.env` files.
- **One canonical location** — methodology lives in `AiNative/`, runtime config in `personalAgent/`; never copy a doc into the other.

---

## Getting started

1. Read [AiNative/ENGINEERING-OS.md](./AiNative/ENGINEERING-OS.md) — the architecture spec (5 min).
2. Browse [AiNative/docs/README.md](./AiNative/docs/README.md) — the retrieval index.
3. Bring up the runtime with `docker compose up -d --build` in `personalAgent/`.
4. Run `hermes-readiness.sh` to confirm the install is healthy.

# Knowledge

Evergreen technical knowledge — updated in place, no dates. Copy-paste code lives in [snippets/](./snippets/).

## Setup

| File | Topic |
|------|-------|
| [new-project.md](./setup/new-project.md) | Planning, PRD, development phases, design, deployment |
| [cursor-setup.md](./setup/cursor-setup.md) | MCP, rules, skills, indexing |
| [ponytail.md](./setup/ponytail.md) | Lazy-senior Cursor rule — `~/.cursor/rules/` for CLI; optional IDE symlink |
| [harness.md](./setup/harness.md) | Tmux + Cursor CLI — agent runtime layout (part 1 of agentic system) |
| [personal-agents-symlinks.md](./setup/personal-agents-symlinks.md) | `setup-machine.sh` / `setup-project.sh` — global commands + per-project agent symlinks |
| [server-setup.md](./setup/server-setup.md) | SSH keys, users, remote access |
| [local-shared-services.md](./setup/local-shared-services.md) | Local Docker databases (MariaDB, MongoDB, Adminer) |

## Commands

| File | Topic |
|------|-------|
| [linux.md](./commands/linux.md) | Users, disk, ufw, network, jq |
| [macos.md](./commands/macos.md) | Clipboard (cb2f — image file to clipboard) |
| [git.md](./commands/git.md) | Branches, stash, fetch |
| [docker.md](./commands/docker.md) | Containers, images, volumes, Dockerfile |
| [postgres.md](./commands/postgres.md) | psql, backup, restore |
| [mongodb.md](./commands/mongodb.md) | mongosh, create db/user, admin password, backup/restore |
| [nginx.md](./commands/nginx.md) | Log paths |
| [tmux.md](./commands/tmux.md) | Sessions, panes, shortcuts |

## Architecture

| File | Topic |
|------|-------|
| [backend-patterns.md](./architecture/backend-patterns.md) | Backend design notes |
| [database-patterns.md](./architecture/database-patterns.md) | Database design notes |
| [infra-patterns.md](./architecture/infra-patterns.md) | Infrastructure notes |

## Other

| File | Topic |
|------|-------|
| [backup-system.md](./backup-system.md) | Backup strategy and restore drills |
| [tools.md](./tools.md) | Software, websites, learning sources |

## Retrieval

| When you need... | Go to... |
|------------------|----------|
| A specific command | `commands/<tool>.md` |
| Project setup | `setup/` |
| Local databases (Docker) | `setup/local-shared-services.md` |
| Architecture patterns | `architecture/` |
| A working config or script | `snippets/<type>/` |
| Backup strategy | `backup-system.md` |

See [ENGINEERING-OS.md](../../ENGINEERING-OS.md) for the full retrieval map.

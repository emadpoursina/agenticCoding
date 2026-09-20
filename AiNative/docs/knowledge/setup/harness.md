# Harness

The **Harness** is where agents run — Tmux for session layout, Cursor CLI for the agent pane. It is part 1 of the [agentic system](../../systems/agentic-system.md).

Model, context, tools, and agents are configured separately. The Harness only provides a stable, repeatable runtime per project.

---

## Stack

| Component | Role |
|-----------|------|
| **Tmux** | One session per project; pane layout; attach/detach without killing agents |
| **Cursor CLI** | Agent pane — PIV commands, critic/tester |

Cursor rules, MCP, and commands: [cursor-setup.md](./cursor-setup.md).

---

## Layout

One **session** per project. One **window** in that session. Three **panes**, left to right:

```text
┌─────────────┬─────────────┬─────────────┐
│   Agent     │  Terminal   │  Services   │
│ Cursor CLI  │  shell      │  dev stack  │
└─────────────┴─────────────┴─────────────┘
```

| Pane | Purpose | Typical contents |
|------|---------|------------------|
| **Agent** | AI work — planning, implementation, validation agents | Cursor CLI session for the project |
| **Terminal** | Human shell — git, scripts, debugging, one-off commands | zsh in project root |
| **Services** | Long-running processes for this project | `npm run dev`, `docker compose up`, test watchers |

Keep services visible so you see crashes and port conflicts without scrolling the agent pane.

---

## Session conventions

- **Session name** — match the project (repo folder name or short alias).
- **Window name** — project name or `main`; one window is enough unless you add a dedicated debug layout later.
- **Working directory** — all three panes start in the project root.

### Create a session (manual)

```bash
PROJECT=myapp
tmux new-session -d -s "$PROJECT" -c "$HOME/path/to/$PROJECT"

# Three equal columns
tmux split-window -h -t "$PROJECT"
tmux split-window -h -t "$PROJECT:0.1"
tmux select-layout -t "$PROJECT" even-horizontal

# Pane 0: Agent — start Cursor CLI here after attach
# Pane 1: Terminal — default shell
# Pane 2: Services — start dev stack here

tmux attach -t "$PROJECT"
```

After attach, focus each pane and start the right process (Cursor CLI in pane 0, dev server in pane 2).

### Attach to an existing session

```bash
tmux ls
tmux attach -t myapp
```

Tmux shortcuts: [tmux.md](../commands/tmux.md).

---

## Why three panes

| Need | Pane |
|------|------|
| Agent should run autonomously | Agent — dedicated; no mixed shell output |
| You need git, scripts, or manual commands | Terminal — does not pollute agent context |
| Dev server or Docker must stay up | Services — always visible, restart without touching agent |

This matches PIV: Plan and Implementation in the agent pane; you intervene in Terminal; Validation and local testing assume Services are running.

---

## Related

- [agentic-system.md](../../systems/agentic-system.md) — five-part model (Harness is part 1)
- [cursor-setup.md](./cursor-setup.md) — MCP, rules, global commands, hooks
- [tmux.md](../commands/tmux.md) — attach, rename, shortcuts

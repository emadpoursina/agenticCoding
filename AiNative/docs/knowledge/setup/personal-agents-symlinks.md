# Personal agents via symlinks

Use one canonical AiNative checkout on your machine (`$AINATIVE_HOME`). **Commands** live globally in `~/.cursor/commands/` (set once). Each app project symlinks **rules and agent docs** from AiNative — no submodules, no per-project bump commits, no drift.

## Scripts

Both are idempotent — run to set up or to repair. Run them **from this checkout**. They wrap `scripts/ainative-link.mjs` and take home as `scripts/..`. A stale `$AINATIVE_HOME` is ignored when this tree is valid; it is only used if the scripts were copied elsewhere.

| Goal | Command |
|------|---------|
| **Machine** — global slash commands + alert hook | `./scripts/setup-machine.sh` |
| **Project** — agents/rules in one repo (new or old) | `./scripts/setup-project.sh ~/projects/my-app` |
| Status | `node ./scripts/ainative-link.mjs status` |

```bash
cd /path/to/AiNative
./scripts/setup-machine.sh                      # once per machine; re-run to fix
./scripts/setup-project.sh ~/projects/my-app    # new or old app repo
```

`setup-project.sh` keeps an existing `.cursor/rules/ai-rules.mdc`, repairs broken symlinks, and skips a real `docs/systems/` folder unless you pass `--force-workflows`.

If this checkout is missing `docs/agents` or `.cursor/commands`, the scripts stop with an error. Optionally export `AINATIVE_HOME` to another valid checkout as a fallback when the scripts are not sitting in a real tree.

## What this solves

- One place to improve agents and rules; every project sees updates immediately
- Slash commands (`/critic`, `/tester`, `/pr-reviewer`, etc.) available in every project without per-repo setup
- Personal AI layer stays out of the project git history (symlinks are gitignored)
- No `git submodule update`, detached HEAD, or dirty submodule status

## Layout

```
~/Projects/playground/AiNative/          ← canonical checkout (edit + push here)
├── .cursor/rules/                       ← shared rules (engineering-os, piv-gate, Commit-style)
├── .cursor/commands/                    ← agent command sources
└── docs/agents/                      ← agent definitions (loaded by commands)

~/.cursor/commands/                      ← global commands (symlink once per machine)
├── critic.md → AINATIVE_HOME/.cursor/commands/critic.md
└── …

~/projects/my-app/
├── .cursor/rules/
│   ├── ai-rules.mdc                     ← project-specific (committed)
│   └── personal → AINATIVE_HOME/.cursor/rules   ← symlink (gitignored)
└── docs/
    ├── agents → AINATIVE_HOME/docs/agents       ← symlink (gitignored)
    └── systems → AINATIVE_HOME/docs/systems   ← if needed
```

Project-specific `ai-rules.mdc` stays at `.cursor/rules/ai-rules.mdc` (committed). Shared OS rules load from `.cursor/rules/personal/` via symlink. Commands reference project-relative paths (`docs/agents/...`), so each project still needs those doc symlinks.

---

## One-time machine setup

### 1. Clone AiNative (if you have not already)

```bash
git clone <your-ainative-remote> ~/Projects/playground/AiNative
cd ~/Projects/playground/AiNative
```

### 2. Symlink agent commands and global hooks

Set up once — commands and the agent alert hook are then available in every project:

```bash
./scripts/setup-machine.sh
```

This also symlinks `~/.cursor/hooks/agent-alert.sh` and merges alert hook entries into `~/.cursor/hooks.json` (plays a sound when the agent finishes or needs your input). See [cursor-setup.md](./cursor-setup.md#global-agent-alert-hook).

Manual equivalent:

```bash
mkdir -p ~/.cursor/commands
for f in "$AINATIVE_HOME/.cursor/commands/"*.md; do
  ln -sf "$f" "$HOME/.cursor/commands/$(basename "$f")"
done
mkdir -p ~/.cursor/hooks
ln -sf "$AINATIVE_HOME/.cursor/hooks/agent-alert.sh" ~/.cursor/hooks/agent-alert.sh
```

After you add a new agent command in AiNative, re-run `machine` (or symlink the single new file).

**Note:** `~/.cursor/commands/` is the documented global location. If Cursor does not list them (known issue on some SSH setups), symlink commands into the project `.cursor/commands/` as a fallback — see [Troubleshooting](#troubleshooting).

### 3. Optional: `agents` status helper

Add to the same shell config:

```bash
agents() {
  local rules_link=".cursor/rules/personal"
  local agents_link="docs/agents"
  local global_cmds="$HOME/.cursor/commands"

  if [ ! -d "$AINATIVE_HOME" ]; then
    echo "AINATIVE_HOME not found: $AINATIVE_HOME"
    return 1
  fi

  local commit
  commit=$(cd "$AINATIVE_HOME" && git log -1 --format="%h %s" 2>/dev/null)
  echo "AiNative: $commit"

  if [ -L "$rules_link" ]; then
    echo "  rules:    $rules_link → $(readlink "$rules_link")"
  elif [ -f ".git" ] || [ -d ".git" ]; then
    echo "  rules:    missing — run new-project symlink steps"
  fi

  if [ -L "$agents_link" ]; then
    echo "  agents:   $agents_link → $(readlink "$agents_link")"
  elif [ -f ".git" ] || [ -d ".git" ]; then
    echo "  agents:   missing — run new-project symlink steps"
  fi

  local cmd_count
  cmd_count=$(find "$global_cmds" -maxdepth 1 -type l -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  echo "  commands: ${cmd_count} global (in ~/.cursor/commands/)"
}
```

Run `agents` from any project root to confirm project symlinks and see the loaded AiNative commit.

---

## New project setup

Run from the **AiNative checkout** after `git init` in the app (or anytime you add agents to an existing repo). Assumes [one-time machine setup](#one-time-machine-setup) is done.

**Automated (recommended):**

```bash
# from the AiNative checkout
./scripts/setup-project.sh ~/projects/my-app
```

Then edit `.cursor/rules/ai-rules.mdc` for the project. Use `status` to verify:

```bash
node ./scripts/ainative-link.mjs status ~/projects/my-app
```

Manual steps below if you prefer not to use the script.

### 1. Project-specific rules

```bash
mkdir -p .cursor/rules
cp "$AINATIVE_HOME/docs/systems/ai-rules-template.md" .cursor/rules/ai-rules.mdc
# Fill in stack, context, and out-of-scope items for this project
```

Also copy or symlink `piv-gate.mdc` if the project uses PIV — see [new-project.md](./new-project.md#agent-setup).

### 2. Symlink shared rules

```bash
ln -sf "$AINATIVE_HOME/.cursor/rules" .cursor/rules/personal
```

### 3. Symlink agent docs (required by commands)

Commands load `docs/agents/<agent>/AGENTS.md`. Symlink the agents tree:

```bash
mkdir -p docs
ln -sf "$AINATIVE_HOME/docs/agents" "docs/agents"
```

Agent rules cross-reference `docs/systems/` — symlink that folder too if you use critic or tester:

```bash
ln -sf "$AINATIVE_HOME/docs/systems" "docs/systems"
```

If the project already has its own `docs/systems/`, symlink only the files agents need instead of the whole folder.

### 4. Scratch folder

Every project includes a `scratch/` folder for temp files and agent working material — gitignored so nothing temporary is pushed.

```bash
mkdir -p scratch
cp "$AINATIVE_HOME/scratch/README.md" scratch/README.md
```

Add to `.gitignore` (if not already present):

```gitignore
# Scratch — agent-accessible temp files (not committed)
scratch/*
!scratch/README.md
```

Or run `./scripts/setup-project.sh` from the AiNative checkout — it creates `scratch/` and updates `.gitignore`.

### 5. Gitignore personal symlinks

Add to `.gitignore`:

```gitignore
# Personal AiNative symlinks (machine-local)
.cursor/rules/personal
docs/agents
docs/systems
```

### 6. Verify

```bash
node ./scripts/ainative-link.mjs status
# or: agents   (shell helper below)
ls -la .cursor/rules/personal docs/agents
```

Open the project in Cursor and run `/critic` or `/tester` to confirm commands resolve agent files.

### One-liner (after machine setup)

```bash
mkdir -p .cursor/rules docs && \
cp "$AINATIVE_HOME/docs/systems/ai-rules-template.md" .cursor/rules/ai-rules.mdc && \
ln -sf "$AINATIVE_HOME/.cursor/rules" .cursor/rules/personal && \
ln -sf "$AINATIVE_HOME/docs/agents" "docs/agents" && \
ln -sf "$AINATIVE_HOME/docs/systems" "docs/systems"
```

Then add the gitignore entries and fill in `ai-rules.mdc`.

---

## Day-to-day workflow

### Improve an agent or shared rule

```bash
cd "$AINATIVE_HOME"
# edit .cursor/rules/*.mdc, docs/agents/*, or .cursor/commands/*
git add -A && git commit -m "fix: …" && git push
```

Global commands and project symlinks pick up the change on the next Cursor session — no pull or bump commit in app repos. Re-run `./scripts/setup-machine.sh` if you added a new command file.

### Start work in a project

```bash
cd ~/projects/my-app
agents
```

Optional: `cd "$AINATIVE_HOME" && git pull` if you edited agents on another machine.

### New machine

1. Clone AiNative to the same path (or update `AINATIVE_HOME`)
2. Re-run [one-time machine setup](#one-time-machine-setup) (global commands)
3. Re-run [new project setup](#new-project-setup) symlink steps in each project

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| not a valid AiNative checkout | Run the scripts from the AiNative repo (`./scripts/setup-machine.sh`). `$AINATIVE_HOME` is only a fallback if the scripts were copied elsewhere |
| `/critic` not in command list | Re-run `./scripts/setup-machine.sh`; restart Cursor |
| Global commands not detected (SSH) | Fallback: symlink into project `.cursor/commands/` per file from this checkout's `.cursor/commands/` |
| Command cannot find `docs/agents/...` | From AiNative: `./scripts/setup-project.sh ~/path/to/app` |
| Duplicate or conflicting rules | Keep only one `ai-rules.mdc` at `.cursor/rules/ai-rules.mdc`; shared rules live under `personal/` |
| Symlinks committed by mistake | Add gitignore entries from step 5; `git rm --cached` any tracked symlinks |
| `readlink` shows broken path | Re-run `./scripts/setup-project.sh ~/path/to/app` from a valid AiNative checkout |
| Old `docs/8-agents` / `docs/2-ai-workflows` symlinks | Re-run `./scripts/setup-project.sh ~/path/to/app` — it removes the stale links and creates `docs/agents` + `docs/systems` (clean break, ADR-003) |

---

## Why symlinks over submodules

| | Symlinks | Submodules |
|---|----------|------------|
| Per-project bump commits | No | Yes, on every agent change |
| Drift across projects | No — one checkout | Yes — each repo pins a SHA |
| Personal layer in git history | No (gitignored) | Yes (committed) |
| Travels with `git clone` | No — re-link per machine | Yes |
| Detached HEAD when updating | N/A | Common pitfall |

For a personal agents layer you improve often, symlinks are lower tax. Submodules fit when teammates must pin and inherit the same agent version via git.

---

## Related

- [cursor-setup.md](./cursor-setup.md) — MCP, indexing, global vs project commands
- [new-project.md](./new-project.md) — full bootstrap checklist
- [agents/README.md](../../agents/README.md) — agent catalog and commands

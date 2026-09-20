# Script writing

A global Cursor rule that makes the agent write scripts with safe defaults: dry-run by default, explicit flags to apply changes, separate flag for production, per-action flags, and merge-not-overwrite by default.

Part of the [agentic system](../../systems/agentic-system.md) — **Context** (always-on rule), scoped to script files via globs.

In Cursor, the rule is **instruction-only**: it applies every turn when the agent writes or edits a script file (shell, Python, Node, ts-node).

---

## How it works

Before and while writing a script, the agent follows:

- **Safe guard** — validate inputs and preconditions before mutating anything
- **Dry-run default** — apply changes only with an explicit `--force` flag
- **Production gate** — one separate flag (e.g. `--prod`) gates production-only changes
- **Per-action flags** — expose individual actions behind their own flags so partial runs are possible
- **Merge, don't overwrite** — default behavior merges / updates existing state; never overwrite unless an explicit `--overwrite` flag is passed

---

## Install globally on Cursor

Canonical source is version-controlled in AiNative at `.cursor/rules/script-writing.mdc`. It is symlinked into the global Cursor rules directories so every project on the machine sees it — no per-project setup needed.

**Cursor CLI** walks ancestor `.cursor/rules/` from the project root — it does **not** load Application Support user rules. For CLI (and the AiNative harness), install under `~/.cursor/rules/`. Keep a symlink under Application Support if you also use the IDE Rules UI.

### 1. Global rules directories

| Surface | Path |
|---------|------|
| **Cursor CLI** (required for harness) | `~/.cursor/rules/` |
| IDE User rules (macOS) | `~/Library/Application Support/Cursor/User/.cursor/rules/` |
| IDE User rules (Linux) | `~/.config/Cursor/User/.cursor/rules/` |
| IDE User rules (Windows) | `%APPDATA%\Cursor\User\.cursor\rules\` |

### 2. Symlink the rule (one-time, after cloning AiNative)

```bash
# CLI — canonical for AiNative / Cursor Agent
ln -sf "$AINATIVE_HOME/.cursor/rules/script-writing.mdc" ~/.cursor/rules/script-writing.mdc
```

```bash
# IDE User rules (macOS) — symlink keeps one source of truth
ln -sf ~/.cursor/rules/script-writing.mdc \
  ~/Library/Application\ Support/Cursor/User/.cursor/rules/script-writing.mdc
```

```bash
# Linux IDE path
ln -sf ~/.cursor/rules/script-writing.mdc \
  ~/.config/Cursor/User/.cursor/rules/script-writing.mdc
```

```powershell
# Windows IDE path (run from an elevated shell; New-Item -ItemType SymbolicLink)
New-Item -ItemType SymbolicLink -Force `
  -Path "$env:APPDATA\Cursor\User\.cursor\rules\script-writing.mdc" `
  -Target "$env:USERPROFILE\.cursor\rules\script-writing.mdc"
```

Manual: copy `.cursor/rules/script-writing.mdc` from the AiNative checkout into `~/.cursor/rules/` (CLI) and optionally the IDE User rules directory. Symlinking is preferred so edits in AiNative propagate.

### 3. Restart and verify

1. Quit Cursor fully (Cmd+Q on macOS) if using the IDE
2. Reopen any project / restart Cursor Agent CLI
3. Confirm file exists: `ls ~/.cursor/rules/script-writing.mdc`
4. IDE (optional): Command palette → **Cursor: Open Rules** → `script-writing.mdc` listed as a global rule

Smoke check (CLI or IDE): ask for a small shell script that modifies files. Expect a dry-run default with a `--force` flag and a safe guard; expect no destructive overwrite without `--overwrite`.

---

## Note on AiNative-linked projects

Projects that ran `./scripts/setup-project.sh` symlink `.cursor/rules/personal → AiNative/.cursor/rules`, so they already load `script-writing.mdc` via `personal/`. The global `~/.cursor/rules/script-writing.mdc` symlink is additive — it makes the rule available in **non-AiNative** projects too. In AiNative-linked projects the rule content is identical (same file via symlink), so any duplicate loading is harmless.

---

## Disable per project (optional)

Create `.cursor/rules/disable-script-writing.mdc` in that project:

```yaml
---
description: Override Script writing
alwaysApply: true
globs:
  - "**/*"
---
# Disable global Script writing rule for this project
```

---

## Uninstall

```bash
rm ~/.cursor/rules/script-writing.mdc
rm ~/Library/Application\ Support/Cursor/User/.cursor/rules/script-writing.mdc
```

The canonical source remains in AiNative at `.cursor/rules/script-writing.mdc`.

See also [cursor-setup.md](./cursor-setup.md), [ponytail.md](./ponytail.md), [agentic-coding.md](../../systems/agentic-coding.md).

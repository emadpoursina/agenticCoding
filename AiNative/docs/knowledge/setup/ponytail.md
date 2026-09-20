# Ponytail

[Ponytail](https://github.com/DietrichGebert/ponytail) is a Cursor ruleset that makes agents write less code — a "lazy senior" ladder (YAGNI → reuse → stdlib → native → dependency → one line → minimum). Benchmarks claim ~54% less LOC and ~20% lower cost vs a no-skill baseline, while keeping validation, security, and accessibility.

Part of the [agentic system](../../systems/agentic-system.md) — **Context** (always-on rule). Evaluation status: [2026-07-ponytail.md](../../records/evaluations/2026-07-ponytail.md).

In Cursor, Ponytail is **instruction-only**: the ruleset applies every turn; slash commands (`/ponytail-review`, etc.) need a skill-capable host (Claude Code, Codex, …).

---

## How it works

Before writing code, the agent stops at the first rung that holds:

1. Does this need to exist? → skip (YAGNI)
2. Already in this codebase? → reuse
3. Stdlib does it? → use it
4. Native platform feature? → use it
5. Installed dependency? → use it
6. One line? → one line
7. Only then: the minimum that works

Lazy about the solution, not about reading the problem. Never cut trust-boundary validation, data-loss handling, security, or accessibility.

---

## Install globally on Cursor (docs excluded)

Recommended default: apply to code files only so AiNative-style doc work stays full-prose.

**Cursor CLI** walks ancestor `.cursor/rules/` from the project root — it does **not** load Application Support user rules. For CLI (and the AiNative harness), install under `~/.cursor/rules/`. Keep a copy (or symlink) under Application Support if you also use the IDE Rules UI.

### 1. Global rules directories

| Surface | Path |
|---------|------|
| **Cursor CLI** (required for harness) | `~/.cursor/rules/` |
| IDE User rules (macOS) | `~/Library/Application Support/Cursor/User/.cursor/rules/` |
| IDE User rules (Linux) | `~/.config/Cursor/User/.cursor/rules/` |
| IDE User rules (Windows) | `%APPDATA%\Cursor\User\.cursor\rules\` |

```bash
# CLI — required if you use Cursor Agent / harness
mkdir -p ~/.cursor/rules/
```

```bash
# IDE User rules (optional; macOS)
mkdir -p ~/Library/Application\ Support/Cursor/User/.cursor/rules/
```

```bash
# IDE User rules (optional; Linux)
mkdir -p ~/.config/Cursor/User/.cursor/rules/
```

```powershell
# IDE User rules (optional; Windows)
New-Item -ItemType Directory -Force $env:APPDATA\Cursor\User\.cursor\rules\
```

### 2. Download the rule

```bash
# CLI (canonical for AiNative / Cursor Agent)
curl -o ~/.cursor/rules/ponytail.mdc \
  https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.cursor/rules/ponytail.mdc
```

```bash
# Optional: also expose to IDE User rules (macOS) — symlink keeps one source of truth
ln -sf ~/.cursor/rules/ponytail.mdc \
  ~/Library/Application\ Support/Cursor/User/.cursor/rules/ponytail.mdc
```

```bash
# Or download into IDE path only (macOS) — CLI will not see this
curl -o ~/Library/Application\ Support/Cursor/User/.cursor/rules/ponytail.mdc \
  https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.cursor/rules/ponytail.mdc
```

```bash
# Linux IDE path
curl -o ~/.config/Cursor/User/.cursor/rules/ponytail.mdc \
  https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.cursor/rules/ponytail.mdc
```

```powershell
# Windows IDE path
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.cursor/rules/ponytail.mdc" `
  -OutFile "$env:APPDATA\Cursor\User\.cursor\rules\ponytail.mdc"
```

Manual: open the raw URL above, copy into `ponytail.mdc` in `~/.cursor/rules/` (CLI) and optionally the IDE User rules directory.

### 3. Frontmatter — code only, exclude docs

Replace the top frontmatter with:

```yaml
---
description: Ponytail - Code only (Global)
alwaysApply: true
globs:
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.py"
  - "**/*.java"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.c"
  - "**/*.cpp"
  - "**/*.h"
  - "**/*.hpp"
  - "**/*.cs"
  - "**/*.php"
  - "**/*.rb"
  - "**/*.swift"
  - "**/*.kt"
  - "**/*.scala"
  - "**/*.vue"
  - "**/*.svelte"
  - "**/*.html"
  - "**/*.css"
  - "**/*.scss"
  - "**/*.json"
  - "**/*.yaml"
  - "**/*.yml"
  - "**/*.toml"
  - "**/*.xml"
  - "**/*.sh"
  - "**/*.bash"
  - "**/*.zsh"
  - "**/*.fish"
  - "**/*.ps1"
  - "**/*.sql"
  - "!**/*.md"
  - "!**/*.txt"
  - "!**/*.rst"
  - "!**/*.adoc"
  - "!**/*.mdx"
  - "!**/*.org"
  - "!**/docs/**/*"
  - "!**/documentation/**/*"
  - "!**/CHANGELOG*"
  - "!**/CONTRIBUTING*"
  - "!**/README*"
  - "!**/LICENSE*"
---
```

Leave the rule body unchanged.

### 4. Restart and verify

1. Quit Cursor fully (Cmd+Q on macOS) if using the IDE
2. Reopen any project / restart Cursor Agent CLI
3. Confirm file exists: `ls ~/.cursor/rules/ponytail.mdc`
4. IDE (optional): Command palette → **Cursor: Open Rules** → `ponytail.mdc` listed as a global rule

Smoke check (CLI or IDE): ask for a small helper in a `.ts` file (expect minimal code); ask for API docs in a `.md` file (expect full documentation — Ponytail should not apply).

---

## Disable per project (optional)

Create `.cursor/rules/disable-ponytail.mdc` in that project:

```yaml
---
description: Override Ponytail
alwaysApply: true
globs:
  - "**/*"
---
# Disable global Ponytail for this project
```

Or, if supported in project Cursor settings:

```json
{
  "rules": {
    "disabled": ["ponytail"]
  }
}
```

---

## Default mode (optional)

`~/.config/ponytail/config.json` (macOS/Linux) or `%APPDATA%\ponytail\config.json` (Windows):

```json
{
  "defaultMode": "ultra"
}
```

Modes: `lite`, `full`, `ultra`, `off`. Default is `full`. Cursor loads the rule text only — mode switching commands need a plugin host.

---

## Quick reference

| File type | Ponytail applied? |
|-----------|-------------------|
| `*.js`, `*.ts`, `*.py`, … | Yes |
| `*.md`, `*.txt`, `*.rst`, `*.adoc`, `*.mdx` | No |
| `docs/**/*` | No |
| `README*`, `CONTRIBUTING*`, `CHANGELOG*`, `LICENSE*` | No |

---

## Uninstall

Delete `~/.cursor/rules/ponytail.mdc` (and any IDE symlink under Application Support / `%APPDATA%`). Upstream also documents `node scripts/uninstall.js` for leftover config when using the plugin hosts.

See also [cursor-setup.md](./cursor-setup.md), [tools.md](../tools.md), [agentic-coding.md](../../systems/agentic-coding.md).

#!/usr/bin/env bash
# Self-check: machine + project setup/fix against a fake HOME and temp repos.
# Does not touch the real ~/.cursor or any real project.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AINATIVE="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
mkdir -p "$HOME"

# broken env must not win over this checkout
export AINATIVE_HOME="/nonexistent"

"$SCRIPT_DIR/setup-machine.sh"
[[ -L "$HOME/.cursor/commands/critic.md" ]]
[[ -L "$HOME/.cursor/hooks/agent-alert.sh" ]]
[[ -f "$HOME/.cursor/hooks.json" ]]
# idempotent re-run
"$SCRIPT_DIR/setup-machine.sh"
[[ -L "$HOME/.cursor/commands/critic.md" ]]

if node "$SCRIPT_DIR/ainative-link.mjs" machine --ainative-home /nonexistent 2>/dev/null; then
  echo "FAIL: should reject a broken --ainative-home"
  exit 1
fi

# copied script with no checkout: valid env is the fallback
ORPHAN="$TMP/orphan/scripts"
mkdir -p "$ORPHAN"
cp "$SCRIPT_DIR/ainative-link.mjs" "$ORPHAN/"
export AINATIVE_HOME="$AINATIVE"
node "$ORPHAN/ainative-link.mjs" machine
[[ -L "$HOME/.cursor/commands/critic.md" ]]

export AINATIVE_HOME="/nonexistent"
if node "$ORPHAN/ainative-link.mjs" machine 2>/dev/null; then
  echo "FAIL: orphan script with broken AINATIVE_HOME should error"
  exit 1
fi

unset AINATIVE_HOME
if node "$ORPHAN/ainative-link.mjs" machine 2>/dev/null; then
  echo "FAIL: orphan script with no env should error"
  exit 1
fi

if node "$SCRIPT_DIR/ainative-link.mjs" project "$AINATIVE" --ainative-home "$AINATIVE" 2>/dev/null; then
  echo "FAIL: should refuse linking into AiNative itself"
  exit 1
fi

# new project
NEW="$TMP/new-app"
mkdir -p "$NEW"
"$SCRIPT_DIR/setup-project.sh" "$NEW"
[[ -L "$NEW/.cursor/rules/personal" ]]
[[ -L "$NEW/docs/agents" ]]
[[ -L "$NEW/docs/systems" ]]
[[ -f "$NEW/.cursor/rules/ai-rules.mdc" ]]
[[ -f "$NEW/scratch/README.md" ]]
grep -q "Personal AiNative symlinks" "$NEW/.gitignore"

# old project: keep existing ai-rules, remove stale numbered symlinks, add new ones
OLD="$TMP/old-app"
mkdir -p "$OLD/.cursor/rules" "$OLD/docs" "$OLD/.git"
echo "project-stack" > "$OLD/.cursor/rules/ai-rules.mdc"
ln -s /nonexistent "$OLD/docs/8-agents"
ln -s /nonexistent "$OLD/docs/2-ai-workflows"
mkdir -p "$OLD/docs/systems"
echo "keep-me" > "$OLD/docs/systems/local.md"
cat > "$OLD/.gitignore" <<'EOF'
node_modules/
# Personal AiNative symlinks (machine-local)
.cursor/rules/personal
docs/8-agents
docs/2-ai-workflows
EOF
"$SCRIPT_DIR/setup-project.sh" "$OLD"
grep -q "project-stack" "$OLD/.cursor/rules/ai-rules.mdc"
[[ ! -L "$OLD/docs/8-agents" && ! -e "$OLD/docs/8-agents" ]]
[[ ! -L "$OLD/docs/2-ai-workflows" && ! -e "$OLD/docs/2-ai-workflows" ]]
[[ -L "$OLD/docs/agents" ]]
[[ -f "$OLD/docs/systems/local.md" && ! -L "$OLD/docs/systems" ]]
# gitignore symlink entries migrated to the new layout
grep -q "^docs/agents$" "$OLD/.gitignore"
grep -q "^docs/systems$" "$OLD/.gitignore"
! grep -q "^docs/8-agents$" "$OLD/.gitignore"
! grep -q "^docs/2-ai-workflows$" "$OLD/.gitignore"

echo "OK: machine + project setup/fix (new, old, stale symlinks, gitignore migration, real systems folder)"

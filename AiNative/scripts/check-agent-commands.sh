#!/usr/bin/env bash
# Verify agent folder ↔ command file parity and AGENTS.md / SKILL.md file contract.
# Exits non-zero on missing or orphan commands, or a broken agent/skill file.

set -euo pipefail

AGENTS_DIR="docs/agents"
COMMANDS_DIR=".cursor/commands"
EXCLUDE_DIRS=("template" "_skills")

missing=()
orphans=()
contract_fail=()

is_excluded() {
  local name="$1"
  for d in "${EXCLUDE_DIRS[@]}"; do
    [[ "$name" == "$d" ]] && return 0
  done
  return 1
}

skill_name_line() {
  awk 'NR==1{next} /^---$/{exit} /^name:/{print; exit}' "$1"
}

check_skill_md() {
  local file="$1"
  local expected_name="$2"
  local label="$3"
  if [[ ! -f "$file" ]]; then
    contract_fail+=("$label missing SKILL.md")
    return
  fi
  if [[ "$(head -n 1 "$file")" != "---" ]]; then
    contract_fail+=("$label SKILL.md missing YAML frontmatter")
    return
  fi
  local name_line
  name_line=$(skill_name_line "$file")
  if [[ "$name_line" != "name: $expected_name" ]]; then
    contract_fail+=("$label SKILL.md name mismatch: got '${name_line}', expected 'name: ${expected_name}'")
  fi
}

# File contract: every agent folder (including template)
for dir in "$AGENTS_DIR"/*/; do
  name=$(basename "$dir")
  [[ "$name" == "_skills" ]] && continue
  for f in AGENTS.md SKILL.md rule.md; do
    if [[ ! -f "$dir$f" ]]; then
      contract_fail+=("$name missing $f")
    fi
  done
  expected_name="$name"
  [[ "$name" == "template" ]] && expected_name="agent-name"
  check_skill_md "$dir/SKILL.md" "$expected_name" "$name"
done

for skill_dir in "$AGENTS_DIR/_skills"/*/; do
  skill=$(basename "$skill_dir")
  check_skill_md "${skill_dir}SKILL.md" "$skill" "_skills/$skill"
done

# Check each agent folder has a command
for dir in "$AGENTS_DIR"/*/; do
  name=$(basename "$dir")
  is_excluded "$name" && continue
  if [[ ! -f "$COMMANDS_DIR/$name.md" ]]; then
    missing+=("$name")
  fi
done

# Check each command has an agent folder (excluding utility commands)
UTILITY_COMMANDS=("sync-branch" "short-answer")
for cmd in "$COMMANDS_DIR"/*.md; do
  name=$(basename "$cmd" .md)
  for util in "${UTILITY_COMMANDS[@]}"; do
    [[ "$name" == "$util" ]] && continue 2
  done
  if is_excluded "$name"; then
    continue
  fi
  if [[ ! -d "$AGENTS_DIR/$name" ]]; then
    orphans+=("$name")
  fi
done

if [[ ${#contract_fail[@]} -gt 0 ]]; then
  echo "Broken agent/skill file contract:"
  printf '  - %s\n' "${contract_fail[@]}"
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Missing commands (agent folder exists, no command file):"
  printf '  - %s → expected %s/%s.md\n' "${missing[@]}" "$COMMANDS_DIR" "${missing[@]}"
fi

if [[ ${#orphans[@]} -gt 0 ]]; then
  echo "Orphan commands (command file exists, no agent folder):"
  printf '  - %s\n' "${orphans[@]}"
fi

if [[ ${#contract_fail[@]} -gt 0 || ${#missing[@]} -gt 0 || ${#orphans[@]} -gt 0 ]]; then
  exit 1
fi

echo "OK: agent file contract and command parity."

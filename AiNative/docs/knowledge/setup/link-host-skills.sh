#!/usr/bin/env bash
# Link AiNative agents into host editor skill dirs (Cursor / OpenCode).
# Canonical source is always AiNative/docs/agents/<name>/. Editors only symlink.
#
#   ./docs/knowledge/setup/link-host-skills.sh          # Cursor only
#   ./docs/knowledge/setup/link-host-skills.sh --all    # Cursor + OpenCode
#   ./docs/knowledge/setup/link-host-skills.sh --opencode
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
ainative=$(cd "$here/../../.." && pwd)
agents="$ainative/docs/agents"
cursor_skills="${CURSOR_SKILLS:-$HOME/.cursor/skills}"
cursor_cmds="${CURSOR_COMMANDS:-$HOME/.cursor/commands}"
opencode_skill="${OPENCODE_SKILL:-$HOME/.config/opencode/skill}"
opencode_skills="${OPENCODE_SKILLS:-$HOME/.config/opencode/skills}"
cmd_src="$ainative/.cursor/commands"

do_cursor=1
do_opencode=0
for arg in "$@"; do
  case "$arg" in
    --all) do_cursor=1; do_opencode=1 ;;
    --opencode) do_cursor=0; do_opencode=1 ;;
    --cursor) do_cursor=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# Skip the copy template; it is not an invokable agent.
skip_agent() {
  case "$1" in template|README.md|_skills) return 0 ;; esac
  return 1
}

link_dir() {
  local src=$1 dest=$2
  mkdir -p "$(dirname "$dest")"
  if [ -L "$dest" ]; then
    local cur
    cur=$(readlink "$dest")
    if [ "$cur" = "$src" ]; then
      echo "ok  $dest"
      return
    fi
    ln -sfn "$src" "$dest"
    echo "retarget $dest -> $src (was $cur)"
    return
  fi
  if [ -e "$dest" ]; then
    local bak="$dest.bak-$(date +%Y%m%d)"
    i=0
    while [ -e "$bak" ]; do
      i=$((i + 1))
      bak="$dest.bak-$(date +%Y%m%d)-$i"
    done
    mv "$dest" "$bak"
    echo "backup $dest -> $bak"
  fi
  ln -s "$src" "$dest"
  echo "link $dest -> $src"
}

write_cursor_command() {
  local name=$1
  local skill="$agents/$name/SKILL.md"
  local out="$cmd_src/$name.md"
  [ -f "$skill" ] || return 0
  mkdir -p "$cmd_src"
  if [ -f "$out" ]; then
    return 0
  fi
  local desc
  desc=$(python3 - "$skill" <<'PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text()
m = re.search(r"^---\n(.*?)\n---", text, re.S)
if not m:
    print("Follow the named AiNative skill.")
    raise SystemExit
fm = m.group(1)
dm = re.search(r"^description:\s*(?:>-\s*)?(.*)", fm, re.S | re.M)
if not dm:
    print("Follow the named AiNative skill.")
    raise SystemExit
raw = dm.group(1)
# stop at next top-level key
raw = re.split(r"\n[a-zA-Z0-9_-]+:", raw, maxsplit=1)[0]
line = " ".join(raw.split())
print(line[:400])
PY
)
  cat > "$out" <<EOF
---
description: ${desc}
---

# /${name}

Cursor slash entry for the AiNative **${name}** skill. Do not invent a parallel workflow.

1. Read \`\$HOME/.cursor/skills/${name}/SKILL.md\` and follow it.
2. Also read \`AGENTS.md\` and \`rule.md\` in that same folder when they exist.
3. Pass \`\$ARGUMENTS\` as the user request.

This file exists because Cursor slash commands are a separate surface from Agent Skills. OpenCode loads the same skill from \`~/.config/opencode/skill/${name}/\`.
EOF
  echo "wrote $out"
}

link_inventory() {
  local dest_root=$1
  mkdir -p "$dest_root"
  local d name
  for d in "$agents"/*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    skip_agent "$name" && continue
    [ -f "$d/SKILL.md" ] || continue
    link_dir "$d" "$dest_root/$name"
  done
  for d in "$agents/_skills"/*; do
    [ -d "$d" ] || continue
    [ -f "$d/SKILL.md" ] || continue
    name=$(basename "$d")
    link_dir "$d" "$dest_root/$name"
  done
}

if [ "$do_cursor" = 1 ]; then
  echo "== Cursor skills ($cursor_skills) =="
  link_inventory "$cursor_skills"
  echo "== Cursor commands ($cursor_cmds) =="
  mkdir -p "$cmd_src" "$cursor_cmds"
  for d in "$agents"/*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    skip_agent "$name" && continue
    write_cursor_command "$name"
  done
  # Historical Cursor slash name for pr-reviewer (same skill).
  if [ ! -f "$cmd_src/pr-review.md" ] && [ -f "$cmd_src/pr-reviewer.md" ]; then
    sed 's|# /pr-reviewer|# /pr-review|' "$cmd_src/pr-reviewer.md" > "$cmd_src/pr-review.md"
    echo "wrote $cmd_src/pr-review.md"
  fi
  if [ ! -f "$cmd_src/pr-generate.md" ] && [ -f "$cursor_skills/pr-generate/SKILL.md" ]; then
    cat > "$cmd_src/pr-generate.md" <<'EOF'
---
description: Opens a GitHub pull request with a body structured for /pr-reviewer. Use when the user runs /pr-generate or asks to create a review-ready PR.
---

# /pr-generate

Cursor-only slash entry. This skill is not an AiNative agent; OpenCode has no equivalent. Follow `$HOME/.cursor/skills/pr-generate/SKILL.md` and pass `$ARGUMENTS` as the user request.
EOF
    echo "wrote $cmd_src/pr-generate.md"
  fi
  for f in "$cmd_src"/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    dest="$cursor_cmds/$name"
    if [ -f "$dest" ] && [ ! -L "$dest" ]; then
      echo "keep local $dest"
      continue
    fi
    link_dir "$f" "$dest"
  done
fi

if [ "$do_opencode" = 1 ]; then
  echo "== OpenCode skill ($opencode_skill) =="
  link_inventory "$opencode_skill"
  if [ -d "$opencode_skills" ]; then
    echo "== OpenCode skills ($opencode_skills) =="
    link_inventory "$opencode_skills"
  fi
fi

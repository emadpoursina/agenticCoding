#!/usr/bin/env bash
# Hermes readiness check — the single INSTALL-gate check for "does Hermes have
# everything it needs to run?" (branch/layout per-card checks: ready gate)
#
# Usage:
#   On the Mac (host checks, then re-runs itself inside the container):
#     bash AiNative/docs/knowledge/setup/hermes-readiness.sh [target-project]
#   Inside the container (container checks only):
#     bash /opt/data/mnt/AiNative/docs/knowledge/setup/hermes-readiness.sh [target-project]
#
# [target-project] is the project probed for git sanity (repo + origin reachable;
# Spec Kit layout belongs to the ready gate). Default: the first
# workspace dir that has an .ainative/project.yaml, else `agenticCoding`.
# Accepts either a host path or a container path; each mode maps it itself.
#
# Read-only. The only writes are a writability probe (temp dir, removed) and an
# AiNative write-probe that is expected to FAIL and is removed if it ever lands.
#
# Ownership (one gate per concern — do not duplicate other gates' checks here):
#   hermes-readiness.sh  INSTALL gate: can Hermes run? mounts, keys, DBs,
#                        config, CLI reachable. Target probed only for
#                        "is a git repo + origin reachable" (sanity).
#   ready-check.sh       PER-FLOW gate: branch state, Spec Kit layout,
#                        .specify/ready.yml. Owner of those decisions.
#   task-groomer         CARD gate: card shape and dispatch-readiness. No
#                        environment checks.
#
# Levels:
#   PASS  check passed
#   FAIL  step-2 gate — project onboarding cannot start
#   GAP   step-3 gate — speckit-orchestrate cannot start (does not block onboarding)
#   NOTE  informational
#
# Exit 0 = ONBOARDING: ok.  Exit 1 = ONBOARDING: blocked.
# Never prints secret values — only whether a variable/key exists.

set -uo pipefail

S2=0   # step-2 gate failures
S3=0   # step-3 gate gaps

hdr()   { printf '\n== %s ==\n' "$1"; }
pass()  { printf 'PASS  %-24s %s\n' "$1" "${2:-}"; }
note()  { printf 'NOTE  %-24s %s\n' "$1" "${2:-}"; }
gate2() { printf 'FAIL  %-24s %s\n' "$1" "${2:-}"; S2=$((S2 + 1)); }
gate3() { printf 'GAP   %-24s %s\n' "$1" "${2:-}"; S3=$((S3 + 1)); }

# probe_write <dir> <label> <gate:2|3|none>
probe_write() {
  local d=$1 lbl=$2 g=${3:-none} t
  if t=$(mktemp -d "$d/.readiness.XXXXXX" 2>/dev/null); then
    rmdir "$t" 2>/dev/null
    pass "$lbl" "writable: $d"
  elif [ "$g" = 2 ]; then
    gate2 "$lbl" "not writable: $d"
  elif [ "$g" = 3 ]; then
    gate3 "$lbl" "not writable: $d"
  else
    note "$lbl" "not writable: $d"
  fi
}

# ---------------------------------------------------------------- container ---
container_checks() {
  local target=$1 hbin out f DB_HOME=${HERMES_HOME:-/opt/data}

  hdr "runtime (container)"
  note "mode" "container $(hostname 2>/dev/null) / user $(id -un 2>/dev/null) uid $(id -u 2>/dev/null) HOME=${HOME:-unset}"
  [ -n "${HERMES_HOME:-}" ] && pass "hermes-home" "$HERMES_HOME" || gate2 "hermes-home" "HERMES_HOME unset"

  hbin=/opt/hermes/bin/hermes
  [ -x "$hbin" ] || hbin=$(command -v hermes 2>/dev/null || true)
  if [ -n "$hbin" ] && [ -x "$hbin" ]; then
    pass "hermes-bin" "$hbin"
    if out=$("$hbin" --version 2>&1); then pass "hermes-version" "$(printf '%s' "$out" | head -1)"; else gate2 "hermes-version" "$out"; fi
  else
    gate2 "hermes-bin" "/opt/hermes/bin/hermes missing"; hbin=""
  fi

  probe_write "$DB_HOME" "hermes-home-writable" 2
  if [ -f "$DB_HOME/SOUL.md" ]; then pass "soul" "$DB_HOME/SOUL.md present"; else gate2 "soul" "SOUL.md missing (startup identity)"; fi

  if [ -n "$hbin" ]; then
    if out=$("$hbin" config get model.default 2>&1); then pass "config-model" "model.default=$out"; else gate2 "config-model" "$out"; fi
    if out=$("$hbin" config get model.provider 2>&1); then pass "config-provider" "model.provider=$out"; else gate2 "config-provider" "$out"; fi
    if out=$("$hbin" profile list 2>/dev/null | wc -l | tr -d ' '); then note "profile-list" "$out line(s)"; fi
  fi
  if [ -r "$DB_HOME/config.yaml" ]; then pass "config-file" "$DB_HOME/config.yaml readable"; else gate2 "config-file" "$DB_HOME/config.yaml missing — model routing lives here"; fi
  if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ] || [ -n "${OPENROUTER_API_KEY:-}" ]; then
    note "model-key" "provider key present in env (name only, value redacted)"
  else
    gate3 "model-key" "no ANTHROPIC/OPENAI/OPENROUTER key in env — model calls fail unless key lives in Hermes config"
  fi
  if command -v sqlite3 >/dev/null 2>&1; then pass "sqlite3" "available — db integrity verifiable"; else gate3 "sqlite3" "not installed — db integrity not verifiable here (see host section)"; fi

  for f in kanban.db projects.db; do
    if [ ! -f "$DB_HOME/$f" ]; then gate2 "db-$f" "$f missing"; continue; fi
    if command -v sqlite3 >/dev/null 2>&1; then
      if [ "$(sqlite3 "$DB_HOME/$f" 'pragma integrity_check;' 2>/dev/null)" = "ok" ]; then
        pass "db-$f" "integrity ok"
      else
        gate2 "db-$f" "integrity check failed"
      fi
    else
      note "db-$f" "present ($(wc -c <"$DB_HOME/$f" | tr -d ' ') B); sqlite3 not installed here"
    fi
  done

  note "db-files" "$(find "$DB_HOME" -maxdepth 3 \( -name '*.db' -o -name '*.sqlite*' \) -not -path '*/mnt/*' 2>/dev/null | sed "s|$DB_HOME/||" | sort | tr '\n' ' ')"
  note "task-db-rule" "exactly one DB may hold tasks (checked on host, where sqlite3 exists)"

  hdr "methodology (read-only mount)"
  if touch /opt/data/mnt/AiNative/.readiness-probe.$$ 2>/dev/null; then
    rm -f /opt/data/mnt/AiNative/.readiness-probe.$$
    gate2 "ainative-ro" "write was ALLOWED — mount is not read-only"
  else
    pass "ainative-ro" "write correctly refused"
  fi
  for f in docs/knowledge/setup/new-project.md docs/systems/feature-loop.md \
           docs/agents/project-bootstrapper/SKILL.md docs/agents/prd-writer/SKILL.md; do
    if [ -r "/opt/data/mnt/AiNative/$f" ]; then pass "ainative-file" "$f"; else gate2 "ainative-file" "unreadable: $f"; fi
  done

  hdr "workspace (read-write)"
  probe_write /opt/data/mnt/workspace workspace-writable 2
  note "workspace-contents" "$(ls -1 /opt/data/mnt/workspace 2>/dev/null | tr '\n' ' ')"

  hdr "git & github"
  if [ -r /opt/data/home/.gitconfig ]; then pass "gitconfig" "/opt/data/home/.gitconfig readable"; else gate2 "gitconfig" "missing"; fi
  if [ -r /opt/data/home/.ssh/git_key ]; then pass "git-key" "/opt/data/home/.ssh/git_key readable"; else gate2 "git-key" "missing"; fi
  if [ -n "${GIT_SSH_COMMAND:-}" ]; then pass "git-ssh-command" "set (key path redacted)"; else gate2 "git-ssh-command" "unset — ssh would ignore git_key (must match container env)"; fi
  _gname="$(git config --global user.name 2>/dev/null || printf '%s' "${GIT_AUTHOR_NAME:-}")"
  _gemail="$(git config --global user.email 2>/dev/null || printf '%s' "${GIT_AUTHOR_EMAIL:-}")"
  if [ -n "$_gname" ] && [ -n "$_gemail" ]; then pass "git-identity" "user.name+user.email set (values redacted)"; else gate2 "git-identity" "user.name and/or user.email missing — commits would have no identity"; fi

  if [ -d "$target/.git" ]; then
    if out=$(git -C "$target" ls-remote --heads origin 2>&1); then
      pass "git-ls-remote" "origin reachable, $(printf '%s' "$out" | grep -c . ) head(s) — $target"
    else
      gate2 "git-ls-remote" "$(printf '%s' "$out" | head -2 | tr '\n' ' ')"
    fi
    note "git-branch" "$(git -C "$target" status -sb 2>/dev/null | head -1)"
    if git -C "$target" worktree list >/dev/null 2>&1; then
      pass "worktree" "git worktree supported in $target (dispatcher isolation)"
    else
      gate2 "worktree" "git worktree list failed in $target — per-card isolation would fail"
    fi
  else
    gate2 "git-target" "not a git repo: $target"
  fi

  local tok=""
  [ -n "${GH_TOKEN:-}" ] && tok="GH_TOKEN"
  [ -n "${GITHUB_TOKEN:-}" ] && tok="$tok GITHUB_TOKEN"
  if command -v gh >/dev/null 2>&1; then
    if gh auth status >/dev/null 2>&1; then
      if _ghuser=$(gh api user --jq .login 2>/dev/null) && [ -n "$_ghuser" ]; then
        pass "gh-auth" "$(gh --version | head -1 | cut -d' ' -f1-3) authenticated as $_ghuser (${tok:-key unknown})"
      else
        gate3 "gh-auth" "gh auth passes but gh api user failed — token expired or lacking scopes (${tok:-no token in env})"
      fi
    else
      gate3 "gh-auth" "gh present but not authenticated (${tok:-no token in env}) — PR ship would fail"
    fi
  else
    gate3 "gh" "gh CLI not installed — PR ship would fail"
  fi

  hdr "hermes CLI"
  if [ -z "$hbin" ]; then
    gate2 "hermes-cli" "hermes binary unavailable"
  elif "$hbin" --version >/dev/null 2>&1 && "$hbin" project --help >/dev/null 2>&1 && "$hbin" kanban --help >/dev/null 2>&1; then
    pass "hermes-cli" "$hbin project+kanban reachable"
  else
    gate2 "hermes-cli" "hermes CLI present but project/kanban subcommands failed"
  fi

  hdr "step-3 prerequisites (gaps do not block onboarding)"
  local missing="" skill
  for skill in speckit-orchestrate/SKILL.md speckit-ready/SKILL.md speckit-ready/scripts/ready-check.sh \
               route-work/SKILL.md change/SKILL.md; do
    [ -r "${HOME:-/opt/data/home}/.config/opencode/skill/$skill" ] || missing="$missing $skill"
  done
  if [ -z "$missing" ]; then
    pass "opencode-skills" "all present under ~/.config/opencode/skill"
  else
    gate3 "opencode-skills" "not reachable from container:$missing"
  fi

  # Spec Kit layout and git branch state are intentionally NOT checked here.
  # Owner: the ready gate — ready-check.sh (per-card: branch, layout,
  # .specify/ready.yml). This script owns install facts only. Checking them
  # twice with different rules caused confusion; see harness.md.

  if find /opt/data/mnt/AiNative -name '*project*yaml*' 2>/dev/null | grep -q .; then
    pass "project-yaml-template" "$(find /opt/data/mnt/AiNative -name '*project*yaml*' 2>/dev/null | head -1)"
  else
    gate3 "project-yaml-template" "no .ainative/project.yaml template in AiNative"
  fi

  if command -v sqlite3 >/dev/null 2>&1; then
    out=$(sqlite3 "$DB_HOME/kanban.db" 'select count(*) from kanban_notify_subs;' 2>/dev/null || echo 0)
    if [ "${out:-0}" -gt 0 ] 2>/dev/null; then pass "notify-subscribers" "$out"; else gate3 "notify-subscribers" "0 — park/ship gates have nobody to notify"; fi
  else
    note "notify-subscribers" "not checkable here (no sqlite3); see host section"
  fi

  if command -v curl >/dev/null 2>&1; then
    out=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:9119/ 2>/dev/null || echo 000)
    case "$out" in 200|301|302) pass "dashboard" "localhost:9119 → $out" ;; *) gate3 "dashboard" "localhost:9119 → ${out:-unreachable}" ;; esac
  else
    note "dashboard" "curl not installed"
  fi
}

# --------------------------------------------------------------------- host ---
host_checks() {
  local airoot pa out status mounts m keys k dbs
  airoot=$(cd "$(dirname "$0")/../../.." && pwd)          # .../AiNative
  pa="$(dirname "$airoot")/personalAgent"                 # sibling of AiNative

  hdr "host runtime"
  if [ -f "$pa/docker-compose.yml" ]; then pass "compose-file" "$pa/docker-compose.yml"; else gate2 "compose-file" "$pa/docker-compose.yml missing"; return; fi
  if docker compose version >/dev/null 2>&1; then
    if out=$(docker compose -f "$pa/docker-compose.yml" config -q 2>&1); then pass "compose-config" "valid"; else gate2 "compose-config" "$(printf '%s' "$out" | head -2)"; fi
  else
    gate2 "compose-cli" "docker compose not available"
  fi

  status=$(docker inspect -f '{{.State.Status}}' hermes-personal-coding 2>/dev/null || echo absent)
  if [ "$status" = "running" ]; then pass "container" "hermes-personal-coding running"; else gate2 "container" "state=$status"; return; fi

  hdr "host mounts"
  mounts=$(docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' hermes-personal-coding 2>/dev/null)
  for m in /opt/data /opt/data/mnt/AiNative /opt/data/mnt/workspace /opt/data/home/.ssh /opt/data/home/.gitconfig; do
    case "$mounts" in *"$m"*) pass "mount" "$m" ;; *) gate2 "mount" "$m not mounted" ;; esac
  done
  if docker inspect -f '{{range .Mounts}}{{if eq .Destination "/opt/data/mnt/AiNative"}}{{.RW}}{{end}}{{end}}' hermes-personal-coding 2>/dev/null | grep -q false; then
    pass "mount-ro" "AiNative read-only"
  else
    gate2 "mount-ro" "AiNative is NOT read-only"
  fi
  if grep -qE 'config/opencode' "$pa/docker-compose.yml" 2>/dev/null; then
    pass "mount-skills" "~/.config/opencode referenced in compose"
  else
    gate3 "mount-skills" "~/.config/opencode not in compose mounts — step-3 skills unreachable inside the container"
  fi
  if docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' hermes-personal-coding 2>/dev/null | grep -q '^GIT_SSH_COMMAND='; then
    pass "env-git-ssh" "GIT_SSH_COMMAND set in container env"
  else
    gate2 "env-git-ssh" "GIT_SSH_COMMAND missing from container env"
  fi

  hdr "host env (names only — no values)"
  keys=$(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$pa/.env" 2>/dev/null | tr -d '=' | tr '\n' ' ')
  if [ -n "$keys" ]; then note "env-keys" "$keys"; else gate2 "env-keys" "$pa/.env missing or empty"; fi
  if printf '%s' "$keys" | grep -qE '^(GH_TOKEN|GITHUB_TOKEN)$| GH_TOKEN| GITHUB_TOKEN'; then
    pass "gh-token-key" "present in .env"
  else
    gate3 "gh-token-key" "no GH_TOKEN/GITHUB_TOKEN in personalAgent/.env"
  fi

  hdr "host workspace & dbs"
  probe_write "$HOME/hermes-workspace-personal-coding" workspace-writable 2
  if command -v sqlite3 >/dev/null 2>&1; then
    dbs=""
    for f in "$HOME"/.hermes-personal-coding/*.db; do
      [ -f "$f" ] || continue
      n=$(sqlite3 "$f" "select count(*) from sqlite_master where type='table' and name='tasks';" 2>/dev/null || echo 0)
      [ "${n:-0}" -gt 0 ] 2>/dev/null && dbs="$dbs $(basename "$f")"
    done
    if [ "$(printf '%s' "$dbs" | wc -w | tr -d ' ')" = "1" ]; then
      pass "single-task-db" "only$(printf '%s' "$dbs") holds tasks"
    else
      gate2 "single-task-db" "task DBs:$(printf '%s' "$dbs" | tr '\n' ' ' | sed 's/^$/ none/') — must be exactly one (kanban.db)"
    fi
    out=$(sqlite3 "$HOME/.hermes-personal-coding/kanban.db" 'select count(*) from kanban_notify_subs;' 2>/dev/null || echo 0)
    if [ "${out:-0}" -gt 0 ] 2>/dev/null; then pass "notify-subscribers" "$out"; else gate3 "notify-subscribers" "0 — park/ship gates have nobody to notify"; fi
    out=$(sqlite3 "$HOME/.hermes-personal-coding/projects.db" "select slug || ' → ' || coalesce(primary_path,'?') || ' → board=' || coalesce(board_slug,'none') from projects where archived=0;" 2>/dev/null)
    note "enrolled-projects" "$(printf '%s' "${out:-none}" | tr '\n' ' ')"
    out=$(sqlite3 "$HOME/.hermes-personal-coding/kanban.db" 'select count(*) from tasks;' 2>/dev/null || echo 0)
    note "board-tasks" "$out"
  else
    gate2 "sqlite3" "sqlite3 not installed on host — db checks skipped"
  fi

  hdr "host skills (needed by speckit-orchestrate)"
  local missing="" s
  for s in speckit-orchestrate/SKILL.md speckit-ready/SKILL.md speckit-ready/scripts/ready-check.sh route-work/SKILL.md change/SKILL.md; do
    [ -r "$HOME/.config/opencode/skill/$s" ] || missing="$missing $s"
  done
  if [ -z "$missing" ]; then pass "opencode-skills" "all present on host"; else gate3 "opencode-skills" "missing:$missing"; fi

  if curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:9119/ 2>/dev/null | grep -qE '200|301|302'; then
    pass "dashboard" "localhost:9119 reachable"
  else
    gate3 "dashboard" "localhost:9119 unreachable"
  fi
}

# -------------------------------------------------------------------- driver ---
first_with_scaffold() {
  local d
  for d in "$1"/*; do
    [ -f "$d/.ainative/project.yaml" ] && { printf '%s' "$d"; return 0; }
  done
  return 1
}

if [ -d /opt/data/mnt/AiNative ]; then
  # ---- container mode
  T=${1:-$(first_with_scaffold /opt/data/mnt/workspace || printf '%s' /opt/data/mnt/workspace/agenticCoding)}
  container_checks "$T"
else
  # ---- host mode
  HOST_T=${1:-$(first_with_scaffold "$HOME/hermes-workspace-personal-coding" || printf '%s' "$HOME/hermes-workspace-personal-coding/agenticCoding")}
  host_checks
  if docker inspect -f '{{.State.Status}}' hermes-personal-coding 2>/dev/null | grep -q running; then
    C_T="/opt/data/mnt/workspace/$(basename "$HOST_T")"
    inner=$(docker exec hermes-personal-coding \
      bash /opt/data/mnt/AiNative/docs/knowledge/setup/hermes-readiness.sh "$C_T" 2>&1)
    printf '\n######## container view (docker exec, target %s) ########\n%s\n' "$C_T" "$inner"
    n2=$(printf '%s\n' "$inner" | grep -c '^FAIL' || true)
    n3=$(printf '%s\n' "$inner" | grep -c '^GAP' || true)
    S2=$((S2 + n2)); S3=$((S3 + n3))
  else
    gate2 "container-exec" "container not running — container view skipped"
  fi
fi

echo
[ "$S2" -gt 0 ] && echo "ONBOARDING: blocked  (step-2 FAILs: $S2)" || echo "ONBOARDING: ok"
[ "$S3" -gt 0 ] && echo "STEP3: blocked  (step-3 GAPs: $S3)"        || echo "STEP3: ok"
[ "$S2" -eq 0 ]

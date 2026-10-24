#!/usr/bin/env bash
# ready-check.sh -- speckit ready-stage gate.
#
# Usage: ready-check.sh <repo_root> <flow_id> <slug>
#
# Prints the compact READY report to stdout.
# Exit 0 when READY: ok, 1 when READY: blocked, 2 on usage/environment errors.

set -euo pipefail

REPO_ROOT="${1:-}"
FLOW_ID="${2:-}"
SLUG="${3:-}"

if [ -z "$REPO_ROOT" ] || [ -z "$FLOW_ID" ] || [ -z "$SLUG" ]; then
  echo "Usage: ready-check.sh <repo_root> <flow_id> <slug>" >&2
  exit 2
fi

if [ ! -d "$REPO_ROOT" ]; then
  echo "ready-check.sh: repo root is not a directory: $REPO_ROOT" >&2
  exit 2
fi

cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ready-check.sh: not a git repository: $REPO_ROOT" >&2
  exit 2
fi

# Resolve to the physical path so WORKTREE paths are absolute and stable.
REPO_ROOT="$(pwd -P)"

# ---------------------------------------------------------------------------
# Branch state (required)
# ---------------------------------------------------------------------------

branch_fail=0
branch_note=""
branch_fix=""

current_branch="$(git symbolic-ref --short -q HEAD 2>/dev/null || true)"
if [ -z "$current_branch" ]; then
  short_sha="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  current_branch="(detached HEAD @ ${short_sha})"
  branch_fail=1
  branch_note="detached HEAD"
  branch_fix="detached HEAD; check out the default branch or '${SLUG}', then re-run."
fi

if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
  branch_fail=1
  if [ -n "$branch_note" ]; then
    branch_note="${branch_note}; merge in progress"
  else
    branch_note="merge in progress"
  fi
  branch_fix="merge in progress; resolve or abort it, then re-run the ready stage."
fi

find_branch_ref() {
  local branch_name="$1"
  local remote_ref=""
  local remote_branch=""
  local matching_ref=""
  local matching_count=0
  local remote_refs=""

  if ! git check-ref-format --branch "$branch_name" >/dev/null 2>&1; then
    return 1
  fi
  if git show-ref --verify --quiet "refs/heads/$branch_name"; then
    printf 'refs/heads/%s\n' "$branch_name"
    return 0
  fi
  if git show-ref --verify --quiet "refs/remotes/origin/$branch_name"; then
    printf 'refs/remotes/origin/%s\n' "$branch_name"
    return 0
  fi

  remote_refs="$(git for-each-ref --format='%(refname)' refs/remotes 2>/dev/null || true)"
  for remote_ref in $remote_refs; do
    case "$remote_ref" in */HEAD) continue ;; esac
    remote_branch="${remote_ref#refs/remotes/}"
    remote_branch="${remote_branch#*/}"
    if [ "$remote_branch" = "$branch_name" ]; then
      matching_ref="$remote_ref"
      matching_count=$((matching_count + 1))
    fi
  done

  if [ "$matching_count" -eq 1 ]; then
    printf '%s\n' "$matching_ref"
    return 0
  fi
  if [ "$matching_count" -gt 1 ]; then
    return 2
  fi
  return 1
}

default_branch=""
default_ref=""
default_detection_note=""
base_override="${SPECKIT_BASE_BRANCH:-}"
base_override_source="SPECKIT_BASE_BRANCH"
if [ -z "$base_override" ]; then
  base_override="$(git config --local --get speckit.baseBranch 2>/dev/null || true)"
  if [ -n "$base_override" ]; then
    base_override_source="git config speckit.baseBranch"
  fi
fi

if [ -n "$base_override" ]; then
  if ! git check-ref-format --branch "$base_override" >/dev/null 2>&1; then
    branch_fail=1
    branch_note="invalid base-branch override"
    branch_fix="set SPECKIT_BASE_BRANCH or this repository's speckit.baseBranch to a valid local or remote-tracking branch name, then re-run."
  elif candidate_ref="$(find_branch_ref "$base_override")"; then
    default_branch="$base_override"
    default_ref="$candidate_ref"
    default_detection_note="using $base_override_source"
  else
    ref_status=$?
    branch_fail=1
    branch_note="configured base branch '$base_override' is not available"
    if [ "$ref_status" -eq 2 ]; then
      branch_fix="multiple remotes contain '$base_override'; set SPECKIT_BASE_BRANCH to a uniquely available branch or configure speckit.baseBranch with a local branch, then re-run."
    else
      branch_fix="fetch or check out '$base_override', or set SPECKIT_BASE_BRANCH / speckit.baseBranch to the correct branch, then re-run."
    fi
  fi
else
  origin_head="$(git symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -n "$origin_head" ]; then
    candidate_branch="${origin_head#refs/remotes/origin/}"
    if [ "$candidate_branch" = "$origin_head" ] || [ -z "$candidate_branch" ]; then
      default_detection_note="origin/HEAD does not point to a recognizable branch"
    elif candidate_ref="$(find_branch_ref "$candidate_branch")"; then
      default_branch="$candidate_branch"
      default_ref="$candidate_ref"
      default_detection_note="detected from origin/HEAD"
    else
      default_detection_note="origin/HEAD points to '$candidate_branch', but that branch is unavailable"
    fi
  else
    remote_head_count=0
    remote_head_ref=""
    remote_refs="$(git for-each-ref --format='%(refname)' refs/remotes 2>/dev/null || true)"
    for remote_ref in $remote_refs; do
      case "$remote_ref" in */HEAD) ;; *) continue ;; esac
      [ "$remote_ref" = "refs/remotes/origin/HEAD" ] && continue
      remote_target="$(git symbolic-ref -q "$remote_ref" 2>/dev/null || true)"
      if [ -n "$remote_target" ] && git show-ref --verify --quiet "$remote_target"; then
        remote_head_ref="$remote_target"
        remote_head_count=$((remote_head_count + 1))
      fi
    done

    if [ "$remote_head_count" -eq 1 ]; then
      remote_path="${remote_head_ref#refs/remotes/}"
      candidate_branch="${remote_path#*/}"
      if candidate_ref="$(find_branch_ref "$candidate_branch")"; then
        default_branch="$candidate_branch"
        default_ref="$candidate_ref"
        default_detection_note="detected from remote HEAD"
      else
        default_detection_note="remote HEAD points to '$candidate_branch', but that branch is ambiguous or unavailable"
      fi
    elif [ "$remote_head_count" -gt 1 ]; then
      default_detection_note="multiple remote HEAD branches are configured"
    else
      candidate_count=0
      candidate_ambiguous=""
      for candidate_branch in main master develop development; do
        if candidate_ref="$(find_branch_ref "$candidate_branch")"; then
          candidate_count=$((candidate_count + 1))
          default_branch="$candidate_branch"
          default_ref="$candidate_ref"
        else
          ref_status=$?
          if [ "$ref_status" -eq 2 ]; then
            candidate_ambiguous="$candidate_branch"
          fi
        fi
      done
      if [ -n "$candidate_ambiguous" ]; then
        default_branch=""
        default_ref=""
        default_detection_note="multiple remotes contain '$candidate_ambiguous'"
      elif [ "$candidate_count" -eq 1 ]; then
        default_detection_note="detected as the only conventional base-branch candidate"
      elif [ "$candidate_count" -gt 1 ]; then
        default_branch=""
        default_ref=""
        default_detection_note="multiple conventional base-branch candidates exist"
      else
        default_detection_note="no base branch could be detected"
      fi
    fi
  fi
fi

if [ "$branch_fail" -eq 0 ] && ! git check-ref-format --branch "$SLUG" >/dev/null 2>&1; then
  branch_fail=1
  branch_note="invalid feature branch slug"
  branch_fix="choose a feature description that produces a valid Git branch name, then re-run."
fi

worktree_path=""

if [ "$branch_fail" -eq 0 ]; then
  protected_branch=0
  case "$current_branch" in
    main|master|develop|development) protected_branch=1 ;;
  esac
  if [ -n "$default_branch" ] && [ "$current_branch" = "$default_branch" ]; then
    protected_branch=1
  fi

  wt_root="$(dirname "$REPO_ROOT")/.speckit-worktrees/$(basename "$REPO_ROOT")"
  wt_path="$wt_root/$SLUG"

  if [ "$current_branch" = "$SLUG" ] && [ "$protected_branch" -eq 0 ]; then
    worktree_path="$REPO_ROOT"
    branch_note="on feature branch '$SLUG'; reusing this checkout as the feature worktree"
  elif [ "$protected_branch" -eq 1 ]; then
    if [ -z "$default_branch" ] || [ -z "$default_ref" ]; then
      branch_fail=1
      branch_note="on protected branch '$current_branch'; base branch could not be resolved (${default_detection_note})"
      branch_fix="set SPECKIT_BASE_BRANCH for this run or run 'git config speckit.baseBranch <branch>' in this repository, then re-run."
    elif [ "$SLUG" = "$default_branch" ] || [ "$SLUG" = "main" ] || [ "$SLUG" = "master" ] || [ "$SLUG" = "develop" ] || [ "$SLUG" = "development" ]; then
      branch_fail=1
      branch_note="feature slug '$SLUG' conflicts with a protected branch name"
      branch_fix="choose a feature description that produces a non-protected branch name, then re-run."
    else
      existing_wt=""
      list_wt=""
      list_branch=""
      while IFS= read -r wt_line; do
        case "$wt_line" in
          worktree\ *)
            list_wt="${wt_line#worktree }"
            list_branch=""
            ;;
          branch\ *)
            list_branch="${wt_line#branch }"
            ;;
          bare)
            list_branch=""
            ;;
        esac
        if [ "$list_branch" = "refs/heads/$SLUG" ] && [ -n "$list_wt" ]; then
          existing_wt="$list_wt"
        fi
      done <<LIST
$(git worktree list --porcelain 2>/dev/null || true)
LIST
      if [ -n "$existing_wt" ]; then
        worktree_path="$existing_wt"
        current_branch="$SLUG"
        branch_note="reused existing feature worktree for '$SLUG' at $worktree_path (base '$default_branch'; $default_detection_note)"
      elif git show-ref --verify --quiet "refs/heads/$SLUG"; then
        if mkdir -p "$wt_root" && git worktree add -- "$wt_path" "$SLUG" >/dev/null 2>&1; then
          worktree_path="$wt_path"
          current_branch="$SLUG"
          branch_note="added feature worktree for existing branch '$SLUG' at $worktree_path (base '$default_branch'; $default_detection_note)"
        else
          branch_fail=1
          branch_note="failed to add a worktree for existing branch '$SLUG'"
          branch_fix="could not add a worktree for '${SLUG}' at ${wt_path}; remove the conflicting directory or check where the branch is checked out, then re-run."
        fi
      else
        if mkdir -p "$wt_root" && git worktree add -b "$SLUG" -- "$wt_path" "$default_ref" >/dev/null 2>&1; then
          worktree_path="$wt_path"
          current_branch="$SLUG"
          branch_note="created feature branch '$SLUG' from '$default_branch' ($default_detection_note); feature worktree at $worktree_path"
        else
          branch_fail=1
          branch_note="failed to create branch '$SLUG' with a feature worktree"
          branch_fix="could not create branch '${SLUG}' with a worktree at ${wt_path}; resolve the Git error (existing path, permissions, or invalid base ref), then re-run."
        fi
      fi
    fi
  else
    branch_fail=1
    if [ -n "$default_branch" ]; then
      branch_note="on '$current_branch', which is neither the protected base ('$default_branch') nor '$SLUG'"
      branch_fix="on '${current_branch}'; switch to the base branch '${default_branch}' or to '${SLUG}', then re-run. Do not create a second feature branch."
    else
      branch_note="on unrelated branch '$current_branch'; base branch could not be resolved (${default_detection_note})"
      branch_fix="set SPECKIT_BASE_BRANCH for this run or run 'git config speckit.baseBranch <branch>' in this repository, then switch to that base or '${SLUG}' and re-run."
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Spec Kit layout (required)
# ---------------------------------------------------------------------------

layout_fail=0
layout_missing=""
layout_flavor=""

if [ ! -d ".specify" ]; then
  layout_fail=1
  layout_missing=".specify/"
fi

# Canonical: Pi enrollment (specify init --integration pi).
pi_ok=1
for rel in \
  ".pi/prompts/speckit.specify.md" \
  ".pi/prompts/speckit.clarify.md" \
  ".pi/prompts/speckit.plan.md" \
  ".pi/prompts/speckit.tasks.md" \
  ".pi/prompts/speckit.analyze.md" \
  ".pi/prompts/speckit.implement.md" \
  ".pi/prompts/speckit.converge.md"; do
  if [ ! -f "$rel" ]; then
    pi_ok=0
    break
  fi
done

if [ "$pi_ok" -eq 1 ]; then
  layout_flavor="pi (.pi/prompts/)"
else
  # Legacy fallback 1: Cursor enrollment.
  cursor_ok=1
  for rel in \
    ".cursor/skills/speckit-specify/SKILL.md" \
    ".cursor/skills/speckit-clarify/SKILL.md" \
    ".cursor/skills/speckit-plan/SKILL.md" \
    ".cursor/skills/speckit-tasks/SKILL.md" \
    ".cursor/skills/speckit-analyze/SKILL.md" \
    ".cursor/skills/speckit-implement/SKILL.md" \
    ".cursor/skills/speckit-converge/SKILL.md"; do
    if [ ! -f "$rel" ]; then
      cursor_ok=0
      break
    fi
  done
  if [ "$cursor_ok" -eq 1 ]; then
    layout_flavor="cursor-legacy (.cursor/skills/)"
  else
    # Legacy fallback 2: retired Opencode enrollment.
    opencode_ok=1
    for rel in \
      ".opencode/commands/speckit.specify.md" \
      ".opencode/commands/speckit.clarify.md" \
      ".opencode/commands/speckit.plan.md" \
      ".opencode/commands/speckit.tasks.md" \
      ".opencode/commands/speckit.analyze.md" \
      ".opencode/commands/speckit.implement.md" \
      ".opencode/commands/speckit.converge.md"; do
      if [ ! -f "$rel" ]; then
        opencode_ok=0
        break
      fi
    done
    if [ "$opencode_ok" -eq 1 ]; then
      layout_flavor="opencode-legacy (.opencode/commands/)"
    else
      layout_fail=1
      layout_missing=".pi/prompts/speckit.{specify,clarify,plan,tasks,analyze,implement,converge}.md (or legacy .cursor/skills/speckit-*/SKILL.md)"
    fi
  fi
fi

if [ "$layout_fail" -eq 0 ]; then
  layout_note=".specify/ and all seven project speckit skills present via ${layout_flavor:-pi}"
else
  layout_note="missing ${layout_missing}"
fi

# ---------------------------------------------------------------------------
# Optional project checks from .specify/ready.yml
# ---------------------------------------------------------------------------

project_check_lines=""
project_fix_lines=""
project_required_fail=0
saw_malformed=0

PYPROG="$(cat <<'PY'
import re
import sys


def emit_malformed(msg):
    sys.stdout.write("MALFORMED\x1f" + msg + "\n")


path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        raw_lines = fh.read().splitlines()
except Exception as exc:  # noqa: BLE001
    emit_malformed("cannot read ready.yml: %s" % exc)
    sys.exit(0)

start = None
for i, line in enumerate(raw_lines):
    s = line.strip()
    if s == "" or s.startswith("#"):
        continue
    if re.match(r"^checks\s*:\s*$", s):
        start = i
        break
    if re.match(r"^[A-Za-z0-9_.-]+\s*:", s):
        continue
    emit_malformed("unexpected top-level content on line %d" % (i + 1))
    sys.exit(0)

if start is None:
    emit_malformed("no 'checks:' block found")
    sys.exit(0)

items = []
cur = None
for j in range(start + 1, len(raw_lines)):
    line = raw_lines[j]
    s = line.strip()
    if s == "" or s.startswith("#"):
        continue
    indent = len(line) - len(line.lstrip())
    if indent == 0:
        break
    m = re.match(r"^\s*-\s*(.*)$", line)
    if m:
        if cur is not None:
            items.append(cur)
        cur = []
        rest = m.group(1).strip()
        if rest:
            km = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", rest)
            if not km:
                emit_malformed("invalid list item on line %d" % (j + 1))
                sys.exit(0)
            cur.append((km.group(1), km.group(2).strip()))
        continue
    km = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
    if km is not None and cur is not None:
        cur.append((km.group(1), km.group(2).strip()))
        continue
    emit_malformed("invalid line %d" % (j + 1))
    sys.exit(0)

if cur is not None:
    items.append(cur)


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_bool(value, default):
    value = value.strip().lower()
    if value == "":
        return default
    if value in ("true", "yes", "on", "1"):
        return True
    if value in ("false", "no", "off", "0"):
        return False
    return default


for idx, pairs in enumerate(items):
    kv = {}
    names = []
    for key, value in pairs:
        key_l = key.lower()
        value_u = unquote(value)
        if key_l == "name":
            names.append(value_u)
        else:
            kv[key_l] = value_u

    label = names[0] if names else ("check-%d" % (idx + 1))
    check = kv.get("check", "").lower()
    required = parse_bool(kv.get("required", ""), True)

    var = ""
    for key in ("var", "env_var", "env", "value"):
        if kv.get(key):
            var = kv[key]
            break
    if not var:
        if len(names) >= 2:
            var = names[-1]
        elif names:
            var = names[0]

    fields = [
        "name=%s" % label,
        "check=%s" % check,
        "required=%s" % ("true" if required else "false"),
    ]
    if check == "tcp":
        fields.append("host=%s" % kv.get("host", ""))
        fields.append("port=%s" % kv.get("port", ""))
    elif check == "http":
        fields.append("url=%s" % kv.get("url", ""))
        fields.append("expect_status=%s" % (kv.get("expect_status", "") or "200"))
    elif check == "file_exists":
        fields.append("path=%s" % kv.get("path", ""))
    elif check == "env_var_set":
        fields.append("var=%s" % var)

    sys.stdout.write("\x1f".join(fields) + "\n")
PY
)"

tcp_ok() {
  python3 - "$1" "$2" <<'PY' >/dev/null 2>&1
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect((sys.argv[1], int(sys.argv[2])))
except Exception:
    sys.exit(1)
finally:
    sock.close()
sys.exit(0)
PY
}

http_code() {
  curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "$1" 2>/dev/null || true
}

if [ -f ".specify/ready.yml" ]; then
  parse_out="$(python3 -c "$PYPROG" ".specify/ready.yml" 2>/dev/null || true)"
  if [ -n "$parse_out" ]; then
    while IFS= read -r record; do
      if [ -z "$record" ]; then
        continue
      fi
      IFS=$'\x1f' read -ra parts <<< "$record"
      first="${parts[0]:-}"

      if [ "$first" = "MALFORMED" ]; then
        if [ "$saw_malformed" -eq 0 ]; then
          saw_malformed=1
          msg="${parts[1]:-malformed ready.yml}"
          project_required_fail=1
          project_check_lines="${project_check_lines}- [required] ready-yml: fail — malformed: ${msg}"$'\n'
          project_fix_lines="${project_fix_lines}- .specify/ready.yml is malformed (${msg}); fix its YAML, then re-run."$'\n'
        fi
        continue
      fi

      label=""
      ctype=""
      creq="true"
      cvar=""
      cpath=""
      chost=""
      cport=""
      curl_url=""
      cstatus="200"
      for field in "${parts[@]}"; do
        key="${field%%=*}"
        val="${field#*=}"
        case "$key" in
          name) label="$val" ;;
          check) ctype="$val" ;;
          required) creq="$val" ;;
          var) cvar="$val" ;;
          path) cpath="$val" ;;
          host) chost="$val" ;;
          port) cport="$val" ;;
          url) curl_url="$val" ;;
          expect_status) cstatus="$val" ;;
        esac
      done

      cstat="pass"
      cnote=""
      case "$ctype" in
        tcp)
          if [ -z "$chost" ] || [ -z "$cport" ]; then
            cstat="fail"; cnote="missing host or port"
          elif tcp_ok "$chost" "$cport" || tcp_ok "$chost" "$cport"; then
            cstat="pass"; cnote="${chost}:${cport} reachable"
          else
            cstat="fail"; cnote="${chost}:${cport} not reachable"
          fi
          ;;
        http)
          if [ -z "$curl_url" ]; then
            cstat="fail"; cnote="missing url"
          else
            code="$(http_code "$curl_url")"
            if [ "$code" != "$cstatus" ]; then
              code="$(http_code "$curl_url")"
            fi
            if [ "$code" = "$cstatus" ]; then
              cstat="pass"; cnote="status ${code}"
            else
              cstat="fail"; cnote="status ${code:-none} (expected ${cstatus})"
            fi
          fi
          ;;
        file_exists)
          if [ -z "$cpath" ]; then
            cstat="fail"; cnote="missing path"
          elif [ -e "$REPO_ROOT/$cpath" ]; then
            cstat="pass"; cnote="${cpath} exists"
          else
            cstat="fail"; cnote="${cpath} missing"
          fi
          ;;
        env_var_set)
          if [ -z "$cvar" ]; then
            cstat="fail"; cnote="missing variable name"
          elif [ -n "${!cvar:-}" ]; then
            cstat="pass"; cnote="${cvar} is set"
          else
            cstat="fail"; cnote="${cvar} is not set"
          fi
          ;;
        *)
          cstat="fail"
          cnote="unknown check type '${ctype:-<none>}'"
          creq="true"
          ;;
      esac

      if [ "$creq" = "true" ]; then
        rlabel="required"
      else
        rlabel="optional"
      fi
      project_check_lines="${project_check_lines}- [${rlabel}] ${label} (${ctype:-unknown}): ${cstat} — ${cnote}"$'\n'
      if [ "$cstat" = "fail" ] && [ "$creq" = "true" ]; then
        project_required_fail=1
        project_fix_lines="${project_fix_lines}- ${label} (${ctype:-unknown}): ${cnote}; fix it or set required: false, then re-run."$'\n'
      fi
    done <<< "$parse_out"
  fi
fi

# ---------------------------------------------------------------------------
# Worker runtime (required for the backend this run will use)
# Resolution: SPECKIT_WORKER, else git config speckit.worker, else antigravity.
# ---------------------------------------------------------------------------

worker_fail=0
worker_note=""
worker_fix=""
worker_raw="${SPECKIT_WORKER:-}"
worker_source="SPECKIT_WORKER"
if [ -z "$worker_raw" ]; then
  worker_raw="$(git config --local --get speckit.worker 2>/dev/null || true)"
  if [ -n "$worker_raw" ]; then
    worker_source="git config speckit.worker"
  else
    worker_raw="antigravity"
    worker_source="default"
  fi
fi
worker_lc="$(printf '%s' "$worker_raw" | tr '[:upper:]' '[:lower:]')"
case "$worker_lc" in
  pi)
    worker="pi"
    pi_bin="${SPECKIT_PI_BIN:-pi}"
    if command -v "$pi_bin" >/dev/null 2>&1; then
      pi_ver="$("$pi_bin" --version 2>/dev/null | head -n 1 | tr '\n' ' ')"
      worker_note="pi on PATH (${worker_source}${pi_ver:+; $pi_ver})"
    else
      worker_fail=1
      worker_note="pi not on PATH (${worker_source})"
      worker_fix="install Pi and put 'pi' on PATH, or unset SPECKIT_WORKER / set SPECKIT_WORKER=antigravity to use the default Antigravity SDK backend, then re-run."
    fi
    ;;
  antigravity|agy|google-antigravity)
    worker="antigravity"
    if ! command -v python3 >/dev/null 2>&1; then
      worker_fail=1
      worker_note="python3 not on PATH (${worker_source})"
      worker_fix="install Python 3, then 'pip install google-antigravity', then re-run."
    elif ! python3 -c "from google.antigravity import Agent, LocalAgentConfig" >/dev/null 2>&1; then
      worker_fail=1
      worker_note="google.antigravity is not importable (${worker_source})"
      worker_fix="pip install google-antigravity (PyPI wheel; a git clone has no localharness binary), then re-run."
    else
      auth_ok=0
      auth_note=""
      if [ -n "${GEMINI_API_KEY:-}" ] || [ -n "${GOOGLE_API_KEY:-}" ]; then
        auth_ok=1
        auth_note="Gemini API key env is set"
      elif [ "${GOOGLE_GENAI_USE_VERTEXAI:-}" = "True" ] || [ "${GOOGLE_GENAI_USE_VERTEXAI:-}" = "true" ] || [ "${GOOGLE_GENAI_USE_VERTEXAI:-}" = "1" ] || [ "${GOOGLE_GENAI_USE_ENTERPRISE:-}" = "True" ] || [ "${GOOGLE_GENAI_USE_ENTERPRISE:-}" = "true" ]; then
        if [ -n "${GOOGLE_CLOUD_PROJECT:-}" ] || [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
          auth_ok=1
          auth_note="Vertex/Enterprise env is set"
        else
          worker_fail=1
          worker_note="Vertex enabled but GOOGLE_CLOUD_PROJECT / ADC missing (${worker_source})"
          worker_fix="set GOOGLE_CLOUD_PROJECT (and ADC via gcloud auth application-default login) or GEMINI_API_KEY, then re-run."
        fi
      else
        worker_fail=1
        worker_note="no Gemini API key or Vertex env (${worker_source})"
        worker_fix="set GEMINI_API_KEY (or GOOGLE_API_KEY), or Vertex GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT, then re-run. Do not paste keys into chat."
      fi
      if [ "$worker_fail" -eq 0 ] && [ "$auth_ok" -eq 1 ]; then
        worker_note="google.antigravity importable; ${auth_note} (${worker_source})"
      fi
    fi
    ;;
  *)
    worker="$worker_lc"
    worker_fail=1
    worker_note="unknown worker backend '$worker_raw' (${worker_source})"
    worker_fix="set SPECKIT_WORKER or git config speckit.worker to 'pi' or 'antigravity', then re-run."
    ;;
esac

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

if [ "$branch_fail" -eq 0 ]; then
  bstat="pass"
else
  bstat="fail"
fi
if [ "$layout_fail" -eq 0 ]; then
  lstat="pass"
else
  lstat="fail"
fi

if [ "$worker_fail" -eq 0 ]; then
  wstat="pass"
else
  wstat="fail"
fi

ready="ok"
if [ "$branch_fail" -ne 0 ] || [ "$layout_fail" -ne 0 ] || [ "$project_required_fail" -ne 0 ] || [ "$worker_fail" -ne 0 ]; then
  ready="blocked"
fi

printf 'READY: %s\n' "$ready"
printf 'FLOW_ID: %s\n' "$FLOW_ID"
printf 'BRANCH: %s\n' "$current_branch"
printf 'WORKER: %s\n' "$worker"
if [ "$ready" = "ok" ]; then
  printf 'WORKTREE: %s\n' "$worktree_path"
fi
printf 'CHECKS:\n'
printf -- '- [required] git-branch-state: %s — %s\n' "$bstat" "$branch_note"
printf -- '- [required] speckit-layout: %s — %s\n' "$lstat" "$layout_note"
printf -- '- [required] worker-runtime: %s — %s\n' "$wstat" "$worker_note"
if [ -n "$project_check_lines" ]; then
  printf '%s' "$project_check_lines"
fi

if [ "$ready" = "blocked" ]; then
  printf 'FIXES:\n'
  if [ "$branch_fail" -ne 0 ] && [ -n "$branch_fix" ]; then
    printf -- '- %s\n' "$branch_fix"
  fi
  if [ "$layout_fail" -ne 0 ]; then
    printf -- '- restore the missing Spec Kit files under %s (%s), then re-run.\n' "$REPO_ROOT" "$layout_missing"
  fi
  if [ "$worker_fail" -ne 0 ] && [ -n "$worker_fix" ]; then
    printf -- '- %s\n' "$worker_fix"
  fi
  if [ -n "$project_fix_lines" ]; then
    printf '%s' "$project_fix_lines"
  fi
fi

if [ "$ready" = "ok" ]; then
  exit 0
else
  exit 1
fi

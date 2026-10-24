#!/usr/bin/env bash
# ready-check.selftest.sh -- deterministic self-test for ready-check.sh.
# No live network is used.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$SCRIPT_DIR/ready-check.sh"

if [ ! -x "$CHECK" ]; then
  echo "SELFTEST FAIL: ready-check.sh is not executable at $CHECK"
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Pin Pi for the suite so fixtures stay READY-ok without the Antigravity SDK.
# Default-backend coverage is a separate case below.
export SPECKIT_WORKER=pi
STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
printf '#!/bin/sh\necho pi-stub 0.0.0\n' > "$STUB_BIN/pi"
chmod +x "$STUB_BIN/pi"
export PATH="$STUB_BIN:$PATH"

fail() {
  echo "SELFTEST FAIL: $1"
  exit 1
}

make_fixture() {
  local d="$1"
  local base_branch="${2:-main}"
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" checkout -q -b "$base_branch" 2>/dev/null || true
  mkdir -p "$d/.specify"
  local s
  for s in specify clarify plan tasks analyze implement converge; do
    mkdir -p "$d/.cursor/skills/speckit-$s"
    printf '# %s\n' "$s" > "$d/.cursor/skills/speckit-$s/SKILL.md"
  done
  printf 'hello\n' > "$d/README.md"
  git -C "$d" add -A
  git -C "$d" -c user.email=selftest@example.com -c user.name=selftest commit -qm init
}

# run_check <repo> <flow_id> <slug> -> sets OUT and RC
run_check() {
  OUT="$("$CHECK" "$1" "$2" "$3" 2>&1)" && RC=0 || RC=$?
}

run_check_with_base() {
  OUT="$(SPECKIT_BASE_BRANCH="$4" "$CHECK" "$1" "$2" "$3" 2>&1)" && RC=0 || RC=$?
}

expect_rc() {
  if [ "$RC" -ne "$1" ]; then
    fail "$2: exit $RC (expected $1); output:
$OUT"
  fi
}

expect_contains() {
  case "$OUT" in
    *"$1"*) ;;
    *) fail "$2: output missing '$1'; output:
$OUT" ;;
  esac
}

expect_not_contains() {
  case "$OUT" in
    *"$1"*) fail "$2: output unexpectedly contains '$1'; output:
$OUT" ;;
    *) ;;
  esac
}

# Physical (symlink-resolved) form of a directory, matching ready-check.sh's
# own REPO_ROOT resolution, so expected worktree paths compare equal.
phys() {
  (cd "$1" && pwd -P)
}

# expected worktree path for a repo/slug pair
wt_path() {
  local repo="$1" slug="$2"
  printf '%s/.speckit-worktrees/%s/%s\n' "$(dirname "$(phys "$repo")")" "$(basename "$(phys "$repo")")" "$slug"
}

# assert_worktree_ok <repo> <slug> — WORKTREE is reported, exists, is a git
# worktree checked out on <slug>, and the original checkout did not move.
assert_worktree_ok() {
  local repo="$1" slug="$2" label="$3"
  local wt
  wt="$(printf '%s\n' "$OUT" | sed -n 's/^WORKTREE: //p')"
  [ -n "$wt" ] || fail "$label: no WORKTREE line in report; output:
$OUT"
  local expected
  expected="$(wt_path "$repo" "$slug")"
  [ "$wt" = "$expected" ] || fail "$label: WORKTREE '$wt' != expected '$expected'"
  [ -d "$wt" ] || fail "$label: worktree path does not exist: $wt"
  [ "$(git -C "$wt" rev-parse --is-inside-work-tree)" = "true" ] || fail "$label: $wt is not a git worktree"
  local wt_branch
  wt_branch="$(git -C "$wt" rev-parse --abbrev-ref HEAD)"
  [ "$wt_branch" = "$slug" ] || fail "$label: worktree HEAD is '$wt_branch', expected '$slug'"
}

# --- Case 1: clean main fixture -> creates branch worktree, main stays on main
REPO1="$TMP/repo1"
make_fixture "$REPO1"
run_check "$REPO1" flow_selftest_1 user-auth
expect_rc 0 "case1 (create branch worktree)"
expect_contains "READY: ok" "case1"
expect_contains "FLOW_ID: flow_selftest_1" "case1"
expect_contains "BRANCH: user-auth" "case1"
expect_contains "WORKTREE: " "case1"
expect_contains "git-branch-state: pass" "case1"
expect_contains "speckit-layout: pass" "case1"
expect_contains "WORKER: pi" "case1"
expect_contains "worker-runtime: pass" "case1"
branch1="$(git -C "$REPO1" rev-parse --abbrev-ref HEAD)"
[ "$branch1" = "main" ] || fail "case1: original checkout is '$branch1', expected main (no feature checkout)"
assert_worktree_ok "$REPO1" user-auth "case1"
WT1="$(wt_path "$REPO1" user-auth)"

# --- Case 2: re-run on same slug -> reuses same worktree, READY ok -----------
run_check "$REPO1" flow_selftest_2 user-auth
expect_rc 0 "case2 (reuse worktree)"
expect_contains "READY: ok" "case2"
expect_contains "BRANCH: user-auth" "case2"
expect_contains "git-branch-state: pass" "case2"
assert_worktree_ok "$REPO1" user-auth "case2"
WT2="$(wt_path "$REPO1" user-auth)"
[ "$WT1" = "$WT2" ] || fail "case2: re-run produced a different worktree path ('$WT2' vs '$WT1')"
wt_count="$(git -C "$REPO1" worktree list --porcelain | grep -c "^worktree .*/user-auth$" || true)"
[ "$wt_count" = "1" ] || fail "case2: expected exactly 1 worktree for user-auth, found $wt_count"

# --- Case 2b: reuse note mentions reused worktree ----------------------------
expect_contains "reused existing feature worktree" "case2b"

# --- Case 3: unrelated branch -> blocked, stays on unrelated branch ----------
git -C "$REPO1" checkout -q -b other-feature
run_check "$REPO1" flow_selftest_3 user-auth
expect_rc 1 "case3 (wrong branch)"
expect_contains "READY: blocked" "case3"
expect_contains "git-branch-state: fail" "case3"
expect_contains "FIXES:" "case3"
expect_contains "switch" "case3"
branch3="$(git -C "$REPO1" rev-parse --abbrev-ref HEAD)"
[ "$branch3" = "other-feature" ] || fail "case3: branch changed to '$branch3', expected other-feature"

# --- Case 4: missing .specify -> layout fail, blocked ------------------------
REPO2="$TMP/repo2"
make_fixture "$REPO2"
rm -rf "$REPO2/.specify"
run_check "$REPO2" flow_selftest_4 layout-check
expect_rc 1 "case4 (missing layout)"
expect_contains "READY: blocked" "case4"
expect_contains "speckit-layout: fail" "case4"
expect_contains ".specify/" "case4"

# --- Case 5: ready.yml required + optional file_exists -----------------------
REPO3="$TMP/repo3"
make_fixture "$REPO3"
cat > "$REPO3/.specify/ready.yml" <<'YML'
checks:
  - name: env-file-present
    type: setup
    required: true
    check: file_exists
    path: .env
  - name: optional-note
    type: setup
    required: false
    check: file_exists
    path: notes/optional.txt
YML
git -C "$REPO3" add .specify/ready.yml
git -C "$REPO3" -c user.email=selftest@example.com -c user.name=selftest commit -qm 'add ready checks'
run_check "$REPO3" flow_selftest_5 checks-required
expect_rc 1 "case5 (required file missing)"
expect_contains "READY: blocked" "case5"
expect_contains "env-file-present" "case5"
expect_contains "FIXES:" "case5"

cat > "$REPO3/.specify/ready.yml" <<'YML'
checks:
  - name: optional-note
    type: setup
    required: false
    check: file_exists
    path: notes/optional.txt
YML
git -C "$REPO3" add .specify/ready.yml
git -C "$REPO3" -c user.email=selftest@example.com -c user.name=selftest commit -qm 'make ready check optional'
run_check "$REPO3" flow_selftest_5b checks-required
expect_rc 0 "case5b (only optional missing)"
expect_contains "READY: ok" "case5b"
expect_contains "optional-note" "case5b"
expect_contains "[optional]" "case5b"
expect_not_contains "FIXES:" "case5b"
assert_worktree_ok "$REPO3" checks-required "case5b"

# --- Case 6: malformed ready.yml -> blocked ----------------------------------
REPO4="$TMP/repo4"
make_fixture "$REPO4"
cat > "$REPO4/.specify/ready.yml" <<'YML'
checks:
  - name: broken
    this is not valid yaml
YML
git -C "$REPO4" add .specify/ready.yml
git -C "$REPO4" -c user.email=selftest@example.com -c user.name=selftest commit -qm 'add malformed ready checks'
run_check "$REPO4" flow_selftest_6 malformed-check
expect_rc 1 "case6 (malformed ready.yml)"
expect_contains "READY: blocked" "case6"
expect_contains "ready-yml" "case6"
expect_contains "malformed" "case6"

# --- Case 7: development as the only conventional base -> worktree from it ---
REPO5="$TMP/repo5"
make_fixture "$REPO5" development
run_check "$REPO5" flow_selftest_7 branch-development
expect_rc 0 "case7 (development base)"
expect_contains "READY: ok" "case7"
expect_contains "created feature branch 'branch-development' from 'development'" "case7"
branch7="$(git -C "$REPO5" rev-parse --abbrev-ref HEAD)"
[ "$branch7" = "development" ] || fail "case7: original checkout is '$branch7', expected development"
assert_worktree_ok "$REPO5" branch-development "case7"

# --- Case 8: origin/HEAD overrides local candidate-name guesses --------------
REPO6="$TMP/repo6"
make_fixture "$REPO6"
git -C "$REPO6" checkout -q -b development
printf 'development baseline\n' >> "$REPO6/README.md"
git -C "$REPO6" add README.md
git -C "$REPO6" -c user.email=selftest@example.com -c user.name=selftest commit -qm development
development_sha="$(git -C "$REPO6" rev-parse HEAD)"
git -C "$REPO6" checkout -q main
git -C "$REPO6" update-ref refs/remotes/origin/development "$development_sha"
git -C "$REPO6" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/development
run_check "$REPO6" flow_selftest_8 remote-default
expect_rc 0 "case8 (origin HEAD)"
expect_contains "created feature branch 'remote-default' from 'development' (detected from origin/HEAD)" "case8"
assert_worktree_ok "$REPO6" remote-default "case8"
feature8_sha="$(git -C "$(wt_path "$REPO6" remote-default)" rev-parse HEAD)"
[ "$feature8_sha" = "$development_sha" ] || fail "case8: feature worktree HEAD was not created from origin/HEAD's development target"

# --- Case 9: local repo config explicitly selects the base -------------------
REPO7="$TMP/repo7"
make_fixture "$REPO7"
git -C "$REPO7" checkout -q -b development
printf 'configured development baseline\n' >> "$REPO7/README.md"
git -C "$REPO7" add README.md
git -C "$REPO7" -c user.email=selftest@example.com -c user.name=selftest commit -qm development
configured_sha="$(git -C "$REPO7" rev-parse HEAD)"
git -C "$REPO7" checkout -q main
git -C "$REPO7" config speckit.baseBranch development
run_check "$REPO7" flow_selftest_9 configured-base
expect_rc 0 "case9 (configured base)"
expect_contains "created feature branch 'configured-base' from 'development' (using git config speckit.baseBranch)" "case9"
assert_worktree_ok "$REPO7" configured-base "case9"
configured_feature_sha="$(git -C "$(wt_path "$REPO7" configured-base)" rev-parse HEAD)"
[ "$configured_feature_sha" = "$configured_sha" ] || fail "case9: feature worktree did not use configured base branch"

# --- Case 10: ambiguous default branches -> block without a worktree ---------
REPO8="$TMP/repo8"
make_fixture "$REPO8"
git -C "$REPO8" branch master
run_check "$REPO8" flow_selftest_10 ambiguous-base
expect_rc 1 "case10 (ambiguous base)"
expect_contains "READY: blocked" "case10"
expect_contains "multiple conventional base-branch candidates exist" "case10"
expect_contains "git config speckit.baseBranch" "case10"
expect_not_contains "WORKTREE: " "case10"
branch10="$(git -C "$REPO8" rev-parse --abbrev-ref HEAD)"
[ "$branch10" = "main" ] || fail "case10: branch changed to '$branch10', expected main"
[ ! -e "$(wt_path "$REPO8" ambiguous-base)" ] || fail "case10: a worktree was created despite an unresolved base"
[ ! -e "$(dirname "$(phys "$REPO8")")/.speckit-worktrees/$(basename "$(phys "$REPO8")")" ] || fail "case10: .speckit-worktrees dir was created despite an unresolved base"

# --- Case 11: dirty protected branch -> still READY ok via worktree ----------
REPO9="$TMP/repo9"
make_fixture "$REPO9"
printf 'uncommitted\n' > "$REPO9/uncommitted.txt"
run_check "$REPO9" flow_selftest_11 dirty-base
expect_rc 0 "case11 (dirty protected base)"
expect_contains "READY: ok" "case11"
expect_contains "git-branch-state: pass" "case11"
branch11="$(git -C "$REPO9" rev-parse --abbrev-ref HEAD)"
[ "$branch11" = "main" ] || fail "case11: original checkout is '$branch11', expected main"
assert_worktree_ok "$REPO9" dirty-base "case11"
[ -f "$REPO9/uncommitted.txt" ] || fail "case11: uncommitted file vanished from the original tree"
[ ! -e "$(wt_path "$REPO9" dirty-base)/uncommitted.txt" ] || fail "case11: uncommitted file leaked into the feature worktree"

# --- Case 12: one-run override takes precedence over repo config -------------
REPO10="$TMP/repo10"
make_fixture "$REPO10"
git -C "$REPO10" checkout -q -b development
printf 'environment override baseline\n' >> "$REPO10/README.md"
git -C "$REPO10" add README.md
git -C "$REPO10" -c user.email=selftest@example.com -c user.name=selftest commit -qm development
environment_sha="$(git -C "$REPO10" rev-parse HEAD)"
git -C "$REPO10" checkout -q main
git -C "$REPO10" config speckit.baseBranch main
run_check_with_base "$REPO10" flow_selftest_12 env-override development
expect_rc 0 "case12 (environment override)"
expect_contains "created feature branch 'env-override' from 'development' (using SPECKIT_BASE_BRANCH)" "case12"
assert_worktree_ok "$REPO10" env-override "case12"
environment_feature_sha="$(git -C "$(wt_path "$REPO10" env-override)" rev-parse HEAD)"
[ "$environment_feature_sha" = "$environment_sha" ] || fail "case12: environment override did not take precedence"

# --- Case 13: already on the non-protected slug -> reuse REPO_ROOT -----------
REPO11="$TMP/repo11"
make_fixture "$REPO11"
git -C "$REPO11" checkout -q -b existing-slug
run_check "$REPO11" flow_selftest_13 existing-slug
expect_rc 0 "case13 (already on slug)"
expect_contains "READY: ok" "case13"
expect_contains "BRANCH: existing-slug" "case13"
wt13="$(printf '%s\n' "$OUT" | sed -n 's/^WORKTREE: //p')"
[ "$wt13" = "$(phys "$REPO11")" ] || fail "case13: WORKTREE '$wt13' != '$(phys "$REPO11")'"

# --- Case 14: slug colliding with a protected name -> blocked ----------------
REPO12="$TMP/repo12"
make_fixture "$REPO12"
run_check "$REPO12" flow_selftest_14 develop
expect_rc 1 "case14 (protected slug)"
expect_contains "READY: blocked" "case14"
expect_contains "conflicts with a protected branch name" "case14"
expect_not_contains "WORKTREE: " "case14"
branch14="$(git -C "$REPO12" rev-parse --abbrev-ref HEAD)"
[ "$branch14" = "main" ] || fail "case14: branch changed to '$branch14', expected main"

# --- Case 15: invalid slug -> blocked ----------------------------------------
REPO13="$TMP/repo13"
make_fixture "$REPO13"
run_check "$REPO13" flow_selftest_15 "bad..slug"
expect_rc 1 "case15 (invalid slug)"
expect_contains "READY: blocked" "case15"
expect_contains "invalid feature branch slug" "case15"
expect_not_contains "WORKTREE: " "case15"

# --- Case 16: missing pi on PATH -> worker-runtime fail ----------------------
REPO14="$TMP/repo14"
make_fixture "$REPO14"
OUT="$(SPECKIT_WORKER=pi SPECKIT_PI_BIN=/no-such-pi-binary "$CHECK" "$REPO14" flow_selftest_16 worker-pi-missing 2>&1)" && RC=0 || RC=$?
expect_rc 1 "case16 (pi missing)"
expect_contains "READY: blocked" "case16"
expect_contains "WORKER: pi" "case16"
expect_contains "worker-runtime: fail" "case16"
expect_contains "pi not on PATH" "case16"

# --- Case 17: antigravity without SDK package -> worker-runtime fail ---------
REPO15="$TMP/repo15"
make_fixture "$REPO15"
OUT="$(env -u GEMINI_API_KEY -u GOOGLE_API_KEY -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_GENAI_USE_ENTERPRISE -u GOOGLE_CLOUD_PROJECT -u GOOGLE_APPLICATION_CREDENTIALS SPECKIT_WORKER=antigravity "$CHECK" "$REPO15" flow_selftest_17 worker-agy-missing 2>&1)" && RC=0 || RC=$?
expect_rc 1 "case17 (antigravity sdk missing or unauthenticated)"
expect_contains "READY: blocked" "case17"
expect_contains "WORKER: antigravity" "case17"
expect_contains "worker-runtime: fail" "case17"

# --- Case 18: unknown worker backend -> blocked ------------------------------
REPO16="$TMP/repo16"
make_fixture "$REPO16"
OUT="$(SPECKIT_WORKER=not-a-backend "$CHECK" "$REPO16" flow_selftest_18 worker-unknown 2>&1)" && RC=0 || RC=$?
expect_rc 1 "case18 (unknown worker)"
expect_contains "READY: blocked" "case18"
expect_contains "unknown worker backend" "case18"

# --- Case 19: unset SPECKIT_WORKER -> default antigravity --------------------
REPO17="$TMP/repo17"
make_fixture "$REPO17"
OUT="$(env -u SPECKIT_WORKER -u GEMINI_API_KEY -u GOOGLE_API_KEY -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_GENAI_USE_ENTERPRISE -u GOOGLE_CLOUD_PROJECT -u GOOGLE_APPLICATION_CREDENTIALS "$CHECK" "$REPO17" flow_selftest_19 worker-default 2>&1)" && RC=0 || RC=$?
expect_contains "WORKER: antigravity" "case19 (default antigravity)"
expect_contains "worker-runtime:" "case19"

echo "SELFTEST: ok"
exit 0

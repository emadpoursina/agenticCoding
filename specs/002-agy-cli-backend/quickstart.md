# Quickstart: validating the Antigravity CLI worker backend

Runnable checks after implementation. No live `agy` job required for the gate below (operator-auth CLI is optional extra). Run from repository root.

## Prerequisites

- Git worktree for this feature (`specs/002-agy-cli-backend`)
- `python3`, `rg`, `bash`
- Do **not** `pip install google-antigravity` for these checks

## 1. Wrapper self-test (AC-1, AC-4, AC-5, AC-6, AC-9, AC-10)

```bash
python3 AiNative/docs/agents/antigravity-harness/agy-spawn.py --self-test
```

**Pass**: prints `SELFTEST: ok`. Covers STATUS regex, timeout parse, edit vs scout argv, always `-p`, no `--input-format`, contract prepend, stream-json reconstruct, missing `--model` exit 2 (if asserted), skip-permissions fail-closed helper.

## 2. No SDK import on the worker path (FR-001, FR-017)

```bash
rg -n "from google.antigravity|google.antigravity.Agent" \
  AiNative/docs/agents/antigravity-harness/agy-spawn.py
```

**Pass**: no matches in the wrapper (comments must not instruct SDK Agent as the runtime).

## 3. Ready selftests (AC-3, AC-8, FR-014, FR-015)

```bash
bash AiNative/docs/agents/ready/scripts/ready-check.selftest.sh
bash AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh
```

**Pass**: both exit 0. Case 17 fails closed without `agy` on PATH; fix text is CLI PATH, not `pip install google-antigravity`.

## 4. Forbidden doc claims (AC-7, FR-016)

```bash
rg -n "there is no \`agy -p\`|SDK is the worker runtime" \
  AiNative/docs/agents/antigravity-harness/ \
  AiNative/docs/agents/speckit-orchestrate/ \
  AiNative/docs/agents/ready/SKILL.md \
  AiNative/docs/agents/speckit-ready/SKILL.md \
  AiNative/docs/agents/README.md \
  AiNative/docs/systems/feature-loop.md \
  AiNative/.cursor/commands/antigravity-harness.md
```

**Pass**: zero matches. Positive search should still find `agy-spawn.py`, `agy -p`, and Ready `agy models`.

## 5. Parent still wrapper-only (AC-2)

```bash
rg -n "agy-spawn.py" AiNative/docs/agents/speckit-orchestrate/SKILL.md \
  AiNative/docs/agents/antigravity-harness/SKILL.md
```

**Pass**: spawn instructions name the wrapper. Skills tell the parent not to exec `agy -p` itself.

## 6. Pi unchanged (AC-12)

```bash
git diff --name-only -- AiNative/docs/agents/pi-harness/pi-spawn.mjs
```

**Pass**: empty (or no behavior hunks if the file is listed).

## 7. Changelog (AC-11)

```bash
rg -n "agy -p|CLI headless|agy models" AiNative/CHANGELOG.md
```

**Pass**: newest version records the switch (Keep a Changelog). Recommend `0.4.0`.

## Optional live smoke (not required for tester PASS)

If `agy` is on PATH and `agy models` works:

```bash
python3 AiNative/docs/agents/antigravity-harness/agy-spawn.py \
  --name agy-cli-smoke --cwd "$PWD" --model <id-from-agy-models> --print --timeout 60 \
  -- "Reply with exactly: STATUS: ok"
```

**Pass**: wrapper stdout has `RUN_DIR=` / `LIFECYCLE=`; `report.json` has `workerStatus` from stdout; `ps`/argv of child (if still visible) includes `-p`; stdin of child is not a TTY. Do not start the TUI.

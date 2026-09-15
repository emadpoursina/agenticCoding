# Quickstart: Hermes Startup Context

This guide validates exact-path startup loading, safe diagnostics, precedence,
revision-only records, and the first-delivery templates. It uses temporary
fixtures for failure cases and the existing Hermes container for the operator
path. It does not require a live model, GitHub push, pull request, or
production repository.

## Prerequisites

- Python 3.12 and `uv`
- Docker Compose if running the container check
- The repository at `/Users/emad/Projects/playground/agenticCoding`
- A disposable Hermes home/workspace for any live check

Do not put credentials in the example files or test fixtures.

## 1. Inspect the first-delivery files

```bash
cd /Users/emad/Projects/playground/agenticCoding
test -s personalAgent/AGENTS.md
test -s personalAgent/docs/context/SYSTEM.example.md
test -s personalAgent/docs/context/USER.example.md
git grep -n -E \
  'password|api[_ -]?key|token|private key|BEGIN (RSA|OPENSSH)' \
  -- personalAgent/AGENTS.md personalAgent/docs/context
```

Expected result: the three files exist, the last command finds no secrets, and
the two example files say that the operator must complete them later.

## 2. Run focused startup-context checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest tests/test_startup_context.py
uv run ruff check src tests
```

The focused checks must cover:

- all three files load in registration order;
- exact configured paths are used without fallback lookup;
- missing, unreadable, directory, empty, invalid-UTF-8, duplicate, and
  host-only paths fail with role/path diagnostics;
- no missing file is created;
- revisions change when source bytes change;
- diagnostics contain paths and revisions but not bodies or secrets;
- precedence resolves all documented conflicts; and
- registered text is absent from coding-job requests, model contexts, and
  overlay/task records.

## 3. Run the complete Hermes checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest
uv run ruff check src tests
```

The existing harness, orchestrator, project, workspace, and read-only
AiNative checks must continue to pass. No test should require the persistent
`/opt/data` files or a network credential.

## 4. Provision the persistent files manually

The operator copies safe templates into the host directory that is mounted as
`/opt/data`. Hermes must not do this automatically:

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
mkdir -p "$HERMES_HOME/hermes-context"
cp docs/context/SYSTEM.example.md "$HERMES_HOME/hermes-context/SYSTEM.md"
cp docs/context/USER.example.md "$HERMES_HOME/hermes-context/USER.md"
```

Complete the two copied files before starting the container. Keep the actual
files outside Git.

## 5. Run the safe container diagnostic

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
docker compose up -d
docker exec hermes-personal-agent \
  python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --doctor
```

Expected result: the command exits successfully and reports the configured
AiNative root, available agents, enrolled projects, workspace root, active
harness, persistent state path, and three role/path/revision records. It must
not print any `SYSTEM.md`, `USER.md`, or `AGENTS.md` body.

## 6. Verify fail-closed startup

Temporarily rename one persistent file in the mounted host directory and run
the doctor command again:

```bash
mv "$HERMES_HOME/hermes-context/USER.md" \
   "$HERMES_HOME/hermes-context/USER.md.saved"
docker exec hermes-personal-agent \
  python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --doctor
mv "$HERMES_HOME/hermes-context/USER.md.saved" \
   "$HERMES_HOME/hermes-context/USER.md"
```

Expected result: startup exits non-zero with the `user` role and exact
`/opt/data/hermes-context/USER.md` path, names the missing-file reason, and
does not create a replacement file or print its contents.

## Completion criteria

1. Focused and complete Hermes checks pass.
2. The live doctor command validates all three exact container paths.
3. Missing persistent files stop startup and are never auto-created.
4. Diagnostics contain only safe runtime locations and context metadata.
5. Coding jobs continue to receive project-local context only.

# Quickstart: Ready worktree local files

Validation for implementers and tester. No production app to boot.

## Prerequisites

- This checkout on branch `skip` (spec dir `specs/001-worktree-include-setup`).
- `bash`, `git`, `python3`, `rsync` on PATH (macOS openrsync is enough).
- Do not run the live Ready gate against this repo to “try copy”; use the selftest fixtures.

## Prove the copy step (FR-013 / SC-002)

From either twin (they must stay identical):

```bash
bash AiNative/docs/agents/ready/scripts/ready-check.selftest.sh
bash AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh
```

Expect `SELFTEST: ok` twice. The new case must fail the suite unless:

- a gitignored `.env` listed in `.worktreeinclude` exists in the **created** worktree, and
- a gitignored file **not** listed is absent from that worktree.

Also expect:

- setup `exit 1` → `READY: blocked`, a FIXES line, and the worktree added in that run is gone.
- second Ready on an existing worktree does not overwrite an extra local file and does not re-run setup.
- CHECKS copy notes contain a file count and do not contain copied paths (e.g. `.env` as a path in the copy note).

## Operator docs (SC-007)

```bash
rg -n 'worktreeinclude|setup:' \
  AiNative/docs/agents/ready/AGENTS.md \
  AiNative/docs/agents/ready/SKILL.md \
  AiNative/docs/agents/speckit-ready/AGENTS.md \
  AiNative/docs/agents/speckit-ready/SKILL.md
```

Each of the four files must mention both `.worktreeinclude` and `setup:`.

## Twin sync (FR-012)

```bash
cmp AiNative/docs/agents/ready/scripts/ready-check.sh \
    AiNative/docs/agents/speckit-ready/scripts/ready-check.sh
cmp AiNative/docs/agents/ready/scripts/ready-check.selftest.sh \
    AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh
```

Both `cmp` commands must be silent (exit 0).

## Contracts

See [contracts/ready-report.md](./contracts/ready-report.md) and [contracts/ready-yml-setup.md](./contracts/ready-yml-setup.md). See [data-model.md](./data-model.md) for worktree lifecycle (add vs reuse vs rollback).

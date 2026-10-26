# Contract: `.specify/ready.yml` `setup:`

Optional top-level key. Existing `checks:` list and types are unchanged.

```yaml
# optional
setup: pnpm install

checks:
  - name: example
    check: file_exists
    path: package.json
    required: true
```

Rules:

- `setup` is a single command string (quotes optional). Ready runs it with cwd = the **newly added** worktree only.
- Missing `setup:` → skip setup (not a failure).
- Missing `.specify/ready.yml` → skip project checks and setup (not a failure).
- File with `setup:` and no `checks:` block is valid (setup-only).
- Malformed YAML / invalid `checks:` items remain a required `ready-yml` failure as today.
- `checks:` must not gain a shell/run type. Per-item `type:` keys (including fixture `type: setup`) stay ignored.
- Ready must not invent `.worktreeinclude` or `setup:` for a repo that omitted them.

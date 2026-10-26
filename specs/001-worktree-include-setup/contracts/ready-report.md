# Contract: compact Ready report (copy/setup)

Parent parsers (`speckit-orchestrate`, Hermes) keep the existing field set. This feature only adds CHECKS/FIXES bullets.

```text
READY: ok | blocked
FLOW_ID: <flow_id>
BRANCH: <branch-name>
WORKER: pi | antigravity
WORKTREE: <absolute path; only when READY: ok>
CHECKS:
- [required] git-branch-state: pass|fail — <note>
- [required] speckit-layout: pass|fail — <note>
- [required] worker-runtime: pass|fail — <note>
- [required] worktree-copy: pass|fail — <outcome; if copied, "copied N files"; never paths>
- [required] worktree-setup: pass|fail — <outcome; never command stdout/stderr>
FIXES:
- <only when blocked; one line per required failure>
```

`worktree-copy` / `worktree-setup` appear when Ready selected a feature worktree (new or reuse). They are omitted when the gate never selected a worktree (e.g. invalid slug before add).

Forbidden in any stdout/stderr of the gate: copied relative paths, copied file contents, setup command stdout/stderr.

`WORKTREE` remains omitted on `READY: blocked` (including after rollback of a newly added tree).

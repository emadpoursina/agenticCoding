# Contract: `evidence.md` manifest

**Location**: `specs/<flow>/evidence.md` where `<flow>` is the feature directory basename from `.specify/feature.json` (example: `specs/001-pivs-evidence-bundle`).

**Artifacts directory**: `specs/<flow>/evidence/` (captures). Manifest is a **feature-root sibling**, not a file inside `evidence/`.

**Git**: Recommend ignoring both `specs/*/evidence/` and `specs/*/evidence.md`. Workers MUST NOT commit these files (FR-013, FR-013a).

## Format

- UTF-8 Markdown.
- **No** YAML front matter.
- **No** JSON or secondary machine manifest.
- Body is **one** Markdown table with exactly these column headers (order fixed):

| Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA |
|----------------------|-----------|---------|-----------|------------------|------------|

- One row per acceptance criterion (or stable criterion id in the first column when the Plan uses ids).
- `Artifact path(s)`: relative to repository root; comma-separate multiple paths.
- `Commit SHA`: full 40-char git SHA of worktree `HEAD` when the tester finishes the validation run, immediately before emitting the compact report.

## Example (illustrative)

```markdown
# Validation evidence

| Acceptance criterion | Flow name | Command | Exit code | Artifact path(s) | Commit SHA |
|----------------------|-----------|---------|-----------|------------------|------------|
| Login shows dashboard | E2E happy path | `pnpm exec playwright test e2e/login.spec.ts` | 0 | specs/001-feature/evidence/playwright/trace.zip, specs/001-feature/evidence/playwright/video.webm, specs/001-feature/evidence/playwright/screenshot.png | a1b2c3d4e5f6789012345678901234567890abcd |
| API returns 401 without token | API auth negative | `curl -sS -D specs/001-feature/evidence/api/headers.txt -o specs/001-feature/evidence/api/body.json http://localhost:3000/api/me` | 0 | specs/001-feature/evidence/api/headers.txt, specs/001-feature/evidence/api/body.json | a1b2c3d4e5f6789012345678901234567890abcd |
```

## Regeneration

Each validation run **replaces** the entire file and reconciles artifacts for that run (delete or overwrite stale captures). No incremental patching of leftover rows. After Implement loop-back, regenerate for the **full** validation run even if execution still prefers failed flows first.

## FAIL verdict

When overall tester verdict is FAIL, rows and files MUST still be written for every flow that was executed, with actual exit codes and paths where produced. Omitting evidence because the verdict is FAIL is not allowed.

## Produced files, not chat

Every artifact path MUST point at a file created by the executed command (screenshot, trace archive, HTTP dump, transcript, JUnit XML, and similar), not text invented in the worker report (FR-004).

## Secrets

- API captures MUST redact credentials and `Authorization` tokens before they are written.
- UI traces and screenshots can contain secrets; keep them local/CI-only; tester docs MUST warn operators.
- Evidence MUST remain uncommitted.

# Data model: PIVS evidence bundle

Logical entities for documentation and contracts. No runtime database. Files live under `specs/<flow>/` where `<flow>` is the Spec Kit feature directory basename from `.specify/feature.json` (not `FLOW_ID`, not the git branch when they differ).

## Evidence bundle

| Field | Description |
|-------|-------------|
| `feature_directory` | Path such as `specs/001-pivs-evidence-bundle` from `.specify/feature.json` |
| `manifest_path` | Feature-root sibling: `specs/<flow>/evidence.md` |
| `captures_root` | `specs/<flow>/evidence/` |
| `git_policy` | Local/CI-only. Recommend ignore `specs/*/evidence/` **and** `specs/*/evidence.md`. Never commit. |

**Lifecycle**: Created or **fully replaced** on each tester validation run (FR-003b). Not shipped in git. Parent Ship reads the manifest into the PR body; bulky files stay as CI artifacts.

## Manifest row

One row per acceptance criterion proven (or executed) in the latest validation run.

| Column (FR-003, order fixed) | Type | Rules |
|------------------------------|------|--------|
| Acceptance criterion | string | Wording or stable id from the Plan |
| Flow name | string | Matches Plan test flow name |
| Command | string | Exact command executed |
| Exit code | integer | Recorded even on FAIL verdict |
| Artifact path(s) | string | Repo-relative; comma-separated; files produced by the command |
| Commit SHA | string | Full 40-char `HEAD` at tester completion |

**Validation rules**:

- Paths MUST reference files the command created, not chat prose (FR-004).
- On tester FAIL, rows MUST exist for every executed flow (FR-003a).
- Full replace each run — no leftover rows from prior SHAs (FR-003b).
- API dump artifacts MUST be redacted (credentials, `Authorization`) before write (FR-013a).

## Proof type (on Plan test flow)

Assigned at plan time (FR-001). Exactly one per test flow.

| Value | Required artifact shapes | Command constraint |
|-------|--------------------------|--------------------|
| `UI` | Playwright trace **and** video **and** screenshot(s) | Validation commands MUST be Playwright. Otherwise critic FAILs; use CLI/job or logic. |
| `API` | HTTP request/response capture (redacted) | Any HTTP client/dump the Plan names |
| `CLI/job` | Terminal transcript + exit code | Shell/job command |
| `logic` | Test identifier + JUnit-style XML (or project-standard report) | Project unit runner |

Plan MUST link each listed acceptance criterion to ≥1 test flow with a proof type, including on a change-path Plan (FR-002).

## Stale evidence

| Condition | pr-reviewer meaning |
|-----------|---------------------|
| Manifest SHA ≠ current PR head | Stale until tester re-runs at that head |
| Tester PASS, missing `evidence.md` / missing required artifact | Claimed but unproven — **blocking** |
| Tester PASS, CI job for `validation_commands` failed, skipped, or unfinished on this head | Claimed but unproven — **blocking**. Job success is enough; bytes need not match. |
| Second pr-review after a fix push | Re-apply the same rules to the new head; prior PASS does not waive stale proof |

## CI artifact (external)

| Field | Description |
|-------|-------------|
| `artifact_name` | Documented workflow artifact name used in PR `## Evidence` when CI URLs are not yet known |
| `url` | Optional link once CI finishes |
| `head_sha` | PR head the jobs ran against |

Not stored in git. Requirement is CI-vendor-neutral; docs show one GitHub Actions example (FR-006).

## Compact report extensions

See `contracts/compact-reports.md`. Tester adds `EVIDENCE: <path>`; Ship adds `EVIDENCE: included|none` without dropping existing fields.

## Relationships

```text
Plan (acceptance criteria)
  └── test flows (proof type UI|API|CLI/job|logic)
        └── tester execution at HEAD SHA S
              ├── evidence/* (command-produced files)
              └── evidence.md (manifest rows)
                    └── Ship PR ## Evidence (table + small screenshots + CI names)
                          └── pr-reviewer evidence audit (completeness, SHA vs head, CI job success)
```

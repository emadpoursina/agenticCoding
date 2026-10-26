# Research: PIVS evidence bundle

**Feature**: `specs/001-pivs-evidence-bundle`  
**Date**: 2026-10-26

Skip was active; spec **Clarifications** and **Assumptions** are the source of truth. No `NEEDS CLARIFICATION` remain.

## R-001 — Manifest format

- **Decision**: Single Markdown table in `specs/<flow>/evidence.md` (feature-root sibling of `evidence/`) with FR-003 columns. No YAML front matter, no JSON manifest.
- **Rationale**: Ship copies the table into PR `## Evidence`; pr-reviewer greps the same file. A second schema would need a parser this feature does not add (FR-011).
- **Alternatives considered**: JSON/YAML manifest (rejected in clarify); YAML front matter plus table (rejected — plain table only).

## R-002 — Commit SHA semantics

- **Decision**: Every manifest row uses worktree `HEAD` when the tester finishes the validation run (immediately before the compact report). Not merge-base, not a later Ship push SHA.
- **Rationale**: pr-reviewer stale detection compares that SHA to current PR head. Re-run tester after each implement push so SHA matches the code under review.
- **Alternatives considered**: Merge-base SHA (does not move with fix pushes); SHA at Ship time (tester runs before Ship).

## R-003 — FAIL verdict vs evidence persistence

- **Decision**: On tester FAIL, still write rows and artifacts for every executed flow (including non-zero exit codes). Each validation run **replaces** `evidence.md` and reconciles `evidence/` (full regeneration).
- **Rationale**: Operators need an audit trail of what ran. Loop-back leftover rows would look fresh while pointing at old SHAs.
- **Alternatives considered**: Skip files on FAIL (rejected); incremental row patch (rejected). Failed-flow-first **execution** may stay in tester docs, but the **written bundle** must represent the full run (overrides current “re-run only the failed flows” wording for evidence files).

## R-004 — Git vs CI storage

- **Decision**: Recommend gitignoring **both** `specs/*/evidence/` and `specs/*/evidence.md`. Bulky traces/videos are CI workflow artifacts, never git history. Ship may inline small PNG/JPEG screenshots from local captures when they exist; bulky files are named CI artifacts (PR open must not wait for CI).
- **Rationale**: Clarify alignment of ignore rules and Ship; git stays small (FR-006a, SC-006).
- **Alternatives considered**: Commit traces (rejected); gitignore directory only (rejected — manifest would still land in history).

## R-005 — Proof type taxonomy

- **Decision**: Four labels: **UI** (Playwright trace, video, **and** screenshots — all three; Playwright commands only), **API** (HTTP request/response capture), **CLI/job** (terminal transcript + exit code), **logic** (test name + JUnit-style report).
- **Rationale**: Matches tester sub-roles and validation stack without new tools (FR-012). Non-Playwright UI work uses CLI/job or logic; non-UI projects do not add Playwright.
- **Alternatives considered**: Other UI recorders (explicitly out of scope); fifth “manual” type (weakens file-based proof); third-party products (reference only).

## R-006 — Scope boundary (reuse)

- **Decision**: Documentation-only edits to the spec **In Scope** list. No new agents, loop states, Hermes/runtime code, or `agy-spawn.py`. Canonical docs stay under `AiNative/`; host skill promotion is out of this worktree unless tasks add it.
- **Rationale**: FR-011, FR-015. Feature loop already points runtimes at AiNative.
- **Alternatives considered**: New runtime compact-report parser (rejected); new evidence product (rejected).

## R-007 — Plan artifact proof-type enforcement

- **Decision**: Enforce at **critic plan-review** (FR-002) and document in plan-stage guidance (FR-001). Same fail on a change-path Plan for every criterion that Plan lists. Critic also fails a UI proof type whose validation commands are not Playwright.
- **Rationale**: Plan remains Markdown; critic already reviews plans. No new Spec Kit JSON schema.
- **Alternatives considered**: Machine-validated `plan.json` (YAGNI); plan-reviewer as the only gate (plan-reviewer is same-model, optional; critic is the specified fail).

## R-008 — Constitution

- **Decision**: `.specify/memory/constitution.md` is an unfilled template. Constitution Check in `plan.md` records **N/A — documentation-only; no ratified code gates**. Feature constraints in the spec (no new deps, workers never ship, scope list) still apply.
- **Rationale**: Blocking on placeholder principles would be noise; spec FRs already constrain the change.
- **Alternatives considered**: Draft a project constitution (out of feature scope).

## R-009 — Secrets in captures

- **Decision**: API captures MUST redact credentials and `Authorization` tokens before write. Tester/validation docs MUST warn that UI traces and screenshots can contain secrets. Evidence stays gitignored and uncommitted (FR-013a).
- **Rationale**: HTTP dumps and Playwright traces routinely include tokens; clarify made this mandatory, not advisory-only for API.
- **Alternatives considered**: Commit redacted evidence (rejected — still gitignore); encrypt captures in-repo (new dependency / product).

## R-010 — CI vendor and example

- **Decision**: Requirement is vendor-neutral: PR CI re-executes Plan `validation_commands` (or documented equivalent) and uploads bulky captures as workflow artifacts. Documentation ships **one GitHub Actions example snippet only**. Do not commit workflow files into arbitrary enrolled repos (FR-006).
- **Rationale**: Clarify chose GitHub Actions as the sole example without locking enrolled projects to that vendor.
- **Alternatives considered**: Multiple vendor snippets (out of scope); requiring GitHub Actions in every enrolled repo (rejected).

## R-011 — CI agreement vs local bytes

- **Decision**: pr-reviewer treats CI as agreeing when, on the **current PR head**, CI re-ran `validation_commands` (or documented equivalent) and those jobs **succeeded**. Artifact bytes need not match local files. FAIL, skipped, or unfinished jobs for a tester PASS claim are **claimed but unproven** (blocking).
- **Rationale**: Independent re-proof, not a file-diff of traces. Ship may open the PR before CI finishes; unfinished CI does not count as agreement.
- **Alternatives considered**: Require byte-identical artifacts (rejected in clarify).

## R-012 — Changelog

- **Decision**: One Keep a Changelog + SemVer entry in `AiNative/CHANGELOG.md` (currently `0.2.2`). Recommend **0.3.0** (Added methodology capability). Do not add a playground-root changelog for this feature (FR-014).
- **Rationale**: Spec names that file as the source of truth.
- **Alternatives considered**: Patch bump `0.2.3` (too small for a new operator-facing loop contract); second changelog at repo root (rejected).

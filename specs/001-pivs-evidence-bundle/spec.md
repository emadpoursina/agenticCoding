# Feature Specification: PIVS evidence bundle

**Feature Branch**: `pivs-evidence-bundle`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "skip" (operator skip flag). Full intent: give the operator commit-tied, acceptance-criterion–mapped evidence that agent-built code works, by adding an evidence bundle to the PIVS loop (tester writes files, CI re-proves, Ship puts it in the PR, pr-reviewer audits). This augments — it does not replace — PR + walkthrough + UAT.

## Clarifications

### Session 2026-10-26

- Q: Where must the tester write `evidence.md` relative to capture files so ignore rules and Ship stay aligned? → A: Feature-root sibling `specs/<flow>/evidence.md`; captures under `specs/<flow>/evidence/`. Gitignore both `specs/*/evidence/` and `specs/*/evidence.md`.
- Q: What counts as CI agreeing with a tester PASS during the pr-reviewer evidence audit? → A: On the current PR head, CI re-ran the Plan `validation_commands` (or the documented equivalent) and those jobs succeeded. Artifact bytes need not match local files. A FAIL, skipped, or unfinished CI job for a PASS claim is claimed but unproven.
- Q: Which CI product should the documentation example workflow snippet use? → A: GitHub Actions as the sole example; the requirement itself is vendor-neutral (re-execute the commands and upload bulky captures as CI artifacts).
- Q: How must evidence docs treat secrets that can appear in HTTP dumps, traces, or screenshots? → A: API captures must redact credentials and `Authorization` tokens; docs must warn that UI traces and screenshots can contain secrets; evidence stays gitignored and must not be committed.
- Q: May a Plan use the UI proof type when the project does not run Playwright? → A: No. UI means Playwright trace, video, and screenshots. Non-Playwright UI work must use CLI/job or logic instead.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Planner names how each criterion is proven (Priority: P1)

When a Plan is drafted, every acceptance criterion is tied to at least one test flow, and every flow names a **proof type** so later stages know what artifact must exist.

**Why this priority**: Proof types at plan time are the contract tester, CI, Ship, and pr-reviewer enforce. Without them, evidence cannot be required.

**Independent Test**: Inspect a sample Plan: each acceptance criterion maps to a test flow with a proof type. Critic documentation fails a Plan that leaves any criterion without a way to be proven.

**Acceptance Scenarios**:

1. **Given** a Plan with acceptance criteria and test flows, **When** the critic reviews the Plan, **Then** every acceptance criterion has at least one linked test flow that names a proof type: UI (Playwright trace, video, and screenshots), API (HTTP request/response capture), CLI/job (terminal transcript and exit code), or logic (test name and JUnit-style report).
2. **Given** a Plan where an acceptance criterion has no test flow or no proof type, **When** the critic runs the plan review, **Then** the critic fails with a blocking finding that names the orphan criterion.
3. **Given** a Plan that labels a flow UI but the commands are not Playwright, **When** the critic runs the plan review, **Then** the critic fails and the Plan must use CLI/job or logic for that flow instead.

---

### User Story 2 - Tester persists evidence on disk (Priority: P1)

After the critic passes, the tester runs Plan test flows, writes **files produced by those commands** (not prose typed into the chat), and records a manifest tied to the current commit.

**Why this priority**: Evidence must outlive the worker session and be auditable without reading chat logs.

**Independent Test**: After a validation run, `specs/<flow>/evidence.md` is the manifest (one row per acceptance criterion: flow, command, exit code, artifact path, commit SHA) and capture files live under `specs/<flow>/evidence/`. The tester compact report includes `EVIDENCE: <path>` pointing at that manifest.

**Acceptance Scenarios**:

1. **Given** a feature flow with a Plan and implemented code at commit SHA `S`, **When** the tester completes a validation run, **Then** capture files live under `specs/<flow>/evidence/` and `specs/<flow>/evidence.md` lists each acceptance criterion with flow name, exact command, exit code, relative artifact path(s), and `S`.
2. **Given** a test flow that ran, **When** evidence is collected, **Then** every artifact path in the manifest points to a file created by the command (screenshot, trace archive, HTTP dump, transcript, JUnit XML, and similar), not text invented in the report.
3. **Given** the tester finishes, **When** the parent parses the compact report, **Then** existing PASS/FAIL fields remain and the report adds `EVIDENCE: <path>` pointing at `specs/<flow>/evidence.md`.
4. **Given** the tester verdict is FAIL after some flows ran, **When** the compact report is emitted, **Then** the manifest still has rows for every executed flow (including non-zero exit codes) and any produced artifacts remain on disk.

---

### User Story 3 - CI independently re-proves validation (Priority: P1)

Enrolled-project guidance requires PR CI to re-run the same `validation_commands` the tester used, with Playwright trace/video/screenshot on for UI flows, and to upload bulky captures as workflow artifacts — never as git history.

**Why this priority**: An independent re-run is the anti-hallucination guarantee. Git stays small.

**Independent Test**: AiNative validation and feature-loop docs include the CI requirement plus an example workflow snippet. This change does not add workflow files to enrolled repos.

**Acceptance Scenarios**:

1. **Given** an operator reading validation-layer and feature-loop docs, **When** they look for how PRs prove tests, **Then** they see a vendor-neutral requirement that PR CI re-executes `validation_commands`, enables UI capture where UI proof types apply, and publishes those files as workflow artifacts, plus one GitHub Actions example snippet.
2. **Given** large trace or video files, **When** evidence is produced, **Then** docs state they belong in CI artifacts or local `evidence/` directories, never in git history.
3. **Given** enrolled-project git hygiene guidance, **When** an operator follows it, **Then** they have recommended ignore patterns for `specs/*/evidence/` and `specs/*/evidence.md`.

---

### User Story 4 - Ship surfaces evidence beside walkthrough (Priority: P2)

The parent Ship step keeps mandatory `## Walkthrough` and adds mandatory `## Evidence` sourced from the tester manifest: the acceptance-criterion table, small screenshots inline, and links to CI artifacts.

**Why this priority**: The PR is the single review surface for human UAT and machine-checkable proof.

**Independent Test**: Ship documentation requires `## Evidence` next to `## Walkthrough`. The Ship compact report adds `EVIDENCE: included|none` without dropping `WALKTHROUGH`.

**Acceptance Scenarios**:

1. **Given** the tester produced `evidence.md` and the path passed validation, **When** Ship opens the PR, **Then** the PR body contains `## Evidence` with the acceptance-criterion table from the manifest, small screenshots inlined when they exist, and links (or named CI artifact pointers) for bulky captures.
2. **Given** Ship completes, **When** the parent emits its report, **Then** fields include `EVIDENCE: included` or `EVIDENCE: none` in addition to existing `SHIP`, `PR`, `WALKTHROUGH`, and `SUMMARY`.
3. **Given** no usable manifest, **When** Ship still opens a PR after a passing path, **Then** Ship reports `EVIDENCE: none` and still includes `## Walkthrough`.

---

### User Story 5 - pr-reviewer audits evidence across fix pushes (Priority: P2)

On demand after Ship, pr-reviewer gains an evidence audit step: every acceptance criterion has evidence, the manifest commit SHA matches PR head (otherwise marked stale), and CI results agree with tester claims. "Claimed but unproven" is blocking. The audit is valid on every later pr-review pass after a fix push, because CI re-runs.

**Why this priority**: Operators run one or more pr-reviews per PR. Stale or mismatched evidence must be visible after each push.

**Independent Test**: pr-reviewer prompts and the PR-review system overview document the audit step, stale-SHA behavior, and a blocking "claimed but unproven" finding.

**Acceptance Scenarios**:

1. **Given** a PR whose `evidence.md` records SHA `S_old` while PR head is `S_new`, **When** pr-reviewer runs the evidence audit, **Then** those rows are marked stale relative to PR head until the tester re-runs at `S_new`.
2. **Given** the tester claimed PASS for a criterion but CI failed, skipped, or has not finished the re-run of `validation_commands` on this head, or the required artifact is missing, **When** pr-reviewer audits, **Then** it reports a blocking finding that the criterion is claimed but unproven. CI agreement is job success on this head, not byte-identical artifacts.
3. **Given** evidence and CI agree for all criteria at PR head, **When** pr-reviewer completes, **Then** no blocking evidence findings remain.
4. **Given** a second pr-review after a fix push, **When** CI has re-run on the new head, **Then** the same audit rules apply to the new head (fresh SHA match, or stale if the tester did not re-run).

---

### User Story 6 - Optional fail-before / pass-after discipline (Priority: P3)

Documentation describes an optional check: new tests should fail on the base commit before implementation and pass after, when that check is practical.

**Why this priority**: Strengthens proof that tests measure the new behavior without blocking adoption where it is impractical.

**Independent Test**: Validation-layer or tester docs include a short optional procedure. It is not required for every project or every flow.

**Acceptance Scenarios**:

1. **Given** a new test flow added for a feature, **When** an operator follows the optional fail-before guidance, **Then** they run the test against the merge-base commit, observe failure, then confirm pass on the feature branch.

---

### User Story 7 - Compact-report contracts stay aligned (Priority: P2)

`feature-loop.md` compact-report definitions for tester and Ship match the agent docs: tester adds `EVIDENCE: <path>`; Ship adds `EVIDENCE: included|none`; existing PASS/FAIL and walkthrough fields stay.

**Why this priority**: The parent parses compact reports, not chat prose. Drift between the graph and the agent skills breaks dispatch.

**Independent Test**: Grep the tester and Ship `EVIDENCE` fields in `feature-loop.md` and the corresponding agent skills; they match.

**Acceptance Scenarios**:

1. **Given** updated tester and Ship skills, **When** an operator reads `feature-loop.md` compact reports, **Then** tester and Ship field lists include the new `EVIDENCE` fields and do not drop existing required fields.

---

### Edge Cases

- Tester PASS but no `specs/<flow>/evidence.md` or empty `evidence/` → Ship reports `EVIDENCE: none`; pr-reviewer treats missing proof as blocking if criteria were claimed proven.
- Spec directory name differs from git branch name → evidence path uses `specs/<flow>/` from `.specify/feature.json`, not the branch name.
- Change path (thinner Plan artifacts) → every acceptance criterion listed on that Plan still needs a proof-typed test flow (same critic fail as the feature path); tester still writes file-based proof for flows it actually runs.
- Plan assigns UI proof without Playwright commands → critic fails; the project must use CLI/job or logic instead. This feature does not introduce other UI recorders.
- Re-validation after Implement loop-back → tester **replaces** `specs/<flow>/evidence.md` and refreshes artifacts for the **full** validation run (not a row patch, and not "failed flows only" for the manifest). SHA updates to the worktree `HEAD` at the end of that run.
- Tester FAIL → manifest records executed commands; Ship may report `EVIDENCE: included` with a FAIL tester verdict; missing or stale proof remains blocking for pr-reviewer.
- Accidental `git add` of evidence files → guidance recommends ignoring `specs/*/evidence/` and `specs/*/evidence.md`; bulky UI captures belong in CI workflow artifacts only.
- Ship opens the PR before CI finishes → `## Evidence` still includes the manifest table and local small screenshots; bulky files are referenced by the documented workflow artifact name so the operator and pr-reviewer can open them after CI completes. Until that head's CI re-run finishes successfully, pr-reviewer treats PASS claims as claimed but unproven.
- Multiple pr-review passes → each pass re-checks SHA vs current PR head and current CI; prior-pass PASS does not waive a newly stale bundle.
- Captures that would include secrets (tokens, `Authorization` headers, credential screens) → API dumps must be redacted before they are written; UI traces and screenshots stay local/CI-only with an explicit warning in tester docs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Plan-stage documentation MUST require each acceptance criterion's test flow to declare one of: UI (Playwright trace, video, and screenshots — all three; Playwright commands only), API (HTTP request/response), CLI/job (terminal transcript + exit code), or logic (test name + JUnit report).
- **FR-002**: Critic documentation MUST include a plan-review check that fails when any acceptance criterion lacks a provable test flow or proof type, including on a change-path Plan for every criterion that Plan lists. The critic MUST fail a UI proof type whose validation commands are not Playwright.
- **FR-003**: Tester and test-execution skills MUST require writing capture files under `specs/<flow>/evidence/` and the manifest at `specs/<flow>/evidence.md` as a **single Markdown table** (no YAML front matter, no JSON manifest) with columns: acceptance criterion (or id), flow name, command, exit code, artifact path(s), commit SHA.
- **FR-003a**: On tester FAIL, skills MUST still write manifest rows and artifacts for every flow that was executed (including failed exit codes). Omitting evidence because the verdict is FAIL is not allowed.
- **FR-003b**: Each validation run MUST **replace** the prior `evidence.md` and reconcile artifacts for that run (full regeneration, not incremental patch of leftover rows).
- **FR-004**: Manifest artifact paths MUST reference files produced by executed commands, not free-text evidence in the worker chat.
- **FR-005**: Tester compact report contract MUST add `EVIDENCE: <path>` pointing at `specs/<flow>/evidence.md` (or the resolved manifest path) while preserving existing PASS/FAIL verdict fields.
- **FR-006**: Validation-layer and/or feature-loop docs MUST require enrolled projects' PR CI to re-run `validation_commands`, enable Playwright capture for UI flows, and upload large files as workflow artifacts. The requirement is CI-vendor-neutral. Provide one GitHub Actions example snippet only — do not commit workflow files into arbitrary enrolled repos, and do not require GitHub Actions as the only allowed CI.
- **FR-006a**: Those docs MUST recommend gitignoring `specs/*/evidence/` and `specs/*/evidence.md` in enrolled repos so local captures and the manifest are never committed. CI artifact URLs (or named artifacts) satisfy PR `## Evidence` links for bulky files.
- **FR-007**: Speckit-orchestrate Ship / UAT section MUST require PR body `## Evidence` alongside `## Walkthrough`, populated from the manifest (table, inline small screenshots, CI artifact links or names). Walkthrough purpose MUST stay mandatory and unchanged.
- **FR-008**: Ship compact report MUST add `EVIDENCE: included|none` without removing `SHIP`, `PR`, `WALKTHROUGH`, or `SUMMARY`.
- **FR-009**: pr-reviewer prompts and pr-review-system overview MUST add an evidence audit step covering completeness, SHA freshness vs PR head, and CI agreement with tester claims. CI agreement means the PR CI re-run of `validation_commands` (or documented equivalent) on the current head succeeded; artifact bytes need not match the local bundle. A tester PASS whose CI job failed, was skipped, or has not finished is "claimed but unproven". "Claimed but unproven" MUST be a blocking finding. The step MUST be specified so it is re-runnable on every pr-review pass after a fix push.
- **FR-010**: `feature-loop.md` compact-report definitions for tester and Ship MUST match the updated agent docs.
- **FR-011**: Scope MUST be limited to the listed AiNative documentation paths plus `AiNative/CHANGELOG.md`. No new loop states, no new agents, no Hermes/runtime code, no third-party evidence products (reference-only mentions allowed).
- **FR-012**: No new dependencies. UI proof uses Playwright's built-in trace, video, and screenshot only. Plans MUST NOT assign the UI proof type unless the flow's commands are Playwright.
- **FR-013**: Workers MUST still never commit, push, or open PRs. Only the parent Ship step publishes evidence in the PR.
- **FR-013a**: Tester and validation docs MUST require redacting credentials and `Authorization` tokens from API captures, and MUST warn that UI traces and screenshots can contain secrets. Evidence files MUST remain uncommitted.
- **FR-014**: `AiNative/CHANGELOG.md` MUST receive an entry following the existing Keep a Changelog + SemVer scheme when these documentation changes ship.
- **FR-015**: `docs/agents/antigravity-harness/agy-spawn.py` MUST NOT be modified.
- **FR-016**: Validation or tester docs MUST document the optional fail-before / pass-after check (new tests fail on the base commit, pass after) without making it mandatory.

### Key Entities

- **Evidence bundle**: Manifest `specs/<flow>/evidence.md` plus directory `specs/<flow>/evidence/` for one feature flow. Local-only; not committed to git.
- **Manifest row**: One acceptance criterion's proof metadata: flow, command, exit code, artifact path(s), commit SHA.
- **Proof type**: Label on a Plan test flow that determines required artifact shapes (UI = Playwright only, API, CLI/job, logic).
- **Stale evidence**: Manifest or artifacts recorded at a commit SHA that does not match current PR head.
- **CI artifact**: Workflow-uploaded file (trace, video, report) linked or named from the PR Evidence section, not stored in git.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can open a shipped PR and, from `## Evidence` alone, see every acceptance criterion with a file path or CI artifact pointer — without reading tester chat logs.
- **SC-002**: A tabletop review of pr-reviewer prompts yields a blocking finding whenever any criterion lacks evidence or the manifest SHA does not match PR head, including on a second review after a fix push.
- **SC-003**: Plan plus critic documentation together make it a documented fail for the critic to approve a Plan whose acceptance criterion has no proof type.
- **SC-004**: Tester and Ship `EVIDENCE` fields in `feature-loop.md` match the agent skills (same field names and allowed values).
- **SC-005**: UAT still has a mandatory walkthrough; evidence is present in the PR next to it, not instead of it.
- **SC-006**: An operator following the docs can see that `evidence/` and `evidence.md` must never enter git history, that PR CI is the independent re-run (job success on the head, not matching file bytes), and that the example snippet is GitHub Actions while the rule is vendor-neutral.

## Assumptions

- **Skip clarify**: Operator skip was active for specify and this clarify session. Session answers are in **Clarifications**; there are no `[NEEDS CLARIFICATION]` markers.
- **Manifest format**: `specs/<flow>/evidence.md` is one Markdown table with the FR-003 headers so Ship and pr-reviewer can parse it without a second format.
- **Commit SHA**: Each manifest row uses the worktree `HEAD` when the tester finishes the validation run (immediately before the compact report), not merge-base and not a later Ship push SHA. Re-run tester after each implement push before Ship so SHA matches the code under review.
- **Flow directory**: `<flow>` is the Spec Kit feature directory basename from `.specify/feature.json` (for example `001-pivs-evidence-bundle`), not `FLOW_ID` and not the git branch name when they differ.
- **FAIL still records**: Executed flows are always written to the bundle; FAIL is the verdict, not a reason to skip files.
- **Replace on re-run**: Loop-back re-validation regenerates the whole manifest so leftover rows cannot go stale silently. This overrides the current tester "re-run only failed flows" guidance for **evidence files**; failed-flow-first execution may still be described, but the written bundle must represent the full run.
- **Playwright**: Only projects whose UI flows already run Playwright may use the UI proof type (trace, video, and screenshots). Other UI projects use CLI/job or logic. Non-UI projects are not required to add Playwright.
- **Small screenshots**: "Small" means a still image suitable to embed in a PR body (PNG/JPEG of a representative viewport). Traces and videos stay off-git and are CI artifacts.
- **CI URLs at Ship time**: Opening the PR must not wait for CI. Ship embeds the manifest table and any small local screenshots; bulky proof is referenced by the documented workflow artifact name. pr-reviewer uses completed CI on that head when auditing; unfinished CI does not count as agreement.
- **CI vendor**: Enrolled repos may use any CI that can re-run `validation_commands` and upload artifacts. Docs ship one GitHub Actions snippet as the example.
- **pr-reviewer timing**: Remains an on-demand tool after Ship, not a loop gate. Evidence audit is an extra step in the staged review.
- **Hermes**: Methodology docs only; this work does not change Hermes/`personalAgent` runtime.
- **References**: Devin, Twill, Cursor Cloud Agents, Currents, ProofShot, RecordLoop, GitGlimpse may be cited as inspiration only, not integrated.
- **Changelog**: Follow `AiNative/CHANGELOG.md` (Keep a Changelog, SemVer). Do not add a second changelog at the playground repo root for this feature.
- **Workers**: Specify/plan/implement workers still never commit, push, or open PRs.

## Out of Scope (explicit)

- New loop states or agents; making pr-reviewer a Ship gate.
- Adopting ProofShot, Currents, RecordLoop, GitGlimpse, or other third-party evidence products.
- Writing or modifying enrolled projects' CI workflow files (documentation and one example only).
- `personalAgent` / Hermes runtime changes.
- Replacing UAT or walkthrough with evidence-only review.
- Editing `AiNative/docs/agents/antigravity-harness/agy-spawn.py`.

## In Scope (file list)

- `AiNative/docs/systems/feature-loop.md`
- `AiNative/docs/systems/validation-layer.md`
- `AiNative/docs/systems/pr-review-system.md`
- `AiNative/docs/agents/tester/` (`SKILL.md`, `rule.md`, `AGENTS.md`)
- `AiNative/docs/agents/_skills/test-execution/SKILL.md`
- `AiNative/docs/agents/critic/` (proof-type plan check)
- `AiNative/docs/agents/speckit-orchestrate/SKILL.md` (Ship / UAT section)
- `AiNative/docs/agents/pr-reviewer/` prompts
- `AiNative/CHANGELOG.md`

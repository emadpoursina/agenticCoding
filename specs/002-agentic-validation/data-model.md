# Data model: Agentic validation loop

Logical entities for dispatcher contracts. No runtime database. Spec directory is `FEATURE_DIR` from specify / `.specify/feature.json` (basename e.g. `002-agentic-validation`), never inferred from git `BRANCH` (`agentic-validation` may differ).

## Parent dispatcher

The speckit-orchestrate controller. Owns stage sequence, compact-report parsing, stuck policy, ship, UAT park, and finish report. Never implements, never writes `spec.md` / `plan.md` / `tasks.md`, never ships from a worker session.

| Field | Rules |
|-------|--------|
| Path | `feature` \| `change` \| `job` from route-work |
| `keep-local` | If set: skip ship, automatic pr-review, and UAT; emit `SHIP: declined` after path validation PASS |
| Open PR | URL from first `SHIP: ok` this run; reused on later same-PR ship |
| Previous pr-review report | Artifact path passed to re-review as `--extra` |

## Validator

Stage-dumb worker: critic, PIVS tester, or pr-reviewer. Emits a compact report. Never writes `tasks.md`, never ships, never dispatches the next stage.

Change-path `STEP: tester` is the thin change tester (FINDINGS retry), not the PIVS tester agent. It does not grow `LOOP_BACK`. Job path has no validator after ship.

## LOOP_BACK

Present on **critic** and **PIVS tester** compact reports.

| Value | When | Parent action |
|-------|------|----------------|
| `none` | PASS | Continue (tester after critic; ship after tester unless `keep-local`) |
| `implement` | FAIL, only implement-target findings | Converge with findings as `$ARGUMENTS`, then implement↔converge, then critic→tester |
| `plan` | FAIL, spec/plan is wrong | Park. Do not re-run critic/tester/pr-review until a human unparks |

Mixed implement+plan findings on one FAIL → treat as `plan` (park). Missing field: see spec Assumptions (assertion → implement; explicit spec/plan contradiction → plan; else park).

## Validator finding ID

Stable token inside a compact report: critic `C1`, tester flow id `flow-2`, pr-review Critical `C1`. Used in task **description** (`[critic: C1]`) and converge `FINGERPRINT`. Never used as a converge source-ref.

## Converge fingerprint

Identity of the current stuck point.

| Component | Content |
|-----------|---------|
| Source-refs | Sorted, comma-separated spec/plan/constitution refs only |
| Validator IDs | Sorted ids present in the current FINDINGS / `$ARGUMENTS` (e.g. `critic:C1`, `tester:flow-2`, `pr-review:C1`) |

Unchanged fingerprint across original + two resumes → park. `CONVERGE_OUTCOME: blocked` → park immediately. `converged` while a validator FAIL is still open → parent parks (do not treat as validation PASS).

## PR-review verdict

| Verdict | Meaning for the loop |
|---------|----------------------|
| `APPROVE` | No Criticals. Park for existing operator UAT pass/fail. Does not complete the run. Merge stays human. |
| `REQUEST CHANGES` with `CRITICAL_COUNT ≥ 1` | Feature: converge then implement↔converge then critic→tester then same-PR ship then re-review. Change: change worker + FINDINGS then tester then same-PR ship then re-review. |
| `REQUEST CHANGES` with `CRITICAL_COUNT = 0` | Route as APPROVE for loop purposes |
| `BLOCKED` | Phase 1.5. Park. Not a REQUEST CHANGES retry |

## Same PR / same-PR ship

| Field | Rules |
|-------|--------|
| Same PR | The pull request opened by this run’s first Ship |
| Same-PR ship | Parent: commit, push `BRANCH`, refresh walkthrough (and Evidence), keep existing PR URL. Must not `gh pr create` a second PR |
| First ship | Create PR as today when none exists for `BRANCH` |

## Relationships

```text
Parent dispatcher
  ├── feature: implement ↔ converge
  │     └── on converged → critic → tester → [ship] → pr-review → uat
  ├── change: change worker → tester (no critic)
  │     └── on tester PASS → [ship] → pr-review → uat
  └── job: named skill → [ship]   (never pr-review, never UAT)

Validator FAIL (feature, LOOP_BACK implement)
  └── converge ($ARGUMENTS = Criticals) → append-only tasks.md → implement ↔ converge
        └── fingerprint includes validator IDs

pr-review REQUEST CHANGES (Criticals)
  ├── feature → same converge path → same-PR ship → re-review (--extra previous report)
  └── change → FINDINGS to change worker (no tasks.md)
```

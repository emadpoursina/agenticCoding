# Contract: compact report field extensions

Parent parsers rely on these fields; workers must not bury them in prose. `AiNative/docs/systems/feature-loop.md` MUST list the same fields as the agent skills (FR-010).

## Tester (after existing PASS/FAIL verdict)

Preserve all existing tester compact-report / verdict fields. **Add**:

```text
EVIDENCE: specs/<flow>/evidence.md
```

Use the resolved manifest path when the feature layout differs; default is `specs/<flow>/evidence.md` with artifacts under `specs/<flow>/evidence/`.

When flows ran, write the manifest even on FAIL (FR-003a) and still emit `EVIDENCE: <path>`.

## Ship (parent only)

Preserve:

```text
SHIP: ok | blocked | declined
PR: <URL or none>
WALKTHROUGH: included | none | blocked
SUMMARY: <text>
```

**Add**:

```text
EVIDENCE: included | none
```

- `included`: PR body contains mandatory `## Evidence` sourced from a usable manifest (table copied; small screenshots inlined when present; bulky files referenced by documented CI artifact name or URL). Allowed even if tester verdict was FAIL.
- `none`: no usable manifest (missing, empty, or path failed validation) — `## Walkthrough` remains mandatory.

Ship MUST NOT wait for CI to finish before opening the PR.

## Plan worker (unchanged baseline + analyze)

```text
FLOW_ID: <id>
ARTIFACTS: <paths>
STATUS: ok | stuck | blocked
ANALYZE: yes | no
ANALYZE_REASON: <one line>
SUMMARY: <paragraph>
```

## PR body: Evidence section

Required alongside `## Walkthrough` when Ship runs (FR-007). Walkthrough purpose stays mandatory and unchanged.

- Heading: `## Evidence`
- Acceptance-criterion table from the manifest (may mirror `evidence.md`)
- Inline small screenshots (PNG/JPEG of a representative viewport) when they exist locally
- Links or **named CI artifact pointers** for traces, videos, and other bulky files so operators can open them after CI completes

## Critical path blocked by optional tracking code

**Date:** 2026-06-06
**Domain:** billing

### Symptom
A core user action stopped working after a third-party key was removed. In our case: the purchase / membership button worked on launch day, then failed once the original developer removed their Facebook tracking key. The regression went unnoticed for a long time because nobody routinely tested that flow.

### Root cause
This was not really a purchase-only bug. It exposed a general design mistake on a **critical path**:

1. **Inverted dependency.** Optional observability (tracking, analytics, pixels) was wired so the **core action depended on tracking succeeding**. When the tracking integration failed, the main function failed with it. The rule is the opposite: the core action runs first; tracking listens to it and must never gate it.

2. **No protection for the project's most important function.** Every project has one or a few actions that matter most — purchase, signup, save, submit, publish, send, etc. We allowed non-critical code (third-party SDKs, analytics, feature flags, logging) to sit on that path with no timeout, no isolation, and no fail-open behavior. Optional code should never block what the product exists to do.

3. **Assumption instead of verification.** We treated the critical path as known good since launch and had no smoke test, E2E coverage, or release check for it. A config change (missing key) broke production without anyone exercising the flow.

**Concrete instance:** Facebook tracking blocked purchase when the key was removed.

### Fix
- Identify each project's **critical paths** — the actions that must always work.
- Decouple all tracking and analytics from those paths: emit events after success, or fire-and-forget in parallel; never await or require them before proceeding.
- Wrap optional integrations in non-blocking code (try/catch, skip when unconfigured, timeouts).
- Move third-party credentials to org-owned config, not individual developer keys.
- Add tests and release gates for critical paths, including optional dependency broken → core action still works.

### How to detect early
- **Rule:** For every project, name the 1–3 functions that must never fail silently. Nothing optional may block them.
- **Dependency direction:** Observability depends on business actions; business actions never depend on observability.
- **Release gate:** Manual or automated smoke test of each critical path before every deploy.
- **Negative test:** Run critical paths with tracking/analytics disabled or misconfigured; assert they still succeed.
- **Review checklist:** Any PR touching a critical path — ask whether optional code can still block the main action.

### Related patterns
- Treating launch-day verification as permanent proof.
- Silent failure: UI looks fine, core action does nothing.
- Individual-owned third-party keys in production.

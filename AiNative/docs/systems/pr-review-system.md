# **AI-Powered PR Review System**

A structured system to use AI effectively for reviewing pull requests without noise, overwhelm, or shallow feedback.  
---

## Core Principle

Do NOT ask AI to "review this PR" directly.  
Instead, run a staged workflow that builds understanding → architecture compliance → risk awareness → deep analysis → adversarial testing → human judgment.  
AI is a thinking partner, not an authority.  

**Loop Integration:** On the feature and change paths, PR review is an automatic loop state after Ship (`ship → pr-review → uat`), not on-demand-only after `SHIP: ok`. It reviews architecture, risk, and evidence on the opened PR (not a second implementation critique replacing critic). The merge gate remains strictly Critical-only: only Critical findings trigger REQUEST CHANGES; Warnings and Suggestions never change the verdict. The job path skips PR review entirely.

**Prompts:** [pr-reviewer agent](../agents/pr-reviewer/)

---

## Workflow Overview

### Phase 0 — Input Discipline

Before using AI:

* Do not review immediately  
* Do not request general feedback  
* Always structure the review into phases

---

### Phase 1 — PR Understanding

* Goal: Build a mental model of the change.  
* Use **Phase 1** prompt in [pr-reviewer agent](../agents/pr-reviewer/).

---

### Phase 1.5 — Architecture Compliance

* Goal: Verify the PR reuses existing design and abstractions — not just "good code" in isolation.  
* **Run for any feature PR** in an existing subsystem. Skip typo-only or dependency-only changes.  
* Attach design docs, ADRs, and 2–3 similar features with `@` before pasting the prompt.  
* Use **Phase 1.5** prompt in [pr-reviewer agent](../agents/pr-reviewer/).  
* If verdict is **blocking**, stop and request rework before Phase 2.

---

### Phase 2 — Risk Classification

* Goal: Identify where attention should go.  
* Use **Phase 2** prompt in [pr-reviewer agent](../agents/pr-reviewer/).

---

### Phase 3 — Select Review Focus (IMPORTANT)

* Do NOT run all review types.
* **Default:** pick the category with the highest rating from Phase 2's risk classification. Phase 2 drives Phase 3 — never default to a fixed category out of habit.
* **Override:** the caller may pass `--focus <security|reliability|maintainability|performance>` to force a focus when the human sees something the ratings missed.
* Map Phase 2 categories to Phase 4 prompts:
  * security → Security Review
  * reliability, migration → Reliability Review
  * maintainability → Maintainability / Architecture Review
  * scalability → Performance Review

---

### Phase 4 — Deep Focus Review

Run **one** focus prompt from [pr-reviewer agent](../agents/pr-reviewer/) matching the PR type (security, reliability, maintainability, or performance).

---

### Phase 5 — Adversarial Review

* Goal: Break the system mentally.  
* Use **Phase 5** prompt in [pr-reviewer agent](../agents/pr-reviewer/).

---

### Phase 5.5 — Evidence audit (feature PRs, on demand)

* Goal: verify the tester evidence bundle proves the PR's acceptance criteria **at the current head**. Run after Ship whenever the PR carries (or should carry) `specs/<flow>/evidence.md`; skip typo/dependency/config-only PRs and docs with no Plan ACs. Re-run on every pr-review pass after a fix push.
* **Completeness (verdict-aware):** tester PASS ⇒ every acceptance criterion has a manifest row and the artifact shape its proof type requires. Tester FAIL ⇒ rows are required for every executed flow; unexecuted criteria are not "claimed proven".
* **SHA freshness:** manifest row SHA ≠ PR head ⇒ **stale**.
* **CI agreement:** the PR-head CI re-run of `validation_commands` (or documented equivalent) **succeeded** — job success, not byte-identical artifacts. Failed, skipped, or unfinished CI behind a tester PASS ⇒ **claimed but unproven**.
* **stale** and **claimed but unproven** are **Critical** under the pr-reviewer merge gate (trouble ≥ 0.8, file:line, trigger). They REQUEST CHANGES. They are not a second blocker beside Critical. The audit is not a loop gate; a prior-pass PASS does not waive a newly stale bundle.
* Use the **Evidence audit** prompt in the [pr-reviewer agent](../agents/pr-reviewer/).

---

### Phase 6 — Human Review (Critical Step)

* AI does NOT finalize decisions.  
* Ask yourself:  
  * Would I deploy this on Friday night?  
  * What breaks under real traffic?  
  * Is this over-engineered?  
  * Will future engineers suffer?  
  * Does this align with product needs?

---

## PR Complexity Strategy

### Small PR (<200 lines)

* Understanding  
* Architecture compliance (if feature touches an existing subsystem)  
* One focused review  
* Human pass

### Medium PR

* Understanding  
* Architecture compliance  
* Risk classification  
* 1–2 focused reviews  
* Adversarial review  
* Human pass

### Large PR

* Understanding  
* Diff compression (optional — see prompts doc)  
* Architecture compliance (per subsystem if needed)  
* Risk classification  
* Multiple subsystem reviews  
* Adversarial review  
* Human architecture review

---

## Key Mental Model

You are not asking:  
"Is this good?"  
You are asking:

* What can break?  
* Does this reuse what we already built?  
* Where are hidden risks?  
* What assumptions exist?  
* What becomes painful later?

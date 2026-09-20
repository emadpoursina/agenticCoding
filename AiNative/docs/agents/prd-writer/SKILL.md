---
name: prd-writer
description: Interviews the user through structured discovery (5–20 multiple-choice questions with recommendations), then generates a comprehensive Product Requirements Document as a markdown file. Use when starting a new product or feature that needs a written spec before implementation.
---

# PRD writer

Procedural instructions for generating a Product Requirements Document through structured discovery and templated output.

---

## Discovery interrogation (before writing anything)

The discovery phase is mandatory. Do not write a single section of the PRD until discovery is complete and confirmed.

### Step 1: Intake

Read the user's initial idea description. If it is under 3 sentences, ask one open-ended follow-up to expand: "Tell me more about who this is for and what problem it solves." Do not count this as part of the structured question set.

### Step 2: Assess complexity

| Complexity | Questions | Typical signal |
|------------|-----------|----------------|
| Low | 5–7 | Narrow-scope tool, single user, simple functionality |
| Medium | 10–12 | Consumer app, SaaS product, marketplace |
| High | 15–20 | Enterprise platform, multi-stakeholder, heavy integration, regulated domain |

Default to medium (10–12) unless the idea is clearly trivial or clearly enterprise.

### Step 3: Question domains

Cover these domains across the question set. Order matters — start broad, narrow to specifics:

1. **Problem and audience** — who, what problem, why now
2. **Scope and MVP** — what must ship first, what can wait
3. **User personas** — primary users, secondary users, their goals
4. **Key user journeys** — the critical path(s) through the product
5. **Feature prioritization** — must-have vs. should-have vs. nice-to-have
6. **Platform and form factor** — web, mobile, desktop, voice, API
7. **Tech stack preferences** — languages, frameworks, hosting, third-party services
8. **Authentication and data model** — user accounts, permissions, data ownership
9. **Design and UX tone** — visual style, interaction density, accessibility level
10. **Monetization and business model** — free, freemium, subscription, marketplace, ads
11. **Competitive landscape** — existing alternatives, differentiation
12. **Success metrics** — how you know it's working
13. **Constraints and risks** — timeline, budget, regulatory, technical

Do not cover every domain for low-complexity projects. Cover all domains for high-complexity projects.

### Step 4: Question format

**Exactly 4 options per question.** No yes/no questions during discovery. Every question includes a recommended answer.

```text
**Q3. What is the primary platform for this product?**

- (Recommended) Responsive web app (desktop-first) — widest reach, lowest friction to adoption, and matches the productivity-tool category most similar products use
- Mobile-first with a companion web dashboard — better for on-the-go use but doubles initial scope
- Desktop application (Electron) — best for offline-heavy or OS-integrated tools but higher distribution friction
- API-only with third-party clients — fastest to market if consumers are developers but excludes non-technical users

Rationale: web apps provide the broadest initial audience with a single codebase; mobile can follow post-MVP.
```

Source alignment: this matches the [PIV Plan interrogation contract](../../systems/agentic-coding.md) and `.cursor/rules/asking-questions.mdc`.

### Step 5: Batch presentation

- Low (5–7): present all questions in one message
- Medium (8–12): split into two batches of 4–6
- High (13–20): split into three batches of 5–7

After each batch, summarize confirmed answers in 2–3 bullets before presenting the next batch.

### Step 6: Confirmation

After all questions are answered, summarize every confirmed decision in a compact table:

| Domain | Decision |
|--------|----------|
| Problem | ... |
| Audience | ... |
| Platform | ... |

Ask: "Does this summary capture your intent correctly? I'll generate the full PRD once confirmed."

Wait for explicit confirmation before proceeding.

---

## PRD generation

Generate the PRD only after confirmation. Write it to a markdown file.

### File location

- Default: `PRD.md` at the project root
- If the user specifies a different path, use that
- If a `docs/` directory exists, offer `docs/PRD.md` as an alternative

### PRD structure

Use this exact structure. Every section is mandatory unless the user explicitly says it doesn't apply.

```markdown
# Product Requirements Document: [Product Name]

**Version:** 1.0
**Date:** [Today's date]
**Status:** Draft
**Author:** [PRD Writer Agent, based on discovery with [User]]

---

## 1. Executive Summary

[One paragraph — what the product is, who it's for, and why it matters. No jargon. A new team member should understand the product from this paragraph alone.]

## 2. Business Model

| Element | Detail |
|---------|--------|
| **Who** | [Target users — be specific: role, context, demographics if known] |
| **Problem** | [The pain point or gap this product addresses] |
| **Solution** | [How the product solves the problem, at a high level] |
| **Name** | [Product name — working title or confirmed] |

## 3. User Personas

### Primary Persona: [Name/Role]

- **Who they are**: [1–2 sentences]
- **Goals**: [What they need to accomplish]
- **Pain points**: [What frustrates them today]
- **Context**: [When/where/how they'll use the product]

### Secondary Persona: [Name/Role]

- **Who they are**: [1–2 sentences]
- **Goals**: [...]
- **Pain points**: [...]
- **Context**: [...]

[Repeat for additional personas as needed]

## 4. User Journeys

### Journey 1: [Journey Name]

1. [Step — start from entry point]
2. [Step]
3. [Step — end at value delivered]

### Journey 2: [Journey Name]

[...]

## 5. Feature Set

### MVP (Must-Have)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| F1 | [Feature name] | [One-line description] | P0 |
| ... | ... | ... | ... |

### V1.1 (Should-Have)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| ... | ... | ... | P1 |

### Future (Nice-to-Have)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| ... | ... | ... | P2 |

## 6. Page / Screen List

```
/
├── Landing page
├── Sign up / Login
├── Dashboard
│   ├── [Section]
│   └── [Section]
├── [Feature page]
├── Settings
│   ├── Profile
│   ├── [Billing / Plan]
│   └── [Integrations]
└── [Other pages]
```

## 7. Functional Requirements

Use EARS (Easy Approach to Requirements Syntax) format. Each requirement is a user story with acceptance criteria.

### F1: [Feature Name]

**User Story:** As a [role], I want [capability], so that [benefit].

#### Acceptance Criteria

1. WHEN [trigger event occurs], THE [System] SHALL [expected response]
2. WHILE [condition is true], THE [System] SHALL [continuous behavior]
3. IF [error/unwanted condition], THEN THE [System] SHALL [recovery action]
4. WHERE [optional feature is enabled], THE [System] SHALL [conditional behavior]

[2–5 acceptance criteria per requirement.]

### F2: [Feature Name]

[...]

## 8. Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Page load time (LCP) | < 2.5s |
| Performance | Time to interactive (TTI) | < 3s |
| Availability | Uptime SLA | 99.9% |
| Security | Authentication method | [OAuth 2.0 / magic link / passwordless] |
| Security | Data encryption | At rest and in transit |
| Scalability | Concurrent users (year 1) | [N] |
| Accessibility | WCAG compliance level | AA |
| Accessibility | Screen reader support | Yes |
| [Other category] | [Requirement] | [Target] |

## 9. Tech Stack Recommendations

| Layer | Recommended | Rationale |
|-------|-------------|-----------|
| Backend | [Language + framework] | [Why] |
| Auth | [Provider or library] | [Why] |
| Frontend | [Framework + meta-framework] | [Why] |
| Database | [Primary DB + cache if needed] | [Why] |
| Hosting | [Platform + region] | [Why] |
| CI/CD | [Tooling] | [Why] |
| Monitoring | [Tooling] | [Why] |
| Payment (if applicable) | [Provider] | [Why] |
| AI/ML (if applicable) | [Provider or model] | [Why] |

### Liberties and Alternatives

[Anything the stack choice assumes. Viable alternatives if constraints change.]

## 10. Design Direction

- **Visual tone**: [Clean/minimal, bold/playful, professional/enterprise, etc.]
- **Key interaction patterns**: [e.g., real-time updates, drag-and-drop, infinite scroll]
- **Accessibility targets**: [WCAG level, screen-reader support, keyboard navigation]
- **Responsive strategy**: [Desktop-first, mobile-first, adaptive breakpoints]
- **Design system**: [Existing or build from scratch]

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| [e.g., Daily Active Users] | [N by month 3] | [Analytics source] |
| [e.g., Conversion rate] | [X%] | [Funnel stage] |
| [e.g., Time to value] | [< N minutes] | [User interview or telemetry] |
| [e.g., NPS] | [Score] | [Survey cadence] |

## 12. Risks and Assumptions

| # | Risk / Assumption | Impact | Mitigation |
|---|-------------------|--------|------------|
| R1 | [Description] | [High/Medium/Low] | [What we'll do about it] |
| ... | ... | ... | ... |

## 13. Open Questions

- [Question that needs stakeholder or user research to answer]
- [Question deferred to design or technical spike]
- [Question about third-party dependency or integration]

---

*Generated by the PRD Writer agent. Review with stakeholders before committing to implementation.*
```

### Quality checklist

Before writing the file, verify:

- [ ] Every section has content (no placeholder text left)
- [ ] Functional requirements use EARS format and pass INCOSE quality rules (Singular, Complete, Verifiable, Unambiguous, Consistent)
- [ ] Feature set is prioritized (P0/P1/P2)
- [ ] At least one primary user journey is mapped end-to-end
- [ ] Tech stack has a rationale column for every recommendation
- [ ] Success metrics are measurable (no "better UX" without a target)
- [ ] Risks have mitigations, not just descriptions
- [ ] Open questions are specific (not "figure out everything else")

---

## Research first

<!-- source: _skills/research-first/SKILL.md -->

Read the user's entire idea description before asking any questions. Extract what's already clear and what's missing. Flag ambiguities in the idea description during intake — do not assume.

---

## Conventional commits

<!-- source: _skills/conventional-commits/SKILL.md -->

If committing the PRD to a repo: single commit, type `docs`, message `docs: add PRD for [product name]`.

---

## Map to PIV

| PIV phase | PRD writer role |
|-----------|-----------------|
| Pre-Plan | This agent — structured discovery and PRD generation |
| Plan | Handoff to PIV Plan with the PRD as input |
| Implementation | Execute the Plan's work items |
| Validation | critic + tester |
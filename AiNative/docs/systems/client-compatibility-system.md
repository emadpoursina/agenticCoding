# Client Compatibility System

Extends [Release Question 1](./release-management-system.md#1-if-i-release-the-server-will-previous-versions-keep-working) for multi-client projects: **which clients are bound to this server tag's contract?**

Pair with [release-management-system.md](./release-management-system.md). Run the pre-tag check before every version tag. Run the post-deploy monitor after every production deploy.

---

## Core Idea

Every server tag has a **compatibility contract**: which client versions can talk to it, and what breaks if they can't.

---

## The Matrix

Maintain this table. Update it before every release tag.

```md
## Compatibility Matrix

| Client        | Min Version | Max Version | Notes                        |
|---------------|-------------|-------------|------------------------------|
| iOS           | 2.1.0       | *           | —                            |
| Android       | 2.0.0       | *           | v1.x missing /v2/auth header |
| Web           | —           | —           | Always current               |
| Desktop       | 1.5.0       | *           | —                            |
| Internal API  | —           | —           | No version contract          |
```

`*` = no upper bound (current). `—` = not applicable.

---

## Capability / Contract Changes

Tracks which clients actually adopted a specific route or contract change. This is where "iOS is behind" stops being tribal knowledge.

```md
## Capability Matrix

| Change             | Server since | iOS      | Android  | Desktop  | Legacy fallback | Sunset   |
|--------------------|--------------|----------|----------|----------|-----------------|----------|
| POST /v2/foo       | v2.4.0       | ≤2.1 ❌  | ≥3.2 ✅  | ≥1.8 ✅  | POST /v1/foo    | Q3 2026  |
| X-Auth-Version: 2  | v2.2.0       | ≥2.2 ✅  | ≥2.0 ✅  | ≥1.6 ✅  | reject v1       | done     |
```

**Column rules:**
- **Change** — the route, header, or contract being introduced
- **Server since** — the tag that first required or exposed it
- **Client columns** — minimum version that supports it (✅) or known to be missing it (❌)
- **Legacy fallback** — what the server does for clients that haven't adopted the change yet
- **Sunset** — when the fallback is removed; `done` means it's already gone

**When to add a row:** any time you introduce a new route, a new required header, a changed request/response shape, or a removed endpoint. One row per change, not per release.

**Pre-tag check addition:** before tagging, scan this table for rows where any client column is ❌ and sunset is approaching. That's your breaking change risk.

---

## Client Identity Headers

Every client sends these on every request:

```
X-Client-Type: ios | android | web | desktop
X-Client-Version: 2.3.1
```

**Server behavior:**
- Missing headers → reject (400) so drift is measurable in logs
- Known-old client on a new-only path → `426 Upgrade Required`
- Old client on a shared path with legacy behavior → degrade (keep working)

Clients must map `426` → force-update UI (store link or in-app update prompt).

Gate behavior server-side:

```
if client_version < MIN_SUPPORTED → return 426 Upgrade Required
```

---

## Parallel API Paths

Only introduce when a breaking change cannot wait for all clients to update.

```
/v1/endpoint   → legacy contract (frozen)
/v2/endpoint   → new contract
```

**Rules:**
- Never run three versions simultaneously — retire v1 before opening v3
- Set a deprecation date on the old path at creation time, not later
- Remove the old path only after the matrix confirms zero active traffic

---

## Phase 4 — Pre-Tag Compatibility Check

Run this before creating the version tag. Add to Release Preparation in your release doc.

```md
## Compatibility Check

- [ ] Compatibility matrix updated — all active clients listed with correct min versions
- [ ] Capability matrix updated — new routes/headers listed; ❌ clients with approaching sunset flagged
- [ ] Breaking changes identified — new required fields, removed endpoints, auth changes
- [ ] Old clients tested against new server — graceful failure confirmed
- [ ] Deprecation notices sent if any path is being removed
- [ ] Header validation in place for new requirements
```

---

## Phase 6 — Post-Deploy Compatibility Monitor

Run this after every production deploy. Add to Post-Release Monitoring in your release doc.

```md
## Compatibility Monitor

- [ ] 426 error rate by client type — spike = old client hitting new contract
- [ ] Traffic on deprecated paths — still active = client has not updated
- [ ] Crash reports filtered by client version — version-specific regressions
- [ ] Alert threshold: >1% 426 rate on any client type → investigate before next deploy
```

---

## Mental Model

```
server tag     → the contract version
matrix         → who signed that contract
client headers → proof of identity at the door
parallel paths → temporary bridge while old contracts expire
monitor        → enforcement after the door opens
```

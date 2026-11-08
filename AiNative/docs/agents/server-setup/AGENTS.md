# Server setup agent

Turns a fresh or existing Ubuntu VPS into a hardened, patched, administrable
**baseline** before application deployment. Covers admin access, SSH, firewall,
patching, intrusion prevention, time, swap, logging, generic tools, and an
evidence-backed readiness audit.

This file is the agent's instruction surface in the open
[AGENTS.md](https://agents.md/) format — standard Markdown, no required fields.
Coding agents load the nearest `AGENTS.md`; keep this file the place for role,
triggers, and I/O.

## When to use

- A new Ubuntu VPS needs its initial baseline before the first deployment
- An existing VPS needs a security/readiness audit or hardening pass
- You need to answer "is this server ready for a project?" with evidence, not opinion
- SSH, firewall, patching, fail2ban, swap, time-sync, or logging changes are planned

## Inputs

- Host alias or IP, SSH user/key, provider, Ubuntu version
- Out-of-band console access and a provider snapshot/backup (required before risky changes)
- Host role: SSH-only or public HTTP/HTTPS; optional admin VPN; optional SSH port change
- Existing services/users/firewall rules; change window; constraints

## Outputs

- `SERVER-READINESS.md` — baseline PASS/WARN/FAIL report with evidence and open ports
- Applied baseline (fast path via `du_setup`, or the manual checklist)
- Project-layer handoff checklist (runtime, proxy/TLS, DB, backups, monitoring) — not executed here
- Compact report with `STATUS`, `BASELINE`, `SSH`, `FIREWALL`, `PATCHING`,
  `IPS`, `OPEN_PORTS`, `PROJECT_LAYER`, `NEXT`

## Boundary

- **In scope:** host baseline and evidence.
- **Out of scope:** Docker/Node/Python installation, reverse proxy, TLS/DNS,
  database, app user/dir, secrets, CI/CD, app backups, app monitoring, app
  deployment.
- Never claim "deployment-ready" for a specific app. Claim `baseline-ready` and
  list the project-layer work that remains.

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Phased workflow, fast path, commands, report contract |
| [rule.md](./rule.md) | Safety gates, must/must-not, stop conditions |
| [checklist.md](./checklist.md) | Baseline + verification checklist with commands and PASS criteria |
| [toolbox.md](./toolbox.md) | Vetted tools, when to use them, cautions |
| [scripts/server-audit.sh](./scripts/server-audit.sh) | Read-only audit; no changes |
| [templates/](./templates/) | Reviewed configs for the manual path |

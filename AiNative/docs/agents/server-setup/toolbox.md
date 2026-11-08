# Toolbox — Server setup

Vetted tools for the **project-agnostic host baseline**. Versions and links were
checked while writing this agent; re-check the current release before use.
Anything marked **project layer** is deliberately not installed here.

## Baseline tools

| Tool | Use | Cautions |
|------|-----|----------|
| [du_setup](https://github.com/buildplan/du_setup) | Fast-path baseline: admin user, SSH, UFW, fail2ban/CrowdSec, auto-updates, chrony, sysctl, optional swap/Docker/Tailscale | MIT, v0.82.1 (2026-11-01), Ubuntu 20.04–26.10. Broad changes; verify SHA256, run `--cleanup-preview`, default to `--skip-cleanup`. Review the log and `/root/setup_harden_backup_*`. |
| [UFW](https://help.ubuntu.com/community/UFW) | Host firewall | Allow SSH before enabling. Docker-published ports bypass UFW. Provider firewall is a separate layer. |
| [fail2ban](https://github.com/fail2ban/fail2ban) | SSH brute-force protection | Default for an SSH-only VPS. Whitelist admin/VPN IPs; use the systemd backend on Ubuntu. Do not enable SYN-probe jails blindly. |
| [CrowdSec](https://crowdsec.net/) | Behavioural IPS + community blocklists | Optional; needs an agent, collections, and a firewall bouncer. More moving parts than fail2ban. Use when the host serves public HTTP and the operator accepts the hub account. |
| [unattended-upgrades](https://wiki.ubuntu.com/UnattendedUpgrades) | Automatic security patches | Enable the security origin; verify with `unattended-upgrade --dry-run -d`. Kernel/library updates still need a reboot. |
| [needrestart](https://github.com/liske/needrestart) | Detect services using old libraries | Report by default. Automatic restarts (`$nrconf{restart}='a'`) are optional and can surprise the operator. |
| [Ubuntu Pro](https://ubuntu.com/pro) | ESM, Livepatch, USG | Free for up to 5 personal machines. Requires an account and `pro attach`. Do not attach without approval. |
| [Lynis](https://cisofy.com/lynis/) | Host hardening audit | Advisory score; do not chase it. Fix findings that affect this host. Read-only with `lynis audit system --quick`. |
| [ssh-audit](https://github.com/jtesta/ssh-audit) | SSH config and algorithm audit | Run from the operator machine against the public endpoint. Version drift can flag algorithms Ubuntu still supports. |
| `debsecan` | Debian package CVE check | **Debian only.** On Ubuntu use `pro security-status` and `apt list --upgradable`. |
| [etckeeper](https://etckeeper.branchable.com/) | Git-track `/etc` | Optional rollback aid. Creates a repo in `/etc`; commit before the baseline pass. Do not commit secrets. |
| [chrony](https://chrony-project.org/) | NTP | du_setup uses chrony; stock Ubuntu uses `systemd-timesyncd`. Pick one and verify `System clock synchronized: yes`. |
| [Tailscale](https://tailscale.com/) | Private admin access | Optional. Keeps SSH off the public internet; whitelist `100.64.0.0/10` in fail2ban. Requires a pre-auth key and a coordination account. |
| `nc`, `nmap` | External port verification | Run from the operator machine. `nmap` needs permission; a full scan can trigger provider IDS. |

## Audit and fleet tools

| Tool | Use | Cautions |
|------|-----|----------|
| [dev-sec/ansible-collection-hardening](https://github.com/dev-sec/ansible-collection-hardening) | Repeatable Linux/SSH hardening | Right for a fleet, overkill for one VPS. It can break custom services; test on a snapshot. |
| [ansible-lockdown](https://ansible-lockdown.readthedocs.io/) | CIS benchmark automation | Strong opinions and scoring; expect exceptions for the app layer. |
| [OpenSCAP](https://www.open-scap.org/) | Compliance scanning | Heavy for a small VPS; useful when a benchmark report is required. |
| [auditd](https://github.com/linux-audit/audit-userspace) | System call/audit logging | Can be noisy and disk-hungry. Add only when the operator needs audit evidence. |
| [Docker Bench for Security](https://github.com/docker/docker-bench-security) | Docker host benchmark | **Project layer.** Only relevant once Docker is installed. |
| [Trivy](https://trivy.dev/) | Image/filesystem CVE scan | **Project layer.** Scan images in CI, not on the host baseline. |

## Project-layer handoff (do not install)

These were researched and deliberately excluded. List them in the readiness
report as remaining work.

| Area | Candidate | Note |
|------|-----------|------|
| Runtime | Docker Engine + Compose, Node, Python, etc. | Project-specific; install with the app. |
| Docker + UFW | [ufw-docker](https://github.com/chaifeng/ufw-docker) or `DOCKER-USER` rules | Published ports bypass UFW. Prefer binding to `127.0.0.1` behind a proxy. |
| Reverse proxy | [Caddy](https://caddyserver.com/) or Nginx | Caddy gives automatic HTTPS; Nginx gives explicit control. |
| TLS/DNS | Let's Encrypt, provider DNS | Needs the domain and project decision. |
| Database | PostgreSQL, MySQL, MongoDB, Redis | Private network or localhost only. |
| Backups | [restic](https://restic.net/), [Borg](https://borgbackup.readthedocs.io/) | Encrypted, offsite, scheduled; test a restore drill. |
| Monitoring | [Beszel](https://beszel.dev/), [Uptime Kuma](https://github.com/louislam/uptime-kuma) | Beszel is lighter than Netdata on small VPS hosts. |
| CI/CD | GitHub Actions, deploy user, SSH key | Project-specific trust boundary. |

## Selection notes

- **One IPS, not two.** fail2ban is enough for SSH-only. Add CrowdSec only when
  public HTTP is in scope and the operator wants community blocklists.
- **Prefer provider snapshot over etckeeper** for whole-host rollback; etckeeper
  is for config diffs and audit.
- **Keep the baseline boring.** Every extra agent is another update, port, and
  failure mode.
- **Re-check versions** before recommending a command. `du_setup` changes often;
  its README, checksum, and `--help` are the source of truth.
- **Do not add third-party APT repositories** (Lynis, CrowdSec, Tailscale)
  without explicit approval and a removal plan.

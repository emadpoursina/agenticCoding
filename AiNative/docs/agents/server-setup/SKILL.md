---
name: server-setup
description: Prepares and hardens an Ubuntu VPS baseline over SSH before application deployment — admin access, SSH, UFW, patching, fail2ban, time/swap/logging, generic tools, and an evidence-backed readiness audit. Use when onboarding a new VPS, auditing an existing host, or changing SSH/firewall/patching on a project-agnostic server.
---

# Server setup

Turns a fresh or existing Ubuntu VPS into a hardened, patched, administrable
**baseline**. Stops at `baseline-ready`; project runtime, proxy/TLS, database,
backups, monitoring, secrets, and deployment belong to the project layer.

Modes:

| Mode | Changes | Output |
|------|---------|--------|
| `audit` | none | Readiness report and gap list |
| `baseline` | approved changes only | Applied baseline, verification, report |
| `verify` | none | Re-audit after a change or drift check |

If the user does not name a mode, start with `audit`. Do not jump from `audit`
to `baseline` without the approval gate in Phase 2.

## Non-negotiables

- Keep an existing SSH session open until a **second** session succeeds.
- Confirm out-of-band console access and a provider snapshot before any change
  that can affect SSH, firewall, or boot.
- Allow the SSH port before enabling the firewall or changing the SSH port.
- Never log secrets, private keys, passwords, or tokens.
- Never reboot, change the SSH port, remove provider agents, or run
  `du_setup --cleanup-only` without explicit approval.
- Do not install project-specific runtime, proxy, TLS, database, or app
  monitoring. Record them in the handoff instead.
- Report evidence, not assumptions. A failed check is `FAIL`, not "probably fine".

## Phase 0 — Intake

Collect and record:

| Item | Why |
|------|-----|
| Host alias or IP, SSH user/key, provider, region, Ubuntu version | Access and compatibility |
| Out-of-band console (VNC/serial/rescue) | Lockout recovery |
| Snapshot or provider backup taken? | Rollback |
| Host role (`ssh-only`/`web`) and extra inbound ports | Keep the firewall minimal |
| Access options: SSH port change? admin VPN/Tailscale? | Default: port 22, no VPN |
| Existing users, services, listening ports, firewall rules | Avoid breaking the host |
| Change window, reboot permission, Ubuntu Pro availability | Scheduling and patching |

If out-of-band console, a snapshot, or a second access path is missing, state
the risk and stop before Phases 3–5. A read-only audit (Phase 1) is still safe.

## Phase 1 — Read-only audit

Run the bundled audit on the host. It makes no changes.

```bash
ssh <host> 'sudo bash -s' < scripts/server-audit.sh
```

Strict mode exits 2 on `FAIL` and 1 on `WARN`:

```bash
ssh <host> 'sudo bash -s -- --strict' < scripts/server-audit.sh
```

The script checks OS, resources, time, SSH effective config, sudo users, UFW,
listening ports, fail2ban, unattended-upgrades, reboot flag, kernel hardening,
swap, and Docker-if-present. It prints `PASS`, `WARN`, or `FAIL` per item and a
summary.

Also record manually:

- Provider firewall rules and whether they can be changed by the operator
- Whether the host is reachable on 80/443 from outside
- Existing app or provider agents that must not be removed
- Current SSH port and how the operator connects

## Phase 2 — Plan and approval

Turn the audit into a gap table. Every proposed action needs a command and a
rollback.

| Area | Current | Target | Action / file | Risk | Rollback |
|------|---------|--------|---------------|------|----------|
| SSH | password auth on | key-only | `templates/sshd-hardening.conf` | lockout | console; restore backup |
| Firewall | inactive | deny incoming | `templates/ufw-baseline.sh` | lockout | console; `ufw disable` |
| Patching | manual | auto security updates | `templates/20auto-upgrades` | reboot needed | disable service |
| ... | | | | | |

Choose the path:

- **Fast path** — fresh or standard Ubuntu host, `du_setup` accepted. Uses the
  checksum-verified script and `templates/du_setup.env.example`.
- **Manual path** — existing host, custom SSH/UFW/users, or the operator does
  not want a third-party script. Uses `checklist.md` and `templates/`.

Both paths end with the same Phase 8 verification. Do not mix them mid-run.

Approval gate — do not proceed until the user confirms:

1. The gap table and the chosen path.
2. A snapshot is taken (or the user explicitly accepts no rollback).
3. The out-of-band console works.
4. Reboot is allowed or deferred.
5. Any port other than SSH to open.

If the user cannot confirm the plan, the console, or a rollback decision, stop
and produce the runbook instead.

## Phase 3 — Admin access and SSH

Use the existing root or sudo session. Create or verify the admin user first,
then prove it works, then harden SSH.

```bash
# As root over the existing session
adduser --disabled-password --gecos "" deploy
passwd deploy          # set a sudo password; do not log it
usermod -aG sudo deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
printf '%s\n' 'ssh-ed25519 AAAA... operator@laptop' \
  | tee -a /home/deploy/.ssh/authorized_keys >/dev/null
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

If the user already exists, only add the key and confirm sudo. Do not reset an
existing password unless asked. Do not enable passwordless sudo by default.

Verify the new path **before** changing SSH config:

```bash
ssh -o BatchMode=yes -i ~/.ssh/<key> deploy@<host> \
  'id; sudo -n true 2>/dev/null || echo "sudo needs password"'
```

Back up and install the hardening drop-in. The drop-in must sort before
provider drop-ins such as `50-cloud-init.conf`, because the first value wins in
`sshd_config`.

```bash
install -d -m 755 /etc/ssh/sshd_config.d
cp -a /etc/ssh/sshd_config /root/sshd_config.backup.$(date +%Y%m%d%H%M%S)
install -m 644 templates/sshd-hardening.conf \
  /etc/ssh/sshd_config.d/00-hardening.conf
sshd -t
sshd -T | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|kbdinteractiveauthentication|maxauthtries|permitemptypasswords)'
```

`sshd -T` must show `permitrootlogin no`, `passwordauthentication no`,
`pubkeyauthentication yes`, `permitemptypasswords no`. If a provider drop-in
still overrides a value, edit or remove that earlier file — do not assume the
last file wins.

Apply without dropping the current session:

```bash
systemctl reload ssh 2>/dev/null || systemctl restart ssh
```

Open a new session as the admin user. Only after it succeeds, close the old
session. If it fails, use the console and restore the backup or remove
`00-hardening.conf`.

### Optional SSH port change

Keep port 22 by default. A port change adds lockout risk and little security.
When approved:

```bash
# 1. Allow the new port everywhere before moving SSH.
ufw allow 2222/tcp comment 'ssh-new'
# Also add 2222/tcp to the provider firewall before continuing.

# 2. Socket-activated SSH (Ubuntu 22.10+).
install -d /etc/systemd/system/ssh.socket.d
cat >/etc/systemd/system/ssh.socket.d/10-port.conf <<'EOF'
[Socket]
ListenStream=
ListenStream=2222
EOF

# 3. Non-socket fallback; set Port 2222 in the hardening drop-in.
#    Edit 00-hardening.conf and add: Port 2222

sshd -t
systemctl daemon-reload
systemctl restart ssh.socket
```

Verify from a **new local terminal** with `ssh -p 2222 deploy@<host>` before
closing the old session. Then remove the old rule:

```bash
ufw delete allow 22/tcp
```

If `ssh.socket` does not exist, set `Port 2222` in the drop-in and restart the
`ssh` service instead. Never remove port 22 from the provider firewall until the
new port is proven.

## Phase 4 — Firewall

Allow SSH first, then enable UFW. On a host where SSH already works, the order
still matters: a default-deny firewall with no SSH rule locks you out.

```bash
apt-get -y install ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'ssh'   # use the actual SSH port
ufw --force enable
ufw status verbose
grep '^IPV6=' /etc/default/ufw
```

Replace `22` with the actual SSH port; after Phase 3a, allow only the new port.

If the host is declared `web` in intake, open HTTP/HTTPS. Otherwise leave them
closed and say so in the report.

```bash
ufw allow 80/tcp comment 'http'
ufw allow 443/tcp comment 'https'
```

Keep the rule set minimal. For each additional port, record the owner and
reason. Do not open a database, cache, or admin port to the internet — use
localhost binding, a private network, or an SSH tunnel.

Provider firewall is a separate layer. List the required inbound rules and have
the operator apply them; verify externally. A host is not `ready` if UFW and
the provider firewall disagree.

Docker note: published container ports bypass UFW. If Docker is already
present, run `docker ps --format '{{.Names}}\t{{.Ports}}'` and report any
`0.0.0.0:` or `[::]:` mapping. Fixing it belongs to the project layer
(`127.0.0.1` binding, reverse proxy, or `DOCKER-USER`/`ufw-docker` with
approval). Do not install Docker here.

## Phase 5 — Patching and system baseline

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y full-upgrade
apt-get -y autoremove --purge
apt-get -y install unattended-upgrades needrestart
install -m 644 templates/20auto-upgrades /etc/apt/apt.conf.d/20auto-upgrades
systemctl enable --now unattended-upgrades
unattended-upgrade --dry-run -d
```

Confirm `/etc/apt/apt.conf.d/50unattended-upgrades` enables the security origin
for this release. Run `needrestart -b` and report services that need a restart;
automatic restarts are optional and off by default.

Check the reboot flag:

```bash
test -f /var/run/reboot-required && cat /var/run/reboot-required /var/run/reboot-required.pkgs
```

Reboot only with approval, then re-verify SSH, UFW, fail2ban, time, and
services. Never reboot in the same step as an unverified SSH change.

Time:

```bash
timedatectl set-timezone Etc/UTC
timedatectl set-ntp true
timedatectl status
```

Require `System clock synchronized: yes`. If `systemd-timesyncd` is unavailable,
install and verify `chrony` instead.

Swap — only if RAM is under 2 GB and no swap exists:

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Conservative kernel settings:

```bash
install -m 644 templates/99-baseline-hardening.conf /etc/sysctl.d/99-baseline-hardening.conf
sysctl --system
```

Read the file before applying. `kernel.unprivileged_bpf_disabled=1` can break
rootless container tooling; remove that line when it conflicts with a declared
workload.

Journald limits:

```bash
install -d /etc/systemd/journald.conf.d
cat >/etc/systemd/journald.conf.d/99-baseline.conf <<'EOF'
[Journal]
SystemMaxUse=500M
SystemKeepFree=1G
MaxRetentionSec=1month
Compress=yes
EOF
systemctl restart systemd-journald
```

Hostname only if requested; update the `127.0.1.1` line in `/etc/hosts` and the
provider's reverse DNS separately.

## Phase 6 — Intrusion prevention

Default to fail2ban for SSH. CrowdSec is optional when the host will serve
public HTTP and the operator accepts a bouncer and hub account.

```bash
apt-get -y install fail2ban
install -m 644 templates/fail2ban-jail.local /etc/fail2ban/jail.local
# Edit ignoreip: localhost, operator IPs, and the Tailscale CIDR if used.
fail2ban-client -t
systemctl enable --now fail2ban
fail2ban-client status sshd
```

Confirm the admin IP is not banned. Do not enable the `ufw-probes` jail by
default — spoofed SYN packets can ban legitimate clients unless allowlisted.
If the host is behind Tailscale, whitelist `100.64.0.0/10` and put SSH behind
Tailscale where possible.

## Phase 7 — Generic tools

Minimal, project-agnostic set:

```bash
apt-get -y install curl wget git jq htop tmux rsync ncdu unzip zip tree \
  ca-certificates gnupg lsb-release
```

Audit tools:

```bash
apt-get -y install lynis
apt-get -y install ssh-audit || { apt-get -y install pipx && pipx install ssh-audit; }
```

Do not add a third-party APT repository without approval. `debsecan` is
Debian-only; on Ubuntu use `pro security-status` (if Ubuntu Pro is enabled) and
`apt list --upgradable`.

Optional: `apt-get -y install etckeeper && etckeeper init && etckeeper commit "baseline before server-setup"` to git-track `/etc` for rollback.

Install no application runtime, web server, database, container engine, or app
dependency here.

## Phase 8 — Verification

Re-run the audit and attach evidence:

```bash
ssh <host> 'sudo bash -s -- --strict' < scripts/server-audit.sh
```

From the operator's machine, not the host:

```bash
nc -zv -w 5 <host> 22
nmap -Pn -p- --min-rate 2000 <host>     # only with permission
ssh-audit -p 22 <host>
```

Require all of:

- Second SSH session as the admin user succeeds; root login and password auth
  are disabled.
- UFW is active, default deny incoming, and only approved ports are open.
- Provider firewall matches the host firewall.
- `unattended-upgrades` is enabled and no pending security updates remain.
- `fail2ban` is active and the `sshd` jail is running.
- Time is synchronized to UTC.
- Swap exists when RAM is under 2 GB.
- `systemctl --failed` is empty or explained.
- No service listens on `0.0.0.0`/`[::]` unless approved.
- Lynis and `ssh-audit` results are recorded, with residual warnings explained.

## Phase 9 — Readiness report and handoff

Write `SERVER-READINESS.md` on the operator side (never commit secrets):

```markdown
# Server readiness — <host>
Date / operator / mode / Ubuntu / provider / snapshot:

OVERALL: baseline-ready | ready-with-warnings | blocked

| Area | Result | Evidence |
|------|--------|----------|
| Access / SSH | PASS/WARN/FAIL | |
| Firewall | | |
| Patching | | |
| Intrusion prevention | | |
| Time / swap / logging | | |
| Tools / audit | | |

Open ports: <port/proto, purpose, owner>
Applied changes: <list>
Rollback: <backups, SSH drop-in, UFW, reboot required>
Project layer: runtime, proxy/TLS, DB, secrets, CI/CD, app backups, monitoring, deploy
Next: <one action>
```

Compact report contract for the agent response:

```text
STATUS: baseline-ready | ready-with-warnings | blocked
BASELINE: <n> PASS / <n> WARN / <n> FAIL
SSH: key-only=<yes/no> root-login=<no/yes> port=<n>
FIREWALL: active=<yes/no> inbound=<deny/allow> open=<ports>
PATCHING: auto=<yes/no> pending-security=<n> reboot-required=<yes/no>
IPS: fail2ban=<active/inactive> jail=<running/not-running>
OPEN_PORTS: <port/proto purpose; ...>
PROJECT_LAYER: runtime, proxy/TLS, DB, backups, monitoring, deployment
NEXT: <one action>
```

`baseline-ready` requires zero `FAIL` in access, firewall, and patching.
Warnings are allowed only when explained and accepted by the operator.

## Fast path — du_setup

Use only on a compatible host (Ubuntu 20.04–26.10, Debian 12/13) after Phase 2
approval. The script makes broad changes; review its log and backup directory.

1. Copy and edit the config on the host:

```bash
scp templates/du_setup.env.example <admin>@<host>:/tmp/du_setup.env
ssh -t <admin>@<host> 'sudo install -m 600 /tmp/du_setup.env /root/du_setup.env && rm /tmp/du_setup.env && sudo nano /root/du_setup.env'
```

If the host only has root access, use `root@<host>` and `/root/du_setup.env`
directly.

Replace `DU_USERNAME`, `DU_SSH_PUBLIC_KEY`, and confirm every `DU_*` value.
Keep `DU_SSH_PORT="22"`, `DU_INSTALL_DOCKER="false"`, `DU_VPN="none"`, and
`DU_AUTO_REBOOT="false"` unless intake says otherwise.

2. Download, verify, preview cleanup, then run:

```bash
cd /root
curl -fsSLO https://raw.githubusercontent.com/buildplan/du_setup/refs/heads/main/du_setup.sh
curl -fsSLO https://raw.githubusercontent.com/buildplan/du_setup/refs/heads/main/du_setup.sh.sha256
sha256sum -c du_setup.sh.sha256
chmod +x du_setup.sh
sudo -E ./du_setup.sh --cleanup-preview
sudo -E ./du_setup.sh --config ./du_setup.env --quiet --skip-cleanup
```

`sha256sum -c` must print `du_setup.sh: OK`. If it does not, stop.

3. Review the summary and log:

```bash
ls -1t /var/log/du_setup_* | head
ls -1dt /root/setup_harden_backup_* | head
```

4. Re-run Phase 8. If the script fails partway, do not rerun blindly: read the
log, record what completed, and finish only the remaining gaps with the manual
path. The backup directory holds the original configs.

`--skip-cleanup` is the default because cleanup can remove `cloud-init`,
provider monitoring agents, and default users. Run `--cleanup-only` only with a
reviewed preview and explicit approval.

## Manual path

Use `checklist.md` for exact commands and PASS criteria, and `templates/` for
the reviewed configs. Both paths end at Phase 8.

## Stop conditions

Stop and ask the operator when:

- A second SSH session or console cannot be verified.
- The provider firewall cannot be changed and a required port would be blocked.
- `sshd -t` fails and the cause is not obvious.
- A service the operator needs would be disrupted and no window is agreed.
- Pending updates require a reboot the operator has not approved.
- Docker publishes ports publicly and the project-layer owner is unavailable.
- A finding needs project-specific knowledge (runtime, proxy, database, TLS).

Record the stop, the evidence, and the safe state in the report.

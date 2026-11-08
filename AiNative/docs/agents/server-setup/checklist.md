# Checklist — Server setup

Per-item contract for the [SKILL.md](./SKILL.md) workflow. Run top to bottom.
Every `PASS` needs the command output, not an assumption. `WARN` is acceptable
only with a written reason; `FAIL` blocks `baseline-ready`.

Use `sudo` for privileged commands. Record the host, date, and operator first.

## 0. Intake evidence

- [ ] Host/IP, SSH user, key path, provider, Ubuntu version recorded
- [ ] Out-of-band console tested (open it, do not just assume it exists)
- [ ] Provider snapshot or backup taken; snapshot ID recorded
- [ ] Host role recorded: `ssh-only` or `web`
- [ ] SSH port change: approved / rejected (default rejected)
- [ ] Reboot window: approved / deferred
- [ ] Existing services, users, and open ports listed
- [ ] Provider firewall rules reviewed

**PASS:** all items above are answered. Missing console or snapshot means no
SSH/firewall change.

## 1. Read-only audit

```bash
ssh <host> 'sudo bash -s' < scripts/server-audit.sh
```

**PASS:** report generated, every `FAIL` understood. This step changes nothing.

## 2. Admin user and key

```bash
adduser --disabled-password --gecos "" deploy
passwd deploy
usermod -aG sudo deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
printf '%s\n' 'ssh-ed25519 AAAA... operator@laptop' \
  | tee -a /home/deploy/.ssh/authorized_keys >/dev/null
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

Verify from the operator's machine:

```bash
ssh -o BatchMode=yes -i ~/.ssh/<key> deploy@<host> 'id'
ssh -i ~/.ssh/<key> deploy@<host> 'sudo -v && echo sudo-ok'
```

**PASS:** `uid` is the admin user, `sudo` succeeds with the expected password
or existing policy, and no private key was copied to the host.

**FAIL action:** fix key ownership/permissions (`700` dir, `600` file, owned by
the admin user) before touching `sshd_config`.

## 3. SSH hardening

Back up, install, validate:

```bash
cp -a /etc/ssh/sshd_config /root/sshd_config.backup.$(date +%Y%m%d%H%M%S)
install -m 644 templates/sshd-hardening.conf \
  /etc/ssh/sshd_config.d/00-hardening.conf
sshd -t
sshd -T | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|kbdinteractiveauthentication|permitemptypasswords|maxauthtries)'
systemctl reload ssh 2>/dev/null || systemctl restart ssh
```

Requirements:

- [ ] `00-hardening.conf` sorts before provider drop-ins such as
  `50-cloud-init.conf`; if `sshd -T` shows an old value, find the earlier file
  with `grep -r '^PasswordAuthentication' /etc/ssh/sshd_config*`
- [ ] `permitrootlogin no`
- [ ] `passwordauthentication no`
- [ ] `pubkeyauthentication yes`
- [ ] `permitemptypasswords no`
- [ ] `kbdinteractiveauthentication no` (unless MFA is deliberately configured)
- [ ] `maxauthtries` is 3–4
- [ ] `sshd -t` exits 0 before reload

**PASS:** a new session succeeds as the admin user with the key, and the old
session is still open until that proof exists.

**FAIL action:** use the console. Remove `00-hardening.conf` or restore the
backup, run `sshd -t`, restart SSH, then investigate.

### 3a. Optional port change

```bash
ufw allow 2222/tcp comment 'ssh-new'
install -d /etc/systemd/system/ssh.socket.d
cat >/etc/systemd/system/ssh.socket.d/10-port.conf <<'EOF'
[Socket]
ListenStream=
ListenStream=2222
EOF
# Also add "Port 2222" to /etc/ssh/sshd_config.d/00-hardening.conf
sshd -t
systemctl daemon-reload
systemctl restart ssh.socket
```

- [ ] New port allowed in UFW **and** provider firewall before restart
- [ ] `systemctl show ssh.socket -p Listen` or `ss -ltnp` shows the new port
- [ ] New session on the new port verified before closing the old session
- [ ] Old port removed from UFW only after verification
- [ ] Root/console recovery path still available

**PASS:** `ssh -p 2222 deploy@<host>` works; port 22 is closed externally.

**FAIL action:** restore the socket override (`rm -rf
/etc/systemd/system/ssh.socket.d`), `systemctl daemon-reload`, restart
`ssh.socket`, and reconnect on 22. If `ssh.socket` is absent, restore the old
`Port` value and restart `ssh`.

## 4. Firewall

```bash
apt-get -y install ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'ssh'   # replace 22 with the actual SSH port
ufw --force enable
ufw status verbose
grep '^IPV6=' /etc/default/ufw
```

For a declared `web` host only:

```bash
ufw allow 80/tcp comment 'http'
ufw allow 443/tcp comment 'https'
```

- [ ] `Status: active`
- [ ] `Default: deny (incoming), allow (outgoing)`
- [ ] SSH port allowed
- [ ] Only approved ports allowed
- [ ] IPv6 rules present (`IPV6=yes` and `(v6)` entries)
- [ ] Provider firewall has the same inbound rules
- [ ] External check from the operator machine matches

**PASS:** `ufw status verbose` and the external scan agree, and the current SSH
session still works.

**FAIL action:** from the console, `ufw allow <ssh-port>/tcp` then
`ufw reload`. Never disable UFW remotely unless the console is open.

## 5. Patching

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

- [ ] Full upgrade completed without held-back packages that matter
- [ ] `unattended-upgrades` installed and enabled
- [ ] Security origin enabled in `/etc/apt/apt.conf.d/50unattended-upgrades`
- [ ] Dry run shows the security pocket
- [ ] `apt list --upgradable` has no pending security updates
- [ ] `needrestart -b` reviewed
- [ ] Reboot flag checked

```bash
test -f /var/run/reboot-required && cat /var/run/reboot-required /var/run/reboot-required.pkgs
```

**PASS:** auto-updates active, no unexplained pending security update, reboot
either not required or scheduled with approval.

**FAIL action:** if packages are held, record why; do not force-remove them.
If a reboot is required, schedule it and re-run section 12 after reboot.

## 6. Time

```bash
timedatectl set-timezone Etc/UTC
timedatectl set-ntp true
timedatectl status
```

- [ ] `Time zone: Etc/UTC`
- [ ] `System clock synchronized: yes`
- [ ] `NTP service: active`

**PASS:** all three. **FAIL action:** check `systemctl status
systemd-timesyncd`; install/verify `chrony` if the host does not use timesyncd.

## 7. Swap (only when RAM < 2 GB and no swap)

```bash
free -h
swapon --show
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

- [ ] `swapon --show` lists the swap file
- [ ] `/etc/fstab` entry present
- [ ] `vm.swappiness` set conservatively (10) when appropriate

**PASS:** swap active and persistent. **FAIL action:** check `fallocate`
support; use `dd` only if needed, and verify free disk first.

## 8. Kernel and sysctl

```bash
install -m 644 templates/99-baseline-hardening.conf /etc/sysctl.d/99-baseline-hardening.conf
sysctl --system
sysctl kernel.dmesg_restrict kernel.kptr_restrict kernel.yama.ptrace_scope \
  net.ipv4.conf.all.rp_filter net.ipv4.tcp_syncookies fs.protected_hardlinks
```

- [ ] `sysctl --system` reports no unknown-key errors
- [ ] Values match the template
- [ ] `kernel.unprivileged_bpf_disabled` removed if it breaks a declared workload
- [ ] No reboot-dependent setting is claimed as active

**PASS:** values applied and persist across `sysctl --system`.

## 9. Journald

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
journalctl --disk-usage
```

**PASS:** journald restarts cleanly and disk usage is bounded.

## 10. Intrusion prevention

```bash
apt-get -y install fail2ban
install -m 644 templates/fail2ban-jail.local /etc/fail2ban/jail.local
# Edit ignoreip before enabling.
fail2ban-client -t
systemctl enable --now fail2ban
fail2ban-client status
fail2ban-client status sshd
```

- [ ] `fail2ban-client -t` exits 0
- [ ] `sshd` jail is enabled and running
- [ ] `ignoreip` includes `127.0.0.1/8`, `::1`, and operator/VPN addresses
- [ ] No legitimate admin IP is banned
- [ ] Log path/backend matches the host (`systemd` on Ubuntu)

**PASS:** jail `sshd` is `enabled` and `running`, and any `Total failed`
corresponds to real probes, not the admin IP.

**FAIL action:** check `journalctl -u fail2ban` and `fail2ban-client status
sshd`; fix the backend before claiming protection.

## 11. Generic tools

```bash
apt-get -y install curl wget git jq htop tmux rsync ncdu unzip zip tree \
  ca-certificates gnupg lsb-release
apt-get -y install lynis
apt-get -y install ssh-audit || { apt-get -y install pipx && pipx install ssh-audit; }
```

- [ ] Commands resolve: `curl --version`, `git --version`, `jq --version`
- [ ] `lynis --version` and `ssh-audit --version` work
- [ ] No project runtime, web server, database, or container engine installed
- [ ] Disk space after installs is acceptable (`df -h /`)

**PASS:** all tools run and the project layer is still absent.

## 12. Verification

Re-run the audit:

```bash
ssh <host> 'sudo bash -s -- --strict' < scripts/server-audit.sh
```

From the operator's machine:

```bash
nc -zv -w 5 <host> 22
ssh-audit -p 22 <host>
nmap -Pn -p- --min-rate 2000 <host>   # only with permission
```

On the host:

```bash
lynis audit system --quick
systemctl --failed
ss -tulpn
ufw status verbose
fail2ban-client status sshd
timedatectl status
free -h
df -h /
```

- [ ] Audit has no unexplained `FAIL`
- [ ] Second SSH session works
- [ ] Root login and password auth are off
- [ ] Only approved ports are reachable externally
- [ ] `systemctl --failed` is empty or explained
- [ ] Lynis warnings triaged (score recorded, not chased)
- [ ] `ssh-audit` has no critical failure
- [ ] Time, swap, journald, and fail2ban verified after any reboot

**PASS:** all of the above. **FAIL action:** fix the item and repeat this
section; do not report ready from an earlier run.

## 13. Handoff

- [ ] `SERVER-READINESS.md` written with evidence and open ports
- [ ] Rollback paths and backup locations recorded
- [ ] Project-layer checklist handed off (runtime, proxy/TLS, DB, secrets,
  CI/CD, app backups, app monitoring, deployment)
- [ ] Residual warnings and accepted risks listed
- [ ] No secrets in the report or transcript
- [ ] Final compact report uses the [SKILL.md](./SKILL.md) contract

**PASS:** operator has the report, the rollback steps, and the project-layer
next action.

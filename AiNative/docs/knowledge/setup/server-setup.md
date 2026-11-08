# Server setup

Ubuntu VPS baseline before application deployment. This page is the quick
reference; the repeatable workflow, safety gates, audit script, and templates
live in the [server-setup agent](../../agents/server-setup/).

**Scope:** host baseline only — admin access, SSH, firewall, patching,
fail2ban, time, swap, logging, and generic tools. Runtime, reverse proxy,
TLS/DNS, database, app user/directory, secrets, CI/CD, app backups, and app
monitoring belong to the project layer.

## Baseline order

1. Read-only audit — [server-audit.sh](../../agents/server-setup/scripts/server-audit.sh)
2. Admin user and key; verify a second SSH session
3. SSH hardening; keep the current session open
4. UFW: allow SSH, then default deny, then enable
5. Patching, auto-updates, time, swap, sysctl, journald
6. fail2ban for SSH
7. Generic tools
8. Verify from outside; write the readiness report

Fast path: checksum-verified [du_setup](../../agents/server-setup/templates/du_setup.env.example)
with the project-agnostic env template. Manual path:
[checklist.md](../../agents/server-setup/checklist.md) and
[templates/](../../agents/server-setup/templates/).

## SSH

```bash
ssh username@host
scp -r username@host:/remote/folder ./local/folder
```

## Create user and SSH access

```bash
useradd -m -s /bin/bash deploy
passwd deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

## SSH key

```bash
ssh-keygen -t ed25519 -C "Comment"
ssh-copy-id -i ~/.ssh/specific-key.pub root@your-server-ip
```

`~/.ssh/config` example:

```text
Host myserver
    HostName your-server-ip
    User deploy
    IdentityFile ~/.ssh/id_ed25519
```

```bash
ssh -T git@github.com
ssh-add ~/.ssh/specific-key.pub
```

Add key to agent in `.zshrc` if needed.

## SSH hardening

Install the drop-in as `/etc/ssh/sshd_config.d/00-hardening.conf` from
[sshd-hardening.conf](../../agents/server-setup/templates/sshd-hardening.conf).
The `00-` prefix matters: the first value wins, and provider files such as
`50-cloud-init.conf` can otherwise override it.

```bash
sshd -t
sshd -T | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries)'
systemctl reload ssh 2>/dev/null || systemctl restart ssh
```

Verify a **second** session as the sudo user before closing the current one.

Ubuntu 22.10+ activates SSH through `ssh.socket`. Changing `Port` in
`sshd_config` alone does not move the listener; add a
`/etc/systemd/system/ssh.socket.d/10-port.conf` drop-in with
`ListenStream=` then `ListenStream=<port>`, or disable socket activation and
enable `ssh.service`. Keep port 22 unless the port change is worth the lockout
risk.

## Firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'ssh'
ufw --force enable
ufw status verbose
```

Open 80/443 only when the host is web-facing. A database, cache, or admin port
should not be public — bind it to localhost or use a private network/tunnel.
Provider firewall rules are a separate layer; keep them aligned.

Docker note: published container ports bypass UFW. Bind to `127.0.0.1` behind a
reverse proxy, or apply `DOCKER-USER`/`ufw-docker` rules with approval.

## Patching and system

```bash
apt-get update
apt-get -y full-upgrade
apt-get -y install unattended-upgrades needrestart
systemctl enable --now unattended-upgrades
timedatectl set-timezone Etc/UTC
timedatectl set-ntp true
```

Check `/var/run/reboot-required`; reboot only with a window and a verified
console. Add swap only when RAM is under 2 GB and no swap exists. Apply
[99-baseline-hardening.conf](../../agents/server-setup/templates/99-baseline-hardening.conf)
conservatively and read the comments before `sysctl --system`.

## Fast path

```bash
cd /root
curl -fsSLO https://raw.githubusercontent.com/buildplan/du_setup/refs/heads/main/du_setup.sh
curl -fsSLO https://raw.githubusercontent.com/buildplan/du_setup/refs/heads/main/du_setup.sh.sha256
sha256sum -c du_setup.sh.sha256
chmod +x du_setup.sh
sudo -E ./du_setup.sh --cleanup-preview
sudo -E ./du_setup.sh --config ./du_setup.env --quiet --skip-cleanup
```

Verify the checksum first. Review the cleanup preview. Do not remove
`cloud-init` or provider agents without approval. See the
[agent workflow](../../agents/server-setup/SKILL.md) for the full gate.

## Readiness

`baseline-ready` requires a verified second SSH session, key-only auth, active
UFW with only approved ports, no unexplained pending security updates, active
fail2ban, synchronized time, and a clean audit. Report warnings honestly and
hand off the project-layer checklist.

See also [linux.md](../commands/linux.md) for users and firewall commands.

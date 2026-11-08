#!/usr/bin/env bash
# server-audit.sh — read-only Ubuntu VPS baseline audit.
#
# Usage:
#   sudo bash server-audit.sh
#   sudo bash server-audit.sh --strict
#   sudo bash server-audit.sh --no-apt
#
# Exit codes:
#   0  audit completed (default)
#   1  --strict and at least one WARN
#   2  --strict and at least one FAIL
#   64 bad usage
#
# This script makes no changes. It only reads files, service state, and
# simulated package state. Safe to run on a production host.

set -uo pipefail
export LC_ALL=C

STRICT=0
CHECK_APT=1

usage() {
  cat <<'EOF'
Read-only Ubuntu VPS baseline audit.

Options:
  --strict   Exit non-zero on WARN (1) or FAIL (2).
  --no-apt   Skip the simulated apt upgrade check (faster, no network locks).
  -h, --help Show this help.

Run with sudo for SSH effective config, UFW, fail2ban, and process checks.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --strict) STRICT=1 ;;
    --no-apt) CHECK_APT=0 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$1" >&2; usage >&2; exit 64 ;;
  esac
  shift
done

PASS=0
WARN=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); printf '[PASS] %s: %s\n' "$1" "$2"; }
warn() { WARN=$((WARN + 1)); printf '[WARN] %s: %s\n' "$1" "$2"; }
fail() { FAIL=$((FAIL + 1)); printf '[FAIL] %s: %s\n' "$1" "$2"; }
skip() { SKIP=$((SKIP + 1)); printf '[SKIP] %s: %s\n' "$1" "$2"; }
info() { printf '[INFO] %s: %s\n' "$1" "$2"; }
section() { printf '\n== %s ==\n' "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

ROOT=0
[ "$(id -u)" -eq 0 ] && ROOT=1
SUDO_OK=0
if [ "$ROOT" -eq 0 ] && have sudo && sudo -n true 2>/dev/null; then
  SUDO_OK=1
fi

# Run a command as root when possible; 127 means "needs sudo".
as_root() {
  if [ "$ROOT" -eq 1 ]; then
    "$@"
  elif [ "$SUDO_OK" -eq 1 ]; then
    sudo -n "$@"
  else
    return 127
  fi
}

num_ge() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge "$2" ]
}

SSHD_BIN=$(command -v sshd 2>/dev/null || echo /usr/sbin/sshd)

printf 'Server baseline audit — %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'Host: %s\n' "$(hostname 2>/dev/null || echo unknown)"

if [ "$ROOT" -eq 0 ] && [ "$SUDO_OK" -eq 0 ]; then
  warn "audit.privilege" "not root and passwordless sudo unavailable; privileged checks may be inaccurate"
fi

# ---------------------------------------------------------------------------
section "System"
# ---------------------------------------------------------------------------

os_id=""
os_ver=""
os_name=""
if [ -r /etc/os-release ]; then
  os_id=$(awk -F= '/^ID=/{gsub(/"/, "", $2); print $2; exit}' /etc/os-release)
  os_ver=$(awk -F= '/^VERSION_ID=/{gsub(/"/, "", $2); print $2; exit}' /etc/os-release)
  os_name=$(awk -F= '/^PRETTY_NAME=/{gsub(/"/, "", $2); print $2; exit}' /etc/os-release)
fi
info "os" "${os_name:-unknown} (id=${os_id:-unknown}, version=${os_ver:-unknown})"

if [ "$os_id" = "ubuntu" ] && [ -n "$os_ver" ] \
  && printf '%s\n%s\n' "20.04" "$os_ver" | sort -V -C; then
  pass "os.version" "Ubuntu $os_ver is supported"
elif [ "$os_id" = "ubuntu" ]; then
  warn "os.version" "Ubuntu $os_ver is outside the tested 20.04+ range"
elif [ "$os_id" = "debian" ]; then
  warn "os.version" "Debian detected; this checklist targets Ubuntu"
else
  warn "os.version" "Unrecognized OS (${os_name:-unknown})"
fi

info "kernel" "$(uname -r 2>/dev/null || echo unknown)"
info "arch" "$(uname -m 2>/dev/null || echo unknown)"
info "virt" "$(systemd-detect-virt 2>/dev/null || echo unknown)"
info "uptime" "$(uptime -p 2>/dev/null || uptime 2>/dev/null || echo unknown)"
info "cpu" "$(nproc 2>/dev/null || echo unknown) vCPU"

mem_mb=$(awk '/^MemTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo 2>/dev/null || echo 0)
swap_mb=$(awk '/^SwapTotal:/ {printf "%d", $2 / 1024}' /proc/meminfo 2>/dev/null || echo 0)
mem_mb=${mem_mb:-0}
swap_mb=${swap_mb:-0}
info "memory" "${mem_mb} MB RAM, ${swap_mb} MB swap"

root_use=$(df -P / 2>/dev/null | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
root_use=${root_use:-0}
if num_ge "$root_use" 90; then
  fail "disk.root" "root filesystem ${root_use}% used"
elif num_ge "$root_use" 80; then
  warn "disk.root" "root filesystem ${root_use}% used"
else
  pass "disk.root" "root filesystem ${root_use}% used"
fi

inode_use=$(df -Pi / 2>/dev/null | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
inode_use=${inode_use:-0}
if num_ge "$inode_use" 90; then
  warn "disk.inodes" "root filesystem ${inode_use}% inodes used"
else
  pass "disk.inodes" "root filesystem ${inode_use}% inodes used"
fi

if [ "$swap_mb" -eq 0 ] 2>/dev/null; then
  if [ "$mem_mb" -lt 2048 ] 2>/dev/null; then
    warn "system.swap" "no swap with ${mem_mb} MB RAM; add a swap file"
  else
    pass "system.swap" "no swap; RAM is ${mem_mb} MB"
  fi
else
  pass "system.swap" "${swap_mb} MB swap active"
fi

failed_units=$(systemctl --failed --no-legend --no-pager 2>/dev/null | wc -l | tr -d ' ')
failed_units=${failed_units:-0}
if ! have systemctl; then
  skip "system.units" "systemd not available"
elif [ "$failed_units" -gt 0 ]; then
  warn "system.units" "${failed_units} failed systemd unit(s); run systemctl --failed"
else
  pass "system.units" "no failed systemd units"
fi

if [ -f /var/run/reboot-required ]; then
  pkgs=$(tr '\n' ' ' < /var/run/reboot-required.pkgs 2>/dev/null | cut -c1-160)
  warn "system.reboot" "reboot required${pkgs:+: $pkgs}"
else
  pass "system.reboot" "no reboot required"
fi

# ---------------------------------------------------------------------------
section "Time"
# ---------------------------------------------------------------------------

if have timedatectl; then
  tz=$(timedatectl show -p Timezone --value 2>/dev/null || true)
  ntp_sync=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || true)
  ntp_service=$(timedatectl show -p NTP --value 2>/dev/null || true)
  info "time.zone" "${tz:-unknown}"
  if [ "$ntp_sync" = "yes" ]; then
    pass "time.sync" "clock synchronized (NTP=${ntp_service:-unknown})"
  else
    warn "time.sync" "clock not synchronized; check systemd-timesyncd or chrony"
  fi
  if [ "$tz" = "Etc/UTC" ] || [ "$tz" = "UTC" ]; then
    pass "time.utc" "timezone is UTC"
  else
    warn "time.utc" "timezone is ${tz:-unknown}; UTC is the baseline default"
  fi
else
  warn "time.sync" "timedatectl not available"
fi

# ---------------------------------------------------------------------------
section "Access"
# ---------------------------------------------------------------------------

op_user=${SUDO_USER:-$(id -un 2>/dev/null || echo unknown)}
info "access.operator" "$op_user"
if [ "$op_user" = "root" ]; then
  warn "access.sudo" "audit run as root; use a named sudo user for administration"
elif id -nG "$op_user" 2>/dev/null | grep -qw sudo; then
  pass "access.sudo" "$op_user is in the sudo group"
else
  warn "access.sudo" "$op_user is not in the sudo group"
fi

sudo_users=$(getent group sudo 2>/dev/null | cut -d: -f4)
if [ -n "$sudo_users" ]; then
  pass "access.sudo-users" "sudo group: $sudo_users"
else
  warn "access.sudo-users" "no members in the sudo group"
fi

extra_root=$(awk -F: '$3 == 0 && $1 != "root" {print $1}' /etc/passwd 2>/dev/null | tr '\n' ' ')
if [ -n "$extra_root" ]; then
  fail "access.uid0" "non-root UID 0 account(s): $extra_root"
else
  pass "access.uid0" "only root has UID 0"
fi

root_state=$(as_root passwd -S root 2>/dev/null | awk '{print $2}')
case "$root_state" in
  L|LK) pass "access.root-password" "root password is locked" ;;
  P) warn "access.root-password" "root has a password set" ;;
  *) skip "access.root-password" "could not read root password state (run with sudo)" ;;
esac

key_count=$(find /home -maxdepth 3 -type f -name authorized_keys -size +0c 2>/dev/null | wc -l | tr -d ' ')
key_count=${key_count:-0}
if [ "$key_count" -gt 0 ]; then
  pass "access.keys" "${key_count} non-empty authorized_keys file(s) under /home"
else
  warn "access.keys" "no non-empty authorized_keys under /home; check admin access"
fi

# ---------------------------------------------------------------------------
section "SSH"
# ---------------------------------------------------------------------------

ssh_port=22
socket_listen=""
sshd_present=1
if [ ! -x "$SSHD_BIN" ]; then
  sshd_present=0
  skip "ssh.config-test" "openssh-server not installed"
  sshd_t=""
else
  sshd_test=$(as_root "$SSHD_BIN" -t 2>&1)
  sshd_test_rc=$?
  if [ "$sshd_test_rc" -eq 0 ]; then
    pass "ssh.config-test" "sshd -t passed"
  elif [ "$sshd_test_rc" -eq 127 ]; then
    skip "ssh.config-test" "sshd needs root; rerun with sudo"
  else
    fail "ssh.config-test" "sshd -t failed: ${sshd_test:-unknown error}"
  fi
  sshd_t=$(as_root "$SSHD_BIN" -T 2>/dev/null || true)
fi
if [ "$sshd_present" -eq 0 ]; then
  skip "ssh.effective" "openssh-server not installed"
elif [ -z "$sshd_t" ]; then
  warn "ssh.effective" "could not read effective config (run with sudo)"
else
  sshd_val() { printf '%s\n' "$sshd_t" | awk -v key="$1" '$1 == key {print $2; exit}'; }

  prl=$(sshd_val permitrootlogin)
  case "$prl" in
    no) pass "ssh.root-login" "PermitRootLogin no" ;;
    prohibit-password|without-password) warn "ssh.root-login" "root key login allowed; target is no" ;;
    '') warn "ssh.root-login" "could not read PermitRootLogin" ;;
    *) fail "ssh.root-login" "PermitRootLogin ${prl}" ;;
  esac

  pwa=$(sshd_val passwordauthentication)
  if [ "$pwa" = "no" ]; then
    pass "ssh.password-auth" "PasswordAuthentication no"
  else
    fail "ssh.password-auth" "PasswordAuthentication ${pwa:-unknown}; target is no"
  fi

  pka=$(sshd_val pubkeyauthentication)
  if [ "$pka" = "yes" ]; then
    pass "ssh.pubkey-auth" "PubkeyAuthentication yes"
  else
    fail "ssh.pubkey-auth" "PubkeyAuthentication ${pka:-unknown}; target is yes"
  fi

  kbd=$(sshd_val kbdinteractiveauthentication)
  if [ "$kbd" = "no" ]; then
    pass "ssh.kbd-interactive" "KbdInteractiveAuthentication no"
  else
    warn "ssh.kbd-interactive" "KbdInteractiveAuthentication ${kbd:-unknown}; disable unless MFA is intended"
  fi

  empty=$(sshd_val permitemptypasswords)
  if [ "$empty" = "no" ]; then
    pass "ssh.empty-passwords" "PermitEmptyPasswords no"
  else
    fail "ssh.empty-passwords" "PermitEmptyPasswords ${empty:-unknown}; target is no"
  fi

  tries=$(sshd_val maxauthtries)
  if num_ge "$tries" 1 && [ "$tries" -le 4 ] 2>/dev/null; then
    pass "ssh.max-auth-tries" "MaxAuthTries $tries"
  else
    warn "ssh.max-auth-tries" "MaxAuthTries ${tries:-unknown}; target is 3-4"
  fi

  x11=$(sshd_val x11forwarding)
  if [ "$x11" = "no" ]; then
    pass "ssh.x11" "X11Forwarding no"
  else
    warn "ssh.x11" "X11Forwarding ${x11:-unknown}; disable unless needed"
  fi

  ssh_port=$(sshd_val port)
  ssh_port=${ssh_port:-22}
  socket_listen=$(systemctl show ssh.socket -p Listen --value 2>/dev/null || true)
  info "ssh.port" "sshd port=${ssh_port}${socket_listen:+; ssh.socket listen=${socket_listen}}"

  auth_keys=$(sshd_val authorizedkeysfile)
  info "ssh.authorized-keys-file" "${auth_keys:-default}"
fi

# ---------------------------------------------------------------------------
section "Firewall"
# ---------------------------------------------------------------------------

if have ufw; then
  ufw_status=$(as_root ufw status verbose 2>/dev/null || true)
  if printf '%s\n' "$ufw_status" | grep -q '^Status: active'; then
    pass "firewall.ufw" "UFW active"
    if printf '%s\n' "$ufw_status" | grep -q 'Default: deny (incoming)'; then
      pass "firewall.default" "default deny incoming"
    else
      warn "firewall.default" "default incoming policy is not deny"
    fi
    ipv6=$(grep -E '^IPV6=' /etc/default/ufw 2>/dev/null | cut -d= -f2)
    if [ "$ipv6" = "yes" ]; then
      pass "firewall.ipv6" "IPv6 managed by UFW"
    else
      warn "firewall.ipv6" "UFW IPv6 is not enabled"
    fi
    added=$(as_root ufw show added 2>/dev/null || true)
    if printf '%s\n' "$added" | grep -Eq "allow (${ssh_port}/tcp|OpenSSH)"; then
      pass "firewall.ssh" "SSH port ${ssh_port} allowed"
    else
      warn "firewall.ssh" "could not confirm an allow rule for SSH port ${ssh_port}"
    fi
    info "firewall.rules" "$(printf '%s\n' "$ufw_status" | sed -n '/^--/,$p' | tr '\n' ';' | cut -c1-300)"
  else
    fail "firewall.ufw" "UFW is not active"
  fi
else
  fail "firewall.ufw" "ufw is not installed"
fi

# ---------------------------------------------------------------------------
section "Listening ports"
# ---------------------------------------------------------------------------

if have ss; then
  listeners=$(ss -H -tuln 2>/dev/null | awk '{print $1, $5}' | sort -u)
  public_listeners=$(printf '%s\n' "$listeners" \
    | grep -E '^(tcp|udp) (0\.0\.0\.0|\*|\[::\]):' || true)
  if [ -z "$public_listeners" ]; then
    pass "ports.public" "no public wildcard listeners"
  else
    if printf '%s\n' "$public_listeners" \
      | grep -Eq ':(3306|5432|27017|6379|11211|9200|2375|2376)$'; then
      fail "ports.public" "database/admin port exposed publicly: $(printf '%s\n' "$public_listeners" | tr '\n' ';')"
    else
      warn "ports.public" "public listeners: $(printf '%s\n' "$public_listeners" | tr '\n' ';')"
    fi
  fi
  info "ports.all" "$(printf '%s\n' "$listeners" | tr '\n' ';' | cut -c1-400)"
else
  warn "ports.public" "ss not available"
fi

if have docker; then
  docker_ps=$(as_root docker ps --format '{{.Names}}	{{.Ports}}' 2>/dev/null)
  docker_rc=$?
  if [ "$docker_rc" -ne 0 ]; then
    warn "docker.containers" "Docker installed but the daemon is not reachable"
  elif [ -z "$docker_ps" ]; then
    pass "docker.containers" "Docker present; no running containers"
  else
    public_docker=$(printf '%s\n' "$docker_ps" | grep -E '0\.0\.0\.0:|\[::\]:' || true)
    if [ -z "$public_docker" ]; then
      pass "docker.ports" "running containers bind to localhost/private addresses"
    else
      warn "docker.ports" "published container ports may bypass UFW: $(printf '%s\n' "$public_docker" | tr '\n' ';')"
    fi
  fi
else
  skip "docker.containers" "Docker not installed (project layer)"
fi

# ---------------------------------------------------------------------------
section "Patching"
# ---------------------------------------------------------------------------

if have unattended-upgrade || dpkg -s unattended-upgrades >/dev/null 2>&1; then
  pass "patch.auto-upgrades" "unattended-upgrades installed"
else
  fail "patch.auto-upgrades" "unattended-upgrades is not installed"
fi

periodic=$(apt-config dump APT::Periodic::Unattended-Upgrade 2>/dev/null | tr -d '";' | awk '{print $2}')
if [ "$periodic" = "1" ]; then
  pass "patch.periodic" "APT::Periodic::Unattended-Upgrade 1"
else
  warn "patch.periodic" "automatic upgrades not enabled in apt config"
fi

if systemctl is-enabled --quiet apt-daily-upgrade.timer 2>/dev/null \
  || systemctl is-enabled --quiet unattended-upgrades.service 2>/dev/null; then
  pass "patch.timer" "automatic upgrade unit enabled"
else
  warn "patch.timer" "apt-daily-upgrade.timer is not enabled"
fi

if [ "$CHECK_APT" -eq 1 ] && have apt-get; then
  sim=$(as_root apt-get -s -o Debug::NoLocking=true upgrade 2>/dev/null || true)
  pending=$(printf '%s\n' "$sim" | grep -c '^Inst ' || true)
  pending=${pending:-0}
  security=$(printf '%s\n' "$sim" | grep '^Inst ' | grep -c 'security' || true)
  security=${security:-0}
  if [ "$security" -gt 0 ]; then
    warn "patch.security" "${security} pending security update(s), ${pending} total"
  elif [ "$pending" -gt 0 ]; then
    pass "patch.security" "no pending security updates, ${pending} non-security update(s)"
  else
    pass "patch.security" "no pending updates"
  fi
else
  skip "patch.security" "apt simulation skipped"
fi

if have needrestart; then
  pass "patch.needrestart" "needrestart installed"
else
  warn "patch.needrestart" "needrestart not installed; stale services may go unnoticed"
fi

if have pro; then
  pro_json=$(as_root pro status --format=json 2>/dev/null || true)
  if printf '%s\n' "$pro_json" | grep -q '"attached"[[:space:]]*:[[:space:]]*true'; then
    pass "patch.ubuntu-pro" "Ubuntu Pro attached"
  else
    skip "patch.ubuntu-pro" "Ubuntu Pro available but not attached (optional)"
  fi
else
  skip "patch.ubuntu-pro" "Ubuntu Pro not installed (optional)"
fi

# ---------------------------------------------------------------------------
section "Intrusion prevention"
# ---------------------------------------------------------------------------

if dpkg -s fail2ban >/dev/null 2>&1; then
  if systemctl is-active --quiet fail2ban 2>/dev/null; then
    pass "ips.fail2ban" "fail2ban active"
    jail=$(as_root fail2ban-client status sshd 2>/dev/null || true)
    if printf '%s\n' "$jail" | grep -q 'Status for the jail: sshd'; then
      banned=$(printf '%s\n' "$jail" | awk -F: '/Currently banned/ {gsub(/ /, "", $2); print $2}')
      pass "ips.sshd-jail" "sshd jail running; currently banned=${banned:-0}"
    else
      warn "ips.sshd-jail" "sshd jail not running"
    fi
  else
    fail "ips.fail2ban" "fail2ban installed but not active"
  fi
  if grep -Rqs '^ignoreip' /etc/fail2ban/jail.local /etc/fail2ban/jail.d 2>/dev/null; then
    pass "ips.ignoreip" "ignoreip configured"
  else
    warn "ips.ignoreip" "no ignoreip outside defaults; whitelist admin/VPN addresses"
  fi
else
  warn "ips.fail2ban" "fail2ban is not installed"
fi

if have cscli; then
  if systemctl is-active --quiet crowdsec 2>/dev/null; then
    skip "ips.crowdsec" "CrowdSec active (optional alternate IPS)"
  else
    warn "ips.crowdsec" "CrowdSec installed but not active"
  fi
else
  skip "ips.crowdsec" "CrowdSec not installed (optional)"
fi

# ---------------------------------------------------------------------------
section "Kernel and logging"
# ---------------------------------------------------------------------------

hardening_issues=""
for pair in \
  "kernel.dmesg_restrict:1" \
  "kernel.kptr_restrict:1" \
  "kernel.yama.ptrace_scope:1" \
  "net.ipv4.conf.all.rp_filter:1" \
  "net.ipv4.tcp_syncookies:1" \
  "fs.protected_hardlinks:1" \
  "fs.protected_symlinks:1"; do
  key=${pair%%:*}
  want=${pair##*:}
  got=$(sysctl -n "$key" 2>/dev/null || echo "")
  if ! num_ge "$got" "$want"; then
    hardening_issues="${hardening_issues}${key}=${got:-unset} "
  fi
done
if [ -z "$hardening_issues" ]; then
  pass "kernel.sysctl" "baseline sysctl values present"
else
  warn "kernel.sysctl" "missing/weak: $hardening_issues"
fi

apparmor=$(systemctl is-active apparmor 2>/dev/null || true)
if [ "$apparmor" = "active" ]; then
  pass "kernel.apparmor" "AppArmor active"
else
  warn "kernel.apparmor" "AppArmor not active"
fi

if grep -Rqs 'SystemMaxUse' /etc/systemd/journald.conf /etc/systemd/journald.conf.d 2>/dev/null; then
  pass "logging.journald" "journald size limit configured"
else
  warn "logging.journald" "no journald SystemMaxUse limit"
fi

# ---------------------------------------------------------------------------
section "Generic tools"
# ---------------------------------------------------------------------------

missing=""
for cmd in curl wget git jq htop tmux rsync ncdu unzip tree; do
  have "$cmd" || missing="$missing $cmd"
done
if [ -z "$missing" ]; then
  pass "tools.basic" "basic administration tools installed"
else
  warn "tools.basic" "missing:${missing}"
fi

audit_missing=""
for cmd in lynis ssh-audit; do
  have "$cmd" || audit_missing="$audit_missing $cmd"
done
if [ -z "$audit_missing" ]; then
  pass "tools.audit" "lynis and ssh-audit installed"
else
  warn "tools.audit" "missing:${audit_missing}"
fi

# ---------------------------------------------------------------------------
printf '\n== SUMMARY ==\n'
printf 'PASS=%d WARN=%d FAIL=%d SKIP=%d\n' "$PASS" "$WARN" "$FAIL" "$SKIP"
if [ "$FAIL" -gt 0 ]; then
  verdict="blocked"
elif [ "$WARN" -gt 0 ]; then
  verdict="ready-with-warnings"
else
  verdict="baseline-ready"
fi
printf 'VERDICT: %s\n' "$verdict"

if [ "$STRICT" -eq 1 ]; then
  if [ "$FAIL" -gt 0 ]; then
    exit 2
  fi
  if [ "$WARN" -gt 0 ]; then
    exit 1
  fi
fi
exit 0

#!/usr/bin/env bash
# ufw-baseline.sh — idempotent UFW baseline for an Ubuntu VPS.
#
# Usage:
#   sudo bash ufw-baseline.sh [--ssh-port 22] [--web]
#
# Defaults:
#   - deny incoming, allow outgoing
#   - allow SSH only
#   - open 80/443 only with --web
#
# This script only adds rules. It never disables UFW or removes existing rules.
# Keep the current SSH session open and verify a second session after running.

set -euo pipefail

SSH_PORT=22
WEB=0

usage() {
  cat <<'EOF'
Usage: sudo bash ufw-baseline.sh [--ssh-port PORT] [--web]

  --ssh-port PORT  SSH port to allow (default: 22)
  --web            Also allow 80/tcp and 443/tcp
  -h, --help       Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --ssh-port)
      [ "$#" -ge 2 ] || { echo "Missing value for --ssh-port" >&2; exit 64; }
      SSH_PORT=$2
      shift 2
      ;;
    --web) WEB=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

if ! command -v ufw >/dev/null 2>&1; then
  echo "ufw is not installed. Install it first: apt-get install -y ufw" >&2
  exit 1
fi

case "$SSH_PORT" in
  ''|*[!0-9]*) echo "SSH port must be numeric: $SSH_PORT" >&2; exit 64 ;;
esac
if [ "$SSH_PORT" -lt 1 ] || [ "$SSH_PORT" -gt 65535 ]; then
  echo "SSH port out of range: $SSH_PORT" >&2
  exit 64
fi

if ! systemctl is-active --quiet ssh 2>/dev/null \
  && ! systemctl is-active --quiet ssh.socket 2>/dev/null; then
  echo "Warning: ssh.service and ssh.socket are not active." >&2
  echo "Confirm SSH is running before enabling the firewall." >&2
fi

echo "Applying UFW baseline (SSH port ${SSH_PORT}, web=${WEB})"
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}/tcp" comment 'ssh'

if [ "$WEB" -eq 1 ]; then
  ufw allow 80/tcp comment 'http'
  ufw allow 443/tcp comment 'https'
fi

ufw --force enable
ufw status verbose

echo
if ufw status | grep -Eq "^${SSH_PORT}/tcp[[:space:]]+ALLOW"; then
  echo "OK: SSH port ${SSH_PORT} is allowed."
else
  echo "WARN: could not confirm an allow rule for port ${SSH_PORT}." >&2
  echo "Open another session or the provider console before closing this one." >&2
fi

echo
echo "Next: verify a second SSH session, then check the provider firewall."
echo "If you changed ports, remove the old allow rule only after verification."

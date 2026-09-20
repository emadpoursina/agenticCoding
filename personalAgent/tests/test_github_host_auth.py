"""Verified github.com host keys and compose auth wiring (no live network)."""

from __future__ import annotations

import subprocess
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
KNOWN_HOSTS = PACKAGE_ROOT / "docker" / "ssh" / "github_known_hosts"
GITHUB_SSH_CONF = PACKAGE_ROOT / "docker" / "ssh" / "github.conf"
COMPOSE = PACKAGE_ROOT / "docker-compose.yml"
DOCKERFILE = PACKAGE_ROOT / "docker" / "Dockerfile"
INIT = PACKAGE_ROOT / "docker" / "cont-init.d" / "90-ssh-agent-access.sh"

# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
EXPECTED_FINGERPRINTS = {
    "SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s",
    "SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM",
    "SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU",
}


def test_github_known_hosts_match_published_fingerprints() -> None:
    listed = subprocess.run(
        ["ssh-keygen", "-lf", str(KNOWN_HOSTS)],
        check=True,
        capture_output=True,
        text=True,
    )
    found = {line.split()[1] for line in listed.stdout.splitlines() if line.strip()}
    assert found == EXPECTED_FINGERPRINTS
    text = KNOWN_HOSTS.read_text(encoding="utf-8")
    assert "github.com ssh-ed25519" in text
    assert "ssh-keyscan" not in text
    assert "accept-new" not in text


def test_compose_and_boot_pass_runtime_gh_token_and_verified_hosts() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    init = INIT.read_text(encoding="utf-8")
    ssh_conf = GITHUB_SSH_CONF.read_text(encoding="utf-8")
    assert "GH_TOKEN=${GH_TOKEN:-}" in compose
    assert "GH_CONFIG_DIR=/opt/data/.config/gh" in compose
    assert "COPY docker/ssh/github_known_hosts /etc/ssh/ssh_known_hosts" in dockerfile
    assert "ssh-keyscan" not in compose
    assert "ssh-keyscan" not in dockerfile
    assert "accept-new" not in compose
    assert "github_known_hosts" in init
    assert "gh auth login" in init
    assert "--with-token" in init
    assert "ssh-keyscan" not in init
    assert "accept-new" not in init
    assert "StrictHostKeyChecking yes" in ssh_conf
    assert "accept-new" not in ssh_conf

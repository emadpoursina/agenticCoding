#!/command/with-contenv sh
# Boot-time provisioning for live GitHub delivery (runs once per container
# start, as root, with the container environment).
#
# SSH agent socket: the bind-mounted host agent socket is often owned by
# root with 0600/0640 mode, so the unprivileged hermes user cannot reach it.
# Making it group/world readable is safe: it grants access to an
# authentication broker, not to any key material.

set -eu

if [ -S "${SSH_AUTH_SOCK:-}" ]; then
    chmod 0666 "$SSH_AUTH_SOCK" 2>/dev/null || true
fi

if [ -S /ssh-agent ]; then
    chmod 0666 /ssh-agent 2>/dev/null || true
fi

KNOWN_HOSTS_SRC=""
for candidate in \
    /opt/personal-agent/docker/ssh/github_known_hosts \
    /etc/ssh/github_known_hosts
do
    if [ -f "$candidate" ]; then
        KNOWN_HOSTS_SRC="$candidate"
        break
    fi
done

install_known_hosts() {
    dest_dir=$1
    dest="$dest_dir/known_hosts"
    mkdir -p "$dest_dir"
    cp "$KNOWN_HOSTS_SRC" "$dest"
    chmod 0644 "$dest"
    chown hermes:hermes "$dest_dir" "$dest" 2>/dev/null || true
}

if [ -n "$KNOWN_HOSTS_SRC" ]; then
    if [ ! -f /etc/ssh/ssh_known_hosts ]; then
        mkdir -p /etc/ssh
        cp "$KNOWN_HOSTS_SRC" /etc/ssh/ssh_known_hosts
        chmod 0644 /etc/ssh/ssh_known_hosts
    fi
    install_known_hosts /home/hermes/.ssh
    install_known_hosts /opt/data/.ssh
fi

GH_CONFIG_DIR="${GH_CONFIG_DIR:-/opt/data/.config/gh}"
export GH_CONFIG_DIR
mkdir -p "$GH_CONFIG_DIR"
chown hermes:hermes "$GH_CONFIG_DIR" 2>/dev/null || true

# Named overlay volume is seeded root:root; the worker is unprivileged hermes.
mkdir -p /var/lib/hermes-kanban
chown -R hermes:hermes /var/lib/hermes-kanban

# Keep Pi's image defaults readable while its session store stays writable.
PI_IMAGE_AGENT_DIR=/opt/pi-agent
PI_STORE_DIR="${PI_CODING_AGENT_DIR:-/opt/data/pi-agent}"
mkdir -p "$PI_STORE_DIR"
if [ "$PI_STORE_DIR" != "$PI_IMAGE_AGENT_DIR" ] && [ ! -s "$PI_STORE_DIR/models.json" ]; then
    cp "$PI_IMAGE_AGENT_DIR/models.json" "$PI_STORE_DIR/models.json"
fi
chown -R hermes:hermes "$PI_STORE_DIR"

if [ -n "${GH_TOKEN:-}" ] && command -v gh >/dev/null 2>&1; then
    if ! printf '%s' "$GH_TOKEN" | su -s /bin/sh hermes \
        -c "GH_CONFIG_DIR='$GH_CONFIG_DIR' env -u GH_TOKEN gh auth login --hostname github.com --with-token"
    then
        echo "gh auth login from GH_TOKEN failed (container continues)"
    fi
fi

# Rebuild hermes-agent:local from one consistent official Hermes image.
# Do not docker-commit a running container onto a mixed tree.
FROM nousresearch/hermes-agent:latest

USER root
ARG PI_RUNTIME_VERSION=1.0.0
ENV HERMES_PI_RUNTIME=/opt/pi-runtime
ENV PI_RUNTIME_VERSION=${PI_RUNTIME_VERSION}
ENV PI_CODING_AGENT_DIR=/opt/data/pi-agent
RUN apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && mkdir -p /etc/ssh/ssh_config.d \
    && rm -rf /var/lib/apt/lists/*
RUN npm install --global --prefix /opt/pi @earendil-works/pi-coding-agent@0.84.3
COPY docker/pi-runtime/manifest.json /opt/pi-runtime/manifest.json
COPY docker/pi-runtime/pi /opt/pi-runtime/pi
COPY docker/pi-runtime/models.json /opt/pi-agent/models.json
RUN test -s /opt/pi-runtime/manifest.json \
    && test -x /opt/pi-runtime/pi \
    && test -s /opt/pi-agent/models.json \
    && ln -sf /opt/pi-runtime/pi /usr/local/bin/pi \
    && chmod -R a-w /opt/pi-runtime
COPY docker/cont-init.d/90-ssh-agent-access.sh /etc/cont-init.d/90-ssh-agent-access.sh
COPY docker/ssh/github_known_hosts /etc/ssh/github_known_hosts
COPY docker/ssh/github_known_hosts /etc/ssh/ssh_known_hosts
COPY docker/ssh/github.conf /etc/ssh/ssh_config.d/github.conf
RUN chmod +x /etc/cont-init.d/90-ssh-agent-access.sh \
    && chmod 0644 /etc/ssh/github_known_hosts /etc/ssh/ssh_known_hosts /etc/ssh/ssh_config.d/github.conf

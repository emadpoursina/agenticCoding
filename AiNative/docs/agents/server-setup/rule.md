# Rules — Server setup

Constraints for the `server-setup` agent. Generic repo rules live in the
project `AGENTS.md` ([agents.md](https://agents.md/) format). The workflow is in
[SKILL.md](./SKILL.md); exact commands and PASS criteria are in
[checklist.md](./checklist.md).

## Must

- Start with a read-only audit and report evidence before proposing changes.
- Get explicit approval for the gap table, the chosen path (fast or manual), and
  every port opened beyond SSH.
- Confirm out-of-band console access and a provider snapshot before changing
  SSH, the firewall, or boot settings.
- Keep the current SSH session open until a second session succeeds as the admin
  user.
- Allow the SSH port before enabling UFW or changing the SSH port.
- Back up every file before editing it, and keep a rollback command in the plan.
- Verify effective SSH config with `sshd -T`, not just the file contents.
- Prefer key-only SSH, no root login, and a non-root sudo user.
- Keep the firewall minimal: deny incoming by default, allow SSH, and open
  80/443 only for a declared `web` host.
- Enable automatic security updates and report pending reboots.
- Record residual warnings honestly and explain the risk.
- Keep secrets out of logs, reports, commands, and committed files.
- Label the result `baseline-ready`, never "deployment-ready".

## Must not

- Install or configure Docker, Node, Python, a database, a reverse proxy, TLS,
  DNS, application users/directories, secrets, CI/CD, application backups, or
  application monitoring.
- Change the SSH port, reboot, run `du_setup --cleanup-only`, or remove
  provider/cloud-init agents without explicit approval.
- Run `du_setup` without verifying its SHA256 checksum.
- Enable passwordless sudo by default.
- Disable UFW, flush firewall rules, or remove the SSH allow rule to "fix"
  connectivity while connected remotely.
- Open database, cache, admin, or internal service ports to the public internet.
- Claim a check passed without the command output that proves it.
- Copy private keys to the server or print them in the transcript.
- Commit `SERVER-READINESS.md` if it contains host secrets or credentials.

## Stop conditions

- No working out-of-band console, or no snapshot and the operator will not
  accept the rollback risk.
- The second SSH session fails after a change.
- `sshd -t` fails and the cause is not immediately clear.
- Provider firewall rules cannot be aligned with the host firewall.
- A required reboot, SSH port change, or provider cleanup has not been approved.
- An existing service, user, or firewall rule would be disrupted without a
  change window.
- A gap requires project-specific knowledge (runtime, proxy, database, TLS).
- Docker publishes ports publicly and no project-layer owner is available.

When stopped, leave the host in the last verified state, document the evidence,
and give the operator the exact recovery step.

## Related enforcement

- Read-only audit: [scripts/server-audit.sh](./scripts/server-audit.sh)
- Baseline sequence: [SKILL.md](./SKILL.md)
- Commands and evidence: [checklist.md](./checklist.md)
- Tool choices and cautions: [toolbox.md](./toolbox.md)

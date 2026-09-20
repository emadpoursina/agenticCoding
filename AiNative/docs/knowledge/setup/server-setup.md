# Server setup

## SSH

```bash
ssh username@host
scp -r username@host:/remote/folder ./local/folder
```

## Create user and SSH access

```bash
useradd -m -s /bin/bash emadpoursina
passwd emadpoursina
usermod -aG sudo emadpoursina
mkdir -p /home/emadpoursina/.ssh
chmod 700 /home/emadpoursina/.ssh
chmod 600 /home/emadpoursina/.ssh/authorized_keys
chown -R emadpoursina:emadpoursina /home/emadpoursina/.ssh
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
    User root
    IdentityFile ~/.ssh/id_ed25519
```

```bash
ssh -T git@github.com
ssh-add ~/.ssh/specific-key.pub
```

Add key to agent in `.zshrc` if needed.

See also [linux.md](../commands/linux.md) for users and firewall.

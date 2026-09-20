# Linux commands

## Users

- Change to sudo user: `sudo -i`
- Change to other users: `sudo -iu <username>`
- List all users: `awk -F: '$3 >= 1000 && $1 != "nobody" {print $1 "\t" $6 "\t" $7}' /etc/passwd`

## jq — JSON terminal formatter

```bash
jq . < ugly.json
curl https://api.github.com | jq .
```

## ufw

```bash
ufw status
```

## Disk usage

```bash
df -h
```

## Utility

- ja — json formatter
- htop

## Network

```bash
ping domain
nc -zvw5 <host-or-ip> <port-number>
curl -X POST -H "Content-Type: application/json" --json '{"key": "value", "number": 123}'
```

See [server-setup.md](../setup/server-setup.md) for SSH.

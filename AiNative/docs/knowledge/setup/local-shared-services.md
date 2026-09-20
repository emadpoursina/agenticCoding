# Local shared services

Machine-wide databases and admin UIs run in Docker — one compose file, shared across all local projects.

## Canonical location

```text
/Users/emad/docker-infrastructure/docker-compose.yml
```

Snippet copy (for reference only — edit the canonical file): [shared-services.yml](../../knowledge/snippets/docker-compose/shared-services.yml)

## Services

| Service | Container | Host port | Notes |
|---------|-----------|-----------|-------|
| MariaDB 10.11 | `shared_mariadb` | 3306 | MySQL-compatible |
| MongoDB 7 | `shared_mongodb` | 27017 | |
| Redis 7 | `shared_redis` | 6379 | |
| Adminer | `shared_adminer` | 8081 | DB UI — http://localhost:8081 |
| Nginx | `shared_nginx` | 80 | Reverse proxy — configs in `~/docker-infrastructure/nginx/` |

Data persists in Docker volumes: `mariadb_data`, `mongodb_data`, `redis_data`.

## Lifecycle

```bash
cd /Users/emad/docker-infrastructure

docker compose up -d          # start all
docker compose ps             # status
docker compose logs -f        # follow logs
docker compose stop           # stop (keep data)
docker compose down           # stop and remove containers (volumes kept)
docker compose pull && docker compose up -d   # upgrade images
```

See [docker.md](../commands/docker.md) for general Docker commands.

## Connection strings

Local dev only — not for production.

**MariaDB**

```text
Host:     localhost
Port:     3306
User:     root
Password: rootpass
```

```text
mysql://root:rootpass@localhost:3306/<database>
```

**MongoDB**

```text
mongodb://root:rootpass@localhost:27017/?authSource=admin
```

**Redis**

```text
Host: localhost
Port: 6379
```

```text
redis://localhost:6379
```

**Adminer**

Open http://localhost:8081 — default server is `mariadb` (set in compose). For MongoDB, use a Mongo client or `mongosh` instead.

**Nginx**

Configs live in `/Users/emad/docker-infrastructure/nginx/` (mounted into the container). `00-default.conf` handles bare `http://localhost` — it does **not** proxy to any project. Each project gets its own `server_name`:

| Hostname | Upstream port | Config file |
|----------|---------------|-------------|
| `nml.localhost` | 3000 | `mac.conf` |
| `moss.localhost` | 3002 | `mac.conf` |
| `villionadmin.localhost` | 3009 | `mac.conf` |
| `voicedash.localhost` | 3001 | `mac.conf` |
| `taskforge.localhost` | 3003 | `taskforge.conf` |
| `api.taskforge.localhost` | 3004 | `taskforge.conf` |

Open projects at `http://<hostname>` (e.g. http://nml.localhost). Modern browsers resolve `*.localhost` to 127.0.0.1; add `/etc/hosts` entries only if a name does not resolve.

Proxy upstreams must use `host.docker.internal`, not `127.0.0.1` — inside Docker, localhost is the container, not your Mac.

If port 80 is already in use on the Mac, stop the conflicting service or change the compose mapping (e.g. back to `"8080:80"`).

```bash
# Bare localhost → 404 (no project)
curl http://localhost/

# Project vhost
curl http://nml.localhost/

# Validate and reload after editing configs
docker exec shared_nginx nginx -t
docker exec shared_nginx nginx -s reload
```

See [nginx.md](../commands/nginx.md) for log paths.

## Project setup

Point app `.env` files at `localhost` and the ports above. Create per-project databases inside the shared instances rather than spinning up new containers per repo. For MongoDB provisioning (database, user, roles), see [mongodb.md](../commands/mongodb.md).

When starting a new project, link here from [new-project.md](./new-project.md) database setup.

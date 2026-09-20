# Nginx

Shared local reverse proxy: `shared_nginx` on host port **80**. Configs: `/Users/emad/docker-infrastructure/nginx/`. Setup: [local-shared-services.md](../setup/local-shared-services.md).

## Docker proxy rule

When nginx runs in Docker and proxies to apps on the Mac host, use `host.docker.internal` in `proxy_pass` / `upstream` — not `127.0.0.1`.

## Logs

Inside the container:

- `/var/log/nginx/access.log`
- `/var/log/nginx/error.log`

```bash
docker exec shared_nginx tail -f /var/log/nginx/error.log
docker compose -f ~/docker-infrastructure/docker-compose.yml logs -f nginx
```

## Quick test

```bash
docker exec shared_nginx nginx -t
curl -H "Host: <server_name>" http://localhost/
```

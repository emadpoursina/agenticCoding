# Docker

Configure docker with log limit files.

## Commands

```bash
docker ps [-as]
docker images
docker rm [container]
docker rmi [image]
docker container ls -a
docker container prune
docker run -it --rm -p hostP:containerP --name name -v hostPath:containerPath --network network [image]
docker exec [-it] [container] [cmd]
docker start/stop/restart [container]
docker volume create [name]
docker volume ls
docker build -t tagName:vN [dockerFilePath]
docker network create [name]
docker network ls
docker system df [-v]
```

## Dockerfile basics

- `FROM [image]`
- `COPY`
- `RUN`

## Docker Compose (shared services)

Local machine databases run from a single compose file — see [local-shared-services.md](../setup/local-shared-services.md).

```bash
cd /Users/emad/docker-infrastructure
docker compose up -d
docker compose ps
docker compose logs -f [service]
docker compose stop
docker compose down
```

## Dockerizing a project section

1. Choose a base image
2. Dockerize backend/database/front-end(s)
3. Presenting data

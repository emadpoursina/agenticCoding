# Postgres

- UI: pgadmin
- Command line: psql
- Port: 5432
- Data folder: `/var/lib/postgresql/data`
- Docker: always set resource limits

## Initialize / restore

```bash
psql -h HOST -p 5432 -U postgres -d db -f /path/to/backup.sql
```

## Create db and owner

```text
postgresql://USER:PASSWORD@HOST:5432/postgres
```

```sql
CREATE ROLE username WITH LOGIN PASSWORD 'strong_password';
CREATE DATABASE username OWNER username;
GRANT ALL PRIVILEGES ON DATABASE username TO test;
ALTER USER username WITH CREATEDB;
```

## Interactive

- `\l` — list databases
- `\dt` — list tables
- `\c db` — connect
- `DROP DATABASE database_name;`
- `DROP USER username;`

## Backup and restore

```bash
pg_dump -h host -p port -U user -d db > backup.sql
pg_dump -h host -p port -U user -d db -Fc > backupfile.dump
pg_restore -h host -p port -U user -d db ./path/to/backup
```

See [backup-system.md](../backup-system.md).

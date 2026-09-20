# MongoDB

- Command line: `mongosh`
- Port: `27017`
- Data folder: `/data/db`

## Create database and user

Use an admin account to create the database first, then add a dedicated application user. MongoDB only persists a database after the first write — `use` alone is not enough.

Replace `myapp`, `myapp_user`, `strong_password`, and `HOST` with your values. For local shared Docker MongoDB, see [local-shared-services.md](../setup/local-shared-services.md) (`HOST=localhost`, admin user `root`).

**1. Connect as admin**

```bash
mongosh "mongodb://ADMIN_USER:ADMIN_PASSWORD@HOST:27017/?authSource=admin"
```

**2. Create the database**

Switch context, then create a collection so the database is stored on disk:

```javascript
use myapp
db.createCollection("_init")
```

Confirm it exists:

```javascript
show dbs   // myapp appears (size may be small until the app writes data)
```

**3. Create the user with full access to that database**

Stay in the same `use myapp` context (or run `use myapp` again):

`dbOwner` is the database-scoped owner role (read/write, indexes, collections, and user admin on this database only):

```javascript
db.createUser({
  user: "myapp_user",
  pwd: "strong_password",
  roles: [{ role: "dbOwner", db: "myapp" }],
})
```

**4. Verify the new user can connect**

Exit `mongosh`, then connect as the project user:

```bash
mongosh "mongodb://myapp_user:strong_password@HOST:27017/myapp?authSource=myapp"
```

```javascript
show dbs
db.runCommand({ connectionStatus: 1 })
```

**5. Application connection string**

```text
mongodb://myapp_user:strong_password@HOST:27017/myapp?authSource=myapp
```

`authSource=myapp` must match the database where the user was created (steps 2–3).

## Change admin password

**When you know the current password**

```bash
mongosh "mongodb://ADMIN_USER:ADMIN_PASSWORD@HOST:27017/?authSource=admin"
```

```javascript
use admin
db.changeUserPassword("ADMIN_USER", "new_password")
```

**When the password is lost**

`MONGO_INITDB_ROOT_`* (and similar init env vars) only apply on first startup with an empty data directory — changing them later does not reset an existing password.

1. Stop MongoDB.
2. Start `mongod` temporarily with auth disabled, using the same data directory:

```bash
mongod --dbpath /data/db --noauth --bind_ip 127.0.0.1
```

1. In another session, connect without credentials and reset the admin user:

```bash
mongosh "mongodb://HOST:27017/admin"
```

```javascript
db.changeUserPassword("ADMIN_USER", "new_password")
```

1. Stop the temporary instance and start MongoDB normally with auth enabled.

On Docker, mount the same data volume on a one-off container with `mongod --noauth` (use a different host port if the main container still holds `27017`).

## Interactive

- `show dbs` — list databases
- `show collections` — list collections in current database
- `use myapp` — switch database
- `show users` — users for current database
- `db.dropUser("myapp_user")` — remove user (admin or dbOwner in the same `use` context)
- `db.dropDatabase()` — drop current database (admin or dbOwner)

## Backup and restore

```bash
mongosh
mongodump --host HOST --username username --password your_password --db dbName
mongodump --uri "mongodb://username:password@HOST:27017/?authSource=admin" --out ./backup --gzip --archive
mongorestore --uri="mongodb://username:password@HOST:27017" --host HOST --port 27017 --username user --password pass --db mydb --gzip --archive=file.archive ./backup
```

## Namespace filtering and rename (`mongorestore`)

A namespace is `database.collection`. Patterns accept `*` wildcards. Repeat `--nsInclude` or `--nsExclude` to match multiple patterns. If both are set, `--nsExclude` wins (e.g. `--nsExclude="prod.*"` with `--nsInclude="prod.trips"` restores nothing from `prod`).


| Option                | Purpose                                         |
| --------------------- | ----------------------------------------------- |
| `--nsInclude`         | Restore only namespaces that match              |
| `--nsExclude`         | Skip namespaces that match                      |
| `--nsFrom` / `--nsTo` | Rename namespaces during restore (use together) |


```bash
# One collection
mongorestore --nsInclude=test.purchaseorders dump/

# Whole database
mongorestore --nsInclude=transactions.* dump/

# Database minus dev collections
mongorestore --nsInclude='transactions.*' --nsExclude='transactions.*_dev' dump/

# Rename database on restore (archive or dump dir)
mongorestore --archive=mongodump-test-db --nsFrom="test.*" --nsTo="examples.*"
mongorestore --host HOST --nsFrom="test.*" --nsTo="mongorestore.*" dump/

# Rename with captured segments ($name$); escape literal * and \ with \
mongorestore --nsInclude='data.*' --nsFrom='data.$prefix$_$customer$' --nsTo='$customer$.$prefix$' dump/
```

Works with `--archive` and `--gzip`. Prefer `--nsInclude` over deprecated `--db` / `--collection` when restoring from a dump directory or archive.
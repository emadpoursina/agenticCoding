# Backup system

## Notes

- Backup outside of server
  - Amazon S3
  - Dropbox
  - Google Drive

## Three questions a real backup answers

1. Can I restore quickly? (not just store)
2. Is it automatic? (no human memory involved)
3. Is it safe from failure? (server crash, human mistake, hacking)

## Routine

### Restoring drill

1. Take a backup
2. Delete your local DB
3. Restore it

## Practices

- Backup versioning
- Encryption
- CI/CD backup integration
- Monitoring — notification on failed backup

## Types

### Code backup

- Git + Github/Gitlab
- Daily push
- Branch strategy

### Database backup

- Daily automatic dump
- Stored outside your server
- Use dump command-line tools

### Server full backup

- uploads (images, files)
- configs
- environment

## Rclone

```bash
rclone listremotes
rclone config delete {remote name}
```

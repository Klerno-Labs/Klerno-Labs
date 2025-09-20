# Klerno Labs Backup & Disaster Recovery

## Overview

This document describes the backup and disaster recovery system for Klerno Labs, including:

- Automated backup of PostgreSQL, Redis, file data, and configuration
- Restore procedures
- Scheduling and retention best practices

## Backup Script Usage

Run the backup script inside the production container or host:

```sh
bash deployment/backup.sh
```

- Output: `/app/backups/backup_<timestamp>.tar.gz`
- Includes: PostgreSQL SQL dump, Redis RDB, data, logs, uploads, .env, policy.yaml, tagging.yaml

## Restore Script Usage

To restore from a backup archive:

```sh
bash deployment/restore.sh /app/backups/backup_<timestamp>.tar.gz
```

- Restores database, cache, files, and configs
- Requires correct `POSTGRES_PASSWORD` and `REDIS_PASSWORD` environment variables

## Scheduling Backups

- Use cron or Docker scheduled jobs to run `backup.sh` daily
- Store backup archives offsite (cloud, S3, etc.) for disaster recovery
- Retain at least 7 daily and 4 weekly backups

## Testing Recovery

- Regularly test restore process in a staging environment
- Validate application health and data integrity after restore

## Security

- Restrict access to backup archives
- Encrypt backups at rest and in transit if storing offsite

## Troubleshooting

- Check logs in `/app/logs` and backup script output for errors
- Ensure database and Redis containers are running during backup/restore

---
For questions, contact the DevOps team.

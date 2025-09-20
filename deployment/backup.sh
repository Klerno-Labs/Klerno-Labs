#!/bin/bash
# Automated backup script for Klerno Labs production
# Backs up PostgreSQL, Redis, file data, and configuration

set -e

BACKUP_DIR="/app/backups/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
if [ -n "$POSTGRES_PASSWORD" ]; then
  echo "[INFO] Backing up PostgreSQL database..."
  PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h postgres -U klerno klerno_labs > "$BACKUP_DIR/postgres.sql"
else
  echo "[WARN] POSTGRES_PASSWORD not set, skipping Postgres backup."
fi

# Redis backup
if [ -n "$REDIS_PASSWORD" ]; then
  echo "[INFO] Backing up Redis..."
  redis-cli -h redis -a "$REDIS_PASSWORD" save
  cp /data/dump.rdb "$BACKUP_DIR/redis.rdb"
else
  echo "[WARN] REDIS_PASSWORD not set, skipping Redis backup."
fi

# File and config backup
echo "[INFO] Backing up file data and configs..."
cp -r /app/data "$BACKUP_DIR/data"
cp -r /app/logs "$BACKUP_DIR/logs"
cp -r /app/uploads "$BACKUP_DIR/uploads"
cp /app/.env "$BACKUP_DIR/.env.bak" || true
cp /app/policy.yaml "$BACKUP_DIR/policy.yaml.bak" || true
cp /app/tagging.yaml "$BACKUP_DIR/tagging.yaml.bak" || true

# Archive everything
tar -czf "/app/backups/backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz" -C "$BACKUP_DIR" .

# Cleanup
rm -rf "$BACKUP_DIR"
echo "[SUCCESS] Backup complete: /app/backups/backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"

#!/bin/bash
# Automated restore script for Klerno Labs production
# Restores PostgreSQL, Redis, file data, and configuration from backup archive

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-archive.tar.gz>"
  exit 1
fi

ARCHIVE="$1"
RESTORE_DIR="/app/restore_tmp"

mkdir -p "$RESTORE_DIR"
tar -xzf "$ARCHIVE" -C "$RESTORE_DIR"

# PostgreSQL restore
if [ -f "$RESTORE_DIR/postgres.sql" ] && [ -n "$POSTGRES_PASSWORD" ]; then
  echo "[INFO] Restoring PostgreSQL database..."
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U klerno klerno_labs < "$RESTORE_DIR/postgres.sql"
else
  echo "[WARN] Postgres SQL dump not found or POSTGRES_PASSWORD not set, skipping Postgres restore."
fi

# Redis restore
if [ -f "$RESTORE_DIR/redis.rdb" ] && [ -n "$REDIS_PASSWORD" ]; then
  echo "[INFO] Restoring Redis..."
  cp "$RESTORE_DIR/redis.rdb" /data/dump.rdb
  redis-cli -h redis -a "$REDIS_PASSWORD" shutdown nosave
  redis-server --daemonize yes
else
  echo "[WARN] Redis RDB not found or REDIS_PASSWORD not set, skipping Redis restore."
fi

# File and config restore
echo "[INFO] Restoring file data and configs..."
cp -r "$RESTORE_DIR/data" /app/data || true
cp -r "$RESTORE_DIR/logs" /app/logs || true
cp -r "$RESTORE_DIR/uploads" /app/uploads || true
cp "$RESTORE_DIR/.env.bak" /app/.env || true
cp "$RESTORE_DIR/policy.yaml.bak" /app/policy.yaml || true
cp "$RESTORE_DIR/tagging.yaml.bak" /app/tagging.yaml || true

# Cleanup
rm -rf "$RESTORE_DIR"
echo "[SUCCESS] Restore complete."

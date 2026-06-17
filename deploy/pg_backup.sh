#!/usr/bin/env bash
# MuseAI PostgreSQL backup.
#
# Usage:
#   BACKUP_DIR=/var/backups/museai ./pg_backup.sh
#
# Connection resolution order (no passwords are hardcoded here):
#   1. PG_CONTAINER  — name of the docker compose PostgreSQL container;
#                      pg_dump runs inside it with the container's own auth.
#   2. DATABASE_URL  — SQLAlchemy-style URL from backend/.env; the async
#                      driver suffix (+asyncpg) is stripped for pg_dump.
#   3. libpq env     — PGHOST/PGPORT/PGUSER/PGPASSWORD or ~/.pgpass.
#
# Env vars:
#   BACKUP_DIR      target directory (default /var/backups/museai)
#   RETENTION_DAYS  days to keep old dumps (default 7)
#   DB_NAME         database name (default museai)
#   PG_CONTAINER    optional docker container name
#
# Exits non-zero on any failure; prints the backup file path on success.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/museai}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_NAME="${DB_NAME:-museai}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/museai_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

if [ -n "${PG_CONTAINER:-}" ]; then
    docker exec "$PG_CONTAINER" pg_dump --no-owner -U "${PGUSER:-postgres}" "$DB_NAME" | gzip > "$OUT_FILE"
elif [ -n "${DATABASE_URL:-}" ]; then
    PG_URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql://}"
    PG_URL="${PG_URL/postgres+asyncpg:\/\//postgresql://}"
    pg_dump --no-owner "$PG_URL" | gzip > "$OUT_FILE"
else
    pg_dump --no-owner "$DB_NAME" | gzip > "$OUT_FILE"
fi

# A failed pg_dump aborts above via pipefail; also reject empty output.
if [ ! -s "$OUT_FILE" ]; then
    echo "ERROR: backup file is empty: $OUT_FILE" >&2
    rm -f "$OUT_FILE"
    exit 1
fi

echo "backup written: $OUT_FILE"

find "$BACKUP_DIR" -name 'museai_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

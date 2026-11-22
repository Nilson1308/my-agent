#!/usr/bin/env bash
# Backup lógico PostgreSQL do stack my-agent (pg_dump via container db).
# Uso: ./deploy/backup-pgdata.sh
# Cron exemplo (02:15 diário): 15 2 * * * cd /var/www/my-projects/my-agent && ./deploy/backup-pgdata.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
COMPOSE=(docker-compose -p my-agent -f docker-compose.prod.yml)
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

source "$ROOT/.env" 2>/dev/null || true
DB_NAME="${POSTGRES_DB:-my_agent}"
DB_USER="${POSTGRES_USER:-my_agent}"
OUT="$BACKUP_DIR/${DB_NAME}_${STAMP}.sql.gz"

echo "==> Backup → $OUT"
"${COMPOSE[@]}" exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip -9 >"$OUT"
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +14 -delete 2>/dev/null || true
echo "OK ($(du -h "$OUT" | awk '{print $1}'))"
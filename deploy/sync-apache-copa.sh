#!/usr/bin/env bash
# Sincroniza vhost COPA (inclui Alias /app para o PWA) e recarrega Apache se possível.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/deploy/apache/copa.mogidascruzes.sp.gov.br.conf"
DST="/etc/apache2/sites-available/copa.conf"

if [[ ! -f "$SRC" ]]; then
  echo "Arquivo ausente: $SRC" >&2
  exit 1
fi

cp "$SRC" "$DST"
echo "OK: $DST atualizado (Alias /app → pwa/dist)"

if apache2ctl -t 2>/dev/null; then
  if command -v systemctl >/dev/null; then
  systemctl reload apache2 2>/dev/null || sudo systemctl reload apache2
  else
    service apache2 reload 2>/dev/null || sudo service apache2 reload
  fi
  echo "Apache recarregado."
else
  echo "apache2ctl -t falhou (ex.: outro vhost SSL); conf do COPA foi copiada." >&2
  echo "Recarregue manualmente: sudo systemctl reload apache2" >&2
  exit 1
fi
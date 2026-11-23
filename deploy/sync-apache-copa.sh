#!/usr/bin/env bash
# Sincroniza vhost COPA (inclui Alias /app para o PWA) e recarrega Apache.
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

# Neste servidor, apache2ctl -t só é confiável com sudo (SSL/certs sob /etc/ssl).
if sudo apache2ctl -t; then
  sudo systemctl reload apache2
  echo "Apache recarregado."
else
  echo "apache2ctl -t falhou; conf do COPA foi copiada." >&2
  echo "Corrija o vhost e rode: sudo systemctl reload apache2" >&2
  exit 1
fi
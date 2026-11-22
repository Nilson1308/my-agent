#!/usr/bin/env bash
# Substitui vhost COPA (gestão estoque legado) pelo proxy my-agent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONF_SRC="${ROOT}/deploy/apache/copa.mogidascruzes.sp.gov.br.conf"
CONF_DST="/etc/apache2/sites-available/copa.conf"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Execute: sudo $0"
  exit 1
fi

a2enmod proxy proxy_http headers rewrite >/dev/null 2>&1 || true
cp -a "$CONF_SRC" "$CONF_DST"
a2ensite copa.conf >/dev/null 2>&1 || true
apache2ctl configtest
systemctl reload apache2
echo "Apache: copa.mogidascruzes.sp.gov.br → 127.0.0.1:8045"
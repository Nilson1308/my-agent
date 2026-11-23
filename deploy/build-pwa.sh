#!/usr/bin/env bash
# Build do PWA para publicação em /app/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PWA="$ROOT/pwa"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm não encontrado; instale Node.js 20+" >&2
  exit 1
fi

cd "$PWA"
if [[ ! -d node_modules ]]; then
  npm ci
else
  npm install
fi
npm run build
echo "OK: $PWA/dist pronto para Apache Alias /app"
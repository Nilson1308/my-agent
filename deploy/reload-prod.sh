#!/usr/bin/env bash
# Recarrega produção após mudança de .env, código ou requirements.
# Uso (no servidor, a partir do clone):
#   ./deploy/reload-prod.sh              # rebuild + migrate + collectstatic + smoke
#   ./deploy/reload-prod.sh --env-only   # só recria containers (sem build; ideal pós-editar .env)
#   ./deploy/reload-prod.sh --no-build     # up -d sem --build
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker-compose -p my-agent -f docker-compose.prod.yml)
APP_SERVICES=(web bot celery_worker celery_beat)

BUILD=1
ENV_ONLY=0
MIGRATE=1

for arg in "$@"; do
  case "$arg" in
    --env-only) ENV_ONLY=1; BUILD=0 ;;
    --no-build) BUILD=0 ;;
    --no-migrate) MIGRATE=0 ;;
    -h|--help)
      sed -n '1,8p' "$0"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $arg (use --help)" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Arquivo .env ausente em $ROOT" >&2
  exit 1
fi

echo "==> Diretório: $ROOT"

if [[ "$ENV_ONLY" -eq 1 ]]; then
  echo "==> Recriando serviços de app (sem build): ${APP_SERVICES[*]}"
  "${COMPOSE[@]}" up -d --force-recreate "${APP_SERVICES[@]}"
elif [[ "$BUILD" -eq 1 ]]; then
  echo "==> Build e subida da stack"
  "${COMPOSE[@]}" up -d --build
else
  echo "==> Subida sem build"
  "${COMPOSE[@]}" up -d
fi

echo "==> Aguardando web..."
sleep 3

if [[ "$MIGRATE" -eq 1 ]]; then
  echo "==> Migrations"
  "${COMPOSE[@]}" exec -T web python manage.py migrate --noinput
  echo "==> collectstatic"
  "${COMPOSE[@]}" exec -T web python manage.py collectstatic --noinput
fi

echo "==> Smoke: admin (localhost:8045)"
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8045/admin/login/ || true)"
echo "    /admin/login/ → HTTP ${HTTP_CODE:-erro}"

echo "==> Status"
"${COMPOSE[@]}" ps

echo "==> Últimas linhas (web, bot)"
"${COMPOSE[@]}" logs --tail=15 web bot

echo "OK. Se alterou TELEGRAM/GEOFENCE no .env, use --env-only ou este script completo (nunca só restart de um serviço)."
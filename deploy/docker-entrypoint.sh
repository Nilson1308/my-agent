#!/bin/sh
set -e

mkdir -p "${FASTEMBED_CACHE_PATH:-/app/.cache/fastembed}"
chown -R appuser:appuser "${FASTEMBED_CACHE_PATH:-/app/.cache/fastembed}"

# Estáticos do admin (WhiteNoise); só no serviço web/Gunicorn.
case "$1" in
  gunicorn)
    gosu appuser python manage.py collectstatic --noinput
    ;;
esac

exec gosu appuser "$@"
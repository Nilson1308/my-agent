#!/bin/sh
set -e

mkdir -p "${FASTEMBED_CACHE_PATH:-/app/.cache/fastembed}"
chown -R appuser:appuser "${FASTEMBED_CACHE_PATH:-/app/.cache/fastembed}"

exec gosu appuser "$@"
from __future__ import annotations

import logging

import redis
from django.conf import settings
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

RATE_KEY_PREFIX = "geofence:rl:"


def client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.META.get("REMOTE_ADDR") or "unknown"


def _rate_key(request) -> str:
    return f"{RATE_KEY_PREFIX}{client_ip(request)}"


def enforce_geofence_rate_limit(request) -> None:
    """Uma solicitação bem-sucedida por janela (IP); ignora se Redis indisponível."""
    ttl = int(getattr(settings, "GEOFENCE_RATE_LIMIT_SECONDS", 120))
    if ttl <= 0:
        return

    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        allowed = client.set(_rate_key(request), "1", nx=True, ex=ttl)
    except redis.RedisError as exc:
        logger.warning("geofence rate limit: Redis indisponível (%s), permitindo", exc)
        return

    if not allowed:
        raise HttpError(429, "rate_limited")
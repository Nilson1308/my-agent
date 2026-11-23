from __future__ import annotations

import logging

import redis
from django.conf import settings
from ninja.errors import HttpError

from apps.core.geofence_guard import client_ip

logger = logging.getLogger(__name__)

PWA_RL_WRITE_PREFIX = "pwa:rl:write:"


def enforce_pwa_write_rate_limit(request) -> None:
    """Limita escritas PWA por IP (janela 60s). Snapshot GET não passa aqui."""
    limit = int(getattr(settings, "PWA_WRITE_RATE_LIMIT_PER_MINUTE", 60))
    if limit <= 0:
        return
    ip = client_ip(request)
    key = f"{PWA_RL_WRITE_PREFIX}{ip}"
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        count = client.incr(key)
        if count == 1:
            client.expire(key, 60)
        if count > limit:
            raise HttpError(429, "Muitas alterações; aguarde um minuto.")
    except HttpError:
        raise
    except redis.RedisError as exc:
        logger.warning("pwa rate limit: Redis indisponível (%s), permitindo", exc)
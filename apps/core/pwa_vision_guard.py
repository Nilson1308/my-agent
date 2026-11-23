from __future__ import annotations

import logging
from datetime import date

import redis
from django.conf import settings
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

PWA_RL_VISION_PREFIX = "pwa:rl:vision:day:"


def enforce_pwa_vision_daily_limit() -> None:
    """Limite de chamadas vision por dia (conta Groq free)."""
    limit = int(getattr(settings, "PWA_VISION_MAX_PER_DAY", 20))
    if limit <= 0:
        return
    key = f"{PWA_RL_VISION_PREFIX}{date.today().isoformat()}"
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        count = client.incr(key)
        if count == 1:
            client.expire(key, 90_000)
        if count > limit:
            raise HttpError(429, f"Limite diário de fotos ({limit}/dia). Tente amanhã.")
    except HttpError:
        raise
    except redis.RedisError as exc:
        logger.warning("pwa vision limit: redis (%s), permitindo", exc)
from __future__ import annotations

import logging
import secrets

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

PAIRING_PREFIX = "pwa:pair:"


def _redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def pairing_ttl_seconds() -> int:
    return int(getattr(settings, "PWA_PAIRING_TTL_SECONDS", 900))


def create_pairing_code() -> str:
    """Código de uso único (TTL Redis) para onboarding sem digitar o token."""
    code = secrets.token_urlsafe(18)
    key = f"{PAIRING_PREFIX}{code}"
    try:
        client = _redis()
        client.setex(key, pairing_ttl_seconds(), "1")
    except redis.RedisError as exc:
        logger.error("pairing: redis indisponível (%s)", exc)
        raise RuntimeError("Redis indisponível para pairing") from exc
    return code


def redeem_pairing_code(code: str) -> bool:
    """True se o código existia e foi consumido (one-shot)."""
    cleaned = (code or "").strip()
    if not cleaned or len(cleaned) > 128:
        return False
    key = f"{PAIRING_PREFIX}{cleaned}"
    try:
        client = _redis()
        deleted = client.delete(key)
        return bool(deleted)
    except redis.RedisError as exc:
        logger.warning("pairing redeem: redis (%s)", exc)
        return False


def issue_token_after_pairing() -> str:
    """Token principal retornado após pairing bem-sucedido."""
    return (settings.PWA_API_TOKEN or "").strip()
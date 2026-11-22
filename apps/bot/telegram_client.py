from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
MAX_MESSAGE_LENGTH = 4096
SEND_FAILURES_KEY = "telegram:metrics:send_failures"


def configured_chat_id() -> int | None:
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    chat_raw = (settings.TELEGRAM_ALLOWED_USER_ID or "").strip()
    if not token or not chat_raw:
        return None
    try:
        return int(chat_raw)
    except ValueError:
        logger.error("TELEGRAM_ALLOWED_USER_ID inválido: %s", chat_raw)
        return None


def send_message_sync(text: str, *, timeout: float | None = None) -> bool:
    """Envio síncrono via Bot API (webhooks, Celery, notificações)."""
    chat_id = configured_chat_id()
    if chat_id is None:
        logger.warning("Telegram não configurado (TOKEN ou ALLOWED_USER_ID)")
        _record_send_failure()
        return False
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    body = text if len(text) <= MAX_MESSAGE_LENGTH else text[: MAX_MESSAGE_LENGTH - 1] + "…"
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": body}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    req_timeout = timeout if timeout is not None else settings.TELEGRAM_READ_TIMEOUT

    try:
        with urllib.request.urlopen(request, timeout=req_timeout) as response:
            ok = 200 <= response.status < 300
            if not ok:
                _record_send_failure()
            return ok
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("Telegram sendMessage falhou (%s): %s", exc.code, detail)
        _record_send_failure()
        return False
    except urllib.error.URLError as exc:
        logger.error("Erro de rede ao enviar Telegram: %s", exc)
        _record_send_failure()
        return False


def get_send_failure_count() -> int | None:
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        value = client.get(SEND_FAILURES_KEY)
        return int(value) if value is not None else 0
    except redis.RedisError:
        return None


def _record_send_failure() -> None:
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.incr(SEND_FAILURES_KEY)
    except redis.RedisError as exc:
        logger.debug("métrica telegram:send_failures indisponível: %s", exc)
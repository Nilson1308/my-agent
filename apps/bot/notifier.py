from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"
MAX_MESSAGE_LENGTH = 4096


def send_telegram_message(text: str) -> bool:
    """Envia mensagem proativa via Bot API (síncrono, sem asyncio)."""
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    chat_raw = (settings.TELEGRAM_ALLOWED_USER_ID or "").strip()
    if not token or not chat_raw:
        logger.warning("Telegram não configurado (TOKEN ou ALLOWED_USER_ID)")
        return False

    try:
        chat_id = int(chat_raw)
    except ValueError:
        logger.error("TELEGRAM_ALLOWED_USER_ID inválido: %s", chat_raw)
        return False

    body = text if len(text) <= MAX_MESSAGE_LENGTH else text[: MAX_MESSAGE_LENGTH - 1] + "…"
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": body}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("Telegram sendMessage falhou (%s): %s", exc.code, detail)
        return False
    except urllib.error.URLError as exc:
        logger.error("Erro de rede ao enviar Telegram: %s", exc)
        return False
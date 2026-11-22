from __future__ import annotations

from apps.bot.telegram_client import send_message_sync

MAX_MESSAGE_LENGTH = 4096


def send_telegram_message(text: str) -> bool:
    """Compat: notificações proativas (Celery, webhooks)."""
    return send_message_sync(text)
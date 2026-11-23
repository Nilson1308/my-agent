from __future__ import annotations

import json
import logging

from django.conf import settings

from apps.memory.models import PwaPushSubscription

logger = logging.getLogger(__name__)


def _looks_valid_vapid(value: str) -> bool:
    if not value or value.startswith("<"):
        return False
    if "cryptography.hazmat" in value:
        return False
    return True


def vapid_configured() -> bool:
    pub = (getattr(settings, "VAPID_PUBLIC_KEY", "") or "").strip()
    priv = (getattr(settings, "VAPID_PRIVATE_KEY", "") or "").strip()
    return _looks_valid_vapid(pub) and _looks_valid_vapid(priv)


def vapid_private_key_pem() -> str:
    raw = (getattr(settings, "VAPID_PRIVATE_KEY", "") or "").strip()
    return raw.replace("\\n", "\n")


def vapid_public_key() -> str:
    return (getattr(settings, "VAPID_PUBLIC_KEY", "") or "").strip()


def send_pwa_push(title: str, body: str, *, tag: str = "my-agent") -> int:
    """Envia notificação a todas as subscrições ativas. Retorna quantidade enviada com sucesso."""
    if not vapid_configured():
        return 0
    if not PwaPushSubscription.objects.filter(active=True).exists():
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush não instalado; push PWA ignorado")
        return 0

    payload = json.dumps({"title": title, "body": body, "tag": tag})
    vapid_claims = {"sub": getattr(settings, "VAPID_ADMIN_EMAIL", "mailto:admin@localhost")}
    private_key = vapid_private_key_pem()
    sent = 0

    for sub in PwaPushSubscription.objects.filter(active=True):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as exc:
            logger.info(
                "pwa push falhou endpoint=%s… status=%s",
                sub.endpoint[:48],
                getattr(exc, "response", None),
            )
            if getattr(exc, "response", None) and exc.response.status_code in (404, 410):
                sub.active = False
                sub.save(update_fields=["active"])
    return sent


def push_for_telegram_text(text: str, *, tag: str) -> int:
    """Espelha texto do Telegram em título/corpo curto para o dispositivo."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0
    title = "My Agent"
    if lines[0].startswith("⏰"):
        title = "My Agent · lembrete"
    elif lines[0].startswith("☀️"):
        title = "My Agent · resumo"
    body = lines[0]
    if len(lines) > 1:
        body = f"{body}\n{lines[1][:120]}"
    if len(body) > 240:
        body = body[:237] + "…"
    return send_pwa_push(title, body, tag=tag)
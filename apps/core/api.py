from __future__ import annotations

from django.conf import settings
from ninja import NinjaAPI, Schema
from ninja.security import APIKeyHeader

from apps.bot.notifier import send_telegram_message
from apps.memory.services import format_active_shopping_list


class GeofenceWebhookAuth(APIKeyHeader):
    param_name = "X-Webhook-Token"

    def authenticate(self, request, key: str | None):
        expected = (settings.GEOFENCE_WEBHOOK_TOKEN or "").strip()
        if not expected or not key or key != expected:
            return None
        return key


class GeofencePayload(Schema):
    location: str | None = None


class GeofenceOut(Schema):
    status: str
    items_count: int


geofence_auth = GeofenceWebhookAuth()
api = NinjaAPI(title="My Agent API", version="1.0.0", urls_namespace="core_api")


@api.post("/webhooks/geofence/", auth=geofence_auth, response=GeofenceOut)
def geofence_webhook(request, payload: GeofencePayload | None = None) -> GeofenceOut:
    _ = payload  # reservado p/ localização futura
    message, count = format_active_shopping_list()
    if count == 0:
        return GeofenceOut(status="empty", items_count=0)

    if payload and payload.location:
        header = f"📍 Você chegou em: {payload.location}\n\n"
        message = header + message

    send_telegram_message(message)
    return GeofenceOut(status="sent", items_count=count)
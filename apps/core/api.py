from __future__ import annotations

import logging
import secrets
import time

from django.conf import settings
from django.db import connection
import redis
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.security import APIKeyHeader

from apps.bot.telegram_client import get_send_failure_count, send_message_sync
from apps.core.geofence_guard import client_ip, enforce_geofence_rate_limit
from apps.memory.pwa_mutations import (
    PwaMutationError,
    pwa_complete_task,
    pwa_create_shopping,
    pwa_create_task,
    pwa_dismiss_event,
    pwa_mark_shopping_bought,
    pwa_reopen_task,
)
from apps.memory.pwa_snapshot import build_pwa_snapshot
from apps.memory.services import format_active_shopping_list

logger = logging.getLogger(__name__)

EMPTY_GEOFENCE_MESSAGE = "🛒 Lista de mercado vazia."


class GeofenceWebhookAuth(APIKeyHeader):
    param_name = "X-Webhook-Token"

    def authenticate(self, request, key: str | None):
        expected = (settings.GEOFENCE_WEBHOOK_TOKEN or "").strip()
        if not expected or not key:
            return None
        if not secrets.compare_digest(expected, key.strip()):
            return None
        return key


class GeofencePayload(Schema):
    location: str | None = None


class GeofenceOut(Schema):
    status: str
    items_count: int
    telegram_sent: bool


class HealthOut(Schema):
    status: str
    database: bool
    redis: bool
    telegram_send_failures: int | None = None


geofence_auth = GeofenceWebhookAuth()
api = NinjaAPI(title="My Agent API", version="1.0.0", urls_namespace="core_api")


def _check_database() -> bool:
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return client.ping()
    except redis.RedisError:
        return False


class PwaAuth(APIKeyHeader):
    param_name = "X-PWA-Token"

    def authenticate(self, request, key: str | None):
        expected = (settings.PWA_API_TOKEN or "").strip()
        if not expected or not key:
            return None
        if not secrets.compare_digest(expected, key.strip()):
            return None
        return key


pwa_token_auth = PwaAuth()


@api.get("/health/", auth=None, response=HealthOut)
def health(request) -> HealthOut:
    db_ok = _check_database()
    redis_ok = _check_redis()
    overall = "ok" if db_ok and redis_ok else "degraded"
    return HealthOut(
        status=overall,
        database=db_ok,
        redis=redis_ok,
        telegram_send_failures=get_send_failure_count(),
    )


def _location_prefix(payload: GeofencePayload | None) -> str:
    if payload and payload.location:
        return f"📍 Você chegou em: {payload.location}\n\n"
    return ""


@api.post("/webhooks/geofence/", auth=geofence_auth, response=GeofenceOut)
def geofence_webhook(request, payload: GeofencePayload | None = None) -> GeofenceOut:
    started = time.monotonic()
    ip = client_ip(request)
    enforce_geofence_rate_limit(request)
    message, count = format_active_shopping_list()

    if count == 0:
        text = _location_prefix(payload) + EMPTY_GEOFENCE_MESSAGE
        telegram_sent = send_message_sync(text)
        status = "empty"
        _log_geofence(ip, count, telegram_sent, status, started)
        return GeofenceOut(status=status, items_count=0, telegram_sent=telegram_sent)

    message = _location_prefix(payload) + message
    telegram_sent = send_message_sync(message)
    if not telegram_sent:
        status = "telegram_failed"
        _log_geofence(ip, count, False, status, started)
        return GeofenceOut(
            status=status,
            items_count=count,
            telegram_sent=False,
        )

    status = "sent"
    _log_geofence(ip, count, True, status, started)
    return GeofenceOut(status=status, items_count=count, telegram_sent=True)


@api.get("/pwa/snapshot/", auth=pwa_token_auth)
def pwa_snapshot(request):
    return build_pwa_snapshot()


class ShoppingPatchIn(Schema):
    bought: bool = True


class ShoppingPatchOut(Schema):
    id: int
    name: str
    is_bought: bool


class TaskPatchIn(Schema):
    status: str = "done"


class TaskPatchOut(Schema):
    id: int
    title: str
    status: str
    completed_at: str | None = None
    context: str | None = None


class EventPatchIn(Schema):
    dismissed: bool = True


class EventPatchOut(Schema):
    id: int
    title: str
    dismissed: bool
    was_at: str


def _pwa_mutation_http(exc: PwaMutationError) -> None:
    if exc.code == "not_found":
        code = 404
    elif exc.code in ("already_done", "duplicate", "already_pending"):
        code = 409
    else:
        code = 400
    raise HttpError(code, exc.message)


class ShoppingCreateIn(Schema):
    name: str
    quantity: str = ""


class ShoppingCreateOut(Schema):
    id: int
    name: str
    quantity: str


class TaskCreateIn(Schema):
    title: str
    context: str | None = None


class TaskCreateOut(Schema):
    id: int
    title: str
    context: str


@api.post(
    "/pwa/shopping/",
    auth=pwa_token_auth,
    response={200: ShoppingCreateOut, 409: dict, 400: dict},
)
def pwa_shopping_create(request, payload: ShoppingCreateIn):
    try:
        return pwa_create_shopping(payload.name, payload.quantity)
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.post(
    "/pwa/tasks/",
    auth=pwa_token_auth,
    response={200: TaskCreateOut, 409: dict, 400: dict},
)
def pwa_task_create(request, payload: TaskCreateIn):
    try:
        return pwa_create_task(payload.title, payload.context)
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.patch(
    "/pwa/shopping/{item_id}/",
    auth=pwa_token_auth,
    response={200: ShoppingPatchOut, 404: dict, 409: dict},
)
def pwa_shopping_patch(request, item_id: int, payload: ShoppingPatchIn):
    try:
        return pwa_mark_shopping_bought(item_id, bought=payload.bought)
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.patch(
    "/pwa/tasks/{task_id}/",
    auth=pwa_token_auth,
    response={200: TaskPatchOut, 404: dict, 409: dict},
)
def pwa_task_patch(request, task_id: int, payload: TaskPatchIn):
    try:
        if payload.status == "pending":
            return pwa_reopen_task(task_id)
        return pwa_complete_task(task_id)
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.patch(
    "/pwa/events/{event_id}/",
    auth=pwa_token_auth,
    response={200: EventPatchOut, 404: dict},
)
def pwa_event_dismiss(request, event_id: int, payload: EventPatchIn):
    if not payload.dismissed:
        raise HttpError(400, "Apenas dismissed=true é suportado.")
    try:
        return pwa_dismiss_event(event_id)
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


def _log_geofence(
    ip: str,
    items_count: int,
    telegram_sent: bool,
    status: str,
    started: float,
) -> None:
    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "geofence webhook status=%s items=%s telegram_sent=%s client_ip=%s duration_ms=%s",
        status,
        items_count,
        telegram_sent,
        ip,
        duration_ms,
    )
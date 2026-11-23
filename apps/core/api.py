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
from apps.core.pwa_auth import configured_pwa_tokens, pwa_token_is_valid
from apps.core.pwa_guard import enforce_pwa_write_rate_limit
from apps.core.pwa_pairing import (
    create_pairing_code,
    issue_token_after_pairing,
    pairing_ttl_seconds,
    redeem_pairing_code,
)
from apps.memory.pwa_audit import log_pwa_mutation
from apps.memory.models import PwaPushSubscription
from apps.memory.pwa_push import vapid_configured, vapid_public_key
from apps.memory.pwa_mutations import (
    PwaMutationError,
    pwa_complete_task,
    pwa_create_shopping,
    pwa_create_task,
    pwa_dismiss_event,
    pwa_mark_shopping_bought,
    pwa_reopen_task,
    pwa_snooze_event,
)
from apps.memory.agent_pipeline import run_agent_message
from apps.memory.models import InteractionChannel, InteractionLog
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
        if not configured_pwa_tokens() or not pwa_token_is_valid(key):
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
    if not configured_pwa_tokens():
        raise HttpError(503, "PWA não configurado no servidor.")
    return build_pwa_snapshot()


class PushVapidOut(Schema):
    public_key: str
    enabled: bool


class PushSubscribeIn(Schema):
    endpoint: str
    keys: dict | None = None
    user_agent: str | None = None


class PairingCreateOut(Schema):
    code: str
    expires_in: int
    pair_url: str


class PairingExchangeIn(Schema):
    code: str


class PairingExchangeOut(Schema):
    token: str


class PwaChatIn(Schema):
    text: str


class PwaChatOut(Schema):
    reply: str
    llm_outcome: str = ""
    interaction_log_id: int | None = None
    pending_confirmation: bool = False


@api.post("/pwa/chat/", auth=pwa_token_auth, response={200: PwaChatOut, 400: dict, 503: dict})
def pwa_chat(request, payload: PwaChatIn):
    if not configured_pwa_tokens():
        raise HttpError(503, "PWA não configurado.")
    text = (payload.text or "").strip()
    if not text:
        raise HttpError(400, "Mensagem vazia.")
    if len(text) > 8000:
        raise HttpError(400, "Mensagem muito longa.")
    enforce_pwa_write_rate_limit(request)
    try:
        agent_reply = run_agent_message(
            text,
            channel=InteractionChannel.PWA,
            input_type="text",
        )
    except Exception as exc:
        logger.exception("pwa chat falhou: %s", exc)
        raise HttpError(500, "Falha ao processar mensagem.") from exc

    outcome = ""
    if agent_reply.interaction_log_id:
        log = InteractionLog.objects.filter(pk=agent_reply.interaction_log_id).first()
        if log:
            outcome = log.llm_outcome or ""
    elif agent_reply.pending_confirmation_id:
        outcome = "pending_confirmation"

    log_pwa_mutation(request, "chat_message", target_type="interaction")

    return PwaChatOut(
        reply=agent_reply.message,
        llm_outcome=outcome,
        interaction_log_id=agent_reply.interaction_log_id,
        pending_confirmation=agent_reply.pending_confirmation_id is not None,
    )


@api.get("/pwa/push/vapid/", auth=None, response=PushVapidOut)
def pwa_push_vapid(request):
    key = vapid_public_key()
    return PushVapidOut(public_key=key, enabled=bool(key) and vapid_configured())


@api.post("/pwa/push/subscribe/", auth=pwa_token_auth, response={200: dict})
def pwa_push_subscribe(request, payload: PushSubscribeIn):
    if not configured_pwa_tokens():
        raise HttpError(503, "PWA não configurado.")
    keys = payload.keys or {}
    p256 = keys.get("p256dh") or keys.get("p256DH")
    auth_key = keys.get("auth")
    if not payload.endpoint or not p256 or not auth_key:
        raise HttpError(400, "Subscrição push inválida.")
    ua = (payload.user_agent or request.META.get("HTTP_USER_AGENT", ""))[:255]
    PwaPushSubscription.objects.update_or_create(
        endpoint=payload.endpoint,
        defaults={"p256dh": p256, "auth": auth_key, "user_agent": ua, "active": True},
    )
    return {"ok": True}


@api.post("/pwa/push/unsubscribe/", auth=pwa_token_auth, response={200: dict})
def pwa_push_unsubscribe(request, payload: PushSubscribeIn):
    if payload.endpoint:
        PwaPushSubscription.objects.filter(endpoint=payload.endpoint).update(active=False)
    return {"ok": True}


@api.post("/pwa/pairing/create/", auth=pwa_token_auth, response={200: PairingCreateOut, 503: dict})
def pwa_pairing_create(request):
    if not configured_pwa_tokens():
        raise HttpError(503, "PWA não configurado.")
    enforce_pwa_write_rate_limit(request)
    try:
        code = create_pairing_code()
    except RuntimeError as exc:
        raise HttpError(503, str(exc)) from exc
    base = (settings.PWA_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if not base:
        base = request.build_absolute_uri("/app/").rstrip("/")
    pair_url = f"{base}/?code={code}"
    return PairingCreateOut(code=code, expires_in=pairing_ttl_seconds(), pair_url=pair_url)


@api.post(
    "/pwa/pairing/exchange/",
    auth=None,
    response={200: PairingExchangeOut, 400: dict, 401: dict, 503: dict},
)
def pwa_pairing_exchange(request, payload: PairingExchangeIn):
    if not configured_pwa_tokens():
        raise HttpError(503, "PWA não configurado.")
    enforce_pwa_write_rate_limit(request)
    if not redeem_pairing_code(payload.code):
        raise HttpError(401, "Código inválido ou expirado.")
    token = issue_token_after_pairing()
    if not token:
        raise HttpError(503, "Token PWA ausente no servidor.")
    return PairingExchangeOut(token=token)


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


class EventSnoozeIn(Schema):
    minutes: int | None = None
    preset: str | None = None


class EventSnoozeOut(Schema):
    id: int
    title: str
    start_at: str


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
    enforce_pwa_write_rate_limit(request)
    try:
        out = pwa_create_shopping(payload.name, payload.quantity)
        log_pwa_mutation(request, "shopping_create", target_type="shopping", target_id=out["id"])
        return out
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.post(
    "/pwa/tasks/",
    auth=pwa_token_auth,
    response={200: TaskCreateOut, 409: dict, 400: dict},
)
def pwa_task_create(request, payload: TaskCreateIn):
    enforce_pwa_write_rate_limit(request)
    try:
        out = pwa_create_task(payload.title, payload.context)
        log_pwa_mutation(request, "task_create", target_type="task", target_id=out["id"])
        return out
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.patch(
    "/pwa/shopping/{item_id}/",
    auth=pwa_token_auth,
    response={200: ShoppingPatchOut, 404: dict, 409: dict},
)
def pwa_shopping_patch(request, item_id: int, payload: ShoppingPatchIn):
    enforce_pwa_write_rate_limit(request)
    try:
        out = pwa_mark_shopping_bought(item_id, bought=payload.bought)
        action = "shopping_bought" if payload.bought else "shopping_unbought"
        log_pwa_mutation(request, action, target_type="shopping", target_id=item_id)
        return out
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.patch(
    "/pwa/tasks/{task_id}/",
    auth=pwa_token_auth,
    response={200: TaskPatchOut, 404: dict, 409: dict},
)
def pwa_task_patch(request, task_id: int, payload: TaskPatchIn):
    enforce_pwa_write_rate_limit(request)
    try:
        if payload.status == "pending":
            out = pwa_reopen_task(task_id)
            log_pwa_mutation(request, "task_reopen", target_type="task", target_id=task_id)
            return out
        out = pwa_complete_task(task_id)
        log_pwa_mutation(request, "task_done", target_type="task", target_id=task_id)
        return out
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
    enforce_pwa_write_rate_limit(request)
    try:
        out = pwa_dismiss_event(event_id)
        log_pwa_mutation(request, "event_dismiss", target_type="event", target_id=event_id)
        return out
    except PwaMutationError as exc:
        _pwa_mutation_http(exc)
    raise HttpError(500, "Erro interno")


@api.post(
    "/pwa/events/{event_id}/snooze/",
    auth=pwa_token_auth,
    response={200: EventSnoozeOut, 404: dict, 400: dict},
)
def pwa_event_snooze(request, event_id: int, payload: EventSnoozeIn):
    enforce_pwa_write_rate_limit(request)
    tomorrow = payload.preset == "tomorrow_morning"
    minutes = payload.minutes
    if not tomorrow and minutes is not None and minutes < 1:
        raise HttpError(400, "minutes inválido")
    try:
        out = pwa_snooze_event(
            event_id,
            minutes=minutes,
            tomorrow_morning=tomorrow,
        )
        log_pwa_mutation(request, "event_snooze", target_type="event", target_id=event_id)
        return out
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
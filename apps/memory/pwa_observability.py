from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.ai.llm_outcomes import LLM_OK
from apps.bot.telegram_client import get_send_failure_count
from apps.memory.models import (
    GeofenceEvent,
    InteractionChannel,
    InteractionLog,
    PwaMutationLog,
    PwaPushSubscription,
)

DEFAULT_WINDOW_DAYS = 7


def build_pwa_observability(*, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    window_days = max(1, min(window_days, 90))
    since = timezone.now() - timedelta(days=window_days)
    generated_at = timezone.now()

    interactions = {InteractionChannel.TELEGRAM: 0, InteractionChannel.PWA: 0}
    for row in (
        InteractionLog.objects.filter(created_at__gte=since)
        .values("channel")
        .annotate(n=Count("id"))
    ):
        ch = row["channel"]
        if ch in interactions:
            interactions[ch] = row["n"]

    llm_errors = {InteractionChannel.TELEGRAM: 0, InteractionChannel.PWA: 0}
    for row in (
        InteractionLog.objects.filter(created_at__gte=since)
        .exclude(llm_outcome="")
        .exclude(llm_outcome=LLM_OK)
        .values("channel")
        .annotate(n=Count("id"))
    ):
        ch = row["channel"]
        if ch in llm_errors:
            llm_errors[ch] = row["n"]

    mutations_total = PwaMutationLog.objects.filter(created_at__gte=since).count()
    mutations_by_action: list[dict] = []
    for row in (
        PwaMutationLog.objects.filter(created_at__gte=since)
        .values("action")
        .annotate(n=Count("id"))
        .order_by("-n", "action")[:12]
    ):
        mutations_by_action.append({"action": row["action"], "count": row["n"]})

    last_interaction_at: dict[str, str | None] = {}
    for ch in (InteractionChannel.TELEGRAM, InteractionChannel.PWA):
        ts = (
            InteractionLog.objects.filter(channel=ch)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        last_interaction_at[ch] = ts.isoformat() if ts else None

    return {
        "generated_at": generated_at.isoformat(),
        "window_days": window_days,
        "interactions": {
            "telegram": interactions[InteractionChannel.TELEGRAM],
            "pwa": interactions[InteractionChannel.PWA],
        },
        "llm_errors": {
            "telegram": llm_errors[InteractionChannel.TELEGRAM],
            "pwa": llm_errors[InteractionChannel.PWA],
        },
        "mutations_total": mutations_total,
        "mutations_by_action": mutations_by_action,
        "geofence_events": GeofenceEvent.objects.filter(created_at__gte=since).count(),
        "push_subscriptions_active": PwaPushSubscription.objects.filter(active=True).count(),
        "telegram_send_failures": get_send_failure_count(),
        "last_interaction_at": last_interaction_at,
    }
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.memory.models import InteractionLog

logger = logging.getLogger(__name__)

UNDO_WINDOW_MINUTES = 5


def _get_model(model_label: str) -> type[Any]:
    return apps.get_model(model_label)


def _apply_undo_effect(effect: dict[str, Any]) -> None:
    op = effect.get("op")
    model_label = effect.get("model")
    if not model_label:
        return
    model = _get_model(model_label)

    if op == "delete":
        pk = effect.get("pk")
        if pk:
            model.objects.filter(pk=pk).delete()
        return

    if op == "create":
        fields = dict(effect.get("fields") or {})
        fields.pop("pk", None)
        for key, value in list(fields.items()):
            if isinstance(value, str) and key.endswith("_at") or key == "due_at":
                parsed = parse_datetime(value) if value else None
                if parsed:
                    fields[key] = parsed
        model.objects.create(**_filter_model_fields(model, fields))
        return

    if op == "restore":
        pk = effect.get("pk")
        before = effect.get("before") or {}
        if not pk:
            return
        instance = model.objects.filter(pk=pk).first()
        if not instance:
            return
        for field, value in before.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        instance.save()


def _filter_model_fields(model: type[Any], fields: dict[str, Any]) -> dict[str, Any]:
    allowed = {f.name for f in model._meta.fields}
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        out[key] = value
    return out


def undo_last_interaction(telegram_user_id: int) -> str:
    cutoff = timezone.now() - timedelta(minutes=UNDO_WINDOW_MINUTES)
    log = (
        InteractionLog.objects.filter(
            telegram_user_id=telegram_user_id,
            created_at__gte=cutoff,
            undone_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if not log:
        return (
            f"Nada a desfazer nos últimos {UNDO_WINDOW_MINUTES} minutos "
            "(ou a última ação não é reversível)."
        )

    effects = list(log.effects_json or [])
    if not effects:
        return (
            f"Nada a desfazer nos últimos {UNDO_WINDOW_MINUTES} minutos "
            "(ou a última ação não é reversível)."
        )

    try:
        for effect in reversed(effects):
            _apply_undo_effect(effect)
    except Exception:
        logger.exception("Falha ao desfazer log %s", log.pk)
        return "Não consegui desfazer com segurança. Confira a lista manualmente."

    log.undone_at = timezone.now()
    log.save(update_fields=["undone_at"])
    preview = (log.raw_input or "")[:80]
    if len(log.raw_input or "") > 80:
        preview += "…"
    return f"↩️ Desfeito: “{preview}”"
from __future__ import annotations

from typing import Any

from django.forms.models import model_to_dict


class EffectRecorder:
    """Registra alterações no banco para possível desfazer via InteractionLog."""

    def __init__(self) -> None:
        self.effects: list[dict[str, Any]] = []

    def record_created(self, instance: Any) -> None:
        label = instance._meta.label_lower
        self.effects.append({"op": "delete", "model": label, "pk": instance.pk})

    def record_deleted(self, instance: Any) -> None:
        label = instance._meta.label_lower
        data = model_to_dict(instance)
        data["pk"] = instance.pk
        self.effects.append({"op": "create", "model": label, "fields": data})

    def record_updated(self, instance: Any, before: dict[str, Any]) -> None:
        label = instance._meta.label_lower
        self.effects.append(
            {
                "op": "restore",
                "model": label,
                "pk": instance.pk,
                "before": before,
            }
        )
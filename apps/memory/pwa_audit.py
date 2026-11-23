from __future__ import annotations

from apps.core.geofence_guard import client_ip
from apps.memory.models import PwaMutationLog


def log_pwa_mutation(request, action: str, *, target_type: str = "", target_id: int | None = None) -> None:
    try:
        PwaMutationLog.objects.create(
            action=action,
            target_type=target_type[:32],
            target_id=target_id,
            client_ip=client_ip(request)[:45],
        )
    except Exception:
        pass
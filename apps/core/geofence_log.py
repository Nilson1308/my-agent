from __future__ import annotations

import logging

from apps.memory.models import GeofenceEvent

logger = logging.getLogger(__name__)


def record_geofence_event(
    *,
    client_ip: str,
    status: str,
    items_count: int,
    telegram_sent: bool,
    location_label: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> GeofenceEvent:
    event = GeofenceEvent.objects.create(
        location_label=(location_label or "").strip()[:128],
        latitude=latitude,
        longitude=longitude,
        client_ip=client_ip or None,
        status=status[:24],
        items_count=items_count,
        telegram_sent=telegram_sent,
    )
    logger.info(
        "geofence_event id=%s status=%s label=%s",
        event.pk,
        status,
        event.location_label or "—",
    )
    return event
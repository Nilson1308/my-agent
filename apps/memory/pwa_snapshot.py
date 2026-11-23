from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.memory.models import Event, ShoppingItem, Task, TaskStatus
from apps.memory.services import format_active_shopping_list


def build_pwa_snapshot() -> dict:
    """JSON enxuto para PWA (read-only)."""
    now = timezone.now()
    today = timezone.localdate()
    day_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    day_end = day_start + timedelta(days=1)

    shopping_text, shopping_count = format_active_shopping_list()
    items = [
        {"id": i.pk, "name": i.name, "quantity": i.quantity or ""}
        for i in ShoppingItem.objects.filter(is_bought=False).order_by("name")[:200]
    ]

    tasks = list(
        Task.objects.filter(status=TaskStatus.PENDING).order_by("due_at", "due_date")[:50]
    )
    task_payload = [
        {
            "id": t.pk,
            "title": t.title,
            "context": t.context,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "due_at": timezone.localtime(t.due_at).isoformat() if t.due_at else None,
        }
        for t in tasks
    ]

    events = list(
        Event.objects.filter(start_at__gte=day_start, start_at__lt=day_end).order_by("start_at")[:30]
    )
    event_payload = [
        {
            "id": e.pk,
            "title": e.title,
            "context": e.context,
            "start_at": timezone.localtime(e.start_at).isoformat(),
        }
        for e in events
    ]

    return {
        "generated_at": now.isoformat(),
        "shopping": {
            "count": shopping_count,
            "text": shopping_text,
            "items": items,
        },
        "tasks_pending": task_payload,
        "events_today": event_payload,
    }
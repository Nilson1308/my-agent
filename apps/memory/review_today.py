from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.memory.models import DomainContext, Event, Reminder, Task, TaskStatus
from apps.memory.services import format_active_shopping_list


def build_today_digest(mode: str | None = None) -> str:
    """
    mode: None (resumo), mercado, theo, trabalho, casa, pessoal, atrasadas
    """
    mode = (mode or "").strip().lower() or None
    today = timezone.localdate()
    now = timezone.now()
    day_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    day_end = day_start + timedelta(days=1)

    if mode == "mercado":
        text, count = format_active_shopping_list()
        return text if count else "🛒 Mercado: lista vazia"

    if mode == "atrasadas":
        tasks = list(
            Task.objects.filter(
                status=TaskStatus.PENDING,
                due_date__lt=today,
                due_date__isnull=False,
            ).order_by("due_date", "title")[:25]
        )
        if not tasks:
            return "✅ Nenhuma tarefa atrasada por data."
        lines = [
            f"  – [{t.context}] {t.title} · venceu {t.due_date:%d/%m}" for t in tasks
        ]
        return "⚠️ Tarefas atrasadas:\n" + "\n".join(lines)

    ctx_filter: str | None = None
    if mode in {c.value for c in DomainContext}:
        ctx_filter = mode

    parts: list[str] = [f"📆 Revisão — {today:%d/%m/%Y}"]

    shopping, sc = format_active_shopping_list()
    if sc:
        parts.append(shopping if not ctx_filter else f"🛒 Mercado: {sc} item(ns) na lista")

    task_qs = Task.objects.filter(status=TaskStatus.PENDING)
    if ctx_filter:
        task_qs = task_qs.filter(context=ctx_filter)
    tasks_today = list(
        task_qs.filter(
            Q(due_date=today) | Q(due_at__gte=day_start, due_at__lt=day_end)
        ).order_by("due_at", "due_date", "title")[:20]
    )
    overdue = list(
        task_qs.filter(due_date__lt=today, due_date__isnull=False).order_by("due_date")[:10]
    )
    if tasks_today:
        lines = []
        for t in tasks_today:
            when = ""
            if t.due_at:
                when = f" · {timezone.localtime(t.due_at):%H:%M}"
            elif t.due_date:
                when = f" · {t.due_date:%d/%m}"
            lines.append(f"  – [{t.context}] {t.title}{when}")
        parts.append("✅ Para hoje:\n" + "\n".join(lines))
    if overdue and not ctx_filter:
        parts.append(
            "⚠️ Atrasadas: "
            + ", ".join(f"{t.title} ({t.due_date:%d/%m})" for t in overdue[:8])
        )

    event_qs = Event.objects.filter(start_at__gte=day_start, start_at__lt=day_end)
    if ctx_filter:
        event_qs = event_qs.filter(context=ctx_filter)
    events = list(event_qs.order_by("start_at")[:15])
    if events:
        elines = [
            f"  – [{e.context}] {e.title} · {timezone.localtime(e.start_at):%H:%M}"
            for e in events
        ]
        parts.append("📅 Compromissos hoje:\n" + "\n".join(elines))

    reminders = list(
        Reminder.objects.filter(
            reminded=False,
            remind_at__gte=day_start,
            remind_at__lt=day_end,
        ).order_by("remind_at")[:10]
    )
    if reminders and not ctx_filter:
        rlines = [
            f"  – [{r.context}] {r.title} · {timezone.localtime(r.remind_at):%H:%M}"
            for r in reminders
        ]
        parts.append("⏰ Lembretes hoje:\n" + "\n".join(rlines))

    if len(parts) == 1:
        parts.append("Nada marcado para hoje — use /hoje mercado ou /hoje atrasadas.")

    return "\n\n".join(parts)
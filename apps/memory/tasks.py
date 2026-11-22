from __future__ import annotations

from datetime import datetime, time, timedelta

from celery import shared_task
from django.utils import timezone

from apps.bot.notifier import send_telegram_message
from apps.memory.models import DomainContext, Event, Task, TaskStatus


def _today_bounds() -> tuple[datetime, datetime]:
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, time.min), tz)
    end = timezone.make_aware(datetime.combine(today, time.max), tz)
    return start, end


def build_morning_briefing_message() -> str:
    start_day, end_day = _today_bounds()
    today = timezone.localdate()

    events = list(
        Event.objects.filter(start_at__gte=start_day, start_at__lte=end_day).order_by("start_at")
    )
    tasks_today = list(
        Task.objects.filter(
            status=TaskStatus.PENDING,
            due_date=today,
        ).order_by("context", "title")
    )
    tasks_overdue = list(
        Task.objects.filter(
            status=TaskStatus.PENDING,
            due_date__lt=today,
        ).order_by("due_date", "title")
    )
    theo_pending = list(
        Task.objects.filter(
            status=TaskStatus.PENDING,
            context=DomainContext.THEO,
        ).order_by("due_date", "-created_at")[:15]
    )

    lines: list[str] = [f"☀️ Bom dia! Resumo de {today:%d/%m/%Y}"]

    if events:
        lines.append("\n📅 Compromissos hoje:")
        for event in events:
            lines.append(
                f"  – [{event.context}] {event.title} "
                f"· {timezone.localtime(event.start_at):%H:%M}"
            )

    if tasks_overdue:
        lines.append("\n⚠️ Tarefas atrasadas:")
        for task in tasks_overdue:
            due = f" ({task.due_date:%d/%m})" if task.due_date else ""
            lines.append(f"  – [{task.context}] {task.title}{due}")

    if tasks_today:
        lines.append("\n✅ Para hoje:")
        for task in tasks_today:
            lines.append(f"  – [{task.context}] {task.title}")

    if theo_pending:
        lines.append("\n👦 Pendências Theo:")
        for task in theo_pending:
            due = f" · {task.due_date:%d/%m}" if task.due_date else ""
            lines.append(f"  – {task.title}{due}")

    if not events and not tasks_overdue and not tasks_today and not theo_pending:
        lines.append("\nAgenda livre por aqui. Bom dia!")

    return "\n".join(lines)


@shared_task(name="apps.memory.tasks.send_morning_briefing")
def send_morning_briefing() -> dict[str, object]:
    message = build_morning_briefing_message()
    sent = send_telegram_message(message)
    return {"sent": sent, "length": len(message)}


@shared_task(name="apps.memory.tasks.check_upcoming_events")
def check_upcoming_events() -> dict[str, object]:
    now = timezone.now()
    window_end = now + timedelta(minutes=35)

    events = list(
        Event.objects.filter(
            reminded=False,
            start_at__gt=now,
            start_at__lte=window_end,
        ).order_by("start_at")
    )

    reminded_count = 0
    for event in events:
        local_start = timezone.localtime(event.start_at)
        delta = event.start_at - now
        minutes = max(int(delta.total_seconds() // 60), 0)
        text = (
            f"⏰ Em ~{minutes} min: {event.title}\n"
            f"[{event.context}] · {local_start:%d/%m às %H:%M}"
        )
        if send_telegram_message(text):
            event.reminded = True
            event.save(update_fields=["reminded"])
            reminded_count += 1

    return {"checked": len(events), "reminded": reminded_count}
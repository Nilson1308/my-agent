from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.memory.models import DomainContext, Event, ShoppingItem, Task, TaskStatus

_VALID_CONTEXTS = {c.value for c in DomainContext}


class PwaMutationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def pwa_mark_shopping_bought(item_id: int, *, bought: bool = True) -> dict:
    item = ShoppingItem.objects.filter(pk=item_id).first()
    if not item:
        raise PwaMutationError("not_found", "Item não encontrado.")
    if bought:
        if item.is_bought:
            return {"id": item.pk, "name": item.name, "is_bought": True}
        item.is_bought = True
        item.bought_at = timezone.now()
        item.save(update_fields=["is_bought", "bought_at"])
    else:
        item.is_bought = False
        item.bought_at = None
        item.save(update_fields=["is_bought", "bought_at"])
    return {"id": item.pk, "name": item.name, "is_bought": item.is_bought}


def pwa_reopen_task(task_id: int) -> dict:
    task = Task.objects.filter(pk=task_id, status=TaskStatus.DONE).first()
    if not task:
        existing = Task.objects.filter(pk=task_id).first()
        if existing and existing.status == TaskStatus.PENDING:
            raise PwaMutationError("already_pending", "Tarefa já está pendente.")
        raise PwaMutationError("not_found", "Tarefa concluída não encontrada.")
    task.status = TaskStatus.PENDING
    task.completed_at = None
    task.save(update_fields=["status", "completed_at"])
    return {
        "id": task.pk,
        "title": task.title,
        "status": task.status,
        "context": task.context,
    }


def pwa_complete_task(task_id: int) -> dict:
    task = Task.objects.filter(pk=task_id, status=TaskStatus.PENDING).first()
    if not task:
        existing = Task.objects.filter(pk=task_id).first()
        if existing and existing.status == TaskStatus.DONE:
            raise PwaMutationError("already_done", "Tarefa já concluída.")
        raise PwaMutationError("not_found", "Tarefa não encontrada.")
    now = timezone.now()
    task.status = TaskStatus.DONE
    task.completed_at = now
    task.save(update_fields=["status", "completed_at"])
    return {
        "id": task.pk,
        "title": task.title,
        "status": task.status,
        "completed_at": timezone.localtime(now).isoformat(),
    }


def pwa_create_shopping(name: str, quantity: str = "") -> dict:
    cleaned = name.strip()
    if not cleaned:
        raise PwaMutationError("invalid", "Nome do item obrigatório.")
    if len(cleaned) > 255:
        raise PwaMutationError("invalid", "Nome muito longo.")
    qty = quantity.strip()[:64]
    if ShoppingItem.objects.filter(is_bought=False, name__iexact=cleaned).exists():
        raise PwaMutationError("duplicate", "Esse item já está na lista.")
    item = ShoppingItem.objects.create(name=cleaned, quantity=qty)
    return {"id": item.pk, "name": item.name, "quantity": item.quantity or ""}


def pwa_create_task(title: str, context: str | None = None) -> dict:
    cleaned = title.strip()
    if not cleaned:
        raise PwaMutationError("invalid", "Título da tarefa obrigatório.")
    if len(cleaned) > 512:
        raise PwaMutationError("invalid", "Título muito longo.")
    ctx = (context or DomainContext.PESSOAL).strip().lower()
    if ctx not in _VALID_CONTEXTS:
        ctx = DomainContext.PESSOAL
    task = Task.objects.create(title=cleaned, context=ctx)
    return {
        "id": task.pk,
        "title": task.title,
        "context": task.context,
    }


def pwa_snooze_event(
    event_id: int,
    *,
    minutes: int | None = None,
    tomorrow_morning: bool = False,
) -> dict:
    event = Event.objects.filter(pk=event_id).first()
    if not event:
        raise PwaMutationError("not_found", "Compromisso não encontrado.")
    now = timezone.now()
    if tomorrow_morning:
        local = timezone.localtime(event.start_at)
        next_day = local.date() + timedelta(days=1)
        event.start_at = timezone.make_aware(
            datetime.combine(next_day, time(9, 0)),
            timezone.get_current_timezone(),
        )
    else:
        delta = timedelta(minutes=minutes if minutes is not None else 15)
        base = event.start_at if event.start_at > now else now
        event.start_at = base + delta
    event.save(update_fields=["start_at"])
    return {
        "id": event.pk,
        "title": event.title,
        "start_at": timezone.localtime(event.start_at).isoformat(),
    }


def pwa_dismiss_event(event_id: int) -> dict:
    event = Event.objects.filter(pk=event_id).first()
    if not event:
        raise PwaMutationError("not_found", "Compromisso não encontrado.")
    title = event.title
    start = timezone.localtime(event.start_at).isoformat()
    event.delete()
    return {"id": event_id, "title": title, "dismissed": True, "was_at": start}
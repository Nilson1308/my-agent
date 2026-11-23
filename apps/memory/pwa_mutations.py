from __future__ import annotations

from django.utils import timezone

from apps.memory.models import ShoppingItem, Task, TaskStatus


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
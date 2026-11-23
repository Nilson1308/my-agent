from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from pgvector.django import CosineDistance

from apps.ai.embeddings_service import embed_document
from apps.memory.models import Event, Note, ShoppingItem, Task, TaskStatus

NOTE_COSINE_MAX_DISTANCE = 0.45


def _normalize_item_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def find_similar_shopping(name: str, *, limit: int = 5) -> list[ShoppingItem]:
    raw = name.strip()
    if not raw:
        return []
    normalized = _normalize_item_name(raw)
    pending = ShoppingItem.objects.filter(is_bought=False)
    matches: list[ShoppingItem] = []
    seen: set[int] = set()
    for item in pending:
        if item.pk in seen:
            continue
        n = _normalize_item_name(item.name)
        if n == normalized or normalized in n or n in normalized:
            matches.append(item)
            seen.add(item.pk)
    if len(matches) < limit:
        for item in pending.filter(Q(name__icontains=raw) | Q(name__iexact=raw))[:limit]:
            if item.pk not in seen:
                matches.append(item)
                seen.add(item.pk)
    return matches[:limit]


def find_similar_tasks(
    title: str,
    context: str | None = None,
    due_date=None,
    *,
    limit: int = 5,
) -> list[Task]:
    raw = title.strip()
    if not raw:
        return []
    qs = Task.objects.filter(status=TaskStatus.PENDING)
    if context:
        qs = qs.filter(context=context)
    if due_date:
        qs = qs.filter(due_date=due_date)
    normalized = _normalize_item_name(raw)
    results: list[Task] = []
    for task in qs[:50]:
        t = _normalize_item_name(task.title)
        if t == normalized or raw.lower() in task.title.lower() or task.title.lower() in raw.lower():
            results.append(task)
    if len(results) < limit:
        for task in qs.filter(title__icontains=raw)[:limit]:
            if task not in results:
                results.append(task)
    return results[:limit]


def find_similar_events(title: str, start_at: datetime, *, limit: int = 5) -> list[Event]:
    raw = title.strip()
    if not raw:
        return []
    day_start = timezone.localtime(start_at).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    qs = Event.objects.filter(start_at__gte=day_start, start_at__lt=day_end)
    raw_l = raw.lower()
    results: list[Event] = []
    for event in qs:
        if raw_l in event.title.lower() or event.title.lower() in raw_l:
            results.append(event)
    if not results:
        results = list(qs.filter(title__icontains=raw)[:limit])
    return results[:limit]


def find_similar_notes(content: str, *, limit: int = 3) -> list[Note]:
    raw = content.strip()
    if not raw:
        return []
    if Note.objects.filter(embedding__isnull=False).exists():
        try:
            vector = embed_document(raw)
            return list(
                Note.objects.filter(embedding__isnull=False)
                .annotate(distance=CosineDistance("embedding", vector))
                .filter(distance__lte=NOTE_COSINE_MAX_DISTANCE)
                .order_by("distance")[:limit]
            )
        except Exception:
            pass
    raw_l = raw.lower()
    results: list[Note] = []
    for note in Note.objects.order_by("-created_at")[:80]:
        if raw_l in note.content.lower() or note.content.lower() in raw_l:
            results.append(note)
            if len(results) >= limit:
                break
    return results


def format_match_lines(kind: str, labels: list[str]) -> str:
    bullets = "\n".join(f"  – {label}" for label in labels)
    return f"⚠️ Já existe algo parecido ({kind}):\n{bullets}"
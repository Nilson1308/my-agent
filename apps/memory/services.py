from __future__ import annotations

import logging
from datetime import date, datetime

from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.ai.embeddings_service import embed_document, embed_query
from apps.ai.llm_outcomes import LLM_OK
from apps.ai.schemas import AgentAction, AgentPlan

logger = logging.getLogger(__name__)

NOTE_COSINE_MAX_DISTANCE = 0.45
NOTE_VECTOR_TOP_K = 5

from apps.memory.models import (
    DomainContext,
    Event,
    InteractionLog,
    InputType,
    Note,
    ShoppingItem,
    Task,
    TaskStatus,
)


def execute_agent_plan(
    plan: AgentPlan,
    raw_input: str,
    input_type: str = "text",
    llm_outcome: str = LLM_OK,
) -> str:
    """Executa ações do plano no banco e persiste InteractionLog."""
    lines: list[str] = []

    for action in plan.actions:
        try:
            line = _dispatch_action(action)
            if line:
                lines.append(line)
        except Exception as exc:
            lines.append(f"• Falha em {action.type}: {exc}")

    if not lines and plan.reply_hint:
        lines.append(plan.reply_hint)
    elif plan.reply_hint and lines:
        lines.append(f"— {plan.reply_hint}")

    if not lines:
        lines.append("Nada a registrar ou consultar nesta mensagem.")

    response = "\n".join(lines)

    parsed = plan.model_dump(mode="json")
    valid_input_types = {choice.value for choice in InputType}
    if input_type not in valid_input_types:
        input_type = InputType.TEXT

    InteractionLog.objects.create(
        raw_input=raw_input,
        input_type=input_type,
        parsed_json=parsed,
        bot_response=response,
        llm_outcome=llm_outcome,
    )

    return response


def _dispatch_action(action: AgentAction) -> str | None:
    handlers = {
        "add_shopping": _add_shopping,
        "mark_shopping_bought": _mark_shopping_bought,
        "remove_shopping": _remove_shopping,
        "dedupe_shopping": _dedupe_shopping,
        "list_shopping": _list_shopping,
        "add_task": _add_task,
        "complete_task": _complete_task,
        "delete_task": _delete_task,
        "clear_tasks": _clear_tasks,
        "list_tasks": _list_tasks,
        "add_event": _add_event,
        "delete_event": _delete_event,
        "clear_events": _clear_events,
        "list_events": _list_events,
        "add_note": _add_note,
        "search_notes": _search_notes,
        "summarize": _summarize,
    }
    handler = handlers.get(action.type)
    if not handler:
        return f"• Ação desconhecida: {action.type}"
    return handler(action)


def _default_context(action: AgentAction) -> str:
    return action.context or DomainContext.PESSOAL


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    if "T" in cleaned:
        cleaned = cleaned.split("T", 1)[0]
    return date.fromisoformat(cleaned)


def _parse_iso_datetime(value: str | None) -> datetime:
    if not value:
        raise ValueError("start_at obrigatório")
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _normalize_item_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _add_shopping(action: AgentAction) -> str:
    name = (action.item_name or action.title or "").strip()
    if not name:
        raise ValueError("item_name obrigatório")
    qty = (action.quantity or "").strip()
    if qty and (qty.startswith("-") or (qty.isdigit() and int(qty) < 0)):
        raise ValueError("quantity inválida; use remove_shopping ou dedupe_shopping para remover itens")
    existing = ShoppingItem.objects.filter(is_bought=False, name__iexact=name).first()
    if existing:
        if qty and qty != existing.quantity:
            existing.quantity = qty
            existing.save(update_fields=["quantity"])
        suffix = f" ({existing.quantity})" if existing.quantity else ""
        return f"🛒 Mercado: já na lista — {existing.name}{suffix}"
    ShoppingItem.objects.create(name=name.strip(), quantity=qty)
    suffix = f" ({qty})" if qty else ""
    return f"🛒 Mercado: + {name}{suffix}"


def _mark_shopping_bought(action: AgentAction) -> str:
    name = (action.item_name or "").strip()
    qs = ShoppingItem.objects.filter(is_bought=False)
    if name:
        qs = qs.filter(Q(name__iexact=name) | Q(name__icontains=name))
    updated = list(qs[:20])
    if not updated:
        label = name or "itens"
        return f"🛒 Mercado: nenhum pendente para “{label}”"
    now = timezone.now()
    for item in updated:
        item.is_bought = True
        item.bought_at = now
        item.save(update_fields=["is_bought", "bought_at"])
    names = ", ".join(i.name for i in updated)
    return f"🛒 Mercado: comprado — {names}"


def _remove_shopping(action: AgentAction) -> str:
    name = (action.item_name or action.title or "").strip()
    if not name:
        raise ValueError("item_name obrigatório para remover")
    qs = ShoppingItem.objects.filter(is_bought=False).filter(
        Q(name__iexact=name) | Q(name__icontains=name)
    )
    items = list(qs)
    if not items:
        return f"🛒 Mercado: nada para remover (“{name}”)"
    labels = ", ".join(i.name for i in items)
    removed, _ = qs.delete()
    return f"🛒 Mercado: removido — {labels} ({removed} registro(s))"


def _dedupe_shopping(_action: AgentAction) -> str:
    pending = list(
        ShoppingItem.objects.filter(is_bought=False).order_by("created_at", "id")
    )
    if not pending:
        return "🛒 Mercado: lista vazia, nada a deduplicar"
    seen: set[str] = set()
    duplicate_ids: list[int] = []
    for item in pending:
        key = _normalize_item_name(item.name)
        if key in seen:
            duplicate_ids.append(item.pk)
        else:
            seen.add(key)
    if not duplicate_ids:
        return f"🛒 Mercado: sem duplicatas ({len(seen)} itens únicos)"
    removed, _ = ShoppingItem.objects.filter(pk__in=duplicate_ids).delete()
    return (
        f"🛒 Mercado: {removed} duplicata(s) removida(s); "
        f"{len(seen)} item(ns) únicos na lista"
    )


def format_active_shopping_list() -> tuple[str, int]:
    """Texto da lista de compras ativa e quantidade de itens."""
    items = list(ShoppingItem.objects.filter(is_bought=False).order_by("name"))
    if not items:
        return "", 0
    bullet = "\n".join(
        f"  – {i.name}" + (f" ({i.quantity})" if i.quantity else "") for i in items
    )
    return f"🛒 Lista de mercado ({len(items)}):\n{bullet}", len(items)


def _list_shopping(_action: AgentAction) -> str:
    message, count = format_active_shopping_list()
    if count == 0:
        return "🛒 Mercado: lista vazia"
    return message


def _add_task(action: AgentAction) -> str:
    title = (action.title or action.content or "").strip()
    if not title:
        raise ValueError("title obrigatório")
    ctx = _default_context(action)
    Task.objects.create(
        title=title,
        context=ctx,
        due_date=_parse_iso_date(action.due_date),
    )
    due = f" até {_format_date(action.due_date)}" if action.due_date else ""
    return f"✅ Tarefa [{ctx}]: {title}{due}"


def _complete_task(action: AgentAction) -> str:
    title = (action.title or "").strip()
    qs = Task.objects.filter(status=TaskStatus.PENDING)
    if title:
        qs = qs.filter(Q(title__iexact=title) | Q(title__icontains=title))
    tasks = list(qs[:20])
    if not tasks:
        return f"✅ Tarefa: nada pendente para “{title or '…'}”"
    for task in tasks:
        task.status = TaskStatus.DONE
        task.save(update_fields=["status"])
    names = ", ".join(t.title for t in tasks)
    return f"✅ Tarefa concluída: {names}"


def _clear_tasks(action: AgentAction) -> str:
    qs = Task.objects.filter(status=TaskStatus.PENDING)
    if action.context:
        qs = qs.filter(context=action.context)
    tasks = list(qs)
    if not tasks:
        label = f" [{action.context}]" if action.context else ""
        return f"✅ Tarefas{label}: nenhuma pendente para remover"
    count = len(tasks)
    Task.objects.filter(pk__in=[t.pk for t in tasks]).delete()
    ctx = f" (contexto {action.context})" if action.context else ""
    return f"🗑️ {count} tarefa(s) pendente(s) removida(s){ctx}"


def _delete_task(action: AgentAction) -> str:
    title = (action.title or action.content or "").strip()
    if not title:
        return _clear_tasks(action)
    qs = Task.objects.filter(Q(title__iexact=title) | Q(title__icontains=title))
    tasks = list(qs[:20])
    if not tasks:
        return f"✅ Tarefa: nenhuma encontrada para excluir (“{title}”)"
    names = ", ".join(t.title for t in tasks)
    Task.objects.filter(pk__in=[t.pk for t in tasks]).delete()
    return f"🗑️ Tarefa excluída: {names}"


def _list_tasks(action: AgentAction) -> str:
    qs = Task.objects.filter(status=TaskStatus.PENDING).order_by("due_date", "-created_at")
    if action.context:
        qs = qs.filter(context=action.context)
    tasks = list(qs[:30])
    if not tasks:
        return "✅ Tarefas: nenhuma pendente"
    lines = []
    for t in tasks:
        due = f" · {t.due_date:%d/%m}" if t.due_date else ""
        lines.append(f"  – [{t.context}] {t.title}{due}")
    return "✅ Tarefas pendentes:\n" + "\n".join(lines)


def _add_event(action: AgentAction) -> str:
    title = (action.title or action.content or "").strip()
    if not title:
        raise ValueError("title obrigatório")
    start = _parse_iso_datetime(action.start_at)
    ctx = _default_context(action)
    Event.objects.create(title=title, context=ctx, start_at=start)
    return f"📅 Compromisso [{ctx}]: {title} · {start.astimezone():%d/%m %H:%M}"


def _clear_events(action: AgentAction) -> str:
    now = timezone.now()
    qs = Event.objects.filter(start_at__gte=now)
    if action.context:
        qs = qs.filter(context=action.context)
    events = list(qs)
    if not events:
        label = f" [{action.context}]" if action.context else ""
        return f"📅 Compromissos{label}: nenhum futuro para remover"
    count = len(events)
    Event.objects.filter(pk__in=[e.pk for e in events]).delete()
    ctx = f" (contexto {action.context})" if action.context else ""
    return f"🗑️ {count} compromisso(s) futuro(s) removido(s){ctx}"


def _delete_event(action: AgentAction) -> str:
    title = (action.title or action.content or "").strip()
    if not title:
        return _clear_events(action)
    qs = Event.objects.filter(Q(title__iexact=title) | Q(title__icontains=title))
    events = list(qs[:20])
    if not events:
        return f"📅 Compromisso: nenhum encontrado (“{title}”)"
    names = ", ".join(e.title for e in events)
    Event.objects.filter(pk__in=[e.pk for e in events]).delete()
    return f"🗑️ Compromisso excluído: {names}"


def _list_events(_action: AgentAction) -> str:
    now = timezone.now()
    events = Event.objects.filter(start_at__gte=now).order_by("start_at")[:20]
    if not events:
        return "📅 Agenda: sem compromissos futuros"
    lines = [
        f"  – [{e.context}] {e.title} · {e.start_at.astimezone():%d/%m %H:%M}"
        for e in events
    ]
    return "📅 Próximos compromissos:\n" + "\n".join(lines)


def _add_note(action: AgentAction) -> str:
    content = (action.content or action.title or "").strip()
    if not content:
        raise ValueError("content obrigatório")
    ctx = _default_context(action)
    embedding: list[float] | None = None
    try:
        embedding = embed_document(content)
    except Exception:
        logger.exception("Falha ao gerar embedding da nota; salvando sem vetor")
    Note.objects.create(content=content, context=ctx, embedding=embedding)
    preview = content if len(content) <= 60 else content[:57] + "…"
    return f"💡 Nota [{ctx}]: {preview}"


def _format_note_results(query: str, notes: list[Note]) -> str:
    if not notes:
        return f"💡 Memória: nada para “{query}”"
    lines = []
    for note in notes:
        preview = note.content if len(note.content) <= 80 else note.content[:77] + "…"
        lines.append(f"  – [{note.context}] {preview}")
    return f"💡 Memória (“{query}”):\n" + "\n".join(lines)


def _search_notes_icontains(query: str) -> str:
    notes = list(Note.objects.filter(content__icontains=query).order_by("-created_at")[:10])
    return _format_note_results(query, notes)


def _search_notes_vector(query: str) -> list[Note]:
    query_vector = embed_query(query)
    return list(
        Note.objects.filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lte=NOTE_COSINE_MAX_DISTANCE)
        .order_by("distance")[:NOTE_VECTOR_TOP_K]
    )


def _summarize(_action: AgentAction) -> str:
    parts: list[str] = []
    shopping, _ = format_active_shopping_list()
    parts.append(shopping if shopping else "🛒 Mercado: lista vazia")

    tasks = list(
        Task.objects.filter(status=TaskStatus.PENDING).order_by("due_date", "-created_at")[:15]
    )
    if tasks:
        task_lines = [
            f"  – [{t.context}] {t.title}"
            + (f" · {t.due_date:%d/%m}" if t.due_date else "")
            for t in tasks
        ]
        parts.append("✅ Tarefas pendentes:\n" + "\n".join(task_lines))
    else:
        parts.append("✅ Tarefas: nenhuma pendente")

    now = timezone.now()
    events = list(Event.objects.filter(start_at__gte=now).order_by("start_at")[:10])
    if events:
        event_lines = [
            f"  – [{e.context}] {e.title} · {e.start_at.astimezone():%d/%m %H:%M}"
            for e in events
        ]
        parts.append("📅 Próximos compromissos:\n" + "\n".join(event_lines))
    else:
        parts.append("📅 Agenda: sem compromissos futuros")

    notes = list(Note.objects.order_by("-created_at")[:5])
    if notes:
        note_lines = []
        for note in notes:
            preview = note.content if len(note.content) <= 60 else note.content[:57] + "…"
            note_lines.append(f"  – [{note.context}] {preview}")
        parts.append("💡 Notas recentes:\n" + "\n".join(note_lines))

    return "\n".join(parts)


def _search_notes(action: AgentAction) -> str:
    query = (action.query or action.content or "").strip()
    if not query:
        notes = list(Note.objects.order_by("-created_at")[:5])
        if not notes:
            return "💡 Memória: sem notas salvas"
        lines = []
        for note in notes:
            preview = note.content if len(note.content) <= 80 else note.content[:77] + "…"
            lines.append(f"  – [{note.context}] {preview}")
        return "💡 Últimas notas:\n" + "\n".join(lines)

    if not Note.objects.filter(embedding__isnull=False).exists():
        return _search_notes_icontains(query)

    try:
        notes = _search_notes_vector(query)
        return _format_note_results(query, notes)
    except Exception:
        logger.exception("Falha na busca vetorial; usando icontains")
        return _search_notes_icontains(query)


def _format_date(iso: str) -> str:
    try:
        parsed = _parse_iso_date(iso)
        if parsed is None:
            return iso
        return parsed.strftime("%d/%m")
    except ValueError:
        return iso
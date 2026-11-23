from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.ai.embeddings_service import embed_document, embed_query
from apps.ai.llm_outcomes import LLM_OK
from apps.ai.schemas import AgentAction, AgentPlan

logger = logging.getLogger(__name__)

NOTE_COSINE_MAX_DISTANCE = 0.45
NOTE_VECTOR_TOP_K = 5

from apps.memory.confirmation import ConfirmationPrompt, create_pending
from apps.memory.reply_types import AgentReply
from apps.memory.duplicate_detection import (
    find_similar_events,
    find_similar_notes,
    find_similar_shopping,
    find_similar_tasks,
    format_match_lines,
)
from apps.memory.effects import EffectRecorder
from apps.memory.models import (
    DomainContext,
    Event,
    InteractionLog,
    InputType,
    Note,
    Reminder,
    ShoppingItem,
    Task,
    TaskStatus,
)


def execute_stored_action(
    action: AgentAction,
    *,
    force: bool = True,
    recorder: EffectRecorder | None = None,
) -> str:
    line = _dispatch_action(
        action, force=force, telegram_user_id=None, recorder=recorder
    )
    if isinstance(line, ConfirmationPrompt):
        return line.text
    return line or "Registrado."


def execute_agent_plan(
    plan: AgentPlan,
    raw_input: str,
    input_type: str = "text",
    llm_outcome: str = LLM_OK,
    telegram_user_id: int | None = None,
) -> AgentReply:
    """Executa ações do plano no banco e persiste InteractionLog."""
    lines: list[str] = []
    pending_confirmation_id: int | None = None
    recorder = EffectRecorder()

    for action in plan.actions:
        try:
            line = _dispatch_action(
                action,
                force=False,
                telegram_user_id=telegram_user_id,
                recorder=recorder,
            )
            if isinstance(line, ConfirmationPrompt):
                lines.append(line.text)
                pending_confirmation_id = line.pending_id
            elif line:
                lines.append(line)
        except Exception as exc:
            lines.append(f"• Falha em {action.type}: {exc}")

    if plan.reply_hint:
        hint = plan.reply_hint.strip()
        if hint:
            lines.insert(0, f"💡 {hint}")

    if not lines:
        lines.append("Nada a registrar ou consultar nesta mensagem.")

    response = "\n".join(lines)

    parsed = plan.model_dump(mode="json")
    valid_input_types = {choice.value for choice in InputType}
    if input_type not in valid_input_types:
        input_type = InputType.TEXT

    effects = [] if pending_confirmation_id else recorder.effects
    log = InteractionLog.objects.create(
        raw_input=raw_input,
        input_type=input_type,
        parsed_json=parsed,
        bot_response=response,
        llm_outcome=llm_outcome,
        telegram_user_id=telegram_user_id,
        effects_json=effects,
    )

    return AgentReply(
        message=response,
        pending_confirmation_id=pending_confirmation_id,
        interaction_log_id=log.pk if pending_confirmation_id is None else None,
        telegram_user_id=telegram_user_id,
    )


_TELEGRAM_AWARE = frozenset(
    {
        "add_shopping",
        "add_task",
        "add_event",
        "add_note",
        "clear_tasks",
        "clear_events",
        "delete_task",
        "delete_event",
    }
)


def _dispatch_action(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt | None:
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
        "list_tasks_done": _list_tasks_done,
        "add_event": _add_event,
        "delete_event": _delete_event,
        "clear_events": _clear_events,
        "list_events": _list_events,
        "add_note": _add_note,
        "search_notes": _search_notes,
        "summarize": _summarize,
        "schedule_reminder": _schedule_reminder,
        "list_reminders": _list_reminders,
        "cancel_reminder": _cancel_reminder,
    }
    handler = handlers.get(action.type)
    if not handler:
        return f"• Ação desconhecida: {action.type}"
    recorder_kw = {"recorder": recorder} if recorder is not None else {}
    mutate_with_recorder = {
        "add_shopping",
        "add_task",
        "add_event",
        "add_note",
        "clear_tasks",
        "clear_events",
        "delete_task",
        "delete_event",
        "complete_task",
        "schedule_reminder",
    }
    if action.type in _TELEGRAM_AWARE:
        return handler(
            action,
            force=force,
            telegram_user_id=telegram_user_id,
            **recorder_kw,
        )
    if action.type in mutate_with_recorder:
        return handler(action, **recorder_kw)
    return handler(action)


def _default_context(action: AgentAction, telegram_user_id: int | None = None) -> str:
    if action.context:
        return action.context
    from apps.memory.preferences import default_context_for_user

    pref = default_context_for_user(telegram_user_id)
    return pref or DomainContext.PESSOAL


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


def _parse_task_due(
    action: AgentAction,
) -> tuple[date | None, datetime | None]:
    raw = (action.due_at or action.due_date or "").strip()
    if not raw:
        return None, None
    if "T" in raw or (" " in raw and ":" in raw):
        dt = _parse_iso_datetime(raw)
        return dt.date(), dt
    return _parse_iso_date(raw), None


def _normalize_item_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _add_shopping(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    name = (action.item_name or action.title or "").strip()
    if not name:
        raise ValueError("item_name obrigatório")
    qty = (action.quantity or "").strip()
    if qty and (qty.startswith("-") or (qty.isdigit() and int(qty) < 0)):
        raise ValueError("quantity inválida; use remove_shopping ou dedupe_shopping para remover itens")
    matches = find_similar_shopping(name)
    if matches and not force:
        labels = [f"{i.name}" + (f" ({i.quantity})" if i.quantity else "") for i in matches]
        prompt = format_match_lines("mercado", labels)
        if telegram_user_id is None:
            return prompt + "\n(envie de novo após decidir; confirmação via Telegram)"
        return create_pending(telegram_user_id, action, prompt)
    if force:
        exact = ShoppingItem.objects.filter(is_bought=False, name__iexact=name).first()
        if exact:
            if qty and qty != exact.quantity:
                exact.quantity = qty
                exact.save(update_fields=["quantity"])
            suffix = f" ({exact.quantity})" if exact.quantity else ""
            return f"🛒 Mercado: confirmado — {exact.name}{suffix}"
    item = ShoppingItem.objects.create(name=name.strip(), quantity=qty)
    if recorder:
        recorder.record_created(item)
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


def _add_task(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    title = (action.title or action.content or "").strip()
    if not title:
        raise ValueError("title obrigatório")
    ctx = _default_context(action, telegram_user_id)
    due, due_at = _parse_task_due(action)
    matches = find_similar_tasks(title, context=ctx, due_date=due)
    if matches and not force:
        labels = [
            f"[{t.context}] {t.title}"
            + (f" · {t.due_date:%d/%m}" if t.due_date else "")
            for t in matches
        ]
        prompt = format_match_lines("tarefa", labels)
        if telegram_user_id is None:
            return prompt
        return create_pending(telegram_user_id, action, prompt)
    task = Task.objects.create(
        title=title,
        context=ctx,
        due_date=due,
        due_at=due_at,
    )
    if recorder:
        recorder.record_created(task)
    extra = ""
    if due_at:
        extra = f" · {timezone.localtime(due_at):%d/%m %H:%M}"
    elif due:
        extra = f" até {due:%d/%m}"
    remind_raw = (action.remind_at or "").strip()
    if due_at and remind_raw:
        try:
            remind_at = _parse_iso_datetime(remind_raw)
            if remind_at > timezone.now():
                rem = Reminder.objects.create(
                    title=f"Tarefa: {title}",
                    message=title,
                    context=ctx,
                    remind_at=remind_at,
                )
                if recorder:
                    recorder.record_created(rem)
                extra += f"\n⏰ Lembrete · {timezone.localtime(remind_at):%d/%m %H:%M}"
        except ValueError:
            pass
    return f"✅ Tarefa [{ctx}]: {title}{extra}"


def _complete_task(
    action: AgentAction, *, recorder: EffectRecorder | None = None
) -> str:
    title = (action.title or "").strip()
    qs = Task.objects.filter(status=TaskStatus.PENDING)
    if title:
        qs = qs.filter(Q(title__iexact=title) | Q(title__icontains=title))
    tasks = list(qs[:20])
    if not tasks:
        return f"✅ Tarefa: nada pendente para “{title or '…'}”"
    now = timezone.now()
    for task in tasks:
        if recorder:
            recorder.record_updated(
                task,
                {
                    "status": task.status,
                    "completed_at": task.completed_at,
                },
            )
        task.status = TaskStatus.DONE
        task.completed_at = now
        task.save(update_fields=["status", "completed_at"])
    names = ", ".join(t.title for t in tasks)
    return (
        f"✅ Tarefa concluída e mantida no histórico: {names}\n"
        f"(diga “remover” ou delete_task se quiser apagar do registro.)"
    )


def _clear_tasks(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    qs = Task.objects.filter(status=TaskStatus.PENDING)
    if action.context:
        qs = qs.filter(context=action.context)
    tasks = list(qs)
    if not tasks:
        label = f" [{action.context}]" if action.context else ""
        return f"✅ Tarefas{label}: nenhuma pendente para remover"
    count = len(tasks)
    if not force and telegram_user_id:
        ctx = f" [{action.context}]" if action.context else ""
        prompt = f"⚠️ Isso remove {count} tarefa(s) pendente(s){ctx}."
        return create_pending(telegram_user_id, action, prompt)
    for task in tasks:
        if recorder:
            recorder.record_deleted(task)
    Task.objects.filter(pk__in=[t.pk for t in tasks]).delete()
    ctx = f" (contexto {action.context})" if action.context else ""
    return f"🗑️ {count} tarefa(s) pendente(s) removida(s){ctx}"


def _delete_task(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    title = (action.title or action.content or "").strip()
    if not title:
        return _clear_tasks(
            action,
            force=force,
            telegram_user_id=telegram_user_id,
            recorder=recorder,
        )
    qs = Task.objects.filter(Q(title__iexact=title) | Q(title__icontains=title))
    tasks = list(qs[:20])
    if not tasks:
        return f"✅ Tarefa: nenhuma encontrada para excluir (“{title}”)"
    if not force and telegram_user_id and len(tasks) > 1:
        names = ", ".join(t.title for t in tasks[:5])
        prompt = f"⚠️ Excluir {len(tasks)} tarefa(s)? Ex.: {names}"
        return create_pending(telegram_user_id, action, prompt)
    for task in tasks:
        if recorder:
            recorder.record_deleted(task)
    names = ", ".join(t.title for t in tasks)
    Task.objects.filter(pk__in=[t.pk for t in tasks]).delete()
    return f"🗑️ Tarefa excluída: {names}"


def _list_tasks_done(_action: AgentAction) -> str:
    since = timezone.now() - timedelta(days=7)
    tasks = list(
        Task.objects.filter(status=TaskStatus.DONE, completed_at__gte=since).order_by(
            "-completed_at"
        )[:25]
    )
    if not tasks:
        return "✅ Nenhuma tarefa concluída nos últimos 7 dias."
    lines = []
    for t in tasks:
        when = (
            f" · concluída {timezone.localtime(t.completed_at):%d/%m %H:%M}"
            if t.completed_at
            else ""
        )
        lines.append(f"  – [{t.context}] {t.title}{when}")
    return "✅ Tarefas concluídas (recentes):\n" + "\n".join(lines)


def _list_tasks(action: AgentAction) -> str:
    qs = Task.objects.filter(status=TaskStatus.PENDING).order_by("due_date", "-created_at")
    if action.context:
        qs = qs.filter(context=action.context)
    tasks = list(qs[:30])
    if not tasks:
        return "✅ Tarefas: nenhuma pendente"
    lines = []
    for t in tasks:
        if t.due_at:
            due = f" · {timezone.localtime(t.due_at):%d/%m %H:%M}"
        elif t.due_date:
            due = f" · {t.due_date:%d/%m}"
        else:
            due = ""
        lines.append(f"  – [{t.context}] {t.title}{due}")
    return "✅ Tarefas pendentes:\n" + "\n".join(lines)


def _add_event(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    title = (action.title or action.content or "").strip()
    if not title:
        raise ValueError("title obrigatório")
    start = _parse_iso_datetime(action.start_at)
    ctx = _default_context(action, telegram_user_id)
    matches = find_similar_events(title, start)
    if matches and not force:
        labels = [
            f"[{e.context}] {e.title} · {e.start_at.astimezone():%d/%m %H:%M}"
            for e in matches
        ]
        prompt = format_match_lines("compromisso", labels)
        if telegram_user_id is None:
            return prompt
        return create_pending(telegram_user_id, action, prompt)
    event = Event.objects.create(title=title, context=ctx, start_at=start)
    if recorder:
        recorder.record_created(event)
    return f"📅 Compromisso [{ctx}]: {title} · {start.astimezone():%d/%m %H:%M}"


def _schedule_reminder(
    action: AgentAction, *, recorder: EffectRecorder | None = None
) -> str:
    title = (action.title or action.content or "").strip()
    if not title:
        raise ValueError("title obrigatório")
    when_raw = action.remind_at or action.start_at
    if not when_raw:
        raise ValueError("remind_at obrigatório")
    remind_at = _parse_iso_datetime(when_raw)
    if remind_at <= timezone.now():
        raise ValueError("remind_at deve ser no futuro")
    ctx = _default_context(action, None)
    message = (action.content or "").strip() or title
    reminder = Reminder.objects.create(
        title=title,
        message=message,
        context=ctx,
        remind_at=remind_at,
    )
    if recorder:
        recorder.record_created(reminder)
    local = timezone.localtime(remind_at)
    return f"⏰ Lembrete [{ctx}]: {title} · {local:%d/%m às %H:%M}"


def _list_reminders(_action: AgentAction) -> str:
    now = timezone.now()
    items = list(
        Reminder.objects.filter(reminded=False, remind_at__gte=now).order_by("remind_at")[:20]
    )
    if not items:
        return "⏰ Sem lembretes futuros agendados."
    lines = [
        f"  – [{r.context}] {r.title} · {timezone.localtime(r.remind_at):%d/%m %H:%M}"
        for r in items
    ]
    return "⏰ Lembretes agendados:\n" + "\n".join(lines)


def _cancel_reminder(action: AgentAction) -> str:
    title = (action.title or action.content or "").strip()
    qs = Reminder.objects.filter(reminded=False)
    if title:
        qs = qs.filter(title__icontains=title)
    reminders = list(qs[:20])
    if not reminders:
        return f"⏰ Nenhum lembrete ativo para “{title or '…'}”"
    count = len(reminders)
    Reminder.objects.filter(pk__in=[r.pk for r in reminders]).delete()
    names = ", ".join(r.title for r in reminders)
    return f"⏰ {count} lembrete(s) cancelado(s): {names}"


def _clear_events(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    now = timezone.now()
    qs = Event.objects.filter(start_at__gte=now)
    if action.context:
        qs = qs.filter(context=action.context)
    events = list(qs)
    if not events:
        label = f" [{action.context}]" if action.context else ""
        return f"📅 Compromissos{label}: nenhum futuro para remover"
    count = len(events)
    if not force and telegram_user_id:
        ctx = f" [{action.context}]" if action.context else ""
        prompt = f"⚠️ Remover {count} compromisso(s) futuro(s){ctx}?"
        return create_pending(telegram_user_id, action, prompt)
    for event in events:
        if recorder:
            recorder.record_deleted(event)
    Event.objects.filter(pk__in=[e.pk for e in events]).delete()
    ctx = f" (contexto {action.context})" if action.context else ""
    return f"🗑️ {count} compromisso(s) futuro(s) removido(s){ctx}"


def _delete_event(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    title = (action.title or action.content or "").strip()
    if not title:
        return _clear_events(
            action,
            force=force,
            telegram_user_id=telegram_user_id,
            recorder=recorder,
        )
    qs = Event.objects.filter(Q(title__iexact=title) | Q(title__icontains=title))
    events = list(qs[:20])
    if not events:
        return f"📅 Compromisso: nenhum encontrado (“{title}”)"
    if not force and telegram_user_id and len(events) > 1:
        prompt = f"⚠️ Excluir {len(events)} compromisso(s) com “{title}”?"
        return create_pending(telegram_user_id, action, prompt)
    for event in events:
        if recorder:
            recorder.record_deleted(event)
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


def _add_note(
    action: AgentAction,
    *,
    force: bool = False,
    telegram_user_id: int | None = None,
    recorder: EffectRecorder | None = None,
) -> str | ConfirmationPrompt:
    content = (action.content or action.title or "").strip()
    if not content:
        raise ValueError("content obrigatório")
    ctx = _default_context(action, telegram_user_id)
    matches = find_similar_notes(content)
    if matches and not force:
        labels = []
        for note in matches:
            preview = note.content if len(note.content) <= 50 else note.content[:47] + "…"
            labels.append(f"[{note.context}] {preview}")
        prompt = format_match_lines("nota", labels)
        if telegram_user_id is None:
            return prompt
        return create_pending(telegram_user_id, action, prompt)
    embedding: list[float] | None = None
    try:
        embedding = embed_document(content)
    except Exception:
        logger.exception("Falha ao gerar embedding da nota; salvando sem vetor")
    note = Note.objects.create(content=content, context=ctx, embedding=embedding)
    if recorder:
        recorder.record_created(note)
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

    done_recent = list(
        Task.objects.filter(status=TaskStatus.DONE, completed_at__isnull=False)
        .order_by("-completed_at")[:5]
    )
    if done_recent:
        done_lines = [
            f"  – [{t.context}] {t.title}"
            + (
                f" · {timezone.localtime(t.completed_at):%d/%m %H:%M}"
                if t.completed_at
                else ""
            )
            for t in done_recent
        ]
        parts.append("✅ Concluídas recentemente:\n" + "\n".join(done_lines))

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
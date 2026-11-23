from __future__ import annotations

from apps.ai.schemas import AgentAction, AgentPlan
from apps.memory.reply_types import AgentReply
from apps.memory.review_today import build_today_digest
from apps.memory.services import execute_agent_plan, format_active_shopping_list


def _list_mercado() -> str:
    text, count = format_active_shopping_list()
    if count == 0:
        return "🛒 Mercado: lista vazia"
    return text


def execute_direct_command(
    command: str,
    args: list[str] | None = None,
    telegram_user_id: int | None = None,
) -> AgentReply:
    """Comandos Telegram sem passar pelo Groq."""
    args = args or []
    cmd = command.strip().lower().lstrip("/")
    sub = args[0].lower() if args else ""

    if cmd == "lista":
        if sub in ("tarefas", "task", "tasks"):
            plan = AgentPlan(actions=[AgentAction(type="list_tasks")])
            return execute_agent_plan(
                plan,
                raw_input="/lista tarefas",
                input_type="text",
                telegram_user_id=telegram_user_id,
            )
        if sub in ("eventos", "agenda", "events"):
            plan = AgentPlan(actions=[AgentAction(type="list_events")])
            return execute_agent_plan(
                plan,
                raw_input="/lista eventos",
                input_type="text",
                telegram_user_id=telegram_user_id,
            )
        if sub in ("lembretes", "reminders"):
            plan = AgentPlan(actions=[AgentAction(type="list_reminders")])
            return execute_agent_plan(
                plan,
                raw_input="/lista lembretes",
                input_type="text",
                telegram_user_id=telegram_user_id,
            )
        if sub and sub in ("theo", "casa", "trabalho", "pessoal"):
            plan = AgentPlan(
                actions=[AgentAction(type="list_tasks", context=sub)]  # type: ignore[arg-type]
            )
            msg = execute_agent_plan(
                plan,
                raw_input=f"/lista {sub}",
                input_type="text",
                telegram_user_id=telegram_user_id,
            ).message
            mercado = _list_mercado()
            return AgentReply(message=f"{mercado}\n\n{msg}")
        return AgentReply(message=_list_mercado())

    if cmd == "resumo":
        plan = AgentPlan(actions=[AgentAction(type="summarize")])
        return execute_agent_plan(
            plan,
            raw_input="/resumo",
            input_type="text",
            telegram_user_id=telegram_user_id,
        )

    if cmd == "briefing":
        return AgentReply(message=build_today_digest(sub or None))

    return AgentReply(message=f"Comando /{cmd} não reconhecido. Use /help.")
from __future__ import annotations

from django.conf import settings

from apps.ai.groq_service import parse_user_message
from apps.memory.confirmation import handle_pending_reply
from apps.memory.models import InteractionChannel
from apps.memory.reply_types import AgentReply
from apps.memory.services import execute_agent_plan


def default_owner_user_id() -> int | None:
    raw = (settings.TELEGRAM_ALLOWED_USER_ID or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def run_agent_message(
    text: str,
    *,
    channel: str = InteractionChannel.TELEGRAM,
    input_type: str = "text",
    telegram_user_id: int | None = None,
) -> AgentReply:
    """
    Pipeline único: confirmação pendente → LLM → execute_agent_plan.
    Usado pelo Telegram e pelo PWA.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return AgentReply(message="Envie uma mensagem não vazia.")

    user_id = telegram_user_id if telegram_user_id is not None else default_owner_user_id()

    if user_id is not None:
        pending_reply = handle_pending_reply(user_id, cleaned)
        if pending_reply is not None:
            return AgentReply(message=pending_reply, telegram_user_id=user_id)

    parse_result = parse_user_message(cleaned)
    return execute_agent_plan(
        parse_result.plan,
        cleaned,
        input_type=input_type,
        llm_outcome=parse_result.outcome,
        telegram_user_id=user_id,
        channel=channel,
    )
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.ai.schemas import AgentAction
from apps.memory.models import PendingConfirmation

CONFIRM_RE = re.compile(
    r"^(sim|s|yes|pode|confirma|confirmar|duplica|duplicar|ok)[\s!.]*$",
    re.IGNORECASE,
)
CANCEL_RE = re.compile(
    r"^(não|nao|no|cancela|cancelar|n)[\s!.]*$",
    re.IGNORECASE,
)

PENDING_TTL_MINUTES = 15


@dataclass(frozen=True)
class ConfirmationPrompt:
    text: str
    pending_id: int


def _expire_stale() -> None:
    PendingConfirmation.objects.filter(expires_at__lt=timezone.now()).delete()


def get_active_pending(telegram_user_id: int) -> PendingConfirmation | None:
    _expire_stale()
    return (
        PendingConfirmation.objects.filter(telegram_user_id=telegram_user_id)
        .order_by("-created_at")
        .first()
    )


def create_pending(
    telegram_user_id: int,
    action: AgentAction,
    prompt_message: str,
) -> ConfirmationPrompt:
    _expire_stale()
    PendingConfirmation.objects.filter(telegram_user_id=telegram_user_id).delete()
    expires = timezone.now() + timedelta(minutes=PENDING_TTL_MINUTES)
    pending = PendingConfirmation.objects.create(
        telegram_user_id=telegram_user_id,
        action_type=action.type,
        payload_json=action.model_dump(mode="json"),
        prompt_message=prompt_message,
        expires_at=expires,
    )
    text = (
        f"{prompt_message}\n\n"
        "Incluir mesmo assim?\n"
        "Use os botões ou responda sim / não."
    )
    return ConfirmationPrompt(text=text, pending_id=pending.pk)


def resolve_pending(
    telegram_user_id: int,
    pending_id: int,
    *,
    confirm: bool,
) -> str:
    _expire_stale()
    pending = PendingConfirmation.objects.filter(
        pk=pending_id, telegram_user_id=telegram_user_id
    ).first()
    if not pending:
        return "Essa confirmação expirou. Envie o pedido de novo."

    if not confirm:
        pending.delete()
        return "Ok, não incluí."

    from apps.memory.services import execute_stored_action

    payload = pending.payload_json
    pending.delete()
    action = AgentAction.model_validate(payload)
    return execute_stored_action(action, force=True)


def handle_pending_reply(telegram_user_id: int, text: str) -> str | None:
    """Retorna mensagem se consumiu a resposta; None se não há pendência."""
    pending = get_active_pending(telegram_user_id)
    if not pending:
        return None

    stripped = text.strip()
    if CONFIRM_RE.match(stripped):
        return resolve_pending(telegram_user_id, pending.pk, confirm=True)

    if CANCEL_RE.match(stripped):
        return resolve_pending(telegram_user_id, pending.pk, confirm=False)

    return (
        f"Ainda aguardando sobre:\n{pending.prompt_message}\n\n"
        "Use os botões ou responda sim / não."
    )
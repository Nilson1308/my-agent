from __future__ import annotations

from apps.memory.models import InteractionLog


def apply_interaction_feedback(
    telegram_user_id: int,
    log_id: int,
    *,
    positive: bool,
) -> str:
    log = InteractionLog.objects.filter(pk=log_id, telegram_user_id=telegram_user_id).first()
    if not log:
        return "Não encontrei essa interação."
    value = 1 if positive else -1
    if log.user_feedback == value:
        return "Obrigado — já tinha seu feedback."
    log.user_feedback = value
    log.save(update_fields=["user_feedback"])
    return "👍 Valeu!" if positive else "👎 Anotado, vou ajustar o roteamento."
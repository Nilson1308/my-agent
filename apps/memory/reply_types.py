from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentReply:
    """Resposta ao usuário; `pending_confirmation_id` aciona teclado inline no Telegram."""

    message: str
    pending_confirmation_id: int | None = None
    interaction_log_id: int | None = None
    telegram_user_id: int | None = None

    def __str__(self) -> str:
        return self.message
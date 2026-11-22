from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal[
    "add_shopping",
    "mark_shopping_bought",
    "remove_shopping",
    "dedupe_shopping",
    "list_shopping",
    "add_task",
    "complete_task",
    "delete_task",
    "clear_tasks",
    "list_tasks",
    "add_event",
    "delete_event",
    "clear_events",
    "list_events",
    "add_note",
    "search_notes",
    "summarize",
]

DomainContext = Literal["casa", "theo", "trabalho", "pessoal"]


class AgentAction(BaseModel):
    type: ActionType
    item_name: str | None = None
    quantity: str | None = None
    title: str | None = None
    context: DomainContext | None = None
    due_date: str | None = Field(
        default=None,
        description="Data de vencimento (ISO 8601, ex: 2025-11-20)",
    )
    start_at: str | None = Field(
        default=None,
        description="Início do compromisso (ISO 8601 com timezone ou offset -03:00)",
    )
    content: str | None = None
    query: str | None = None


class AgentPlan(BaseModel):
    actions: list[AgentAction] = Field(default_factory=list)
    reply_hint: str = Field(
        default="",
        description="Tom sugerido para a resposta final ao usuário",
    )
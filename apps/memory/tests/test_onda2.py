from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.ai.schemas import AgentAction, AgentPlan
from apps.memory.models import InteractionLog, ShoppingItem, Task
from apps.memory.review_today import build_today_digest
from apps.memory.services import execute_agent_plan
from apps.memory.undo import undo_last_interaction


class Onda2Tests(TestCase):
    user_id = 424242

    def test_task_due_at(self) -> None:
        future = (timezone.now() + timedelta(days=1)).replace(hour=15, minute=30)
        plan = AgentPlan(
            actions=[
                AgentAction(
                    type="add_task",
                    title="Reunião sync",
                    context="trabalho",
                    due_at=future.isoformat(),
                )
            ]
        )
        reply = execute_agent_plan(
            plan, raw_input="tarefa", telegram_user_id=self.user_id
        )
        task = Task.objects.get(title="Reunião sync")
        self.assertIsNotNone(task.due_at)
        local = timezone.localtime(future)
        self.assertIn(f"{local:%H:%M}", reply.message)

    def test_undo_add_shopping(self) -> None:
        plan = AgentPlan(actions=[AgentAction(type="add_shopping", item_name="banana")])
        execute_agent_plan(plan, raw_input="banana", telegram_user_id=self.user_id)
        self.assertEqual(ShoppingItem.objects.filter(is_bought=False).count(), 1)
        msg = undo_last_interaction(self.user_id)
        self.assertIn("Desfeito", msg)
        self.assertEqual(ShoppingItem.objects.filter(is_bought=False).count(), 0)

    def test_interaction_log_has_effects(self) -> None:
        plan = AgentPlan(actions=[AgentAction(type="add_shopping", item_name="maçã")])
        execute_agent_plan(plan, raw_input="maçã", telegram_user_id=self.user_id)
        log = InteractionLog.objects.latest("created_at")
        self.assertEqual(log.telegram_user_id, self.user_id)
        self.assertTrue(log.effects_json)

    def test_hoje_digest(self) -> None:
        text = build_today_digest()
        self.assertIn("Revisão", text)
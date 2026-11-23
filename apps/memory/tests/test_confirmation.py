from __future__ import annotations

from django.test import TestCase
from django.utils import timezone

from apps.ai.schemas import AgentAction, AgentPlan
from apps.memory.confirmation import create_pending, handle_pending_reply
from apps.memory.models import PendingConfirmation, ShoppingItem
from apps.memory.services import execute_agent_plan


class ConfirmationFlowTests(TestCase):
    def test_confirm_duplicates_shopping(self) -> None:
        ShoppingItem.objects.create(name="leite")
        user_id = 999001
        action = AgentAction(type="add_shopping", item_name="leite")
        prompt = create_pending(user_id, action, "teste")
        self.assertIn("sim", prompt.text.lower())
        self.assertEqual(PendingConfirmation.objects.filter(telegram_user_id=user_id).count(), 1)

        reply = handle_pending_reply(user_id, "sim")
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertIn("leite", reply.lower())
        self.assertEqual(ShoppingItem.objects.filter(is_bought=False, name__iexact="leite").count(), 1)

    def test_cancel_pending(self) -> None:
        user_id = 999002
        action = AgentAction(type="add_shopping", item_name="ovos")
        create_pending(user_id, action, "dup")
        reply = handle_pending_reply(user_id, "não")
        self.assertIn("não incluí", reply.lower())
        self.assertEqual(PendingConfirmation.objects.filter(telegram_user_id=user_id).count(), 0)
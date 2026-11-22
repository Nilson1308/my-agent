from __future__ import annotations

from django.test import TestCase

from apps.ai.schemas import AgentAction, AgentPlan
from apps.memory.models import ShoppingItem
from apps.memory.services import execute_agent_plan, format_active_shopping_list


class ShoppingServicesTests(TestCase):
    def test_format_active_shopping_list_empty(self) -> None:
        text, count = format_active_shopping_list()
        self.assertEqual(count, 0)
        self.assertEqual(text, "")

    def test_format_active_shopping_list_with_items(self) -> None:
        ShoppingItem.objects.create(name="arroz")
        text, count = format_active_shopping_list()
        self.assertEqual(count, 1)
        self.assertIn("arroz", text)

    def test_execute_add_shopping(self) -> None:
        plan = AgentPlan(
            actions=[AgentAction(type="add_shopping", item_name="feijão")],
            reply_hint="ok",
        )
        response = execute_agent_plan(plan, raw_input="comprar feijão")
        self.assertIn("feijão", response.lower())
        self.assertEqual(ShoppingItem.objects.filter(is_bought=False).count(), 1)

    def test_add_shopping_no_duplicate_pending(self) -> None:
        plan = AgentPlan(
            actions=[AgentAction(type="add_shopping", item_name="Feijão")],
            reply_hint="ok",
        )
        execute_agent_plan(plan, raw_input="feijão")
        response = execute_agent_plan(plan, raw_input="feijão de novo")
        self.assertIn("já na lista", response.lower())
        self.assertEqual(ShoppingItem.objects.filter(is_bought=False).count(), 1)
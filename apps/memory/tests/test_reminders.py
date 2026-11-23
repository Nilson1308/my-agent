from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.ai.schemas import AgentAction, AgentPlan
from apps.memory.models import Reminder
from apps.memory.services import execute_agent_plan
from apps.memory.tasks import check_scheduled_reminders


class ReminderTests(TestCase):
    def test_schedule_reminder(self) -> None:
        future = (timezone.now() + timedelta(hours=2)).isoformat()
        plan = AgentPlan(
            actions=[
                AgentAction(
                    type="schedule_reminder",
                    title="Comprar lanche Theo",
                    remind_at=future,
                    context="theo",
                )
            ],
            reply_hint="ok",
        )
        response = execute_agent_plan(plan, raw_input="lembrete")
        self.assertIn("Lembrete", response.message)
        self.assertEqual(Reminder.objects.filter(reminded=False).count(), 1)

    def test_check_scheduled_reminders_sends(self) -> None:
        Reminder.objects.create(
            title="Teste",
            message="Corpo",
            context="theo",
            remind_at=timezone.now() - timedelta(minutes=1),
        )
        result = check_scheduled_reminders()
        self.assertGreaterEqual(result["due"], 1)
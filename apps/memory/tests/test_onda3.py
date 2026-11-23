from __future__ import annotations

from django.test import TestCase

from apps.bot.direct_commands import execute_direct_command
from apps.memory.models import ShoppingItem, UserPreferences
from apps.memory.preferences import apply_preference_update
from apps.memory.pwa_snapshot import build_pwa_snapshot


class Onda3Tests(TestCase):
    user_id = 100100

    def test_lista_mercado(self) -> None:
        ShoppingItem.objects.create(name="pão")
        reply = execute_direct_command("lista", [])
        self.assertIn("pão", reply.message)

    def test_resumo_without_groq(self) -> None:
        reply = execute_direct_command("resumo", [])
        self.assertIn("Mercado", reply.message)

    def test_preferences_context(self) -> None:
        msg = apply_preference_update(self.user_id, ["contexto", "theo"])
        self.assertIn("theo", msg)
        prefs = UserPreferences.objects.get(telegram_user_id=self.user_id)
        self.assertEqual(prefs.default_context, "theo")

    def test_pwa_snapshot_shape(self) -> None:
        data = build_pwa_snapshot()
        self.assertIn("shopping", data)
        self.assertIn("tasks_pending", data)
        self.assertIn("events_today", data)

    def test_golden_direct_routes(self) -> None:
        for sub in ("tarefas", "eventos", "lembretes"):
            reply = execute_direct_command("lista", [sub], self.user_id)
            self.assertGreater(len(reply.message), 5)
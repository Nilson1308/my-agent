from __future__ import annotations

from unittest.mock import patch

from datetime import datetime, time, timedelta

import redis
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.core.pwa_guard import PWA_RL_WRITE_PREFIX

from apps.memory.models import Event, PwaMutationLog, ShoppingItem, Task


@override_settings(
    GEOFENCE_WEBHOOK_TOKEN="test-geofence-token",
    GEOFENCE_RATE_LIMIT_SECONDS=0,
)
class GeofenceApiTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_geofence_unauthorized(self) -> None:
        response = self.client.post(
            "/api/webhooks/geofence/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("apps.core.api.send_message_sync", return_value=True)
    @patch("apps.core.api.format_active_shopping_list", return_value=("lista", 2))
    def test_geofence_sent(self, _list, _send) -> None:
        response = self.client.post(
            "/api/webhooks/geofence/",
            data='{"location":"mercado"}',
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="test-geofence-token",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sent")
        self.assertEqual(data["items_count"], 2)
        self.assertTrue(data["telegram_sent"])

    @patch("apps.core.api.send_message_sync", return_value=True)
    @patch("apps.core.api.format_active_shopping_list", return_value=("", 0))
    def test_geofence_empty(self, _list, _send) -> None:
        response = self.client.post(
            "/api/webhooks/geofence/",
            data="{}",
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="test-geofence-token",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data["items_count"], 0)
        self.assertTrue(data["telegram_sent"])


@override_settings(PWA_API_TOKEN="test-pwa-token", PWA_API_TOKEN_PREVIOUS="")
class PwaApiTests(TestCase):
    def test_pwa_unauthorized(self) -> None:
        response = Client().get("/api/pwa/snapshot/")
        self.assertEqual(response.status_code, 401)

    def test_pwa_ok(self) -> None:
        response = Client().get(
            "/api/pwa/snapshot/",
            HTTP_X_PWA_TOKEN="test-pwa-token",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("shopping", body)

    def test_pwa_mark_shopping_and_complete_task(self) -> None:
        item = ShoppingItem.objects.create(name="Teste PWA")
        task = Task.objects.create(title="Tarefa PWA", context="casa")
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r1 = client.patch(
            f"/api/pwa/shopping/{item.pk}/",
            data='{"bought": true}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r1.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_bought)
        r2 = client.patch(
            f"/api/pwa/tasks/{task.pk}/",
            data='{"status": "done"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r2.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "done")

    def test_pwa_undo_shopping_and_dismiss_event(self) -> None:
        item = ShoppingItem.objects.create(name="Arroz", is_bought=True, bought_at=timezone.now())
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r = client.patch(
            f"/api/pwa/shopping/{item.pk}/",
            data='{"bought": false}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 200)
        item.refresh_from_db()
        self.assertFalse(item.is_bought)

        ev = Event.objects.create(
            title="Dentista",
            context="pessoal",
            start_at=timezone.now() + timedelta(hours=1),
        )
        r2 = client.patch(
            f"/api/pwa/events/{ev.pk}/",
            data='{"dismissed": true}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(Event.objects.filter(pk=ev.pk).exists())

    def test_pwa_create_shopping_and_task(self) -> None:
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r1 = client.post(
            "/api/pwa/shopping/",
            data='{"name": "Iogurte", "quantity": "2"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(ShoppingItem.objects.filter(name__iexact="Iogurte", is_bought=False).exists())
        r1b = client.post(
            "/api/pwa/shopping/",
            data='{"name": "Iogurte"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r1b.status_code, 409)
        r2 = client.post(
            "/api/pwa/tasks/",
            data='{"title": "Ligar pro colégio", "context": "theo"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(Task.objects.filter(title="Ligar pro colégio", context="theo").exists())

    def test_pwa_reopen_task(self) -> None:
        task = Task.objects.create(
            title="Reabrir teste",
            context="casa",
            status="done",
            completed_at=timezone.now(),
        )
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r = client.patch(
            f"/api/pwa/tasks/{task.pk}/",
            data='{"status": "pending"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "pending")
        self.assertIsNone(task.completed_at)

    def test_pwa_snooze_event(self) -> None:
        start = timezone.now() + timedelta(hours=2)
        ev = Event.objects.create(title="Reunião", context="trabalho", start_at=start)
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r = client.post(
            f"/api/pwa/events/{ev.pk}/snooze/",
            data='{"minutes": 15}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 200)
        ev.refresh_from_db()
        self.assertGreater(ev.start_at, start)
        self.assertTrue(
            PwaMutationLog.objects.filter(action="event_snooze", target_id=ev.pk).exists()
        )

    def test_pwa_snooze_tomorrow_morning(self) -> None:
        local_now = timezone.localtime(timezone.now())
        start = timezone.make_aware(
            datetime.combine(local_now.date(), time(14, 0)),
            timezone.get_current_timezone(),
        )
        ev = Event.objects.create(title="Consulta", context="pessoal", start_at=start)
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        r = client.post(
            f"/api/pwa/events/{ev.pk}/snooze/",
            data='{"preset": "tomorrow_morning"}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r.status_code, 200)
        ev.refresh_from_db()
        local_start = timezone.localtime(ev.start_at)
        self.assertEqual(local_start.date(), local_now.date() + timedelta(days=1))
        self.assertEqual(local_start.hour, 9)

    @override_settings(PWA_WRITE_RATE_LIMIT_PER_MINUTE=2)
    def test_pwa_write_rate_limit(self) -> None:
        try:
            rl = redis.from_url(settings.REDIS_URL, decode_responses=True)
            rl.delete(f"{PWA_RL_WRITE_PREFIX}127.0.0.1")
        except redis.RedisError:
            self.skipTest("Redis indisponível")
        items = [
            ShoppingItem.objects.create(name=f"RL-{i}") for i in range(3)
        ]
        client = Client()
        headers = {"HTTP_X_PWA_TOKEN": "test-pwa-token"}
        for i in range(2):
            r = client.patch(
                f"/api/pwa/shopping/{items[i].pk}/",
                data='{"bought": true}',
                content_type="application/json",
                **headers,
            )
            self.assertEqual(r.status_code, 200, msg=f"patch {i}")
        r3 = client.patch(
            f"/api/pwa/shopping/{items[2].pk}/",
            data='{"bought": true}',
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r3.status_code, 429)

    def test_pwa_dual_token_snapshot(self) -> None:
        with override_settings(
            PWA_API_TOKEN="new-token",
            PWA_API_TOKEN_PREVIOUS="legacy-token",
        ):
            client = Client()
            r_new = client.get("/api/pwa/snapshot/", HTTP_X_PWA_TOKEN="new-token")
            r_old = client.get("/api/pwa/snapshot/", HTTP_X_PWA_TOKEN="legacy-token")
            self.assertEqual(r_new.status_code, 200)
            self.assertEqual(r_old.status_code, 200)

    def test_pwa_push_vapid_public(self) -> None:
        r = Client().get("/api/pwa/push/vapid/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("enabled", body)
        self.assertIn("public_key", body)

    def test_pwa_pairing_exchange(self) -> None:
        from apps.core.pwa_pairing import create_pairing_code

        code = create_pairing_code()
        client = Client()
        r = client.post(
            "/api/pwa/pairing/exchange/",
            data=f'{{"code": "{code}"}}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["token"], "test-pwa-token")
        r2 = client.post(
            "/api/pwa/pairing/exchange/",
            data=f'{{"code": "{code}"}}',
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 401)


@override_settings()
class HealthApiTests(TestCase):
    def test_health_ok(self) -> None:
        response = Client().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["status"], ("ok", "degraded"))
        self.assertIn("database", body)
        self.assertIn("redis", body)
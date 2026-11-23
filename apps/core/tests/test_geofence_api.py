from __future__ import annotations

from unittest.mock import patch

from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.memory.models import Event, ShoppingItem, Task


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


@override_settings(PWA_API_TOKEN="test-pwa-token")
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
        r2 = client.patch(f"/api/pwa/tasks/{task.pk}/", **headers)
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


@override_settings()
class HealthApiTests(TestCase):
    def test_health_ok(self) -> None:
        response = Client().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["status"], ("ok", "degraded"))
        self.assertIn("database", body)
        self.assertIn("redis", body)
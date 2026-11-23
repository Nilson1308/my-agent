from __future__ import annotations

from unittest.mock import patch

from django.test import Client, TestCase, override_settings


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


@override_settings()
class HealthApiTests(TestCase):
    def test_health_ok(self) -> None:
        response = Client().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["status"], ("ok", "degraded"))
        self.assertIn("database", body)
        self.assertIn("redis", body)
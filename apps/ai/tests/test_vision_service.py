from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from apps.ai.vision_service import VisionError, describe_image_bytes


@override_settings(GROQ_API_KEY="", GROQ_VISION_MODEL="")
class VisionConfiguredTests(SimpleTestCase):
    def test_unconfigured_raises(self) -> None:
        with self.assertRaises(VisionError) as ctx:
            describe_image_bytes(b"x", "image/png")
        self.assertEqual(ctx.exception.code, "unavailable")
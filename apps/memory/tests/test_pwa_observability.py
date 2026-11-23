from django.test import TestCase

from apps.memory.models import InputType, InteractionChannel, InteractionLog, PwaMutationLog
from apps.memory.pwa_observability import build_pwa_observability
from apps.ai.llm_outcomes import LLM_OK


class PwaObservabilityTests(TestCase):
    def test_counts_by_channel(self) -> None:
        InteractionLog.objects.create(
            raw_input="a",
            input_type=InputType.TEXT,
            channel=InteractionChannel.PWA,
            llm_outcome=LLM_OK,
        )
        InteractionLog.objects.create(
            raw_input="b",
            input_type=InputType.TEXT,
            channel=InteractionChannel.TELEGRAM,
            llm_outcome=LLM_OK,
        )
        PwaMutationLog.objects.create(action="shopping_create", target_type="shopping")
        data = build_pwa_observability(window_days=7)
        self.assertEqual(data["interactions"]["pwa"], 1)
        self.assertEqual(data["interactions"]["telegram"], 1)
        self.assertEqual(data["mutations_total"], 1)
        self.assertEqual(data["mutations_by_action"][0]["action"], "shopping_create")
import json

from django.core.management.base import BaseCommand

from apps.ai.groq_service import parse_user_message
from apps.memory.services import execute_agent_plan


class Command(BaseCommand):
    help = "Testa roteamento Groq + execução no banco (sem Telegram)."

    def add_arguments(self, parser):
        parser.add_argument(
            "message",
            type=str,
            help="Mensagem em linguagem natural",
        )

    def handle(self, *args, **options):
        message = options["message"]
        result = parse_user_message(message)

        self.stdout.write(self.style.HTTP_INFO(f"=== Outcome: {result.outcome} ==="))
        self.stdout.write(self.style.HTTP_INFO("=== JSON Groq (AgentPlan) ==="))
        self.stdout.write(
            json.dumps(result.plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
        )

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=== Resposta execute_agent_plan ==="))
        response = execute_agent_plan(
            result.plan,
            raw_input=message,
            input_type="text",
            llm_outcome=result.outcome,
        )
        self.stdout.write(response)
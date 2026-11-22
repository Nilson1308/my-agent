from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.ai.llm_outcomes import LLM_OK, OUTCOME_CHOICES
from apps.memory.models import InteractionLog


class Command(BaseCommand):
    help = "Resumo de outcomes do roteador LLM (InteractionLog.llm_outcome)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Últimas linhas com problema (não-ok)",
        )

    def handle(self, *args, **options):
        limit: int = options["limit"]
        labels = dict(OUTCOME_CHOICES)

        self.stdout.write(self.style.MIGRATE_HEADING("Contagem por outcome"))
        rows = (
            InteractionLog.objects.values("llm_outcome")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        for row in rows:
            key = row["llm_outcome"] or "(vazio)"
            label = labels.get(row["llm_outcome"], key)
            self.stdout.write(f"  {label}: {row['total']}")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Últimos {limit} com outcome ≠ ok"))
        qs = (
            InteractionLog.objects.exclude(llm_outcome=LLM_OK)
            .exclude(llm_outcome="")
            .order_by("-created_at")[:limit]
        )
        for log in qs:
            preview = (log.raw_input or "")[:60].replace("\n", " ")
            self.stdout.write(
                f"  #{log.id} {log.created_at:%Y-%m-%d %H:%M} "
                f"[{log.llm_outcome}] {preview}"
            )
        if not qs.exists():
            self.stdout.write("  (nenhum)")
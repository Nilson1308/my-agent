from django.core.management.base import BaseCommand

from apps.ai.embeddings_service import embed_document
from apps.memory.models import Note


class Command(BaseCommand):
    help = "Gera embeddings para notas sem vetor (backfill pgvector)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Quantidade de notas processadas por lote",
        )

    def handle(self, *args, **options):
        batch_size: int = options["batch_size"]
        qs = Note.objects.filter(embedding__isnull=True).order_by("id")
        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma nota pendente de reindexação."))
            return

        updated = 0
        failed = 0
        for note in qs.iterator(chunk_size=batch_size):
            try:
                note.embedding = embed_document(note.content)
                note.save(update_fields=["embedding"])
                updated += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Falha id={note.id}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Reindexação concluída: {updated} atualizadas, {failed} falhas, {total} no total."
            )
        )
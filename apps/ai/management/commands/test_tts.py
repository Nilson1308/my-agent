from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai.tts_service import clean_text_for_tts, synthesize_speech_sync


class Command(BaseCommand):
    help = "Gera test_tts.mp3 na raiz do projeto para validar edge-tts."

    def add_arguments(self, parser):
        parser.add_argument("message", type=str, help="Texto a sintetizar")

    def handle(self, *args, **options):
        message = options["message"]
        cleaned = clean_text_for_tts(message)
        output = Path(settings.BASE_DIR) / "test_tts.mp3"

        self.stdout.write(f"Voz: {settings.TTS_VOICE}")
        self.stdout.write(f"Texto limpo: {cleaned}")

        synthesize_speech_sync(message, str(output))
        self.stdout.write(self.style.SUCCESS(f"Áudio salvo em: {output}"))
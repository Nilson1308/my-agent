import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.bot.application import build_application


def _ensure_event_loop() -> None:
    """python-telegram-bot usa get_event_loop(); no Python 3.10+ é preciso setar o loop."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


class Command(BaseCommand):
    help = "Inicia o bot Telegram em modo long polling (desenvolvimento)."

    def handle(self, *args, **options):
        token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
        allowed_raw = (settings.TELEGRAM_ALLOWED_USER_ID or "").strip()

        if not token:
            raise CommandError("Configure TELEGRAM_BOT_TOKEN no .env")
        if not allowed_raw:
            raise CommandError("Configure TELEGRAM_ALLOWED_USER_ID no .env")
        try:
            int(allowed_raw)
        except ValueError as exc:
            raise CommandError(
                "TELEGRAM_ALLOWED_USER_ID deve ser um número (seu chat_id do Telegram)."
            ) from exc

        _ensure_event_loop()
        application = build_application()
        retries = settings.TELEGRAM_BOOTSTRAP_RETRIES
        self.stdout.write(
            self.style.SUCCESS(
                "Conectando ao Telegram (long polling). Ctrl+C para encerrar. "
                f"bootstrap_retries={retries}"
            )
        )
        application.run_polling(
            drop_pending_updates=True,
            bootstrap_retries=retries,
        )
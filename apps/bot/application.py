import logging

from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler
from telegram.request import HTTPXRequest

from apps.bot.handlers import (
    desfazer_command,
    feedback_callback_handler,
    help_command,
    hoje_command,
    lista_command,
    pending_callback_handler,
    prefs_command,
    resumo_command,
    start_command,
    text_message_filter,
    text_message_handler,
    voice_message_filter,
    voice_message_handler,
)

logger = logging.getLogger(__name__)


async def telegram_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.exception("Erro no handler Telegram", exc_info=context.error)


def build_application() -> Application:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN não configurado")

    request = HTTPXRequest(
        connect_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=settings.TELEGRAM_READ_TIMEOUT,
        write_timeout=settings.TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        media_write_timeout=settings.TELEGRAM_MEDIA_WRITE_TIMEOUT,
    )

    builder = (
        Application.builder()
        .token(token)
        .request(request)
        .get_updates_request(request)
    )
    proxy = settings.TELEGRAM_PROXY_URL
    if proxy:
        builder = builder.proxy(proxy).get_updates_proxy(proxy)

    app = builder.build()
    app.add_error_handler(telegram_error_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("comandos", help_command))
    app.add_handler(CommandHandler("hoje", hoje_command))
    app.add_handler(CommandHandler("desfazer", desfazer_command))
    app.add_handler(CommandHandler("lista", lista_command))
    app.add_handler(CommandHandler("resumo", resumo_command))
    app.add_handler(CommandHandler("prefs", prefs_command))
    app.add_handler(CommandHandler("preferencias", prefs_command))
    app.add_handler(CallbackQueryHandler(pending_callback_handler, pattern=r"^pc:"))
    app.add_handler(CallbackQueryHandler(feedback_callback_handler, pattern=r"^fb:"))
    app.add_handler(MessageHandler(text_message_filter, text_message_handler))
    app.add_handler(MessageHandler(voice_message_filter, voice_message_handler))
    return app
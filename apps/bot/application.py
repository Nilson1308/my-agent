import logging

from django.conf import settings
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler
from telegram.request import HTTPXRequest

from apps.bot.handlers import (
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
    app.add_handler(MessageHandler(text_message_filter, text_message_handler))
    app.add_handler(MessageHandler(voice_message_filter, voice_message_handler))
    return app
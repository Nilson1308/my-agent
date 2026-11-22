from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from asgiref.sync import sync_to_async
from django.conf import settings
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, TimedOut
from telegram.ext import ContextTypes, filters

from apps.ai.groq_service import parse_user_message, transcribe_audio
from apps.ai.tts_service import synthesize_speech, try_mp3_to_ogg_opus
from apps.memory.services import execute_agent_plan

logger = logging.getLogger(__name__)

_TELEGRAM_RETRY_ATTEMPTS = 3
_TELEGRAM_RETRY_BASE_DELAY = 2.0

HandlerT = TypeVar("HandlerT", bound=Callable[..., Awaitable[Any]])


async def _telegram_retry(coro_factory: Callable[[], Awaitable[Any]]) -> Any:
    last_error: Exception | None = None
    for attempt in range(_TELEGRAM_RETRY_ATTEMPTS):
        try:
            return await coro_factory()
        except (TimedOut, NetworkError) as exc:
            last_error = exc
            logger.warning(
                "Telegram timeout/rede (tentativa %s/%s): %s",
                attempt + 1,
                _TELEGRAM_RETRY_ATTEMPTS,
                exc,
            )
            if attempt + 1 < _TELEGRAM_RETRY_ATTEMPTS:
                await asyncio.sleep(_TELEGRAM_RETRY_BASE_DELAY * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("falha Telegram sem exceção")

START_MESSAGE = (
    "Olá! Sou seu assistente pessoal.\n\n"
    "Envie texto ou áudio para registrar:\n"
    "• mercado (itens e compras)\n"
    "• tarefas e pendências\n"
    "• compromissos na agenda\n"
    "• ideias e notas\n\n"
    "Também consigo listar e consultar o que você já salvou."
)


def _allowed_user_id() -> int | None:
    raw = (settings.TELEGRAM_ALLOWED_USER_ID or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _is_allowed_user(update: Update) -> bool:
    allowed = _allowed_user_id()
    user = update.effective_user
    if allowed is None or user is None:
        return False
    return user.id == allowed


def allowed_user_only(handler: HandlerT) -> HandlerT:
    """Ignora silenciosamente updates de outros usuários."""

    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if not _is_allowed_user(update):
            return None
        return await handler(update, context)

    return wrapped  # type: ignore[return-value]


async def _keep_chat_action(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    stop: asyncio.Event,
    action: ChatAction,
) -> None:
    while not stop.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception as exc:
            logger.debug("Falha ao enviar chat action: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=4.5)
        except TimeoutError:
            continue


async def _keep_typing(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    stop: asyncio.Event,
) -> None:
    await _keep_chat_action(context, chat_id, stop, ChatAction.TYPING)


async def _with_typing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    work: Callable[[], Awaitable[str]],
) -> str:
    chat = update.effective_chat
    if not chat:
        return await work()

    stop = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context, chat.id, stop))
    try:
        return await work()
    finally:
        stop.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass


async def _run_pipeline(raw_input: str, input_type: str) -> str:
    parse_result = await sync_to_async(parse_user_message, thread_sensitive=False)(raw_input)
    return await sync_to_async(execute_agent_plan, thread_sensitive=True)(
        parse_result.plan,
        raw_input,
        input_type,
        parse_result.outcome,
    )


@allowed_user_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(START_MESSAGE)


@allowed_user_only
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    async def work() -> str:
        try:
            return await _run_pipeline(text, "text")
        except Exception:
            logger.exception("Erro ao processar texto")
            return "Não consegui processar agora. Tente de novo em instantes."

    reply = await _with_typing(update, context, work)
    await _telegram_retry(lambda: message.reply_text(reply))


@allowed_user_only
async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    attachment = message.voice or message.audio
    if not attachment:
        return

    download_path: str | None = None

    async def work() -> tuple[str, str]:
        nonlocal download_path
        try:
            tg_file = await _telegram_retry(lambda: attachment.get_file())
            suffix = ".ogg" if message.voice else ".mp3"
            fd, download_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            await _telegram_retry(lambda: tg_file.download_to_drive(download_path))

            transcript = await sync_to_async(transcribe_audio, thread_sensitive=False)(
                download_path
            )
            transcript = transcript.strip()
            if not transcript:
                text = "Não consegui entender o áudio. Tente falar de novo."
                return text, text

            body = await _run_pipeline(transcript, "audio")
            preview = transcript if len(transcript) <= 280 else transcript[:277] + "…"
            full_reply = f"🎤 Entendi: “{preview}”\n\n{body}"
            tts_text = f"Entendi. {body}"
            return full_reply, tts_text
        except Exception:
            logger.exception("Erro ao processar áudio")
            text = "Não consegui processar o áudio agora. Tente de novo ou envie em texto."
            return text, text
        finally:
            if download_path and os.path.isfile(download_path):
                try:
                    os.remove(download_path)
                except OSError as exc:
                    logger.warning("Não foi possível remover temp %s: %s", download_path, exc)

    full_reply, tts_text = await _with_typing(update, context, work)

    try:
        await _telegram_retry(lambda: message.reply_text(full_reply))
    except (TimedOut, NetworkError):
        logger.exception("Não foi possível enviar texto da resposta ao áudio")
        return

    if not getattr(settings, "TTS_ENABLED", True):
        return

    tts_path: str | None = None
    ogg_path: str | None = None
    record_stop = asyncio.Event()
    record_task: asyncio.Task | None = None
    chat = update.effective_chat
    if chat:
        record_task = asyncio.create_task(
            _keep_chat_action(context, chat.id, record_stop, ChatAction.RECORD_VOICE)
        )

    try:
        fd, tts_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        await synthesize_speech(tts_text, tts_path)

        fd, ogg_path = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)
        if try_mp3_to_ogg_opus(tts_path, ogg_path):

            async def _send_voice() -> Any:
                return await message.reply_voice(
                    voice=ogg_path,
                    filename="resposta.ogg",
                    caption="🎤 Resposta em áudio",
                )
        else:
            if ogg_path and os.path.isfile(ogg_path):
                os.remove(ogg_path)
                ogg_path = None

            async def _send_voice() -> Any:
                # MP3 via sendVoice quebra no cliente; sendAudio reproduz. Passar o path, não InputFile(str).
                return await message.reply_audio(
                    audio=tts_path,
                    filename="resposta.mp3",
                    title="Resposta",
                    caption="🎤 Resposta em áudio",
                )

        await _telegram_retry(_send_voice)
    except Exception:
        logger.exception("Falha no TTS/áudio; resposta em texto já enviada")
    finally:
        record_stop.set()
        if record_task:
            record_task.cancel()
            try:
                await record_task
            except asyncio.CancelledError:
                pass
        for path in (tts_path, ogg_path):
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as exc:
                    logger.warning("Não foi possível remover temp TTS %s: %s", path, exc)


text_message_filter = filters.TEXT & ~filters.COMMAND
voice_message_filter = filters.VOICE | filters.AUDIO
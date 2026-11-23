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
from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, TimedOut
from telegram.ext import ContextTypes, filters

from apps.ai.groq_service import transcribe_audio
from apps.memory.agent_pipeline import run_agent_message
from apps.memory.models import InteractionChannel
from apps.ai.tts_service import synthesize_speech, try_mp3_to_ogg_opus
from apps.bot.direct_commands import execute_direct_command
from apps.bot.help_text import HELP_MESSAGE
from apps.bot.telegram_keyboards import feedback_keyboard, pending_confirmation_keyboard
from apps.memory.preferences import apply_preference_update, feedback_enabled_for_user
from apps.memory.confirmation import resolve_pending
from apps.memory.feedback import apply_interaction_feedback
from apps.memory.models import PendingConfirmation
from apps.memory.review_today import build_today_digest
from apps.memory.undo import undo_last_interaction
from apps.memory.reply_types import AgentReply
from apps.memory.services import format_active_shopping_list

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
    work: Callable[[], Awaitable[Any]],
) -> Any:
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


def _tts_summary(body: str) -> str:
    first = body.strip().split("\n", 1)[0].strip()
    first = first.removeprefix("💡 ").strip()
    if len(first) > 140:
        first = first[:137] + "…"
    return f"Registrei: {first}" if first else "Registrei."


async def _run_pipeline(
    raw_input: str, input_type: str, telegram_user_id: int
) -> AgentReply:
    return await sync_to_async(run_agent_message, thread_sensitive=True)(
        raw_input,
        channel=InteractionChannel.TELEGRAM,
        input_type=input_type,
        telegram_user_id=telegram_user_id,
    )


async def _keyboard_for_reply(
    reply: AgentReply,
    telegram_user_id: int | None = None,
) -> InlineKeyboardMarkup | None:
    if reply.pending_confirmation_id is not None:
        pending = await sync_to_async(
            lambda: PendingConfirmation.objects.filter(pk=reply.pending_confirmation_id).first(),
            thread_sensitive=True,
        )()
        show_list = bool(pending and pending.action_type == "add_shopping")
        return pending_confirmation_keyboard(
            reply.pending_confirmation_id,
            show_shopping_list=show_list,
        )
    if reply.interaction_log_id is not None:
        user = reply.telegram_user_id or telegram_user_id
        if user is not None and not feedback_enabled_for_user(user):
            return None
        return feedback_keyboard(reply.interaction_log_id)
    return None


async def _send_agent_reply(
    message: Any,
    reply: AgentReply,
    *,
    telegram_user_id: int | None = None,
) -> None:
    markup = await _keyboard_for_reply(reply, telegram_user_id)
    await _telegram_retry(
        lambda: message.reply_text(reply.message, reply_markup=markup)
    )


@allowed_user_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(START_MESSAGE)


@allowed_user_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")


@allowed_user_only
async def hoje_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return
    mode = context.args[0] if context.args else None
    text = await sync_to_async(build_today_digest, thread_sensitive=True)(mode)
    await message.reply_text(text)


@allowed_user_only
async def lista_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    if not message or not user:
        return
    reply = await sync_to_async(
        lambda: execute_direct_command("lista", list(context.args or []), user.id),
        thread_sensitive=True,
    )()
    await _send_agent_reply(message, reply, telegram_user_id=user.id)


@allowed_user_only
async def resumo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    if not message or not user:
        return
    reply = await sync_to_async(
        lambda: execute_direct_command("resumo", list(context.args or []), user.id),
        thread_sensitive=True,
    )()
    await _send_agent_reply(message, reply, telegram_user_id=user.id)


@allowed_user_only
async def prefs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    if not message or not user:
        return
    text = await sync_to_async(apply_preference_update, thread_sensitive=True)(
        user.id,
        list(context.args or []),
    )
    await message.reply_text(text, parse_mode="Markdown")


@allowed_user_only
async def desfazer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    if not message or not user:
        return
    text = await sync_to_async(undo_last_interaction, thread_sensitive=True)(user.id)
    await message.reply_text(text)


@allowed_user_only
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    user_id = update.effective_user.id if update.effective_user else 0

    async def work() -> AgentReply:
        try:
            return await _run_pipeline(text, "text", user_id)
        except Exception:
            logger.exception("Erro ao processar texto")
            return AgentReply(message="Não consegui processar agora. Tente de novo em instantes.")

    reply = await _with_typing(update, context, work)
    await _send_agent_reply(message, reply, telegram_user_id=user_id)


@allowed_user_only
async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    attachment = message.voice or message.audio
    if not attachment:
        return

    download_path: str | None = None

    async def work() -> tuple[AgentReply, str]:
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
                return AgentReply(message=text), text

            user_id = update.effective_user.id if update.effective_user else 0
            agent_reply = await _run_pipeline(transcript, "audio", user_id)
            body = agent_reply.message
            preview = transcript if len(transcript) <= 280 else transcript[:277] + "…"
            summary = _tts_summary(body)
            full_reply = f"🎤 Entendi: “{preview}”\n\n{summary}\n\n{body}"
            outbound = AgentReply(
                message=full_reply,
                pending_confirmation_id=agent_reply.pending_confirmation_id,
                interaction_log_id=agent_reply.interaction_log_id,
                telegram_user_id=user_id,
            )
            return outbound, summary
        except Exception:
            logger.exception("Erro ao processar áudio")
            text = "Não consegui processar o áudio agora. Tente de novo ou envie em texto."
            return AgentReply(message=text), text
        finally:
            if download_path and os.path.isfile(download_path):
                try:
                    os.remove(download_path)
                except OSError as exc:
                    logger.warning("Não foi possível remover temp %s: %s", download_path, exc)

    outbound, tts_text = await _with_typing(update, context, work)

    try:
        uid = update.effective_user.id if update.effective_user else None
        await _send_agent_reply(message, outbound, telegram_user_id=uid)
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


@allowed_user_only
async def pending_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    user = update.effective_user
    if not user:
        return

    data = query.data.strip()
    await query.answer()

    if data == "pc:list:shopping":
        text, count = await sync_to_async(format_active_shopping_list, thread_sensitive=True)()
        if count == 0:
            text = "🛒 Mercado: lista vazia"
        await query.edit_message_reply_markup(reply_markup=None)
        if query.message:
            await _telegram_retry(lambda: query.message.reply_text(text))
        return

    if not data.startswith("pc:"):
        return

    parts = data.split(":")
    if len(parts) != 3:
        return
    try:
        pending_id = int(parts[1])
    except ValueError:
        return
    decision = parts[2]
    if decision not in ("y", "n"):
        return

    reply = await sync_to_async(resolve_pending, thread_sensitive=True)(
        user.id,
        pending_id,
        confirm=decision == "y",
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    if query.message:
        await _telegram_retry(lambda: query.message.reply_text(reply))


@allowed_user_only
async def feedback_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.data or not user:
        return
    parts = query.data.split(":")
    if len(parts) != 3 or parts[0] != "fb":
        return
    try:
        log_id = int(parts[1])
    except ValueError:
        return
    positive = parts[2] == "up"
    await query.answer()
    reply = await sync_to_async(apply_interaction_feedback, thread_sensitive=True)(
        user.id,
        log_id,
        positive=positive,
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    if query.message:
        await _telegram_retry(lambda: query.message.reply_text(reply))


text_message_filter = filters.TEXT & ~filters.COMMAND
voice_message_filter = filters.VOICE | filters.AUDIO
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess

from django.conf import settings

logger = logging.getLogger(__name__)

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


TTS_MAX_CHARS_DEFAULT = 900


def truncate_for_tts(text: str, max_chars: int | None = None) -> str:
    """Limita tamanho para áudio curto (evita timeout no upload do Telegram)."""
    limit = max_chars
    if limit is None:
        limit = int(getattr(settings, "TTS_MAX_CHARS", TTS_MAX_CHARS_DEFAULT))
    cleaned = clean_text_for_tts(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"


def clean_text_for_tts(text: str) -> str:
    """Remove emojis, markdown e quebras excessivas para TTS em PT."""
    cleaned = _EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[*_`]", "", cleaned)
    cleaned = cleaned.replace("•", ", ").replace("—", ", ").replace("–", ", ")
    cleaned = re.sub(r"\s*\n+\s*", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def synthesize_speech(text: str, output_path: str) -> str:
    """Gera arquivo .mp3 com edge-tts."""
    import edge_tts

    cleaned = truncate_for_tts(text)
    if not cleaned:
        raise ValueError("texto vazio após limpeza para TTS")

    voice = settings.TTS_VOICE or "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(cleaned, voice=voice)
    await communicate.save(output_path)
    if os.path.getsize(output_path) < 256:
        raise ValueError("TTS gerou arquivo de áudio vazio ou inválido")
    return output_path


def try_mp3_to_ogg_opus(mp3_path: str, ogg_path: str) -> bool:
    """Converte MP3 para OGG/Opus (sendVoice). Requer ffmpeg no PATH."""
    if not shutil.which("ffmpeg"):
        return False
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                mp3_path,
                "-c:a",
                "libopus",
                "-b:a",
                "64k",
                ogg_path,
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg não converteu TTS para OGG: %s", exc)
        return False
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="replace")[:500]
        logger.warning("ffmpeg falhou (%s): %s", result.returncode, err)
        return False
    return os.path.isfile(ogg_path) and os.path.getsize(ogg_path) >= 256


def synthesize_speech_sync(text: str, output_path: str) -> str:
    """Wrapper síncrono para scripts/comandos de management."""
    return asyncio.run(synthesize_speech(text, output_path))
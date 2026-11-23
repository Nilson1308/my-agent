from __future__ import annotations

import base64
import logging

from django.conf import settings
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

logger = logging.getLogger(__name__)

_VISION_PROMPT = (
    "Você recebe uma foto. Transcreva todo o texto legível em português, na ordem natural. "
    "Se não houver texto, descreva o conteúdo útil em até 4 frases. "
    "Responda só com o texto final, sem markdown nem comentários."
)

_ALLOWED_MIME = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


class VisionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def vision_model() -> str:
    return (getattr(settings, "GROQ_VISION_MODEL", "") or "llama-3.2-11b-vision-preview").strip()


def vision_configured() -> bool:
    return bool((settings.GROQ_API_KEY or "").strip()) and bool(vision_model())


def describe_image_bytes(data: bytes, mime_type: str) -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime not in _ALLOWED_MIME:
        raise VisionError("invalid_type", "Formato de imagem não suportado (JPEG, PNG, WebP, GIF).")
    if not vision_configured():
        raise VisionError("unavailable", "Vision Groq não configurada (GROQ_API_KEY / GROQ_VISION_MODEL).")

    b64 = base64.standard_b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    client = Groq(api_key=settings.GROQ_API_KEY)
    try:
        completion = client.chat.completions.create(
            model=vision_model(),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text:
            raise VisionError("empty", "Vision não retornou texto.")
        return text
    except RateLimitError as exc:
        logger.warning("vision rate limit: %s", exc)
        raise VisionError("rate_limit", "Limite Groq vision; tente mais tarde.") from exc
    except (APIConnectionError, APIStatusError) as exc:
        logger.exception("vision api: %s", exc)
        raise VisionError("api", "Falha na API vision.") from exc
from __future__ import annotations

import re

from django.conf import settings

from apps.ai.vision_service import VisionError, describe_image_bytes
from apps.memory.pdf_ingest import PdfIngestError, ingest_text_as_notes


def _safe_image_name(name: str) -> str:
    base = (name or "foto.jpg").split("/")[-1].split("\\")[-1]
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE)[:120]
    return base or "foto.jpg"


def ingest_image_bytes(
    data: bytes,
    filename: str,
    mime_type: str,
    *,
    context: str | None = None,
) -> dict:
    max_bytes = int(getattr(settings, "PWA_IMAGE_MAX_BYTES", 4 * 1024 * 1024))
    if len(data) > max_bytes:
        raise PdfIngestError("too_large", "Imagem muito grande.")
    max_chunks = int(getattr(settings, "PWA_IMAGE_MAX_CHUNKS", 8))

    try:
        text = describe_image_bytes(data, mime_type)
    except VisionError as exc:
        if exc.code == "rate_limit":
            raise PdfIngestError("rate_limit", exc.message) from exc
        raise PdfIngestError(exc.code, exc.message) from exc

    safe_name = _safe_image_name(filename)
    return ingest_text_as_notes(
        text,
        safe_name,
        context=context,
        max_chunks=max_chunks,
        icon="📷",
    )
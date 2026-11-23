from __future__ import annotations

import io
import logging
import re

from django.conf import settings

from apps.ai.embeddings_service import embed_document
from apps.memory.models import DomainContext, Note

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 120


class PdfIngestError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfIngestError("unavailable", "pypdf não instalado no servidor.") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise PdfIngestError("invalid", "Arquivo PDF inválido.") from exc
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        cleaned = text.strip()
        if cleaned:
            parts.append(cleaned)
    return "\n\n".join(parts)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, *, max_chars: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            break_at = normalized.rfind("\n\n", start, end)
            if break_at > start + max_chars // 3:
                end = break_at
            else:
                break_at = normalized.rfind(". ", start, end)
                if break_at > start + max_chars // 3:
                    end = break_at + 1
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _safe_filename(name: str) -> str:
    base = (name or "documento.pdf").split("/")[-1].split("\\")[-1]
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE)[:120]
    return base or "documento.pdf"


def _resolve_context(context: str | None) -> str:
    ctx = (context or DomainContext.PESSOAL).strip().lower()
    if ctx not in {c.value for c in DomainContext}:
        return DomainContext.PESSOAL
    return ctx


def ingest_text_as_notes(
    text: str,
    source_label: str,
    *,
    context: str | None = None,
    max_chunks: int | None = None,
    icon: str = "📎",
) -> dict:
    if not text.strip():
        raise PdfIngestError("empty", "Nenhum texto para indexar.")
    ctx = _resolve_context(context)
    cap = max_chunks if max_chunks is not None else int(getattr(settings, "PWA_PDF_MAX_CHUNKS", 24))
    chunks = chunk_text(text)
    if not chunks:
        raise PdfIngestError("empty", "Texto vazio após processamento.")
    truncated = len(chunks) > cap
    if truncated:
        chunks = chunks[:cap]

    note_ids: list[int] = []
    for i, chunk in enumerate(chunks):
        title = f"{icon} {source_label}"
        if len(chunks) > 1:
            title += f" ({i + 1}/{len(chunks)})"
        content = f"{title}\n\n{chunk}"
        embedding = None
        try:
            embedding = embed_document(chunk)
        except Exception:
            logger.exception("embedding chunk falhou (%s)", source_label)
        note = Note.objects.create(content=content, context=ctx, embedding=embedding)
        note_ids.append(note.pk)

    return {
        "filename": source_label,
        "chunks": len(note_ids),
        "chars": len(text),
        "note_ids": note_ids,
        "truncated": truncated,
        "context": ctx,
    }


def ingest_pdf_bytes(
    data: bytes,
    filename: str,
    *,
    context: str | None = None,
) -> dict:
    max_bytes = int(getattr(settings, "PWA_PDF_MAX_BYTES", 8 * 1024 * 1024))
    if len(data) > max_bytes:
        raise PdfIngestError("too_large", "PDF muito grande.")
    max_chunks = int(getattr(settings, "PWA_PDF_MAX_CHUNKS", 24))

    text = extract_pdf_text(data)
    if not text.strip():
        raise PdfIngestError("empty", "Nenhum texto extraível (PDF escaneado precisa de OCR).")

    safe_name = _safe_filename(filename)
    return ingest_text_as_notes(
        text,
        safe_name,
        context=context,
        max_chunks=max_chunks,
        icon="📎",
    )
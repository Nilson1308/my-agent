from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

from apps.memory.models import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

MODEL_NAME = "intfloat/multilingual-e5-small"
_model_registered = False


def _register_model() -> None:
    global _model_registered
    if _model_registered:
        return

    supported = {m["model"].lower() for m in TextEmbedding.list_supported_models()}
    if MODEL_NAME.lower() not in supported:
        try:
            TextEmbedding.add_custom_model(
                model=MODEL_NAME,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf=MODEL_NAME),
                dim=EMBEDDING_DIMENSIONS,
                model_file="onnx/model.onnx",
            )
        except ValueError as exc:
            logger.debug("Modelo %s já registrado: %s", MODEL_NAME, exc)

    _model_registered = True


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    _register_model()
    return TextEmbedding(model_name=MODEL_NAME)


def _embed_prefixed(text: str, prefix: str) -> list[float]:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("texto vazio para embedding")
    payload = f"{prefix}{cleaned}"
    model = _get_model()
    vector = next(model.embed([payload]))
    array = np.asarray(vector, dtype=np.float32)
    if array.shape[0] != EMBEDDING_DIMENSIONS:
        raise ValueError(f"dimensão inesperada: {array.shape[0]}")
    return [float(v) for v in array]


def embed_document(text: str) -> list[float]:
    """Embedding de documento/nota (prefixo passage:)."""
    return _embed_prefixed(text, "passage: ")


def embed_query(text: str) -> list[float]:
    """Embedding de consulta (prefixo query:)."""
    return _embed_prefixed(text, "query: ")
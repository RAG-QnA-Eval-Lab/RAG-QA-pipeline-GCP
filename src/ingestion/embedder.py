"""임베딩 래퍼 — LiteLLM embedding API."""

from __future__ import annotations

import logging
import time

import litellm

from config.settings import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


def embed_texts(
    texts: list[str],
    model: str | None = None,
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """텍스트 리스트를 임베딩 벡터로 변환.

    Returns:
        각 텍스트에 대응하는 임베딩 벡터 리스트 (dim=768 for text-embedding-004).
    """
    model = model or settings.embedding_model
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = _embed_batch(batch, model)
        all_embeddings.extend(embeddings)

    if all_embeddings:
        dim = len(all_embeddings[0])
        if not all(len(e) == dim for e in all_embeddings):
            raise ValueError(f"임베딩 차원 불일치 (expected {dim})")
        logger.info("임베딩 완료: %d텍스트 → dim=%d", len(all_embeddings), dim)

    return all_embeddings


def _embed_batch(texts: list[str], model: str) -> list[list[float]]:
    """단일 배치 임베딩 with retry."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = litellm.embedding(model=model, input=texts)
            return [item["embedding"] for item in response.data]
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning("임베딩 재시도 %d/%d (%.1fs 후)", attempt + 1, MAX_RETRIES, delay)
                time.sleep(delay)
            else:
                logger.exception("임베딩 실패 (최종 시도)")
    raise RuntimeError("임베딩 최대 재시도 초과") from last_exc

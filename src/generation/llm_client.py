"""LiteLLM 통합 클라이언트 — 멀티 모델 지원, 재시도, 토큰 추적."""

from __future__ import annotations

import logging
import os
import time

import litellm
from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    RateLimitError,
)

from config.settings import settings
from src.generation import LLMResponse

logger = logging.getLogger(__name__)

os.environ.setdefault("VERTEXAI_PROJECT", settings.vertexai_project)
os.environ.setdefault("VERTEXAI_LOCATION", settings.vertexai_location)
if settings.huggingface_api_key:
    os.environ.setdefault("HUGGINGFACE_API_KEY", settings.huggingface_api_key)

litellm.drop_params = True

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


def generate(
    messages: list[dict[str, str]],
    model: str = "vertex_ai/openai/gpt-4o-mini",
    temperature: float = 0.0,
    max_tokens: int = 2048,
    timeout: float = 60.0,
) -> LLMResponse:
    """LLM 호출 — 재시도 + 토큰/레이턴시 추적.

    Args:
        messages: OpenAI 형식 메시지 리스트 [{"role": ..., "content": ...}].
        model: LiteLLM 모델 ID (예: "openai/gpt-4o-mini").
        temperature: 생성 온도.
        max_tokens: 최대 생성 토큰.
        timeout: API 호출 타임아웃(초).

    Returns:
        LLMResponse with content, model, token counts, latency.

    Raises:
        RuntimeError: 최대 재시도 초과 시.
    """
    last_error: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            start = time.monotonic()
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            elapsed = time.monotonic() - start

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model or model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency=round(elapsed, 3),
            )

        except RateLimitError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning("Rate limit (attempt %d/%d), %.1fs 대기: %s", attempt + 1, _MAX_RETRIES, delay, e)
                time.sleep(delay)

        except APIConnectionError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning("연결 오류 (attempt %d/%d), %.1fs 대기: %s", attempt + 1, _MAX_RETRIES, delay, e)
                time.sleep(delay)

    msg = f"LLM 호출 실패 ({_MAX_RETRIES}회 재시도 초과): {last_error}"
    raise RuntimeError(msg)

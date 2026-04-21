"""답변 생성 시스템 — LiteLLM 기반 멀티 모델 RAG 생성."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMResponse:
    """LLM 응답 결과."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency: float = 0.0


@dataclass(frozen=True)
class RAGResponse:
    """RAG 파이프라인 응답 — 검색 + 생성 통합 결과."""

    answer: str
    sources: list[dict] = field(default_factory=list)
    model: str = ""
    search_strategy: str = ""
    llm_response: LLMResponse | None = None
    retrieval_latency: float = 0.0
    generation_latency: float = 0.0

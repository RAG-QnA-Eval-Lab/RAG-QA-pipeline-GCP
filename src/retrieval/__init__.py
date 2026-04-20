"""검색 시스템 — Vector, BM25, Hybrid, Reranker 통합."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchResult:
    """단일 검색 결과."""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)
    rank: int = 0

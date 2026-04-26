"""Hybrid 검색 — RRF (Reciprocal Rank Fusion)."""

from __future__ import annotations

from src.retrieval import SearchResult

RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    k: int = RRF_K,
) -> list[SearchResult]:
    """여러 검색 결과 리스트를 RRF로 통합.

    Score(doc) = sum(1 / (k + rank_i)) for each result list.
    """
    score_map: dict[str, float] = {}
    content_map: dict[str, str] = {}
    metadata_map: dict[str, dict] = {}

    for results in result_lists:
        for result in results:
            policy_id = result.metadata.get("policy_id", "")
            chunk_idx = result.metadata.get("chunk_index", "")
            doc_key = f"{policy_id}_{chunk_idx}" if policy_id else result.content
            rrf_score = 1.0 / (k + result.rank)
            score_map[doc_key] = score_map.get(doc_key, 0.0) + rrf_score
            content_map[doc_key] = result.content
            metadata_map[doc_key] = result.metadata

    sorted_keys = sorted(score_map, key=lambda x: score_map[x], reverse=True)

    return [
        SearchResult(
            content=content_map[key],
            score=score_map[key],
            metadata=metadata_map[key],
            rank=rank,
        )
        for rank, key in enumerate(sorted_keys)
    ]


def hybrid_search(
    vector_results: list[SearchResult],
    bm25_results: list[SearchResult],
    k: int = RRF_K,
) -> list[SearchResult]:
    """Vector + BM25 결과를 RRF로 융합."""
    return reciprocal_rank_fusion([vector_results, bm25_results], k=k)

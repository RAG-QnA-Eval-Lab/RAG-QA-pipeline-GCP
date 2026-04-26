"""검색 엔드포인트."""

import logging
import time

from fastapi import APIRouter, Depends, Request

from src.api.auth import require_api_key
from src.api.deps import get_rag_pipeline
from src.api.rate_limit import limiter
from src.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from src.generation.pipeline import RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["search"], dependencies=[Depends(require_api_key)])

_ALLOWED_METADATA_KEYS = {"title", "category", "source_name", "region", "policy_id"}


@router.post("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
def search(request: Request, body: SearchRequest, pipeline: RAGPipeline = Depends(get_rag_pipeline)) -> SearchResponse:
    start = time.monotonic()
    results = pipeline.retrieval.search(
        query=body.query,
        strategy=body.strategy.value,
        top_k=body.top_k,
    )
    latency_ms = round((time.monotonic() - start) * 1000, 1)

    items = [
        SearchResultItem(
            content=r.content,
            score=r.score,
            metadata={k: v for k, v in r.metadata.items() if k in _ALLOWED_METADATA_KEYS},
            rank=r.rank,
        )
        for r in results
    ]
    return SearchResponse(
        results=items,
        strategy=body.strategy.value,
        total=len(items),
        latency_ms=latency_ms,
    )

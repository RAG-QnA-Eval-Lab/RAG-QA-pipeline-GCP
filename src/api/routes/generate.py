"""생성 엔드포인트."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from config.models import resolve_model_key
from src.api.auth import require_api_key
from src.api.deps import get_rag_pipeline
from src.api.rate_limit import limiter
from src.api.schemas import GenerateRequest, GenerateResponse, SourceItem, TokenUsage
from src.generation.llm_client import LLMError
from src.generation.pipeline import RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["generate"], dependencies=[Depends(require_api_key)])


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("30/minute")
def generate(
    request: Request, body: GenerateRequest, pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> GenerateResponse:
    model_id = resolve_model_key(body.model)

    try:
        if body.no_rag:
            resp = pipeline.run_no_rag(
                query=body.query,
                model=model_id,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
            )
        else:
            resp = pipeline.run(
                query=body.query,
                model=model_id,
                strategy=body.strategy.value,
                top_k=body.top_k,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
            )
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception:
        logger.exception("generate 엔드포인트 예기치 않은 오류 (query=%s)", body.query[:50])
        raise

    sources = [
        SourceItem(
            content=s["content"],
            title=s.get("title", ""),
            category=s.get("category", ""),
            source_name=s.get("source_name", ""),
            score=s.get("score", 0.0),
            rank=s.get("rank", 0),
        )
        for s in resp.sources
    ]

    lr = resp.llm_response
    usage = TokenUsage(
        prompt_tokens=lr.prompt_tokens if lr else 0,
        completion_tokens=lr.completion_tokens if lr else 0,
        total_tokens=lr.total_tokens if lr else 0,
    )

    total_latency = resp.retrieval_latency + resp.generation_latency

    return GenerateResponse(
        answer=resp.answer,
        sources=sources,
        model=resp.model,
        strategy=resp.search_strategy,
        token_usage=usage,
        retrieval_latency_ms=round(resp.retrieval_latency * 1000, 1),
        generation_latency_ms=round(resp.generation_latency * 1000, 1),
        total_latency_ms=round(total_latency * 1000, 1),
    )

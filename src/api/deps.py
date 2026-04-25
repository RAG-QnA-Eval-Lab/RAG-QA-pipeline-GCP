"""FastAPI 의존성 주입 — 공유 리소스 접근."""

from fastapi import Request

from src.generation.pipeline import RAGPipeline
from src.ingestion.mongo_client import PolicyMetadataStore


def get_rag_pipeline(request: Request) -> RAGPipeline:
    return request.app.state.rag_pipeline


def get_mongo(request: Request) -> PolicyMetadataStore | None:
    return getattr(request.app.state, "mongo", None)

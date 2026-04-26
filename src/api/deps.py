"""FastAPI 의존성 주입 — 공유 리소스 접근."""

from fastapi import HTTPException, Request

from src.generation.pipeline import RAGPipeline
from src.ingestion.mongo_client import PolicyMetadataStore


def get_rag_pipeline(request: Request) -> RAGPipeline:
    pipeline = getattr(request.app.state, "rag_pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline unavailable — FAISS index not loaded")
    return pipeline


def get_mongo(request: Request) -> PolicyMetadataStore | None:
    return getattr(request.app.state, "mongo", None)

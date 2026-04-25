"""FastAPI 애플리케이션 — lifespan 기반 초기화."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.api.errors import generic_exception_handler
from src.api.middleware import RequestLoggingMiddleware
from src.api.routes import evaluate, generate, models, policies, search
from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)

_APP_VERSION = "0.2.0"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_INDEX_DIR = Path(os.getenv("INDEX_DIR", str(_REPO_ROOT / "data" / "index")))


def _redact_mongo_target(uri: str) -> str:
    if not uri:
        return "<unset>"
    parsed = urlsplit(uri)
    host = parsed.hostname or "<unknown>"
    database = parsed.path.lstrip("/") or "<default>"
    return f"{host}/{database}"


def _build_cors_origins() -> list[str]:
    origins: list[str] = []
    if settings.api_base_url:
        origins.append(settings.api_base_url)
    origins.append("http://localhost:8501")
    origins.append("http://localhost:8000")
    extra = os.getenv("ALLOWED_ORIGINS", "")
    if extra:
        origins.extend(o.strip() for o in extra.split(",") if o.strip())
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.boot_time = time.monotonic()

    try:
        from src.generation.pipeline import RAGPipeline

        logger.info("Loading FAISS index from %s ...", _INDEX_DIR)
        app.state.rag_pipeline = RAGPipeline(index_dir=_INDEX_DIR)
        doc_count = app.state.rag_pipeline.retrieval.index.ntotal
        logger.info("FAISS loaded: %d vectors", doc_count)
    except Exception:
        logger.exception("FAISS index load failed — search/generate endpoints will return 503")
        app.state.rag_pipeline = None

    mongo = None
    try:
        from src.ingestion.mongo_client import PolicyMetadataStore

        mongo = PolicyMetadataStore()
        mongo.client.admin.command("ping")
        app.state.mongo = mongo
        logger.info("MongoDB connected: %s", _redact_mongo_target(settings.mongodb_uri))
    except Exception:
        logger.warning("MongoDB unavailable — policies endpoints disabled")
        app.state.mongo = None

    yield

    if mongo:
        mongo.close()
        logger.info("MongoDB connection closed")


app = FastAPI(
    title="RAG Youth Policy API",
    version=_APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(search.router)
app.include_router(generate.router)
app.include_router(policies.router)
app.include_router(models.router)
app.include_router(evaluate.router)


@app.get("/health", tags=["health"])
def health() -> JSONResponse:
    pipeline = getattr(app.state, "rag_pipeline", None)
    faiss_loaded = pipeline is not None
    doc_count = pipeline.retrieval.index.ntotal if pipeline is not None else 0

    mongo = getattr(app.state, "mongo", None)
    mongo_ok = False
    if mongo:
        try:
            mongo.client.admin.command("ping", maxTimeMS=500)
            mongo_ok = True
        except Exception:
            pass

    uptime = round(time.monotonic() - getattr(app.state, "boot_time", time.monotonic()), 1)

    status = "ok" if faiss_loaded else "degraded"
    status_code = 200 if faiss_loaded else 503

    body = HealthResponse(
        status=status,
        faiss_loaded=faiss_loaded,
        faiss_doc_count=doc_count,
        mongodb_connected=mongo_ok,
        uptime_seconds=uptime,
        version=_APP_VERSION,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())

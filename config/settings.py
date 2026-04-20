"""프로젝트 설정 — pydantic-settings 기반, .env 자동 로드."""

from __future__ import annotations

import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    data_portal_api_key: str = ""
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "rag_youth_policy"
    gcp_project: str = "rag-qna-eval"
    gcs_bucket: str = "rag-qna-eval-data"
    api_base_url: str = ""

    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 10
    rerank_top_k: int = 5
    default_model: str = "openai/gpt-4o-mini"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _warn_missing_keys(self) -> Settings:
        if not self.openai_api_key:
            warnings.warn("OPENAI_API_KEY 미설정 — 임베딩/생성 실패 가능", stacklevel=2)
        return self


settings = Settings()

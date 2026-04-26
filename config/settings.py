"""프로젝트 설정 — pydantic-settings 기반, .env 자동 로드."""

from __future__ import annotations

import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    huggingface_api_key: str = ""
    data_portal_api_key: str = ""
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "rag_youth_policy"
    gcp_project: str = "rag-qna-eval"
    gcs_bucket: str = "rag-qna-eval-data"
    qa_prompt_gcs_path: str = "prompts/qa_generation_system.txt"
    api_base_url: str = ""
    api_key: str = ""
    environment: str = "development"
    enable_cloud_monitoring: bool = False

    vertexai_project: str = "rag-qna-eval"
    vertexai_location: str = "asia-northeast3"
    gcp_location: str = "asia-northeast3"

    embedding_model: str = "vertex_ai/text-embedding-004"
    embedding_dim: int = 768
    index_gcs_prefix: str = "index"
    download_index_from_gcs: bool = True
    force_gcs_index_download: bool = False
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 10
    rerank_top_k: int = 5
    default_model: str = "openai/gpt-4o-mini"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _warn_missing_vertex_config(self) -> Settings:
        if not self.vertexai_project:
            warnings.warn("VERTEX_PROJECT 미설정 — Vertex AI 모델 호출 실패 가능", stacklevel=2)
        return self


settings = Settings()

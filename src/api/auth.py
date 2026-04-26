"""API Key 인증 — /api/v1/* 엔드포인트 보호."""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from config.settings import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """API Key 검증. settings.api_key가 비어있으면 인증을 건너뛴다 (개발 모드)."""
    if not settings.api_key:
        if settings.environment == "production":
            logger.error("API_KEY is empty in production — rejecting request")
            raise HTTPException(status_code=500, detail="Server misconfiguration")
        return "dev-mode"

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    if not hmac.compare_digest(api_key, settings.api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key

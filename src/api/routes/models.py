"""모델 목록 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter

from config.models import MODELS
from config.settings import settings
from src.api.schemas import ModelInfo, ModelsResponse

router = APIRouter(prefix="/api/v1", tags=["models"])


@router.get("/models", response_model=ModelsResponse)
def list_models() -> ModelsResponse:
    items = [
        ModelInfo(
            key=key,
            model_id=cfg["id"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
        for key, cfg in MODELS.items()
    ]

    default_key = next(
        (k for k, v in MODELS.items() if v["id"] == settings.default_model),
        settings.default_model,
    )
    return ModelsResponse(models=items, default_model=default_key)

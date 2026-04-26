"""모델 목록 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter

from config.models import MODELS
from config.settings import settings
from src.api.schemas import ModelInfo, ModelsResponse

router = APIRouter(prefix="/api/v1", tags=["models"])

_PROVIDER_KEY_MAP: dict[str, str] = {
    "openai/": "openai_api_key",
    "anthropic/": "anthropic_api_key",
    "huggingface/": "huggingface_api_key",
}


def _is_available(model_id: str) -> bool:
    """API 키가 설정된 프로바이더의 모델만 사용 가능."""
    for prefix, settings_attr in _PROVIDER_KEY_MAP.items():
        if model_id.startswith(prefix):
            return bool(getattr(settings, settings_attr, ""))
    return True


@router.get("/models", response_model=ModelsResponse)
def list_models() -> ModelsResponse:
    items = [
        ModelInfo(
            key=key,
            model_id=cfg["id"],
            description=cfg["description"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
        for key, cfg in MODELS.items()
        if _is_available(cfg["id"])
    ]

    default_key = next(
        (k for k, v in MODELS.items() if v["id"] == settings.default_model and _is_available(v["id"])),
        items[0].key if items else "",
    )
    return ModelsResponse(models=items, default_model=default_key)

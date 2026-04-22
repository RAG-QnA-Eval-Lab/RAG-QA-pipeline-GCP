"""수집 파이프라인 유틸리티 — 외부 ML 의존성 없음."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def save_policies_json(policies: list[dict], output_path: str | Path) -> Path:
    """정책 dict 리스트를 JSON으로 저장."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(policies, f, ensure_ascii=False, indent=2)
    logger.info("정책 JSON 저장: %s (%d건)", output_path, len(policies))
    return output_path

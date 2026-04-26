"""정책 데이터 수집기 기반 모듈.

모든 수집기가 공유하는 Policy 스키마와 BaseCollector ABC를 정의한다.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import ClassVar

logger = logging.getLogger(__name__)

CATEGORY_MAP: dict[str, str] = {
    "일자리": "employment",
    "주거": "housing",
    "교육": "education",
    "교육･직업훈련": "education",
    "금융･복지･문화": "welfare",
    "금융·복지·문화": "welfare",
    "참여·권리": "participation",
    "참여･기반": "participation",
    "참여권리": "participation",
    "창업": "startup",
    "복지": "welfare",
    "복지문화": "welfare",
    "금융": "finance",
}

VALID_CATEGORIES = frozenset({"housing", "employment", "startup", "education", "welfare", "finance", "participation"})


@dataclass(frozen=True)
class Policy:
    """정책 표준 스키마. 모든 수집기가 이 형태로 정규화한다."""

    policy_id: str
    title: str
    category: str
    summary: str
    description: str
    eligibility: str
    benefits: str
    how_to_apply: str
    application_period: str
    managing_department: str
    target_age: tuple[int, int]
    region: str
    source_url: str
    source_name: str
    last_updated: str
    raw_content: str

    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = ("policy_id", "title", "category", "source_name")


def validate_policy(policy: Policy) -> list[str]:
    """Policy 필수 필드 검증. 오류 목록을 반환한다 (빈 리스트 = 유효)."""
    errors: list[str] = []
    for field_name in Policy.REQUIRED_FIELDS:
        value = getattr(policy, field_name)
        if not value or not str(value).strip():
            errors.append(f"필수 필드 '{field_name}' 비어 있음")

    if policy.category and policy.category not in VALID_CATEGORIES:
        errors.append(f"유효하지 않은 카테고리: '{policy.category}' (허용: {sorted(VALID_CATEGORIES)})")

    if not isinstance(policy.target_age, tuple) or len(policy.target_age) != 2:
        errors.append(f"target_age는 (min, max) 튜플이어야 함: {policy.target_age}")

    return errors


def normalize_category(raw_category: str) -> str:
    """한국어/코드 카테고리를 영문 표준 카테고리로 변환."""
    if not raw_category:
        return "welfare"
    cat = raw_category.strip()
    # 복수 카테고리(예: "일자리,교육")는 첫 번째 값만 사용
    if "," in cat:
        cat = cat.split(",")[0].strip()
    normalized = CATEGORY_MAP.get(cat)
    if normalized:
        return normalized
    if cat in VALID_CATEGORIES:
        return cat
    logger.warning("알 수 없는 카테고리 '%s', 기본값 'welfare' 사용", raw_category)
    return "welfare"


_AGE_NO_LIMIT_SENTINEL = 99999


def parse_age(value: str | int) -> int:
    """연령 문자열/숫자를 int로 변환. 비정상 값은 0 또는 100 반환."""
    try:
        age = int(value)
        if age >= _AGE_NO_LIMIT_SENTINEL:
            return 100
        return max(age, 0)
    except (ValueError, TypeError):
        return 0


def build_raw_content(policy: Policy) -> str:
    """청킹용 전체 텍스트 생성."""
    from src.ingestion.collectors.region import format_region

    region_display = format_region(policy.region) if policy.region else ""
    parts = [
        f"정책명: {policy.title}",
        f"요약: {policy.summary}" if policy.summary else "",
        f"상세설명: {policy.description}" if policy.description else "",
        f"신청자격: {policy.eligibility}" if policy.eligibility else "",
        f"지원내용: {policy.benefits}" if policy.benefits else "",
        f"신청방법: {policy.how_to_apply}" if policy.how_to_apply else "",
        f"신청기간: {policy.application_period}" if policy.application_period else "",
        f"주관부처: {policy.managing_department}" if policy.managing_department else "",
        f"지역: {region_display}" if region_display else "",
    ]
    return "\n".join(p for p in parts if p)


def policy_to_dict(policy: Policy) -> dict[str, object]:
    """Policy를 직렬화 가능한 dict로 변환."""
    return {f.name: getattr(policy, f.name) for f in fields(policy)}


class BaseCollector(ABC):
    """정책 수집기 기본 인터페이스."""

    source_name: ClassVar[str] = ""

    @abstractmethod
    def collect(self, max_items: int | None = None) -> list[Policy]:
        """정책 데이터를 수집하여 정규화된 Policy 리스트로 반환."""

    def collect_validated(self, max_items: int | None = None) -> tuple[list[Policy], list[dict]]:
        """수집 + 검증. (유효한 정책 리스트, 오류 리스트) 반환."""
        policies = self.collect(max_items=max_items)
        valid: list[Policy] = []
        errors: list[dict] = []
        for policy in policies:
            errs = validate_policy(policy)
            if errs:
                errors.append({"policy_id": policy.policy_id, "title": policy.title, "errors": errs})
                logger.warning("정책 검증 실패: %s — %s", policy.policy_id, errs)
            else:
                valid.append(policy)
        logger.info("%s: 수집 %d건, 유효 %d건, 오류 %d건", self.source_name, len(policies), len(valid), len(errors))
        return valid, errors

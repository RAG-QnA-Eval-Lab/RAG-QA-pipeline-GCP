"""정책 카드 컴포넌트."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from src.ingestion.collectors.region import format_region
from src.ui.utils.style import CATEGORY_BG_COLORS, CATEGORY_COLORS, CATEGORY_LABELS


def _category_tag_html(category: str) -> str:
    color = CATEGORY_COLORS.get(category, "#78716C")
    bg = CATEGORY_BG_COLORS.get(category, "#F5F3EF")
    label = CATEGORY_LABELS.get(category, category or "기타")
    return f'<span class="category-tag" style="background:{bg};color:{color}">{label}</span>'


def render_policy_card(policy: dict[str, Any]) -> None:
    """정책 카드 (목록용)."""
    title = html.escape(policy.get("title", "제목 없음"))
    category = policy.get("category", "")
    summary = policy.get("summary") or policy.get("description") or ""
    tag_html = _category_tag_html(category)

    preview = html.escape(summary[:100] + "..." if len(summary) > 100 else summary)

    st.markdown(
        f"""<div class="policy-card">
            {tag_html}
            <h4>{title}</h4>
            <p>{preview}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_policy_detail(policy: dict[str, Any]) -> None:
    """정책 상세 정보 (expander 내부용)."""
    description = policy.get("description")
    if description:
        st.markdown(description)
        st.markdown("---")

    detail_fields = [
        ("자격 요건", policy.get("eligibility")),
        ("혜택", policy.get("benefits")),
        ("신청 방법", policy.get("how_to_apply")),
        ("신청 기간", policy.get("application_period")),
        ("담당 부서", policy.get("managing_department")),
        ("지역", format_region(policy.get("region", ""))),
        ("최종 업데이트", policy.get("last_updated")),
    ]
    has_detail = False
    for label, value in detail_fields:
        if value:
            has_detail = True
            st.markdown(f"**{label}**: {value}")

    if not description and not has_detail:
        st.caption("상세 정보가 아직 수집되지 않았습니다.")

    source_name = policy.get("source_name", "")
    source_url = policy.get("source_url", "")
    if source_url and source_url.startswith(("https://", "http://")):
        label = source_name or "원문 보기"
        st.markdown(f"**출처**: [{label}]({source_url})")
    elif source_name:
        st.markdown(f"**출처**: {source_name}")

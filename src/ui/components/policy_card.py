"""정책 카드 컴포넌트."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.ui.utils.style import CATEGORY_COLORS, CATEGORY_LABELS


def _category_tag_html(category: str) -> str:
    color = CATEGORY_COLORS.get(category, "#64748B")
    label = CATEGORY_LABELS.get(category, category or "기타")
    return f'<span class="category-tag" style="background:{color}">{label}</span>'


def render_policy_card(policy: dict[str, Any]) -> None:
    """정책 카드 (목록용)."""
    title = policy.get("title", "제목 없음")
    category = policy.get("category", "")
    summary = policy.get("summary") or ""
    tag_html = _category_tag_html(category)

    preview = summary[:120] + "..." if len(summary) > 120 else summary

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
    fields = [
        ("자격 요건", policy.get("eligibility")),
        ("혜택", policy.get("benefits")),
        ("지역", policy.get("region")),
        ("출처", policy.get("source_name")),
        ("최종 업데이트", policy.get("last_updated")),
    ]
    for label, value in fields:
        if value:
            st.markdown(f"**{label}**: {value}")

    summary = policy.get("summary")
    if summary:
        st.markdown("---")
        st.markdown(summary)

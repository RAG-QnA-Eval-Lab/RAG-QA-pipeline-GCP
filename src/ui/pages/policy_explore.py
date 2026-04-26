"""정책 탐색 페이지."""

from __future__ import annotations

import streamlit as st

from src.ui.components.policy_card import render_policy_card, render_policy_detail
from src.ui.utils.api_client import get_api_client
from src.ui.utils.session_state import KEY_POLICY_CATEGORY, KEY_POLICY_PAGE

CATEGORY_TABS = {
    None: "전체",
    "housing": "주거",
    "employment": "취업",
    "startup": "창업",
    "education": "교육",
    "welfare": "복지",
    "finance": "금융",
}

ITEMS_PER_PAGE = 12

st.title("🔍 정책 탐색")

client = get_api_client()

# ── 카테고리 탭 ─────────────────────────────────────

tab_keys = list(CATEGORY_TABS.keys())
tab_labels = list(CATEGORY_TABS.values())
tabs = st.tabs(tab_labels)

for tab, category_key in zip(tabs, tab_keys):
    with tab:
        if category_key != st.session_state.get(KEY_POLICY_CATEGORY):
            page = 1
        else:
            page = st.session_state.get(KEY_POLICY_PAGE, 1)

        data = client.get_policies(category=category_key, page=page, limit=ITEMS_PER_PAGE)

        if not data:
            st.warning("정책 데이터를 불러올 수 없습니다. API 서버를 확인하세요.")
            continue

        policies = data.get("policies", [])
        total = data.get("total", 0)

        if not policies:
            st.info("해당 카테고리에 정책이 없습니다.")
            continue

        st.caption(f"총 {total}건")

        cols = st.columns(3)
        for i, policy in enumerate(policies):
            with cols[i % 3]:
                render_policy_card(policy)
                pid = policy.get("policy_id", f"policy_{i}")
                with st.expander("상세 보기", expanded=False):
                    render_policy_detail(policy)

        # ── 페이지네이션 ────────────────────────────
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        if total_pages > 1:
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if page > 1 and st.button("← 이전", key=f"prev_{category_key}"):
                    st.session_state[KEY_POLICY_PAGE] = page - 1
                    st.session_state[KEY_POLICY_CATEGORY] = category_key
                    st.rerun()
            with nav_cols[1]:
                st.markdown(
                    f"<div style='text-align:center'>{page} / {total_pages}</div>",
                    unsafe_allow_html=True,
                )
            with nav_cols[2]:
                if page < total_pages and st.button("다음 →", key=f"next_{category_key}"):
                    st.session_state[KEY_POLICY_PAGE] = page + 1
                    st.session_state[KEY_POLICY_CATEGORY] = category_key
                    st.rerun()

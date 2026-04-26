"""Streamlit 메인 엔트리포인트."""

from __future__ import annotations

import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[2]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import streamlit as st  # noqa: E402

from src.ui.utils.api_client import get_api_client  # noqa: E402
from src.ui.utils.session_state import init_state  # noqa: E402
from src.ui.utils.style import CUSTOM_CSS  # noqa: E402

_PAGES_DIR = Path(__file__).resolve().parent / "pages"

st.set_page_config(
    page_title="청년 정책 QnA",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
init_state()

# ── 네비게이션 ──────────────────────────────────────

chatbot_page = st.Page(str(_PAGES_DIR / "chatbot.py"), title="정책 QnA", icon="💬", default=True)
explore_page = st.Page(str(_PAGES_DIR / "policy_explore.py"), title="정책 탐색", icon="🔍")
recommend_page = st.Page(str(_PAGES_DIR / "recommend.py"), title="맞춤 추천", icon="🎯")
dashboard_page = st.Page(str(_PAGES_DIR / "dashboard.py"), title="평가 대시보드", icon="📊")

nav = st.navigation([chatbot_page, explore_page, recommend_page, dashboard_page])

# ── 사이드바: 서버 상태 ─────────────────────────────

with st.sidebar:
    st.markdown("---")
    client = get_api_client()
    health = client.health()
    if health and health.get("status") == "ok":
        faiss_count = health.get("faiss_doc_count", 0)
        mongo_ok = health.get("mongodb_connected", False)
        st.markdown(
            f'<span class="status-dot ok"></span> 서버 연결됨 &nbsp;|&nbsp; 문서 {faiss_count:,}건',
            unsafe_allow_html=True,
        )
        if mongo_ok:
            st.caption("MongoDB 연결됨")
    else:
        st.markdown(
            '<span class="status-dot error"></span> 서버 연결 실패',
            unsafe_allow_html=True,
        )
        st.caption("API 서버를 확인하세요")

nav.run()

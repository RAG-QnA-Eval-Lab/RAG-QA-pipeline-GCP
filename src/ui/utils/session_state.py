"""세션 상태 초기화."""

from __future__ import annotations

import streamlit as st

KEY_MESSAGES = "messages"
KEY_MODEL = "selected_model"
KEY_STRATEGY = "selected_strategy"
KEY_TOP_K = "top_k"
KEY_TEMPERATURE = "temperature"
KEY_NO_RAG = "no_rag"
KEY_POLICY_PAGE = "policy_page"
KEY_POLICY_CATEGORY = "policy_category"

_DEFAULTS: dict[str, object] = {
    KEY_MESSAGES: [],
    KEY_MODEL: None,
    KEY_STRATEGY: "hybrid",
    KEY_TOP_K: 5,
    KEY_TEMPERATURE: 0.0,
    KEY_NO_RAG: False,
    KEY_POLICY_PAGE: 1,
    KEY_POLICY_CATEGORY: None,
}


def init_state() -> None:
    """세션 상태가 없으면 기본값으로 초기화."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            if isinstance(default, list):
                st.session_state[key] = list(default)
            else:
                st.session_state[key] = default

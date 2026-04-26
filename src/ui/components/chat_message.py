"""챗봇 메시지 컴포넌트."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_answer(response: dict[str, Any]) -> None:
    """생성 응답을 렌더링: 답변 + 출처 + 메트릭."""
    st.markdown(response.get("answer", ""))

    sources: list[dict[str, Any]] = response.get("sources", [])
    if sources:
        with st.expander(f"출처 ({len(sources)}건)", expanded=False):
            for i, src in enumerate(sources, 1):
                title = src.get("title", "제목 없음")
                source_name = src.get("source_name", "")
                score = src.get("score", 0.0)
                content = src.get("content", "")
                preview = content[:150] + "..." if len(content) > 150 else content
                header = f"**[{i}] {title}**"
                if source_name:
                    header += f"  ({source_name})"
                st.markdown(
                    f"""<div class="source-card">
                        {header} &nbsp; <code>{score:.2f}</code><br/>
                        <small>{preview}</small>
                    </div>""",
                    unsafe_allow_html=True,
                )

    token_usage = response.get("token_usage", {})
    total_tokens = token_usage.get("total_tokens", 0)
    retrieval_ms = response.get("retrieval_latency_ms", 0)
    generation_ms = response.get("generation_latency_ms", 0)
    total_ms = response.get("total_latency_ms", 0)
    model = response.get("model", "")
    strategy = response.get("strategy", "")

    parts: list[str] = []
    if model:
        parts.append(f"모델: {model}")
    if strategy:
        parts.append(f"전략: {strategy}")
    if total_tokens:
        parts.append(f"토큰: {total_tokens:,}")
    if total_ms:
        parts.append(f"검색 {retrieval_ms:.0f}ms + 생성 {generation_ms:.0f}ms = {total_ms:.0f}ms")

    if parts:
        st.caption(" | ".join(parts))

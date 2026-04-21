"""RAG 프롬프트 빌더 — 청년 정책 도메인 한국어 프롬프트."""

from __future__ import annotations

from src.retrieval import SearchResult

SYSTEM_PROMPT = (
    "당신은 대한민국 청년 정책 전문 상담사입니다.\n\n"
    "규칙:\n"
    "1. 반드시 아래 제공된 정책 문서에 있는 정보만 답변하세요.\n"
    "2. 문서에 없는 내용은 '제공된 정보에서 확인할 수 없습니다'라고 답하세요.\n"
    "3. 정책명과 출처를 반드시 명시하세요. 형식: [출처: 정책명, 관할부처]\n"
    "4. 신청 자격, 지원 내용, 신청 방법 등을 구체적으로 안내하세요.\n"
    "5. 답변은 한국어로 작성하세요."
)

NO_RAG_SYSTEM_PROMPT = (
    "당신은 대한민국 청년 정책 전문 상담사입니다.\n\n"
    "규칙:\n"
    "1. 알고 있는 정보를 바탕으로 최선의 답변을 제공하세요.\n"
    "2. 확실하지 않은 내용은 명확히 밝히세요.\n"
    "3. 답변은 한국어로 작성하세요."
)


def _format_context(results: list[SearchResult]) -> str:
    """검색 결과를 프롬프트용 컨텍스트 텍스트로 변환."""
    if not results:
        return "관련 정책 문서를 찾지 못했습니다."

    parts: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.metadata.get("title", "제목 없음")
        source = r.metadata.get("source_name", "")
        category = r.metadata.get("category", "")

        header = f"[{i}] {title}"
        if source:
            header += f" (출처: {source})"
        if category:
            header += f" [{category}]"

        parts.append(f"{header}\n{r.content}")

    return "\n\n".join(parts)


def build_rag_prompt(
    query: str,
    contexts: list[SearchResult],
) -> list[dict[str, str]]:
    """RAG 프롬프트 생성 — 검색 컨텍스트 포함."""
    context_text = _format_context(contexts)

    user_content = (
        f"참고 정책 문서:\n{context_text}\n\n"
        f"질문: {query}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_no_rag_prompt(query: str) -> list[dict[str, str]]:
    """No-RAG 프롬프트 — 비교 실험용, 컨텍스트 없이 질문만."""
    return [
        {"role": "system", "content": NO_RAG_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

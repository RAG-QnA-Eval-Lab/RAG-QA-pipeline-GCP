"""커스텀 CSS 스타일."""

from __future__ import annotations

CATEGORY_COLORS: dict[str, str] = {
    "housing": "#2563EB",
    "employment": "#059669",
    "startup": "#D97706",
    "education": "#7C3AED",
    "welfare": "#DC2626",
    "finance": "#0891B2",
}

CATEGORY_LABELS: dict[str, str] = {
    "housing": "주거",
    "employment": "취업",
    "startup": "창업",
    "education": "교육",
    "welfare": "복지",
    "finance": "금융",
}

CUSTOM_CSS = """
<style>
/* 정책 카드 */
.policy-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
    transition: box-shadow 0.2s ease;
}
.policy-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.policy-card h4 {
    margin: 0 0 0.5rem 0;
    font-size: 1.05rem;
    color: #1E293B;
}
.policy-card p {
    margin: 0;
    font-size: 0.9rem;
    color: #64748B;
    line-height: 1.5;
}

/* 카테고리 태그 */
.category-tag {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
    margin-bottom: 0.5rem;
}

/* 출처 카드 */
.source-card {
    background: #F8FAFC;
    border-left: 3px solid #2563EB;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0;
    border-radius: 0 8px 8px 0;
    font-size: 0.85rem;
}

/* 메트릭 하이라이트 */
.metric-box {
    background: #F1F5F9;
    border-radius: 8px;
    padding: 0.75rem;
    text-align: center;
}
.metric-box .value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1E293B;
}
.metric-box .label {
    font-size: 0.8rem;
    color: #64748B;
}

/* 사이드바 상태 표시 */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-dot.ok { background: #22C55E; }
.status-dot.error { background: #EF4444; }

/* 예시 질문 버튼 */
.example-btn {
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    background: white;
    cursor: pointer;
    text-align: left;
    font-size: 0.9rem;
    width: 100%;
    transition: border-color 0.15s;
}
.example-btn:hover {
    border-color: #2563EB;
}
</style>
"""

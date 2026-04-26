"""커스텀 CSS 스타일 — Linear-inspired precision light theme."""

from __future__ import annotations

CATEGORY_COLORS: dict[str, str] = {
    "housing": "#5E6AD2",
    "employment": "#0D9373",
    "startup": "#D4760A",
    "education": "#7C3AED",
    "welfare": "#E5484D",
    "finance": "#0B7285",
}

CATEGORY_BG_COLORS: dict[str, str] = {
    "housing": "rgba(94,106,210,0.08)",
    "employment": "rgba(13,147,115,0.08)",
    "startup": "rgba(212,118,10,0.08)",
    "education": "rgba(124,58,237,0.08)",
    "welfare": "rgba(229,72,77,0.08)",
    "finance": "rgba(11,114,133,0.08)",
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
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..700&display=swap');

/* ── 디자인 토큰 ──────────────────────────────────── */
:root {
    --bg-page: #F8F9FA;
    --bg-surface: #FFFFFF;
    --bg-elevated: #FFFFFF;
    --bg-sidebar: #F3F4F6;
    --bg-subtle: rgba(0,0,0,0.02);
    --bg-hover: rgba(0,0,0,0.03);

    --text-primary: #0A0A0B;
    --text-secondary: #3B3F46;
    --text-tertiary: #6B7280;
    --text-quaternary: #9CA3AF;

    --accent-indigo: #5E6AD2;
    --accent-bright: #6C72CB;
    --accent-hover: #7C82D2;
    --accent-subtle: rgba(94,106,210,0.06);
    --accent-muted: rgba(94,106,210,0.10);

    --border-default: rgba(0,0,0,0.06);
    --border-subtle: rgba(0,0,0,0.04);
    --border-emphasis: rgba(0,0,0,0.10);
    --border-accent: rgba(94,106,210,0.20);

    --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);

    --radius-xs: 4px;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-pill: 9999px;

    --success: #0D9373;
    --error: #E5484D;
    --warning: #D4760A;
}

/* ── 전역 타이포그래피 ─────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'SF Pro Display', system-ui, sans-serif !important;
    font-feature-settings: 'cv01', 'ss03';
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
h1, h2, h3, h4, h5 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-feature-settings: 'cv01', 'ss03';
    color: var(--text-primary);
}
h1 { letter-spacing: -0.04em; font-weight: 600; }
h2 { letter-spacing: -0.03em; font-weight: 600; }
h3 { letter-spacing: -0.02em; font-weight: 600; }
h4 { letter-spacing: -0.015em; font-weight: 600; }

/* ── 페이지 섹션 헤더 ─────────────────────────── */
.page-header {
    padding: 1.75rem 0 1.25rem 0;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-default);
}
.page-header h1 {
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.03em;
    color: var(--text-primary) !important;
    margin: 0 0 0.25rem 0 !important;
    line-height: 1.2;
}
.page-header p {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    margin: 0;
    font-weight: 400;
    line-height: 1.5;
}

/* ── 정책 카드 ─────────────────────────────────── */
.policy-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 1rem 1.15rem 0.85rem;
    margin-bottom: 0.65rem;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    position: relative;
}
.policy-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-sm);
}
.policy-card h4 {
    margin: 0.3rem 0 0.4rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.45;
    letter-spacing: -0.01em;
}
.policy-card p {
    margin: 0;
    font-size: 0.8rem;
    color: var(--text-tertiary);
    line-height: 1.55;
}

/* ── 카테고리 태그 ─────────────────────────────── */
.category-tag {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-pill);
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    border: 1px solid transparent;
}

/* ── 출처 카드 ─────────────────────────────────── */
.source-card {
    background: var(--bg-subtle);
    border: 1px solid var(--border-default);
    border-left: 2px solid var(--accent-indigo);
    padding: 0.75rem 0.9rem;
    margin: 0.4rem 0;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    font-size: 0.8rem;
    line-height: 1.55;
    transition: border-left-color 0.15s ease;
}
.source-card:hover {
    border-left-color: var(--accent-hover);
}
.source-card .source-header {
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
    font-size: 0.8rem;
}
.source-card .source-score {
    display: inline-block;
    background: var(--accent-subtle);
    color: var(--accent-indigo);
    padding: 0.1rem 0.4rem;
    border-radius: var(--radius-xs);
    font-size: 0.65rem;
    font-weight: 600;
    margin-left: 0.3rem;
    font-variant-numeric: tabular-nums;
}
.source-card .source-preview {
    color: var(--text-tertiary);
    font-size: 0.78rem;
}

/* ── 메트릭 카드 ───────────────────────────────── */
.metric-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 0.85rem 0.75rem;
    text-align: center;
    transition: border-color 0.15s ease;
}
.metric-card:hover {
    border-color: var(--border-accent);
}
.metric-card .metric-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--accent-indigo);
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
}
.metric-card .metric-label {
    font-size: 0.68rem;
    color: var(--text-quaternary);
    font-weight: 500;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── 상태 인디케이터 ───────────────────────────── */
.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0.3rem 0.65rem;
    border-radius: var(--radius-pill);
    font-size: 0.72rem;
    font-weight: 500;
}
.status-indicator.ok {
    background: rgba(13,147,115,0.08);
    color: var(--success);
}
.status-indicator.error {
    background: rgba(229,72,77,0.08);
    color: var(--error);
}
.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    animation: pulse-dot 2.5s ease-in-out infinite;
}
.status-dot.ok { background: var(--success); }
.status-dot.error { background: var(--error); }
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── 예시 질문 버튼 ────────────────────────────── */
.example-question {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 0.8rem 1rem;
    cursor: pointer;
    text-align: left;
    font-size: 0.82rem;
    color: var(--text-secondary);
    width: 100%;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    line-height: 1.4;
    font-weight: 400;
}
.example-question:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-xs);
}
.example-question .eq-icon {
    color: var(--accent-indigo);
    margin-right: 0.35rem;
}

/* ── 정보 배너 ─────────────────────────────────── */
.info-banner {
    background: var(--accent-subtle);
    border: 1px solid rgba(94,106,210,0.12);
    border-radius: var(--radius-md);
    padding: 0.85rem 1.1rem;
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ── 섹션 레이블 ───────────────────────────────── */
.section-label {
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-quaternary);
    margin: 1.5rem 0 0.65rem 0;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--border-subtle);
}

/* ── 응답 메트릭 바 ────────────────────────────── */
.response-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.65rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--border-subtle);
}
.response-meta .meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 0.15rem 0.45rem;
    background: var(--bg-subtle);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xs);
    font-size: 0.65rem;
    color: var(--text-tertiary);
    font-weight: 500;
    font-variant-numeric: tabular-nums;
}

/* ── Streamlit 오버라이드 ──────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    border-bottom: 1px solid var(--border-default);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 0.45rem 0.9rem !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    color: var(--text-tertiary) !important;
    border: none !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent-indigo) !important;
    border-bottom: 2px solid var(--accent-indigo) !important;
}
div[data-testid="stExpander"] {
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s ease !important;
    border: 1px solid var(--border-default) !important;
}
.stButton > button:hover {
    border-color: var(--border-emphasis) !important;
    box-shadow: var(--shadow-xs) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"] {
    background: var(--accent-indigo) !important;
    border-color: var(--accent-indigo) !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stFormSubmitButton"]:hover {
    background: var(--accent-hover) !important;
    border-color: var(--accent-hover) !important;
}
[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-default) !important;
}
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown h2 {
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-quaternary) !important;
    margin-bottom: 0.5rem !important;
}

/* ── 채팅 메시지 ───────────────────────────────── */
[data-testid="stChatMessage"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.75rem !important;
}
[data-testid="stChatInput"] > div {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-default) !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--accent-indigo) !important;
    box-shadow: 0 0 0 2px rgba(94,106,210,0.12) !important;
}

/* ── 파일 업로더 ───────────────────────────────── */
[data-testid="stFileUploader"] > div {
    border: 1px dashed var(--border-default) !important;
    border-radius: var(--radius-md) !important;
}

/* ── 셀렉트박스 / 인풋 ─────────────────────────── */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    border-radius: var(--radius-sm) !important;
}

/* ── 데이터프레임 ──────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}
</style>
"""

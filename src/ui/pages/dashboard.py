"""평가 대시보드 페이지."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import streamlit as st

from src.ui.components.metrics_display import render_eval_summary, render_metrics_table

logger = logging.getLogger(__name__)

_RESULTS_DIR = Path("data/eval/results")


def _load_result_files() -> dict[str, list[dict[str, Any]]]:
    """data/eval/results/ 디렉토리의 JSON 파일 로드."""
    results: dict[str, list[dict[str, Any]]] = {}
    if not _RESULTS_DIR.exists():
        return results
    for fp in sorted(_RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                results[fp.stem] = data
            elif isinstance(data, dict) and "results" in data:
                results[fp.stem] = data["results"]
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load %s", fp)
    return results


def _show_average_chart(items: list[dict[str, Any]]) -> None:
    """평균 메트릭을 바 차트로 표시."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.caption("Plotly가 설치되지 않아 차트를 표시할 수 없습니다.")
        return

    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}

    for item in items:
        ragas = item.get("ragas") or {}
        for k, v in ragas.items():
            if v is not None:
                metric_sums[f"RAGAS/{k}"] = metric_sums.get(f"RAGAS/{k}", 0) + v
                metric_counts[f"RAGAS/{k}"] = metric_counts.get(f"RAGAS/{k}", 0) + 1

        judge = item.get("judge") or {}
        for k, v in judge.items():
            if v is not None:
                metric_sums[f"Judge/{k}"] = metric_sums.get(f"Judge/{k}", 0) + v
                metric_counts[f"Judge/{k}"] = metric_counts.get(f"Judge/{k}", 0) + 1

    if not metric_sums:
        return

    labels = list(metric_sums.keys())
    averages = [metric_sums[k] / metric_counts[k] for k in labels]

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=averages,
            marker_color=[
                "#2563EB" if "RAGAS" in name else "#059669"
                for name in labels
            ],
        )
    ])
    fig.update_layout(
        title="평균 메트릭 점수",
        yaxis_title="점수",
        yaxis_range=[0, 1],
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── 페이지 렌더링 ──────────────────────────────────

st.title("📊 평가 대시보드")

uploaded = st.file_uploader("평가 결과 JSON 파일 업로드", type=["json"])
uploaded_results: list[dict[str, Any]] | None = None
if uploaded is not None:
    try:
        raw = json.loads(uploaded.read())
        if isinstance(raw, list):
            uploaded_results = raw
        elif isinstance(raw, dict) and "results" in raw:
            uploaded_results = raw["results"]
        else:
            st.error("지원하지 않는 JSON 형식입니다.")
    except json.JSONDecodeError:
        st.error("잘못된 JSON 파일입니다.")

all_results = _load_result_files()

if uploaded_results:
    all_results["(업로드됨)"] = uploaded_results

if not all_results:
    st.info(
        "평가 결과가 없습니다. `data/eval/results/` 디렉토리에 JSON 파일을 추가하거나 위에서 업로드하세요."
    )
    st.stop()

result_names = list(all_results.keys())
selected_name = st.selectbox("평가 결과 선택", result_names)

if selected_name:
    items = all_results[selected_name]
    st.markdown(f"### {selected_name} ({len(items)}건)")

    if items:
        st.markdown("#### 전체 결과 테이블")
        render_metrics_table(items)

        st.markdown("#### 개별 결과 상세")
        for item in items:
            item_id = item.get("id", "unknown")
            with st.expander(f"Sample: {item_id}"):
                render_eval_summary(item)

        _show_average_chart(items)

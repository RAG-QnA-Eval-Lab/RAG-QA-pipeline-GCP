"""평가 메트릭 시각화 컴포넌트."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_eval_summary(result: dict[str, Any]) -> None:
    """단일 평가 결과의 RAGAS / Judge / Safety 점수 표시."""
    ragas = result.get("ragas")
    judge = result.get("judge")
    safety = result.get("safety")

    if ragas:
        st.markdown("**RAGAS**")
        cols = st.columns(4)
        _metric(cols[0], "Faithfulness", ragas.get("faithfulness"))
        _metric(cols[1], "Answer Relevancy", ragas.get("answer_relevancy"))
        _metric(cols[2], "Context Precision", ragas.get("context_precision"))
        _metric(cols[3], "Context Recall", ragas.get("context_recall"))

    if judge:
        st.markdown("**LLM Judge**")
        cols = st.columns(4)
        _metric(cols[0], "인용 정확도", judge.get("citation_accuracy"))
        _metric(cols[1], "완전성", judge.get("completeness"))
        _metric(cols[2], "가독성", judge.get("readability"))
        _metric(cols[3], "평균", judge.get("average"))

    if safety:
        st.markdown("**Safety**")
        cols = st.columns(2)
        _metric(cols[0], "환각 점수", safety.get("hallucination_score"))

    if result.get("error"):
        st.error(f"평가 오류: {result['error']}")


def _metric(col: st.delta_generator.DeltaGenerator, label: str, value: float | None) -> None:
    if value is not None:
        col.metric(label, f"{value:.2f}")
    else:
        col.metric(label, "N/A")


def render_metrics_table(results: list[dict[str, Any]]) -> None:
    """여러 평가 결과를 테이블 형태로 표시."""
    rows: list[dict[str, Any]] = []
    for r in results:
        row: dict[str, Any] = {"ID": r.get("id", "")}
        ragas = r.get("ragas") or {}
        row["Faithfulness"] = ragas.get("faithfulness")
        row["Answer Rel."] = ragas.get("answer_relevancy")
        row["Ctx Precision"] = ragas.get("context_precision")
        row["Ctx Recall"] = ragas.get("context_recall")
        judge = r.get("judge") or {}
        row["Judge Avg"] = judge.get("average")
        safety = r.get("safety") or {}
        row["Hallucination"] = safety.get("hallucination_score")
        row["Error"] = r.get("error", "")
        rows.append(row)

    if rows:
        st.dataframe(rows, use_container_width=True)

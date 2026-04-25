"""Stage 3 — DeepEval 안전성 평가 (Hallucination Detection)."""

from __future__ import annotations

import logging

from src.evaluation import SafetyResult

logger = logging.getLogger(__name__)


def evaluate_safety(
    question: str,
    contexts: list[str],
    answer: str,
) -> SafetyResult:
    """DeepEval HallucinationMetric으로 환각 점수 측정.

    RAGAS Faithfulness가 '근거 부족'을 탐지하는 반면,
    DeepEval Hallucination은 '컨텍스트와 명시적 모순'을 탐지한다.

    Args:
        question: 사용자 질문.
        contexts: 검색된 컨텍스트.
        answer: 생성된 답변.

    Returns:
        SafetyResult — hallucination_score (0.0~1.0, 낮을수록 안전).
        평가 실패 시 hallucination_score=None.
    """
    try:
        from deepeval.metrics import HallucinationMetric
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            context=contexts,
        )

        metric = HallucinationMetric(threshold=0.5)
        metric.measure(test_case)

        score = metric.score
        logger.info("Hallucination score: %.4f (reason: %s)", score, metric.reason)
        return SafetyResult(hallucination_score=float(score))

    except Exception:
        logger.exception("DeepEval 안전성 평가 실패")
        return SafetyResult(hallucination_score=None)

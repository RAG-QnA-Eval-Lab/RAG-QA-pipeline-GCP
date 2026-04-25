"""평가 엔드포인트."""

import logging

from fastapi import APIRouter

from src.api.schemas import EvalRequest, EvalResponse, EvalResultItem
from src.evaluation.evaluator import RAGEvaluator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["evaluate"])


@router.post("/evaluate", response_model=EvalResponse)
def evaluate(body: EvalRequest) -> EvalResponse:
    evaluator = RAGEvaluator(judge_model=body.judge_model or "vertex_ai/openai/gpt-4o-mini")

    results: list[EvalResultItem] = []
    errors = 0

    for sample in body.samples:
        try:
            er = evaluator.evaluate_single(
                question=sample.question,
                contexts=sample.contexts,
                answer=sample.answer,
                ground_truth=sample.ground_truth,
            )
            ragas_dict = None
            if er.ragas:
                ragas_dict = {
                    "faithfulness": er.ragas.faithfulness,
                    "answer_relevancy": er.ragas.answer_relevancy,
                    "context_precision": er.ragas.context_precision,
                    "context_recall": er.ragas.context_recall,
                }
            judge_dict = None
            if er.judge:
                judge_dict = {
                    "citation_accuracy": er.judge.citation_accuracy,
                    "completeness": er.judge.completeness,
                    "readability": er.judge.readability,
                    "average": er.judge.average,
                }
            safety_dict = None
            if er.safety:
                safety_dict = {"hallucination_score": er.safety.hallucination_score}

            results.append(
                EvalResultItem(
                    id=sample.id,
                    ragas=ragas_dict,
                    judge=judge_dict,
                    safety=safety_dict,
                    latency=er.latency,
                )
            )
        except Exception:
            logger.exception("Eval failed for sample %s", sample.id)
            errors += 1
            results.append(EvalResultItem(id=sample.id, error="evaluation_failed"))

    return EvalResponse(
        results=results,
        total=len(body.samples),
        evaluated=len(body.samples) - errors,
        errors=errors,
    )

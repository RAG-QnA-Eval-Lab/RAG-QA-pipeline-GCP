"""평가 파이프라인 DAG.

스케줄: 수동 트리거 (schedule=None). 모델별 RAG 응답 생성 → 평가 수행.
QA 데이터셋이 data/eval/qa_pairs.json에 존재해야 함.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param

from dags.utils.notifications import on_failure_callback

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "rag-pipeline",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "on_failure_callback": on_failure_callback,
}

QA_DATASET_PATH = "data/eval/qa_pairs.json"
RESULTS_DIR = "data/eval/results"


@dag(
    dag_id="evaluation_pipeline",
    default_args=DEFAULT_ARGS,
    description="모델별 RAG 응답 생성 + 평가 (RAGAS / LLM Judge)",
    schedule=None,
    start_date=datetime(2026, 4, 25),
    catchup=False,
    tags=["evaluation", "manual"],
    params={
        "models": Param(
            default=["gpt-4o-mini", "gemini-flash"],
            type="array",
            description="평가할 모델 키 (config/models.py MODELS dict)",
        ),
        "strategy": Param(
            default="hybrid_rerank",
            type="string",
            enum=["vector_only", "bm25_only", "hybrid", "hybrid_rerank"],
            description="검색 전략",
        ),
        "max_samples": Param(
            default=0,
            type="integer",
            description="평가 샘플 수 (0=전체)",
        ),
    },
)
def evaluation_pipeline():
    @task()
    def load_qa_dataset(**context) -> list[dict]:
        """QA 데이터셋 로드."""
        qa_path = Path(QA_DATASET_PATH)
        if not qa_path.exists():
            raise FileNotFoundError(f"QA 데이터셋 없음: {qa_path}")

        with open(qa_path) as f:
            dataset = json.load(f)

        samples = dataset.get("samples", [])
        max_samples = context["params"].get("max_samples", 0)
        if max_samples > 0:
            samples = samples[:max_samples]

        logger.info("QA 데이터셋 로드: %d건", len(samples))
        return samples

    @task()
    def generate_rag_responses(qa_samples: list[dict], **context) -> dict:
        """모델별 RAG 응답 생성."""
        from src.generation.pipeline import RAGPipeline

        models = context["params"]["models"]
        strategy = context["params"]["strategy"]

        pipeline = RAGPipeline()
        all_results: dict[str, list[dict]] = {}

        for model_key in models:
            model_results: list[dict] = []
            for sample in qa_samples:
                query = sample["question"]
                try:
                    response = pipeline.run(
                        query=query,
                        model=model_key,
                        strategy=strategy,
                    )
                    model_results.append(
                        {
                            "id": sample["id"],
                            "question": query,
                            "ground_truth": sample.get("ground_truth", ""),
                            "answer": response.answer,
                            "model": response.model,
                            "strategy": strategy,
                            "retrieval_latency": response.retrieval_latency,
                            "generation_latency": response.generation_latency,
                            "total_tokens": response.total_tokens,
                            "contexts": [r.content for r in response.search_results[:3]],
                        }
                    )
                except Exception:
                    logger.exception("응답 생성 실패: model=%s, q=%s", model_key, query[:50])
                    model_results.append(
                        {
                            "id": sample["id"],
                            "question": query,
                            "error": True,
                        }
                    )

            all_results[model_key] = model_results
            logger.info("모델 %s: %d건 응답 생성", model_key, len(model_results))

        return all_results

    @task()
    def save_results(rag_results: dict, **context) -> str:
        """평가 결과 저장."""
        results_dir = Path(RESULTS_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)

        run_id = context["run_id"]
        output_path = results_dir / f"eval_{run_id}.json"

        output = {
            "run_id": run_id,
            "strategy": context["params"]["strategy"],
            "models": context["params"]["models"],
            "results": rag_results,
            "total_samples": sum(len(v) for v in rag_results.values()),
        }

        with open(output_path, "w") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info("결과 저장: %s", output_path)
        return str(output_path)

    qa = load_qa_dataset()
    results = generate_rag_responses(qa)
    save_results(results)


evaluation_pipeline()

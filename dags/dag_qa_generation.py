"""QA 데이터셋 생성 DAG.

스케줄: 수동 트리거 (schedule=None).
정책 원본에서 LLM을 이용해 QA 쌍을 생성한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param

from utils.notifications import on_failure_callback

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "rag-pipeline",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "on_failure_callback": on_failure_callback,
}


@dag(
    dag_id="qa_generation",
    default_args=DEFAULT_ARGS,
    description="정책 데이터에서 QA 쌍 생성 (LLM 기반)",
    schedule=None,
    start_date=datetime(2026, 4, 25),
    catchup=False,
    tags=["qa", "manual"],
    params={
        "target_count": Param(default=100, type="integer", description="생성할 QA 쌍 수"),
        "model": Param(
            default="vertex_ai/gemini-2.5-flash",
            type="string",
            description="QA 생성에 사용할 LLM 모델 ID",
        ),
        "policies_path": Param(
            default="data/policies/raw",
            type="string",
            description="정책 원본 디렉토리",
        ),
        "output_path": Param(
            default="data/eval/qa_pairs.json",
            type="string",
            description="QA 데이터셋 출력 경로",
        ),
        "dry_run": Param(default=False, type="boolean", description="드라이런 (LLM 호출 없이 테스트)"),
    },
)
def qa_generation():
    @task()
    def generate_qa(**context) -> dict:
        """LLM으로 QA 데이터셋 생성."""
        from scripts.generate_qa import generate_qa_dataset

        params = context["params"]
        result = generate_qa_dataset(
            policies_path=Path(params["policies_path"]),
            output_path=Path(params["output_path"]),
            target_count=params["target_count"],
            model=params["model"],
            dry_run=params["dry_run"],
        )
        logger.info("QA 생성 완료: %s", result)
        return result

    @task()
    def upload_to_gcs(gen_result: dict, **context) -> str:  # noqa: ARG001
        """생성된 QA 데이터셋을 GCS에 업로드."""
        from config.settings import settings
        from src.ingestion.gcs_client import GCSClient

        output_path = context["params"]["output_path"]
        gcs = GCSClient(settings.gcs_bucket)
        gcs_path = f"eval/{Path(output_path).name}"
        gcs.upload_file(Path(output_path), gcs_path)

        gcs_uri = f"gs://{settings.gcs_bucket}/{gcs_path}"
        logger.info("GCS 업로드 완료: %s", gcs_uri)
        return gcs_uri

    result = generate_qa()
    upload_to_gcs(result)


qa_generation()

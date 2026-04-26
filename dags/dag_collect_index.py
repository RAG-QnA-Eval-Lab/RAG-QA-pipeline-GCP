"""데이터 수집 + FAISS 인덱스 빌드 DAG.

스케줄: 매일 02:00 KST (17:00 UTC).
흐름: 전체 소스 수집 → GCS 인덱스 빌드 → Cloud Run 재시작 (새 인덱스 반영).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.decorators import dag, task
from utils.cloud_run import restart_cloud_run_service
from utils.notifications import on_failure_callback

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "rag-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": on_failure_callback,
}

REPO_ROOT = Path("/opt/rag-pipeline")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
RAW_OUTPUT_DIR = REPO_ROOT / "data" / "policies" / "raw"


@dag(
    dag_id="collect_and_index",
    default_args=DEFAULT_ARGS,
    description="정책 수집 → GCS 인덱스 빌드 → Cloud Run 재시작",
    schedule="0 17 * * *",
    start_date=pendulum.datetime(2026, 4, 25, tz="Asia/Seoul"),
    catchup=False,
    tags=["ingestion", "daily"],
    max_active_runs=1,
)
def collect_and_index():
    @task()
    def collect_all_sources() -> dict:
        """모든 수집기 실행 → 로컬 + GCS + MongoDB 저장."""
        from scripts.collect_policies import run_all_collections

        # Airflow task의 cwd는 배포/실행 방식에 따라 달라질 수 있다.
        # 상대경로 "data/..."를 쓰면 /opt/rag-pipeline 밖에 쓰려다 PermissionError가 날 수 있어
        # 항상 repo 내부 절대경로를 사용한다.
        os.chdir(REPO_ROOT)
        RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results = run_all_collections(output_dir=str(RAW_OUTPUT_DIR))
        if all(v == "failed" for v in results.values()):
            raise RuntimeError(f"전체 수집 실패: {results}")

        logger.info("수집 결과: %s", results)
        return results

    @task()
    def rebuild_index(collect_result: dict) -> dict:  # noqa: ARG001
        """GCS 원본 → 청킹 → 임베딩 → FAISS 인덱스 빌드 → GCS 업로드."""
        from src.ingestion.pipeline import build_index_from_gcs

        result = build_index_from_gcs()
        if not result.get("index_built"):
            raise RuntimeError(f"인덱스 빌드 실패: {result}")

        logger.info(
            "인덱스 빌드 완료: %d문서, %d청크, dim=%d",
            result["documents"],
            result["chunks"],
            result.get("embedding_dim", 0),
        )
        return result

    @task()
    def restart_api(index_result: dict) -> str:  # noqa: ARG001
        """Cloud Run API 서비스 재시작 — 새 인덱스 로드."""
        return restart_cloud_run_service(
            service="rag-youth-policy-api",
            region="asia-northeast3",
        )

    collected = collect_all_sources()
    indexed = rebuild_index(collected)
    restart_api(indexed)


collect_and_index()

"""정책 수집 CLI — 수집기 → JSON 저장 + GCS 업로드 + MongoDB 메타데이터.

사용법:
    python scripts/collect_policies.py --all
    python scripts/collect_policies.py --source data_portal --max-items 50
    python scripts/collect_policies.py --all --skip-gcs --skip-mongo   # 로컬 테스트
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from config.settings import settings  # noqa: E402
from src.ingestion.collectors.base import BaseCollector, policy_to_dict  # noqa: E402
from src.ingestion.collectors.data_portal import DataPortalCollector  # noqa: E402
from src.ingestion.utils import save_policies_json  # noqa: E402

logger = logging.getLogger(__name__)

COLLECTORS: dict[str, type[BaseCollector]] = {
    "data_portal": DataPortalCollector,
}


def run_collection(
    source: str,
    max_items: int | None = None,
    output_dir: str = "data/policies/raw",
    *,
    skip_gcs: bool = False,
    skip_mongo: bool = False,
) -> None:
    collector_cls = COLLECTORS.get(source)
    if not collector_cls:
        logger.error("알 수 없는 소스: %s (사용 가능: %s)", source, list(COLLECTORS.keys()))
        sys.exit(1)

    logger.info("수집 시작: %s (max_items=%s)", source, max_items)
    collector = collector_cls()
    valid_policies, errors = collector.collect_validated(max_items=max_items)

    if not valid_policies:
        logger.warning("수집된 정책 없음")
        return

    policy_dicts = [policy_to_dict(p) for p in valid_policies]

    # 1. 로컬 JSON 저장 (캐시)
    local_path = Path(output_dir) / f"{source}_policies.json"
    save_policies_json(policy_dicts, local_path)
    logger.info("로컬 저장 완료: %d건 → %s", len(valid_policies), local_path)

    # 2. GCS 업로드
    gcs_uri = None
    if not skip_gcs:
        try:
            from src.ingestion.gcs_client import GCSClient

            gcs = GCSClient(settings.gcs_bucket)
            gcs_path = f"policies/raw/{source}_policies.json"
            gcs_uri = gcs.upload_json(gcs_path, policy_dicts)
            logger.info("GCS 업로드 완료: %s", gcs_uri)
        except Exception:
            logger.exception("GCS 업로드 실패 — 로컬 파일은 저장됨")

    # 3. MongoDB 메타데이터 upsert
    if not skip_mongo:
        try:
            from src.ingestion.mongo_client import PolicyMetadataStore

            mongo = PolicyMetadataStore()
            gcs_raw_path = f"gs://{settings.gcs_bucket}/policies/raw/{source}_policies.json"
            metadata_list = [
                {
                    "policy_id": p["policy_id"],
                    "title": p["title"],
                    "category": p.get("category", ""),
                    "source_name": source,
                    "gcs_path": gcs_raw_path,
                    "status": "active",
                }
                for p in policy_dicts
                if p.get("policy_id")
            ]
            upserted = mongo.upsert_policies_batch(metadata_list)
            logger.info("MongoDB upsert 완료: %d건", upserted)

            # 4. 수집 이력 기록
            mongo.log_ingestion(
                source=source,
                collected_count=len(policy_dicts),
                valid_count=len(valid_policies),
                gcs_paths=[gcs_uri] if gcs_uri else [],
            )
            mongo.close()
        except Exception:
            logger.exception("MongoDB 연동 실패 — 로컬 파일은 저장됨")

    if errors:
        logger.warning("검증 오류 %d건", len(errors))
        for e in errors[:5]:
            logger.warning("  - %s: %s", e["policy_id"], e["errors"])


def run_all_collections(
    max_items: int | None = None,
    output_dir: str = "data/policies/raw",
    *,
    skip_gcs: bool = False,
    skip_mongo: bool = False,
) -> dict[str, str]:
    """전체 소스 수집 실행. 소스별 성공/실패 결과 dict 반환."""
    results: dict[str, str] = {}
    for source in COLLECTORS:
        try:
            run_collection(
                source,
                max_items=max_items,
                output_dir=output_dir,
                skip_gcs=skip_gcs,
                skip_mongo=skip_mongo,
            )
            results[source] = "success"
        except Exception:
            results[source] = "failed"
            logger.exception("수집 실패: %s", source)
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="정책 데이터 수집")
    parser.add_argument("--source", choices=list(COLLECTORS.keys()), help="수집할 소스")
    parser.add_argument("--all", action="store_true", help="모든 소스 수집")
    parser.add_argument("--max-items", type=int, default=None, help="최대 수집 건수")
    parser.add_argument("--output-dir", default="data/policies/raw", help="출력 디렉토리")
    parser.add_argument("--skip-gcs", action="store_true", help="GCS 업로드 건너뛰기 (로컬 테스트)")
    parser.add_argument("--skip-mongo", action="store_true", help="MongoDB 연동 건너뛰기 (로컬 테스트)")
    args = parser.parse_args()

    if args.all:
        run_all_collections(
            max_items=args.max_items,
            output_dir=args.output_dir,
            skip_gcs=args.skip_gcs,
            skip_mongo=args.skip_mongo,
        )
    elif args.source:
        run_collection(
            args.source,
            max_items=args.max_items,
            output_dir=args.output_dir,
            skip_gcs=args.skip_gcs,
            skip_mongo=args.skip_mongo,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

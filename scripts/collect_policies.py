"""정책 수집 CLI — 수집기 → JSON 저장 + MongoDB 메타데이터.

사용법:
    python scripts/collect_policies.py --all
    python scripts/collect_policies.py --source data_portal --max-items 50
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from src.ingestion.collectors.base import BaseCollector, policy_to_dict  # noqa: E402
from src.ingestion.collectors.data_portal import DataPortalCollector  # noqa: E402
from src.ingestion.pipeline import save_policies_json  # noqa: E402

logger = logging.getLogger(__name__)

COLLECTORS: dict[str, type[BaseCollector]] = {
    "data_portal": DataPortalCollector,
}


def run_collection(source: str, max_items: int | None = None, output_dir: str = "data/policies/raw") -> None:
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
    output_path = Path(output_dir) / f"{source}_policies.json"
    save_policies_json(policy_dicts, output_path)

    logger.info("수집 완료: %d건 저장 → %s", len(valid_policies), output_path)
    if errors:
        logger.warning("검증 오류 %d건", len(errors))
        for e in errors[:5]:
            logger.warning("  - %s: %s", e["policy_id"], e["errors"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="정책 데이터 수집")
    parser.add_argument("--source", choices=list(COLLECTORS.keys()), help="수집할 소스")
    parser.add_argument("--all", action="store_true", help="모든 소스 수집")
    parser.add_argument("--max-items", type=int, default=None, help="최대 수집 건수")
    parser.add_argument("--output-dir", default="data/policies/raw", help="출력 디렉토리")
    args = parser.parse_args()

    if args.all:
        for source in COLLECTORS:
            run_collection(source, max_items=args.max_items, output_dir=args.output_dir)
    elif args.source:
        run_collection(args.source, max_items=args.max_items, output_dir=args.output_dir)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

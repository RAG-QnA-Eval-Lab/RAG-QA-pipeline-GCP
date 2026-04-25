"""정책 데이터셋 정리 유틸리티 — raw 집합을 정규화/카테고리별 파생본으로 저장."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

from src.ingestion.utils import save_policies_json

logger = logging.getLogger(__name__)

DEFAULT_POLICY_ROOT = Path("data/policies")


def load_policy_records(path: str | Path) -> list[dict]:
    """파일 또는 디렉토리에서 정책 dict 리스트를 로드한다."""
    path = Path(path)
    if path.is_dir():
        records: list[dict] = []
        for file_path in sorted(path.rglob("*.json")):
            if file_path.name == "manifest.json":
                continue
            records.extend(_load_policy_file(file_path))
        return records
    return _load_policy_file(path)


def build_policy_views(policies: list[dict]) -> dict[str, object]:
    """정책 리스트를 정규화하고 by_source / by_category 뷰를 만든다."""
    normalized = [_normalize_policy(policy) for policy in policies if policy.get("policy_id")]
    deduped = _dedupe_policies(normalized)

    by_source: dict[str, list[dict]] = defaultdict(list)
    by_category: dict[str, list[dict]] = defaultdict(list)

    for policy in deduped:
        by_source[policy.get("source_name", "unknown")].append(policy)
        by_category[policy.get("category", "uncategorized")].append(policy)

    for items in by_source.values():
        items.sort(key=lambda policy: policy.get("policy_id", ""))
    for items in by_category.values():
        items.sort(key=lambda policy: policy.get("policy_id", ""))

    manifest = {
        "total_policies": len(deduped),
        "sources": dict(Counter(policy.get("source_name", "unknown") for policy in deduped)),
        "categories": dict(Counter(policy.get("category", "uncategorized") for policy in deduped)),
        "scopes": dict(Counter(policy.get("scope", "unknown") for policy in deduped)),
    }

    return {
        "all_policies": deduped,
        "by_source": dict(by_source),
        "by_category": dict(by_category),
        "manifest": manifest,
    }


def materialize_policy_views(
    policies: list[dict],
    policy_root: str | Path = DEFAULT_POLICY_ROOT,
) -> dict[str, object]:
    """정규화본과 카테고리별 파생본을 저장한다."""
    policy_root = Path(policy_root)
    normalized_root = policy_root / "normalized"
    by_source_root = normalized_root / "by_source"
    by_category_root = normalized_root / "by_category"

    views = build_policy_views(policies)

    all_path = save_policies_json(views["all_policies"], normalized_root / "all_policies.json")

    source_paths: dict[str, str] = {}
    for source_name, items in views["by_source"].items():
        path = save_policies_json(items, by_source_root / f"{source_name}.json")
        source_paths[source_name] = str(path)

    category_paths: dict[str, str] = {}
    for category, items in views["by_category"].items():
        path = save_policies_json(items, by_category_root / f"{category}.json")
        category_paths[category] = str(path)

    manifest_path = normalized_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(views["manifest"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("정책 manifest 저장: %s", manifest_path)

    return {
        "all_policies_path": str(all_path),
        "by_source_paths": source_paths,
        "by_category_paths": category_paths,
        "manifest_path": str(manifest_path),
        "manifest": views["manifest"],
    }


def rebuild_policy_views_from_raw(
    raw_dir: str | Path,
    policy_root: str | Path = DEFAULT_POLICY_ROOT,
) -> dict[str, object]:
    """raw 디렉토리의 정책 파일들을 읽어 정규화/카테고리별 뷰를 재생성한다."""
    policies = load_policy_records(raw_dir)
    return materialize_policy_views(policies, policy_root)


def _load_policy_file(path: Path) -> list[dict]:
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    data = json.loads(text)

    if isinstance(data, dict) and "policies" in data:
        items = data["policies"]
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    return [item for item in items if isinstance(item, dict)]


def _normalize_policy(policy: dict) -> dict:
    region_codes = [code.strip() for code in str(policy.get("region", "")).split(",") if code.strip()]
    source_name = str(policy.get("source_name", policy.get("source", "unknown")))
    category = str(policy.get("category", "") or "uncategorized")

    normalized = dict(policy)
    normalized["source_name"] = source_name
    normalized["category"] = category
    normalized["raw_path"] = str(policy.get("raw_path", f"{source_name}/latest.json"))
    normalized["region_codes"] = region_codes
    normalized["scope"] = "regional" if region_codes else "national"
    return normalized


def _dedupe_policies(policies: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for policy in policies:
        policy_id = str(policy.get("policy_id", "")).strip()
        if not policy_id:
            continue
        current = by_id.get(policy_id)
        if current is None or _policy_score(policy) >= _policy_score(current):
            by_id[policy_id] = policy
    return sorted(by_id.values(), key=lambda policy: policy.get("policy_id", ""))


def _policy_score(policy: dict) -> int:
    fields = (
        "summary",
        "description",
        "eligibility",
        "benefits",
        "how_to_apply",
        "application_period",
        "raw_content",
    )
    return sum(1 for field in fields if str(policy.get(field, "")).strip())

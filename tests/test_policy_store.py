from __future__ import annotations

import json
from pathlib import Path

from src.ingestion.policy_store import (
    build_policy_views,
    load_policy_records,
    materialize_policy_views,
    rebuild_policy_views_from_raw,
)


def _make_policy(
    policy_id: str,
    *,
    category: str = "housing",
    source_name: str = "data_portal",
    region: str = "",
    summary: str = "요약",
) -> dict:
    return {
        "policy_id": policy_id,
        "title": f"정책 {policy_id}",
        "category": category,
        "summary": summary,
        "description": "설명",
        "eligibility": "자격",
        "benefits": "혜택",
        "how_to_apply": "신청",
        "application_period": "상시",
        "raw_content": "원문",
        "source_name": source_name,
        "region": region,
    }


def test_build_policy_views_groups_by_source_and_category() -> None:
    views = build_policy_views(
        [
            _make_policy("P1", category="housing", source_name="data_portal"),
            _make_policy("P2", category="employment", source_name="youthgo", region="29110,29140"),
        ]
    )

    assert len(views["all_policies"]) == 2
    assert set(views["by_source"]) == {"data_portal", "youthgo"}
    assert set(views["by_category"]) == {"housing", "employment"}
    assert views["all_policies"][1]["scope"] == "regional"
    assert views["all_policies"][1]["region_codes"] == ["29110", "29140"]
    assert views["all_policies"][0]["raw_path"] == "data_portal/latest.json"


def test_materialize_policy_views_writes_expected_files(tmp_path: Path) -> None:
    result = materialize_policy_views(
        [
            _make_policy("P1", category="housing"),
            _make_policy("P2", category="employment"),
        ],
        tmp_path,
    )

    assert Path(result["all_policies_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    assert Path(result["by_source_paths"]["data_portal"]).exists()
    assert Path(result["by_category_paths"]["housing"]).exists()


def test_rebuild_policy_views_from_raw_reads_raw_directory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    policies = [_make_policy("P1"), _make_policy("P2", category="employment")]
    (raw_dir / "data_portal_policies.json").write_text(json.dumps(policies, ensure_ascii=False), encoding="utf-8")

    result = rebuild_policy_views_from_raw(raw_dir, tmp_path)

    all_policies = json.loads(Path(result["all_policies_path"]).read_text(encoding="utf-8"))
    assert len(all_policies) == 2
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["categories"]["housing"] == 1
    assert manifest["categories"]["employment"] == 1


def test_load_policy_records_supports_directory(tmp_path: Path) -> None:
    root = tmp_path / "normalized"
    root.mkdir()
    (root / "housing.json").write_text(json.dumps([_make_policy("P1")], ensure_ascii=False), encoding="utf-8")
    subdir = root / "by_category"
    subdir.mkdir()
    (subdir / "employment.json").write_text(
        json.dumps([_make_policy("P2", category="employment")], ensure_ascii=False),
        encoding="utf-8",
    )

    records = load_policy_records(root)
    assert {record["policy_id"] for record in records} == {"P1", "P2"}

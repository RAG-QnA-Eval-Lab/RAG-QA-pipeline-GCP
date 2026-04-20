"""수집기 테스트 — TDD RED → GREEN."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.collectors.base import (
    VALID_CATEGORIES,
    Policy,
    normalize_category,
    parse_age,
    validate_policy,
)

# ── base.py 유닛 테스트 ──────────────────────────────────────────────────


class TestPolicy:
    def test_frozen(self, sample_policy: Policy) -> None:
        with pytest.raises(AttributeError):
            sample_policy.title = "변경 불가"  # type: ignore[misc]

    def test_required_fields(self, sample_policy: Policy) -> None:
        assert sample_policy.policy_id == "R2025010112345"
        assert sample_policy.title == "청년 월세 한시 특별지원"
        assert sample_policy.category == "housing"
        assert sample_policy.source_name == "data_portal"

    def test_target_age_tuple(self, sample_policy: Policy) -> None:
        assert sample_policy.target_age == (19, 34)
        assert isinstance(sample_policy.target_age, tuple)


class TestValidatePolicy:
    def test_valid_policy(self, sample_policy: Policy) -> None:
        assert validate_policy(sample_policy) == []

    def test_empty_policy_id(self, sample_policy: Policy) -> None:
        from dataclasses import replace

        bad = replace(sample_policy, policy_id="")
        errors = validate_policy(bad)
        assert any("policy_id" in e for e in errors)

    def test_empty_title(self, sample_policy: Policy) -> None:
        from dataclasses import replace

        bad = replace(sample_policy, title="")
        errors = validate_policy(bad)
        assert any("title" in e for e in errors)

    def test_invalid_category(self, sample_policy: Policy) -> None:
        from dataclasses import replace

        bad = replace(sample_policy, category="존재하지않는카테고리")
        errors = validate_policy(bad)
        assert any("카테고리" in e for e in errors)

    def test_valid_categories(self) -> None:
        expected = {"housing", "employment", "startup", "education", "welfare", "finance", "participation"}
        assert VALID_CATEGORIES == expected


class TestNormalizeCategory:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("일자리", "employment"),
            ("주거", "housing"),
            ("교육", "education"),
            ("창업", "startup"),
            ("금융･복지･문화", "welfare"),
            ("참여·권리", "participation"),
        ],
    )
    def test_korean_to_english(self, raw: str, expected: str) -> None:
        assert normalize_category(raw) == expected

    def test_already_english(self) -> None:
        assert normalize_category("housing") == "housing"

    def test_empty_default(self) -> None:
        assert normalize_category("") == "welfare"

    def test_unknown_default(self) -> None:
        assert normalize_category("알수없음") == "welfare"


class TestParseAge:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("19", 19),
            ("34", 34),
            (0, 0),
            (19, 19),
            ("99999", 100),
            ("0", 0),
            ("abc", 0),
            ("", 0),
            (None, 0),
        ],
    )
    def test_parse(self, raw: str | int | None, expected: int) -> None:
        assert parse_age(raw) == expected


# ── DataPortalCollector 테스트 ───────────────────────────────────────────


def _make_api_response(items: list[dict], total: int = 2185, page: int = 1, page_size: int = 100) -> dict:
    """API 응답 mock 생성 헬퍼."""
    return {
        "resultCode": 200,
        "resultMessage": "success",
        "result": {
            "pagging": {"totCount": total, "pageNum": page, "pageSize": page_size},
            "youthPolicyList": items,
        },
    }


def _make_policy_item(plcy_no: str = "R2025010112345", title: str = "테스트 정책", category: str = "주거") -> dict:
    """API 단건 응답 mock."""
    return {
        "plcyNo": plcy_no,
        "plcyNm": title,
        "lclsfNm": category,
        "mclsfNm": "세부분류",
        "plcyExplnCn": "정책 설명",
        "plcySprtCn": "지원 내용",
        "sprvsnInstCdNm": "국토교통부",
        "operInstCdNm": "LH",
        "sprtTrgtMinAge": "19",
        "sprtTrgtMaxAge": "34",
        "bizPrdBgngYmd": "2025-01-01",
        "bizPrdEndYmd": "2025-12-31",
        "aplyUrlAddr": "https://example.com/apply",
        "refUrlAddr1": "https://example.com/ref",
        "zipCd": "서울",
        "plcyAplyMthdCn": "온라인",
        "addAplyQlfcCndCn": "무주택",
        "srngMthdCn": "",
        "sbmssnDcmntCn": "",
        "etcMttrCn": "",
    }


class TestDataPortalCollector:
    def _make_mock_response(self, json_data: dict, status_code: int = 200) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        mock_resp.text = json.dumps(json_data, ensure_ascii=False)
        return mock_resp

    def test_collect_returns_policy_list(self, sample_api_response: dict) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        api_resp = _make_api_response([sample_api_response], total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._make_mock_response(api_resp)

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            result = collector.collect(max_items=1)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Policy)

    def test_field_mapping(self, sample_api_response: dict) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        api_resp = _make_api_response([sample_api_response], total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._make_mock_response(api_resp)

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect(max_items=1)

        p = policies[0]
        assert p.policy_id == "R2025010112345"
        assert p.title == "청년 월세 한시 특별지원"
        assert p.category == "housing"
        assert p.managing_department == "국토교통부"
        assert p.target_age == (19, 34)
        assert p.region == "서울"

    def test_category_normalization(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        item = _make_policy_item(category="일자리")
        api_resp = _make_api_response([item], total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=api_resp))

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect(max_items=1)

        assert policies[0].category == "employment"

    def test_pagination(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        page1_items = [_make_policy_item(f"P{i}", f"정책{i}") for i in range(3)]
        page2_items = [_make_policy_item(f"P{i}", f"정책{i}") for i in range(3, 5)]

        page1_resp = _make_api_response(page1_items, total=5, page=1, page_size=3)
        page2_resp = _make_api_response(page2_items, total=5, page=2, page_size=3)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=page1_resp)),
            MagicMock(status_code=200, json=MagicMock(return_value=page2_resp)),
        ]

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key", page_size=3)
            policies = collector.collect()

        assert len(policies) == 5
        assert mock_client.get.call_count == 2

    def test_max_items_limits_results(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        items = [_make_policy_item(f"P{i}", f"정책{i}") for i in range(10)]
        api_resp = _make_api_response(items, total=100)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=api_resp))

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect(max_items=5)

        assert len(policies) == 5

    def test_api_error_returns_empty(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        error_resp = {"resultCode": 500, "resultMessage": "Internal Server Error", "result": {}}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=error_resp))

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect()

        assert policies == []

    def test_http_error_returns_empty(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=500, text="Server Error")

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect()

        assert policies == []

    def test_empty_result_list(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        api_resp = _make_api_response([], total=0)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=api_resp))

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect()

        assert policies == []

    def test_raw_content_populated(self, sample_api_response: dict) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        api_resp = _make_api_response([sample_api_response], total=1)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=api_resp))

        with patch("httpx.Client", return_value=mock_client):
            collector = DataPortalCollector(api_key="test-key")
            policies = collector.collect(max_items=1)

        assert "청년 월세 한시 특별지원" in policies[0].raw_content
        assert "월 최대 20만원" in policies[0].raw_content

    def test_source_name(self) -> None:
        from src.ingestion.collectors.data_portal import DataPortalCollector

        collector = DataPortalCollector(api_key="test-key")
        assert collector.source_name == "data_portal"

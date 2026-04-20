"""공유 pytest fixtures."""

from __future__ import annotations

import pytest

from src.ingestion.collectors.base import Policy


@pytest.fixture()
def sample_api_response() -> dict:
    """공공데이터포털 API 단건 응답 샘플."""
    return {
        "plcyNo": "R2025010112345",
        "plcyNm": "청년 월세 한시 특별지원",
        "lclsfNm": "주거",
        "mclsfNm": "월세지원",
        "plcyExplnCn": "청년 월세 부담 완화를 위한 한시적 특별지원 사업",
        "plcySprtCn": "월 최대 20만원, 최대 12개월 지원",
        "sprvsnInstCdNm": "국토교통부",
        "operInstCdNm": "한국토지주택공사",
        "sprtTrgtMinAge": "19",
        "sprtTrgtMaxAge": "34",
        "bizPrdBgngYmd": "2025-01-01",
        "bizPrdEndYmd": "2025-12-31",
        "aplyUrlAddr": "https://www.myhome.go.kr",
        "refUrlAddr1": "https://www.youthcenter.go.kr/youthPolicy/policyDetail",
        "zipCd": "서울",
        "plcyAplyMthdCn": "온라인 신청",
        "addAplyQlfcCndCn": "무주택 청년",
        "srngMthdCn": "",
        "sbmssnDcmntCn": "",
        "etcMttrCn": "",
    }


@pytest.fixture()
def sample_api_page_response(sample_api_response: dict) -> dict:
    """API 페이지 응답 전체 (pagging + youthPolicyList 포함)."""
    return {
        "resultCode": 200,
        "resultMessage": "success",
        "result": {
            "pagging": {"totCount": 2185, "pageNum": 1, "pageSize": 10},
            "youthPolicyList": [sample_api_response],
        },
    }


@pytest.fixture()
def sample_policy() -> Policy:
    """유효한 Policy 인스턴스."""
    return Policy(
        policy_id="R2025010112345",
        title="청년 월세 한시 특별지원",
        category="housing",
        summary="청년 월세 부담 완화를 위한 한시적 특별지원 사업",
        description="청년 월세 부담 완화를 위한 한시적 특별지원 사업",
        eligibility="무주택 청년",
        benefits="월 최대 20만원, 최대 12개월 지원",
        how_to_apply="온라인 신청",
        application_period="2025-01-01 ~ 2025-12-31",
        managing_department="국토교통부",
        target_age=(19, 34),
        region="서울",
        source_url="https://www.youthcenter.go.kr/youthPolicy/policyDetail",
        source_name="data_portal",
        last_updated="2025-01-01",
        raw_content="정책명: 청년 월세 한시 특별지원\n요약: 청년 월세 부담 완화",
    )


@pytest.fixture()
def sample_policies(sample_policy: Policy) -> list[Policy]:
    """테스트용 Policy 리스트 (3건)."""
    from dataclasses import replace

    return [
        sample_policy,
        replace(sample_policy, policy_id="R2025010112346", title="청년 전세자금 대출", category="housing"),
        replace(sample_policy, policy_id="R2025010112347", title="국민취업지원제도", category="employment"),
    ]
